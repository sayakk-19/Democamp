import json
from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from PayTm import Checksum
from .models import Orders, OrderUpdate, Product
from .payments import compact_json


@override_settings(DEBUG=True, PAYTM_MODE='demo', PUBLIC_BASE_URL='')
class DemoPaymentTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(product_name='Football', price=500, quantity=10, category='Sports', desc='Test product', pub_date=date(2026, 11, 1))
        self.data = {'itemsJson': json.dumps({'pr' + str(self.product.pk): [2, 'forged name', 1]}), 'amount': '2',
                     'name': 'Test Player', 'email': 'buyer@example.test', 'address1': 'Test Road', 'address2': '',
                     'city': 'Test City', 'state': 'Test State', 'zip_code': '700001', 'phone': '1234567890'}

    def checkout(self, client=None, **overrides):
        return (client or self.client).post(reverse('Checkout'), {**self.data, **overrides}, HTTP_HOST='localhost:8000')

    def test_demo_uses_server_prices_and_never_contacts_paytm(self):
        with patch('shop.payments.urlopen') as network:
            response = self.checkout()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LOCAL DEMO')
        self.assertContains(response, 'LOCAL_DEMO_MERCHANT')
        order = Orders.objects.get()
        self.assertEqual(order.amount, 1000)
        self.assertEqual(json.loads(order.items_json)['pr' + str(self.product.pk)], [2, 'Football', 500])
        self.assertEqual(order.payment_state, 'demo_pending')
        network.assert_not_called()

    def test_all_three_demo_outcomes_are_separate_from_real_payments(self):
        for outcome, expected in [('success', 'demo_paid'), ('failure', 'demo_failed'), ('pending', 'demo_pending')]:
            response = self.checkout()
            token = response.context['demo_token']
            order = response.context['order']
            result = self.client.post(reverse('PaytmDemoPayment'), {'demo_token': token, 'outcome': outcome}, HTTP_HOST='localhost:8000')
            self.assertEqual(result.status_code, 200)
            self.assertContains(result, 'No real money was charged')
            order.refresh_from_db()
            self.assertEqual(order.payment_state, expected)
            self.assertNotEqual(order.payment_state, 'paid')

    def test_demo_success_is_idempotent_and_cannot_be_downgraded(self):
        token = self.checkout().context['demo_token']
        payload = {'demo_token': token, 'outcome': 'success'}
        self.client.post(reverse('PaytmDemoPayment'), payload, HTTP_HOST='localhost:8000')
        count = OrderUpdate.objects.count()
        self.client.post(reverse('PaytmDemoPayment'), payload, HTTP_HOST='localhost:8000')
        self.client.post(reverse('PaytmDemoPayment'), {**payload, 'outcome': 'failure'}, HTTP_HOST='localhost:8000')
        self.assertEqual(OrderUpdate.objects.count(), count)
        self.assertEqual(Orders.objects.get().payment_state, 'demo_paid')

    def test_demo_rejects_tampering_and_other_sessions(self):
        token = self.checkout().context['demo_token']
        for client, value in [(self.client, token + 'x'), (Client(), token)]:
            response = client.post(reverse('PaytmDemoPayment'), {'demo_token': value, 'outcome': 'success'}, HTTP_HOST='localhost:8000')
            self.assertEqual(response.status_code, 400)
        self.assertEqual(Orders.objects.get().payment_state, 'demo_pending')

    def test_demo_requires_post_csrf_and_local_debug(self):
        self.assertEqual(self.client.get(reverse('PaytmDemoPayment'), HTTP_HOST='localhost:8000').status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        self.assertEqual(protected.post(reverse('PaytmDemoPayment'), {}, HTTP_HOST='localhost:8000').status_code, 403)
        response = self.client.post(reverse('Checkout'), self.data, HTTP_HOST='localhost:8000', REMOTE_ADDR='203.0.113.5')
        self.assertEqual(response.status_code, 400)
        with self.settings(DEBUG=False):
            self.assertEqual(self.checkout().status_code, 400)
        self.assertFalse(Orders.objects.exists())

    def test_invalid_cart_stock_and_shipping_do_not_create_orders(self):
        invalid = ['{}', '[]', 'not json', json.dumps({'pr1': [True]}), json.dumps({'bad': [1]}), json.dumps({'pr99999': [1]}), json.dumps({'pr' + '9' * 5000: [1]}), json.dumps({'pr' + str(self.product.pk): [11]})]
        for cart in invalid:
            self.assertEqual(self.checkout(itemsJson=cart).status_code, 400)
        self.assertEqual(self.checkout(email='invalid').status_code, 400)
        self.assertFalse(Orders.objects.exists())

    def test_forged_gateway_success_is_not_accepted_in_demo(self):
        self.checkout()
        response = self.client.post(reverse('HandleRequest'), {'RESPCODE': '01', 'STATUS': 'TXN_SUCCESS'}, HTTP_HOST='localhost:8000')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.context['payment_success'])
        self.assertEqual(Orders.objects.get().payment_state, 'demo_pending')

    @override_settings(PAYTM_MODE='staging', PAYTM_MID='', PAYTM_MERCHANT_KEY='', MID='', MERCHANT_KEY='')
    def test_missing_real_credentials_fail_cleanly(self):
        response = self.checkout()
        self.assertContains(response, 'credentials are not configured', status_code=400)
        self.assertFalse(Orders.objects.exists())


@override_settings(DEBUG=True, PAYTM_MODE='staging', PAYTM_MID='TEST_MERCHANT', PAYTM_MERCHANT_KEY='0123456789abcdef',
                   PAYTM_CALLBACK_URL='https://club.example.test/shop/handlerequest/', PAYTM_WEBSITE_NAME='WEBSTAGING')
