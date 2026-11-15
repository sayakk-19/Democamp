"""Provider sign-in for the existing club account and approval system."""

import base64
import hashlib
import json
import os
import secrets
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods

from .accounts import start_store_session
from .models import Register, SocialIdentity
from .registration_validation import registration_limits


PROVIDERS = {
    'google': {
        'label': 'Google', 'prefix': 'GOOGLE',
        'authorize': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token': 'https://oauth2.googleapis.com/token',
        'profile': 'https://openidconnect.googleapis.com/v1/userinfo',
        'scope': 'openid email profile',
    },
    'github': {
        'label': 'GitHub', 'prefix': 'GITHUB',
        'authorize': 'https://github.com/login/oauth/authorize',
        'token': 'https://github.com/login/oauth/access_token',
        'profile': 'https://api.github.com/user',
        'scope': 'read:user user:email',
    },
    'x': {
        'label': 'X', 'prefix': 'X',
        'authorize': 'https://x.com/i/oauth2/authorize',
        'token': 'https://api.x.com/2/oauth2/token',
        'profile': 'https://api.x.com/2/users/me?user.fields=confirmed_email',
        'scope': 'tweet.read users.read users.email',
    },
}
ATTEMPT_KEY = 'store_oauth_attempt'
PENDING_KEY = 'store_oauth_pending'
FLOW_MAX_AGE = 600


class SocialLoginError(Exception):
    pass


def configured_value(name, default=''):
    """Read runtime configuration; never load a private file automatically."""
    value = getattr(settings, name, None)
    return value if value is not None else os.environ.get(name, default)


def callback_url(request, provider):
    base = configured_value('PUBLIC_BASE_URL').rstrip('/')
    if base:
        parsed = urlsplit(base)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ('', '/')
                or (parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'))):
            raise SocialLoginError('PUBLIC_BASE_URL must be an HTTPS origin, or localhost for development.')
        return base + reverse('store_social_callback', args=[provider])
    return request.build_absolute_uri(reverse('store_social_callback', args=[provider]))


def provider_credentials(provider):
    if provider not in PROVIDERS:
        raise Http404('Unknown sign-in provider')
    config = PROVIDERS[provider]
    client_id = configured_value(config['prefix'] + '_CLIENT_ID')
    client_secret = configured_value(config['prefix'] + '_CLIENT_SECRET')
    if not client_id or (provider != 'x' and not client_secret):
        raise SocialLoginError(
            config['label'] + ' sign-in is not configured yet. The site owner must add its OAuth credentials privately.'
        )
    return config, client_id, client_secret


def request_json(url, *, data=None, headers=None):
    request_headers = {'Accept': 'application/json', 'User-Agent': 'FootballClub-SignIn'}
    request_headers.update(headers or {})
    if data is not None:
        request_headers['Content-Type'] = 'application/x-www-form-urlencoded'
    request = Request(url, data=urlencode(data).encode() if data is not None else None, headers=request_headers)
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read(1_048_577))
    except (OSError, ValueError) as error:
        raise SocialLoginError('The sign-in provider could not be reached. Please try again.') from error
    if not isinstance(result, (dict, list)):
        raise SocialLoginError('The sign-in provider returned an invalid response.')
    return result


def exchange_identity(provider, attempt, code):
    config, client_id, client_secret = provider_credentials(provider)
    data = {'client_id': client_id, 'code': code, 'redirect_uri': attempt['redirect_uri'],
            'grant_type': 'authorization_code', 'code_verifier': attempt['verifier']}
    headers = {}
    if provider == 'x' and client_secret:
        basic = base64.b64encode((client_id + ':' + client_secret).encode()).decode()
        headers['Authorization'] = 'Basic ' + basic
    elif client_secret:
        data['client_secret'] = client_secret
    token = request_json(config['token'], data=data, headers=headers)
    if not isinstance(token, dict) or not isinstance(token.get('access_token'), str) or not token['access_token']:
        raise SocialLoginError('The provider did not authorize sign-in. Please try again.')
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    profile = request_json(config['profile'], headers=headers)
    if not isinstance(profile, dict):
        raise SocialLoginError('The provider did not return an account profile.')
    email = ''
    if provider == 'google':
        subject = profile.get('sub')
        if profile.get('email_verified') is True:
            email = profile.get('email', '')
        name = profile.get('name', '')
    elif provider == 'github':
        subject = profile.get('id')
        name = profile.get('login', '')
        addresses = request_json('https://api.github.com/user/emails', headers=headers)
        if isinstance(addresses, list):
            verified = [item for item in addresses if isinstance(item, dict) and item.get('verified') is True]
            primary = next((item for item in verified if item.get('primary') is True), None)
            if primary or verified:
                email = (primary or verified[0]).get('email', '')
    else:
        profile = profile.get('data', {})
        if not isinstance(profile, dict):
            raise SocialLoginError('X did not return an account profile.')
        subject = profile.get('id')
        name = profile.get('username', '')
        email = profile.get('confirmed_email', '')
    if not isinstance(subject, (str, int)) or isinstance(subject, bool) or not 1 <= len(str(subject)) <= 255:
        raise SocialLoginError('The provider did not return a stable account identifier.')
    return {'provider': provider, 'subject': str(subject), 'name': str(name)[:50],
            'email': email if isinstance(email, str) else '', 'created_at': time.time()}


def fresh_flow(value):
    try:
        age = time.time() - float(value['created_at'])
        return 0 <= age <= FLOW_MAX_AGE
    except (KeyError, TypeError, ValueError):
        return False


