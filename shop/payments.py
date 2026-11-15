"""Local payment simulation and verified Paytm checkout for the existing shop."""

import json
import os
import re
import secrets
from ipaddress import ip_address
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from django import forms
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from PayTm import Checksum
from .models import Orders, OrderUpdate, Product


class PaymentError(Exception):
    pass


def config_value(name, default=''):
    value = getattr(settings, name, None)
    return value if value is not None else os.environ.get(name, default)


def local_demo_allowed(request):
    host = urlsplit('//' + request.get_host()).hostname
    try:
        loopback = ip_address(request.META.get('REMOTE_ADDR', '')).is_loopback
    except ValueError:
        loopback = False
    return bool(settings.DEBUG) and loopback and host in ('localhost', '127.0.0.1', '::1')


def payment_config(request):
    mode = config_value('PAYTM_MODE', 'demo' if local_demo_allowed(request) else 'staging').lower()
    if mode not in ('demo', 'staging', 'production'):
        raise PaymentError('PAYTM_MODE must be demo, staging, or production.')
    if mode == 'demo':
        if not local_demo_allowed(request):
            raise PaymentError('Demo payments are available only on localhost with Django DEBUG enabled.')
        return {'mode': 'demo', 'mid': 'LOCAL_DEMO_MERCHANT'}
    mid = config_value('PAYTM_MID') or config_value('MID')
    key = config_value('PAYTM_MERCHANT_KEY') or config_value('MERCHANT_KEY')
    if not mid or mid == 'MID' or not key:
        raise PaymentError('Paytm test or production credentials are not configured. Local development can use demo mode without credentials.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', str(mid)) or len(key.encode()) not in (16, 24, 32):
        raise PaymentError('The Paytm merchant configuration is invalid. Check the values privately in your merchant dashboard.')
    base = 'https://secure.paytmpayments.com' if mode == 'production' else 'https://securestage.paytmpayments.com'
    callback = config_value('PAYTM_CALLBACK_URL')
    if not callback:
        origin = config_value('PUBLIC_BASE_URL').rstrip('/')
        callback = origin + reverse('HandleRequest') if origin else request.build_absolute_uri(reverse('HandleRequest'))
    parsed = urlsplit(callback)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise PaymentError('Real Paytm checkout needs a reachable HTTPS callback URL. Use demo mode for localhost-only development.')
    return {'mode': mode, 'mid': mid, 'key': key, 'base': base, 'callback': callback,
            'website': config_value('PAYTM_WEBSITE_NAME', 'DEFAULT' if mode == 'production' else 'WEBSTAGING')}