class VerifiedPaytmTests(TestCase):
    def setUp(self):
        self.key = '0123456789abcdef'
        self.order = Orders.objects.create(items_json='{}', amount=500, name='Test', email='buyer@example.test', address='Test',
                                           city='Test', state='Test', zip_code='700001', phone='1234567890', payment_mode='staging',
                                           payment_state='pending', paytm_order_id='FC_1_TEST')

    def callback_data(self, **updates):
        data = {'MID': 'TEST_MERCHANT', 'ORDERID': self.order.paytm_order_id, 'TXNAMOUNT': '500.00', 'RESPCODE': '01', 'STATUS': 'TXN_SUCCESS'}
        data.update(updates)
        data['CHECKSUMHASH'] = Checksum.generate_checksum(data.copy(), self.key)
        return data

    def status(self, **updates):
        body = {'mid': 'TEST_MERCHANT', 'orderId': self.order.paytm_order_id, 'txnAmount': '500.00', 'txnId': 'TEST_TRANSACTION',
                'txnType': 'SALE', 'resultInfo': {'resultStatus': 'TXN_SUCCESS'}}
        body.update(updates)
        return body

    def test_unsigned_or_bad_checksum_cannot_display_success(self):
        for data in [{'RESPCODE': '01'}, {**self.callback_data(), 'CHECKSUMHASH': 'forged'}]:
            with patch('shop.payments.paytm_request') as network:
                response = self.client.post(reverse('HandleRequest'), data)
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.context['payment_success'])
            network.assert_not_called()
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_state, 'pending')

    def test_success_requires_authoritative_status_and_is_idempotent(self):
        with patch('shop.payments.paytm_request', return_value=self.status()) as network:
            response = self.client.post(reverse('HandleRequest'), self.callback_data())
            count = OrderUpdate.objects.count()
            self.client.post(reverse('HandleRequest'), self.callback_data())
        self.assertTrue(response.context['payment_success'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_state, 'paid')
        self.assertEqual(self.order.paytm_transaction_id, 'TEST_TRANSACTION')
        self.assertEqual(OrderUpdate.objects.count(), count)
        self.assertEqual(network.call_args.args[1], '/v3/order/status')

    def test_mismatched_amount_order_merchant_or_missing_transaction_is_rejected(self):
        for updates in [{'txnAmount': '1.00'}, {'orderId': 'OTHER'}, {'mid': 'OTHER'}, {'txnId': ''}, {'txnType': 'PREAUTH'}]:
            with patch('shop.payments.paytm_request', return_value=self.status(**updates)):
                response = self.client.post(reverse('HandleRequest'), self.callback_data())
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.context['payment_success'])
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_state, 'pending')

    def test_pending_and_failure_never_become_success(self):
        for status, state in [('PENDING', 'pending'), ('TXN_FAILURE', 'failed')]:
            with patch('shop.payments.paytm_request', return_value=self.status(resultInfo={'resultStatus': status})):
                response = self.client.post(reverse('HandleRequest'), self.callback_data())
            self.assertFalse(response.context['payment_success'])
            self.order.refresh_from_db()
            self.assertEqual(self.order.payment_state, state)

    def test_tampered_status_api_signature_is_rejected(self):
        result = {'head': {'signature': 'forged'}, 'body': self.status()}
        fake = BytesIO(json.dumps(result).encode())
        with patch('shop.payments.urlopen', return_value=fake):
            response = self.client.post(reverse('HandleRequest'), self.callback_data())
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.context['payment_success'])

    def test_signed_status_api_response_is_accepted(self):
        body = self.status()
        result = {'head': {'signature': Checksum.generate_checksum_by_str(compact_json(body), self.key)}, 'body': body}
        with patch('shop.payments.urlopen', return_value=BytesIO(json.dumps(result).encode())) as network:
            response = self.client.post(reverse('HandleRequest'), self.callback_data())
        self.assertTrue(response.context['payment_success'])
        self.assertTrue(network.call_args.args[0].full_url.startswith('https://securestage.paytmpayments.com/'))

    def test_initiate_uses_current_gateway_config_and_server_amount(self):
        product = Product.objects.create(product_name='Football', price=500, quantity=2, category='Sports', desc='Test', pub_date=date(2026, 11, 1))
        body = {'resultInfo': {'resultStatus': 'S'}, 'txnToken': 'TEST_TOKEN'}
        result = {'head': {'signature': Checksum.generate_checksum_by_str(compact_json(body), self.key)}, 'body': body}
        data = {'itemsJson': json.dumps({'pr' + str(product.pk): [1, 'tampered', 1]}), 'amount': '1', 'name': 'Buyer',
                'email': 'buyer@example.test', 'address1': 'Road', 'city': 'City', 'state': 'State', 'zip_code': '700001', 'phone': '1234567890'}
        with patch('shop.payments.urlopen', return_value=BytesIO(json.dumps(result).encode())) as network:
            response = self.client.post(reverse('Checkout'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['amount'], '500.00')
        self.assertEqual(response.context['paytm_config']['data']['token'], 'TEST_TOKEN')
        sent = json.loads(network.call_args.args[0].data)
        self.assertEqual(sent['body']['mid'], 'TEST_MERCHANT')
        self.assertEqual(sent['body']['txnAmount'], {'value': '500.00', 'currency': 'INR'})
        self.assertTrue(Checksum.verify_checksum_by_str(compact_json(sent['body']), self.key, sent['head']['signature']))

    @override_settings(PAYTM_CALLBACK_URL='http://127.0.0.1:8000/shop/handlerequest/')
    def test_real_gateway_requires_https_callback(self):
        from django.test import RequestFactory
        from .payments import PaymentError, payment_config
        with self.assertRaises(PaymentError):
            payment_config(RequestFactory().get('/shop/checkout/'))
