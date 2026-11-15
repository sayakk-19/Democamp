import hashlib
import base64
import time
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.contrib.auth.hashers import is_password_usable, make_password
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Register, SocialIdentity
from .social_auth import ATTEMPT_KEY, PENDING_KEY, SocialLoginError, exchange_identity


@override_settings(GOOGLE_CLIENT_ID='google-test-client', GOOGLE_CLIENT_SECRET='google-test-secret',
                   GITHUB_CLIENT_ID='github-test-client', GITHUB_CLIENT_SECRET='github-test-secret',
                   X_CLIENT_ID='x-test-client', X_CLIENT_SECRET='x-test-secret', PUBLIC_BASE_URL='')
class SocialSignInTests(TestCase):
    def setUp(self):
        self.password = 'DummySocial9!'
        self.member = Register.objects.create(name='ClubMember', email='member@example.test', phno='0123456789',
                                              pwd=make_password(self.password), reenter_pwd=make_password(self.password),
                                              age=22, position='Forward', appr=1)

    def pending(self, provider='github', subject='123'):
        session = self.client.session
        identity = {'provider': provider, 'subject': subject, 'name': 'NewPlayer', 'email': 'new@example.test', 'created_at': time.time()}
        session[PENDING_KEY] = identity
        session.save()
        return identity

    def callback(self, identity):
        self.client.get(reverse('store_social_start', args=[identity['provider']]))
        state = self.client.session[ATTEMPT_KEY]['state']
        with patch('store.social_auth.exchange_identity', return_value=identity):
            return self.client.get(reverse('store_social_callback', args=[identity['provider']]), {'state': state, 'code': 'dummy-code'})

    def test_landing_page_login_and_existing_member_profile(self):
        response = self.client.get(reverse('store_home'))
        self.assertContains(response, 'href="' + reverse('store_login') + '">Log in</a>')
        session = self.client.session
        session['store_account_type'] = 'register'
        session['store_account_id'] = self.member.pk
        session.save()
        self.assertContains(self.client.get(reverse('store_home')), 'Open your profile')

    def test_existing_logos_link_to_all_three_providers(self):
        for page in ('store_login', 'store_signup'):
            response = self.client.get(reverse(page))
            for provider in ('google', 'github', 'x'):
                self.assertContains(response, 'data-social-url="' + reverse('store_social_start', args=[provider]) + '"')
            self.assertContains(response, 'shared/js/social-buttons.js')

    def test_each_start_uses_state_pkce_and_registered_callback(self):
        for provider in ('google', 'github', 'x'):
            response = self.client.get(reverse('store_social_start', args=[provider]))
            self.assertEqual(response.status_code, 302)
            parameters = parse_qs(urlsplit(response.url).query)
            attempt = self.client.session[ATTEMPT_KEY]
            self.assertEqual(parameters['state'], [attempt['state']])
            self.assertEqual(parameters['code_challenge_method'], ['S256'])
            challenge = base64.urlsafe_b64encode(hashlib.sha256(attempt['verifier'].encode()).digest()).decode().rstrip('=')
            self.assertEqual(parameters['code_challenge'], [challenge])
            self.assertTrue(parameters['redirect_uri'][0].endswith(reverse('store_social_callback', args=[provider])))
            self.assertNotIn('client_secret', response.url)

    @override_settings(GOOGLE_CLIENT_ID='', GOOGLE_CLIENT_SECRET='')
    def test_missing_configuration_is_explained_without_network(self):
        with patch('store.social_auth.request_json') as network:
            response = self.client.get(reverse('store_social_start', args=['google']), follow=True)
        self.assertContains(response, 'not configured yet')
        network.assert_not_called()

    def test_unknown_provider_and_invalid_state_are_denied(self):
        self.assertEqual(self.client.get(reverse('store_social_start', args=['unknown'])).status_code, 404)
        with patch('store.social_auth.exchange_identity') as exchange:
            response = self.client.get(reverse('store_social_callback', args=['github']), {'state': 'forged', 'code': 'code'})
        self.assertRedirects(response, reverse('store_login'), fetch_redirect_response=False)
        exchange.assert_not_called()

    def test_non_ascii_state_is_rejected_without_server_error(self):
        self.client.get(reverse('store_social_start', args=['google']))
        with patch('store.social_auth.exchange_identity') as exchange:
            response = self.client.get(reverse('store_social_callback', args=['google']), {'state': 'invalid-\u2603', 'code': 'code'})
        self.assertRedirects(response, reverse('store_login'), fetch_redirect_response=False)
        exchange.assert_not_called()

    def test_attempt_expires_and_cannot_be_replayed(self):
        self.client.get(reverse('store_social_start', args=['github']))
        session = self.client.session
        attempt = session[ATTEMPT_KEY]
        attempt['created_at'] = time.time() - 601
        session[ATTEMPT_KEY] = attempt
        session.save()
        with patch('store.social_auth.exchange_identity') as exchange:
            self.client.get(reverse('store_social_callback', args=['github']), {'state': attempt['state'], 'code': 'code'})
        exchange.assert_not_called()
        self.assertNotIn(ATTEMPT_KEY, self.client.session)

    def test_cancelled_authorization_does_not_exchange_tokens(self):
        self.client.get(reverse('store_social_start', args=['google']))
        state = self.client.session[ATTEMPT_KEY]['state']
        with patch('store.social_auth.exchange_identity') as exchange:
            self.client.get(reverse('store_social_callback', args=['google']), {'state': state, 'error': 'access_denied'})
        exchange.assert_not_called()
        self.assertNotIn('store_account_id', self.client.session)

    def test_linked_approved_identity_logs_in_with_store_session(self):
        SocialIdentity.objects.create(account=self.member, provider='github', subject='123')
        response = self.callback(self.pending())
        self.assertRedirects(response, reverse('store_home'), fetch_redirect_response=False)
        self.assertEqual(self.client.session['store_account_id'], self.member.pk)

    def test_linked_pending_account_cannot_log_in(self):
        self.member.appr = 0
        self.member.save(update_fields=['appr'])
        SocialIdentity.objects.create(account=self.member, provider='github', subject='123')
        self.callback(self.pending())
        self.assertNotIn('store_account_id', self.client.session)

    def test_matching_email_does_not_automatically_link_existing_account(self):
        identity = self.pending()
        identity['email'] = self.member.email
        response = self.callback(identity)
        self.assertRedirects(response, reverse('store_social_complete'), fetch_redirect_response=False)
        self.assertFalse(SocialIdentity.objects.exists())
        self.assertNotIn('store_account_id', self.client.session)

    def test_new_social_account_still_requires_profile_and_approval(self):
        self.pending()
        response = self.client.post(reverse('store_social_complete'), {'action': 'create', 'name': 'NewPlayer',
                                   'email': 'new@example.test', 'phno': '1234567890', 'age': '21', 'position': 'Defender'})
        self.assertRedirects(response, reverse('store_login'), fetch_redirect_response=False)
        account = Register.objects.get(email='new@example.test')
        self.assertEqual(account.appr, 0)
        self.assertFalse(is_password_usable(account.pwd))
        self.assertEqual(SocialIdentity.objects.get().account_id, account.pk)
        self.assertNotIn(PENDING_KEY, self.client.session)
        self.assertNotIn('store_account_id', self.client.session)

    def test_existing_account_link_requires_correct_password_and_approval(self):
        self.pending()
        self.client.post(reverse('store_social_complete'), {'action': 'link', 'email': self.member.email, 'password': 'wrong'})
        self.assertFalse(SocialIdentity.objects.exists())
        response = self.client.post(reverse('store_social_complete'), {'action': 'link', 'email': self.member.email, 'password': self.password})
        self.assertRedirects(response, reverse('store_home'), fetch_redirect_response=False)
        self.assertEqual(SocialIdentity.objects.get().account_id, self.member.pk)

    def test_link_cannot_move_a_provider_account_from_another_member(self):
        other = Register.objects.create(name='Other', email='other@example.test', phno='1234567890', pwd='!', reenter_pwd='!', age=22, position='Defender', appr=1)
        SocialIdentity.objects.create(account=other, provider='github', subject='123')
        self.pending()
        response = self.client.post(reverse('store_social_complete'), {'action': 'link', 'email': self.member.email, 'password': self.password})
        self.assertContains(response, 'already connected to another')
        self.assertEqual(SocialIdentity.objects.get().account_id, other.pk)

    def test_duplicate_email_and_invalid_profile_are_not_registered(self):
        self.pending()
        response = self.client.post(reverse('store_social_complete'), {'action': 'create', 'name': 'NewPlayer',
                                   'email': self.member.email, 'phno': 'bad', 'age': '6', 'position': 'Defender'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Register.objects.count(), 1)
        self.assertFalse(SocialIdentity.objects.exists())

    def test_completion_requires_csrf_and_fresh_provider_identity(self):
        self.assertRedirects(self.client.get(reverse('store_social_complete')), reverse('store_login'), fetch_redirect_response=False)
        self.pending()
        protected = Client(enforce_csrf_checks=True)
        protected.cookies = self.client.cookies
        self.assertEqual(protected.post(reverse('store_social_complete'), {'action': 'link'}).status_code, 403)

    def test_google_profile_uses_only_verified_email_and_pkce_exchange(self):
        attempt = {'redirect_uri': 'http://localhost/store/social/google/callback/', 'verifier': 'dummy-verifier'}
        with patch('store.social_auth.request_json', side_effect=[{'access_token': 'dummy-token'}, {'sub': '42', 'email': self.member.email, 'email_verified': False}]) as network:
            identity = exchange_identity('google', attempt, 'dummy-code')
        self.assertEqual(identity['email'], '')
        self.assertEqual(identity['subject'], '42')
        self.assertEqual(network.call_args_list[0].kwargs['data']['code_verifier'], 'dummy-verifier')

    def test_github_verified_private_email_and_x_confirmed_email(self):
        attempt = {'redirect_uri': 'http://localhost/callback', 'verifier': 'verifier'}
        with patch('store.social_auth.request_json', side_effect=[{'access_token': 'token'}, {'id': 42, 'login': 'player'},
                    [{'email': 'unverified@example.test', 'primary': True, 'verified': False}, {'email': 'verified@example.test', 'verified': True}]]):
            self.assertEqual(exchange_identity('github', attempt, 'code')['email'], 'verified@example.test')
        with patch('store.social_auth.request_json', side_effect=[{'access_token': 'token'}, {'data': {'id': '99', 'username': 'player', 'confirmed_email': 'x@example.test'}}]) as network:
            self.assertEqual(exchange_identity('x', attempt, 'code')['email'], 'x@example.test')
            self.assertTrue(network.call_args_list[0].kwargs['headers']['Authorization'].startswith('Basic '))

    def test_provider_failure_does_not_log_in(self):
        self.client.get(reverse('store_social_start', args=['google']))
        state = self.client.session[ATTEMPT_KEY]['state']
        with patch('store.social_auth.exchange_identity', side_effect=SocialLoginError('Provider unavailable')):
            response = self.client.get(reverse('store_social_callback', args=['google']), {'state': state, 'code': 'code'})
        self.assertRedirects(response, reverse('store_login'), fetch_redirect_response=False)
        self.assertNotIn('store_account_id', self.client.session)