def compact_json(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


def valid_signature(body, key, signature):
    if not isinstance(signature, str) or not signature or len(signature) > 4096:
        return False
    try:
        return Checksum.verify_checksum_by_str(body, key, signature)
    except (ValueError, TypeError, UnicodeError, IndexError):
        return False


def paytm_request(config, path, body):
    serialized = compact_json(body)
    signature = Checksum.generate_checksum_by_str(serialized, config['key'])
    payload = ('{"body":' + serialized + ',"head":{"signature":' + json.dumps(signature) + '}}').encode()
    request = Request(config['base'] + path, data=payload, headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read(1_048_577))
    except (OSError, ValueError) as error:
        raise PaymentError('Paytm could not be reached. No payment has been confirmed; please try again.') from error
    if not isinstance(result, dict) or not isinstance(result.get('body'), dict) or not isinstance(result.get('head'), dict):
        raise PaymentError('Paytm returned an invalid payment response.')
    if not valid_signature(compact_json(result['body']), config['key'], result['head'].get('signature')):
        raise PaymentError('The Paytm response signature could not be verified. No payment has been confirmed.')
    return result['body']


def validated_cart(raw_cart):
    try:
        cart = json.loads(raw_cart)
    except (TypeError, ValueError) as error:
        raise PaymentError('Your cart could not be read. Please return to the shop and add your items again.') from error
    if not isinstance(cart, dict) or not 1 <= len(cart) <= 100:
        raise PaymentError('Add at least one product before checking out.')
    quantities = {}
    for key, item in cart.items():
        match = re.fullmatch(r'pr([1-9][0-9]*)', key)
        if not match or len(key) > 64 or not isinstance(item, list) or not item:
            raise PaymentError('Your cart contains an invalid product.')
        quantity = item[0]
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 999:
            raise PaymentError('Choose a valid quantity for each cart item.')
        quantities[int(match.group(1))] = quantity
    products = Product.objects.in_bulk(quantities)
    if len(products) != len(quantities):
        raise PaymentError('A product in your cart is no longer available.')
    canonical = {}
    total = 0
    for product_id, quantity in quantities.items():
        product = products[product_id]
        if product.price <= 0 or quantity > product.quantity:
            raise PaymentError('Please review the available stock and price for ' + product.product_name + '.')
        canonical['pr' + str(product_id)] = [quantity, product.product_name, product.price]
        total += quantity * product.price
    if total > 999_999_999:
        raise PaymentError('This cart exceeds the supported order total.')
    return canonical, total


class CheckoutForm(forms.Form):
    name = forms.CharField(max_length=90)
    email = forms.EmailField(max_length=111)
    address1 = forms.CharField(max_length=111)
    address2 = forms.CharField(max_length=111, required=False)
    city = forms.CharField(max_length=111)
    state = forms.CharField(max_length=111)
    zip_code = forms.CharField(max_length=111)
    phone = forms.CharField(max_length=111)

    def clean(self):
        data = super().clean()
        if len((data.get('address1', '') + ' ' + data.get('address2', '')).strip()) > 111:
            raise forms.ValidationError('The combined address must not exceed 111 characters.')
        return data


def payment_result(request, order=None, *, verified=False, message='', error_status=200):
    demo = bool(order and order.payment_mode == 'demo')
    successful = bool(order and ((demo and order.payment_state == 'demo_paid') or (verified and order.payment_state == 'paid')))
    context = {'response': {'ORDERID': order.order_id if order else '', 'RESPMSG': message},
               'payment_success': successful, 'payment_pending': bool(order and order.payment_state in ('pending', 'demo_pending')),
               'is_demo': demo, 'order': order, 'payment_message': message}
    return render(request, 'shop/paymentstatus.html', context, status=error_status)


@require_http_methods(['GET', 'POST'])
def checkout(request):
    if request.method == 'GET':
        return render(request, 'shop/checkout.html')
    form = CheckoutForm(request.POST)
    if not form.is_valid():
        errors = ['{}: {}'.format(form.fields[field].label or field.replace('_', ' ').title(), ' '.join(items))
                  if field in form.fields else ' '.join(items) for field, items in form.errors.items()]
        return render(request, 'shop/checkout.html', {'checkout_errors': errors}, status=400)
    try:
        config = payment_config(request)
        cart, total = validated_cart(request.POST.get('itemsJson', ''))
    except PaymentError as error:
        return render(request, 'shop/checkout.html', {'checkout_errors': [str(error)]}, status=400)
    data = form.cleaned_data
    with transaction.atomic():
        order = Orders.objects.create(items_json=compact_json(cart), amount=total, name=data['name'], email=data['email'],
                                      address=(data['address1'] + ' ' + data['address2']).strip(), city=data['city'],
                                      state=data['state'], zip_code=data['zip_code'], phone=data['phone'],
                                      payment_mode=config['mode'], payment_state='demo_pending' if config['mode'] == 'demo' else 'pending')
        order.paytm_order_id = 'FC_' + str(order.order_id) + '_' + secrets.token_hex(8)
        order.save(update_fields=['paytm_order_id'])
        OrderUpdate.objects.create(order_id=order.order_id, update_desc='Order placed; payment is pending.' if config['mode'] != 'demo' else 'Demo order placed; no money has been charged.')
    amount = format(Decimal(total), '.2f')
    if config['mode'] == 'demo':
        nonce = request.session.get('paytm_demo_nonce') or secrets.token_urlsafe(24)
        request.session['paytm_demo_nonce'] = nonce
        token = signing.dumps({'order_id': order.order_id, 'nonce': nonce}, salt='shop.paytm.demo')
        return render(request, 'shop/paytm_demo.html', {'order': order, 'amount': amount, 'demo_token': token, 'demo_merchant': config['mid']})
    body = {'requestType': 'Payment', 'mid': config['mid'], 'websiteName': config['website'],
            'orderId': order.paytm_order_id, 'callbackUrl': config['callback'],
            'txnAmount': {'value': amount, 'currency': 'INR'},
            'userInfo': {'custId': 'ORDER_' + str(order.order_id), 'email': order.email}}
    query = urlencode({'mid': config['mid'], 'orderId': order.paytm_order_id})
    try:
        result = paytm_request(config, '/theia/api/v1/initiateTransaction?' + query, body)
        token = result.get('txnToken')
        info = result.get('resultInfo')
        if not isinstance(info, dict) or info.get('resultStatus') != 'S' or not isinstance(token, str) or not token:
            raise PaymentError('Paytm could not start this payment. Check the merchant environment and try again.')
    except PaymentError as error:
        return payment_result(request, order, message=str(error), error_status=502)
    return render(request, 'shop/paytm.html', {
        'order': order, 'amount': amount,
        'paytm_script_url': config['base'] + '/merchantpgpui/checkoutjs/merchants/' + quote(config['mid'], safe='') + '.js',
        'paytm_config': {'root': '', 'flow': 'DEFAULT', 'data': {'orderId': order.paytm_order_id, 'token': token, 'tokenType': 'TXN_TOKEN', 'amount': amount},
                         'merchant': {'redirect': True}},
    })


@require_POST
def demo_payment(request):
    if not local_demo_allowed(request):
        return HttpResponseForbidden('Demo payments are restricted to local development.')
    try:
        if payment_config(request)['mode'] != 'demo':
            raise PaymentError('Demo mode is not active.')
        data = signing.loads(request.POST.get('demo_token', ''), salt='shop.paytm.demo', max_age=1800)
        if not isinstance(data, dict):
            raise PaymentError('The demo payment request is invalid.')
        nonce = request.session.get('paytm_demo_nonce', '')
        if not nonce or not secrets.compare_digest(str(data.get('nonce', '')), nonce):
            raise PaymentError('The demo payment belongs to a different session.')
        outcome = request.POST.get('outcome')
        states = {'success': 'demo_paid', 'failure': 'demo_failed', 'pending': 'demo_pending'}
        if outcome not in states:
            raise PaymentError('Choose a valid demo outcome.')
        with transaction.atomic():
            order = Orders.objects.select_for_update().get(pk=data['order_id'], payment_mode='demo')
            if order.payment_state != 'demo_paid' and order.payment_state != states[outcome]:
                order.payment_state = states[outcome]
                order.save(update_fields=['payment_state'])
                OrderUpdate.objects.create(order_id=order.order_id, update_desc='Demo payment ' + outcome + '; no real money was charged.')
    except (PaymentError, signing.BadSignature, KeyError, TypeError, ValueError, Orders.DoesNotExist) as error:
        return payment_result(request, message='The demo payment request is invalid or expired. Please start checkout again.', error_status=400)
    return payment_result(request, order, message='Local simulation only. No real money was charged.')


@csrf_exempt
@require_POST
def handlerequest(request):
    try:
        config = payment_config(request)
        if config['mode'] == 'demo':
            raise PaymentError('Gateway callbacks are not used in local demo mode.')
        values = request.POST.dict()
        signature = values.pop('CHECKSUMHASH', '')
        serialized = '|'.join('' if values[key] == 'null' else str(values[key]) for key in sorted(values))
        if not valid_signature(serialized, config['key'], signature):
            raise PaymentError('Payment verification failed. No successful payment has been recorded.')
        if values.get('MID') != config['mid']:
            raise PaymentError('The payment merchant did not match this shop.')
        order = Orders.objects.get(paytm_order_id=values.get('ORDERID'), payment_mode=config['mode'])
        result = paytm_request(config, '/v3/order/status', {'mid': config['mid'], 'orderId': order.paytm_order_id})
        info = result.get('resultInfo')
        status = info.get('resultStatus') if isinstance(info, dict) else None
        if status not in ('TXN_SUCCESS', 'TXN_FAILURE', 'PENDING'):
            raise PaymentError('Paytm has not confirmed a final payment status. Please contact the shop with your order ID.')
        if (result.get('mid') != config['mid'] or result.get('orderId') != order.paytm_order_id
                or Decimal(str(result.get('txnAmount'))) != Decimal(order.amount)
                or result.get('txnType', 'SALE') != 'SALE'):
            raise PaymentError('The payment amount or order reference did not match this order.')
        if status == 'TXN_SUCCESS' and not result.get('txnId'):
            raise PaymentError('Paytm did not return a transaction reference.')
        state = {'TXN_SUCCESS': 'paid', 'TXN_FAILURE': 'failed', 'PENDING': 'pending'}[status]
        with transaction.atomic():
            order = Orders.objects.select_for_update().get(pk=order.pk)
            if order.payment_state != 'paid' and order.payment_state != state:
                order.payment_state = state
                order.paytm_transaction_id = str(result.get('txnId', ''))[:100]
                order.save(update_fields=['payment_state', 'paytm_transaction_id'])
                OrderUpdate.objects.create(order_id=order.order_id, update_desc='Paytm payment ' + state + '.')
    except (PaymentError, Orders.DoesNotExist, InvalidOperation, TypeError, ValueError) as error:
        message = str(error) if isinstance(error, PaymentError) else 'The payment response could not be verified.'
        return payment_result(request, message=message, error_status=400)
    return payment_result(request, order, verified=True,
                          message='Payment confirmed by Paytm.' if order.payment_state == 'paid' else 'Payment is ' + order.payment_state + '.')