@require_GET
def social_start(request, provider):
    try:
        config, client_id, _ = provider_credentials(provider)
        uri = callback_url(request, provider)
    except SocialLoginError as error:
        messages.error(request, str(error))
        return redirect('store_login')
    verifier = secrets.token_urlsafe(48)
    state = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    request.session.pop(PENDING_KEY, None)
    request.session[ATTEMPT_KEY] = {'provider': provider, 'state': state, 'verifier': verifier,
                                    'redirect_uri': uri, 'created_at': time.time()}
    parameters = {'client_id': client_id, 'redirect_uri': uri, 'response_type': 'code',
                  'scope': config['scope'], 'state': state, 'code_challenge': challenge,
                  'code_challenge_method': 'S256'}
    return redirect(config['authorize'] + '?' + urlencode(parameters))


@require_GET
def social_callback(request, provider):
    if provider not in PROVIDERS:
        raise Http404('Unknown sign-in provider')
    attempt = request.session.pop(ATTEMPT_KEY, None)
    state = request.GET.get('state', '')
    if (not isinstance(attempt, dict) or not fresh_flow(attempt)
            or attempt.get('provider') != provider or not isinstance(attempt.get('state'), str)
            or not secrets.compare_digest(attempt['state'].encode(), state.encode())):
        messages.error(request, 'The sign-in request expired or could not be verified. Please start again.')
        return redirect('store_login')
    if request.GET.get('error') or not request.GET.get('code'):
        messages.error(request, 'Social sign-in was cancelled or not authorized.')
        return redirect('store_login')
    try:
        identity = exchange_identity(provider, attempt, request.GET['code'])
    except SocialLoginError as error:
        messages.error(request, str(error))
        return redirect('store_login')
    existing = SocialIdentity.objects.select_related('account').filter(provider=provider, subject=identity['subject']).first()
    if existing:
        if existing.account.appr != 1:
            messages.error(request, 'Your club account is awaiting approval.')
            return redirect('store_login')
        start_store_session(request, 'register', existing.account)
        messages.success(request, 'You are successfully logged in with ' + PROVIDERS[provider]['label'] + '.')
        return redirect('store_home')
    # Never connect an existing account solely because its email matches.
    request.session[PENDING_KEY] = identity
    return redirect('store_social_complete')


class SocialProfileForm(forms.ModelForm):
    class Meta:
        model = Register
        fields = ['name', 'email', 'phno', 'age', 'position']
        labels = {'name': 'Username', 'phno': 'Phone number', 'position': 'Playing position'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].max_length = registration_limits()['name']['max_length']
        self.fields['name'].widget.attrs['maxlength'] = self.fields['name'].max_length
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_name(self):
        value = self.cleaned_data['name']
        if not value.isalnum() or len(value) > registration_limits()['name']['max_length']:
            raise forms.ValidationError('Use up to 15 letters and numbers for your username.')
        if Register.objects.filter(name=value).exists():
            raise forms.ValidationError('This username is already taken.')
        return value

    def clean_email(self):
        value = self.cleaned_data['email']
        if Register.objects.filter(email__iexact=value).exists():
            raise forms.ValidationError('This email already has a club account. Use the existing-account option below.')
        return value


@sensitive_post_parameters('password')
@require_http_methods(['GET', 'POST'])
def social_complete(request):
    identity = request.session.get(PENDING_KEY)
    if not isinstance(identity, dict) or not fresh_flow(identity) or identity.get('provider') not in PROVIDERS:
        request.session.pop(PENDING_KEY, None)
        messages.error(request, 'Please start social sign-in again; the profile request has expired.')
        return redirect('store_login')
    initial_name = ''.join(c for c in identity.get('name', '') if c.isalnum())[:15]
    form = SocialProfileForm(request.POST if request.method == 'POST' and request.POST.get('action') == 'create' else None,
                             initial={'name': initial_name, 'email': identity.get('email', '')})
    link_error = ''
    if request.method == 'POST' and request.POST.get('action') == 'link':
        account = Register.objects.filter(email=request.POST.get('email', '').strip()).first()
        try:
            valid = account is not None and bool(request.POST.get('password')) and check_password(request.POST['password'], account.pwd)
        except (TypeError, ValueError):
            valid = False
        if not valid:
            link_error = 'Enter the correct email and password for your existing club account.'
        elif account.appr != 1:
            link_error = 'Your club account must be approved before you can connect social sign-in.'
        else:
            with transaction.atomic():
                linked, _ = SocialIdentity.objects.get_or_create(provider=identity['provider'], subject=identity['subject'], defaults={'account': account})
            if linked.account_id != account.pk:
                link_error = 'That provider account is already connected to another club account.'
            else:
                request.session.pop(PENDING_KEY, None)
                start_store_session(request, 'register', account)
                messages.success(request, 'Social sign-in is connected to your club account.')
                return redirect('store_home')
    elif request.method == 'POST' and request.POST.get('action') == 'create' and form.is_valid():
        try:
            with transaction.atomic():
                account = form.save(commit=False)
                account.pwd = make_password(None)
                account.reenter_pwd = account.pwd
                account.appr = 0
                account.full_clean()
                account.save()
                SocialIdentity.objects.create(account=account, provider=identity['provider'], subject=identity['subject'])
        except IntegrityError:
            form.add_error(None, 'That provider account is already connected. Please sign in again.')
        else:
            request.session.pop(PENDING_KEY, None)
            messages.success(request, 'Your club account has been created and is awaiting administrator approval. Use the same social button after approval.')
            return redirect('store_login')
    return render(request, 'store/social_complete.html', {'form': form, 'provider_label': PROVIDERS[identity['provider']]['label'],
                                                          'link_error': link_error, 'suggested_email': identity.get('email', '')})
