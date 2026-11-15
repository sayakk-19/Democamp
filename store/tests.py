from django.test import Client, RequestFactory, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.urls import reverse

from .accounts import get_store_account
from .models import Register, player
from .templatetags.store_ui import store_account_menu, store_account_panels


@override_settings(SECRET_KEY="store-account-tests-only-dummy-key")
class StoreAccountTests(TestCase):
    """Account changes run only in Django's isolated test database."""

    account_password = "DummyPass!1"
    other_account_password = "OtherDummy!2"

    @classmethod
    def setUpTestData(cls):
        cls.account = Register.objects.create(
            name="ExamplePlayer",
            email="player@example.test",
            phno="0123456789",
            pwd=make_password(cls.account_password),
            reenter_pwd=make_password(cls.account_password),
            age=21,
            position="Forward",
            appr=1,
        )
        cls.other_account = Register.objects.create(
            name="OtherPlayer",
            email="other@example.test",
            phno="1234567890",
            pwd=make_password(cls.other_account_password),
            reenter_pwd=make_password(cls.other_account_password),
            age=23,
            position="Defender",
            appr=1,
        )
        cls.legacy_account = player.objects.create(
            Name="LegacyPlayer",
            Email="legacy@example.test",
            Passwd="LegacyDummy!3",
            Age=25,
            Position="Goalkeeper",
            Phno=1234567890,
            appr=1,
        )

    def set_store_session(self, kind="register", account=None):
        account = account or self.account
        session = self.client.session
        session["store_account_type"] = kind
        session["store_account_id"] = account.pk
        session.save()
        return session.session_key

    def account_request(self):
        request = RequestFactory().get(reverse("store_home"))
        request.session = self.client.session
        return request

    def test_approved_hashed_password_login_rotates_session_and_renders_welcome(self):
        self.assertNotEqual(self.account.pwd, self.account_password)
        previous_key = self.set_store_session(account=self.other_account)
        response = self.client.post("/store/indexcode", {
            "email": self.account.email,
            "pwd": self.account_password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "welcome.html")
        self.assertNotEqual(self.client.session.session_key, previous_key)
        self.assertEqual(self.client.session["store_account_type"], "register")
        self.assertEqual(self.client.session["store_account_id"], self.account.pk)

    def test_unapproved_login_does_not_create_account_session(self):
        Register.objects.filter(pk=self.account.pk).update(appr=0)
        response = self.client.post("/store/indexcode", {
            "email": self.account.email,
            "pwd": self.account_password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index1.html")
        self.assertNotIn("store_account_id", self.client.session)
        self.assertNotIn("store_account_type", self.client.session)

    def test_submitted_encoded_password_cannot_log_in(self):
        response = self.client.post("/store/indexcode", {
            "email": self.account.email,
            "pwd": self.account.pwd,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index1.html")
        self.assertNotIn("store_account_id", self.client.session)
        self.assertNotIn("store_account_type", self.client.session)

    def test_plain_or_malformed_stored_password_cannot_log_in(self):
        for stored_password in (
            self.account_password,
            "not-a-password-hash",
            "pbkdf2_sha256$invalid$salt$invalid",
        ):
            with self.subTest(stored_password=stored_password):
                Register.objects.filter(pk=self.account.pk).update(
                    pwd=stored_password, reenter_pwd=stored_password,
                )
                response = self.client.post("/store/indexcode", {
                    "email": self.account.email,
                    "pwd": self.account_password,
                })
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "index1.html")
                self.assertNotIn("store_account_id", self.client.session)
                self.assertNotIn("store_account_type", self.client.session)

    def test_wrong_and_missing_credentials_do_not_create_account_session(self):
        for credentials in ({"email": self.account.email, "pwd": "incorrect"}, {}):
            with self.subTest(credentials=credentials):
                response = self.client.post("/store/indexcode", credentials)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("store_account_id", self.client.session)

    def test_profile_contains_display_details_without_credentials(self):
        self.set_store_session()
        details = get_store_account(self.account_request())
        self.assertEqual(details, {
            "id": self.account.pk,
            "kind": "register",
            "name": self.account.name,
            "email": self.account.email,
            "phone": "0123456789",
            "age": 21,
            "position": "Forward",
        })
        self.assertNotIn("pwd", details)
        self.assertNotIn("reenter_pwd", details)

    def test_profile_is_cached_only_within_the_current_request(self):
        self.set_store_session()
        request = self.account_request()
        request.session.get("store_account_id")
        with self.assertNumQueries(1):
            first = get_store_account(request)
            self.assertIs(first, get_store_account(request))
        Register.objects.filter(pk=self.account.pk).update(appr=0)
        self.assertIsNone(get_store_account(self.account_request()))

    def test_revoked_or_deleted_account_clears_stale_session(self):
        for action in ("revoke", "delete"):
            with self.subTest(action=action):
                self.set_store_session()
                if action == "revoke":
                    Register.objects.filter(pk=self.account.pk).update(appr=0)
                else:
                    Register.objects.filter(pk=self.account.pk).delete()
                request = self.account_request()
                self.assertIsNone(get_store_account(request))
                self.assertNotIn("store_account_id", request.session)
                self.assertNotIn("store_account_type", request.session)

    def test_invalid_session_identifiers_are_rejected(self):
        for kind, account_id in (("unknown", 1), ("register", "1"), ("register", True)):
            with self.subTest(kind=kind, account_id=account_id):
                request = RequestFactory().get("/store/index")
                request.session = {
                    "store_account_type": kind,
                    "store_account_id": account_id,
                }
                self.assertIsNone(get_store_account(request))
                self.assertEqual(request.session, {})

    def test_template_tags_share_safe_account_and_csrf_context(self):
        self.set_store_session()
        request = self.account_request()
        context = {"request": request, "csrf_token": "dummy-csrf-token"}
        menu = store_account_menu(context)
        panels = store_account_panels(context)
        self.assertEqual(menu["store_account"], panels["store_account"])
        self.assertEqual(panels["csrf_token"], "dummy-csrf-token")
        self.assertIs(panels["request"], request)

    def test_legacy_login_uses_post_and_approved_session(self):
        response = self.client.post("/store/logcode", {
            "a1": self.legacy_account.Email,
            "a2": self.legacy_account.Passwd,
        })
        self.assertRedirects(response, reverse("store_home"), fetch_redirect_response=False)
        self.assertEqual(self.client.session["store_account_type"], "player")
        details = get_store_account(self.account_request())
        self.assertEqual(details["name"], "LegacyPlayer")
        self.assertEqual(details["phone"], "1234567890")
        self.assertNotIn("Passwd", details)

    def test_legacy_get_credentials_cannot_log_in(self):
        response = self.client.get("/store/logcode", {
            "a1": self.legacy_account.Email,
            "a2": self.legacy_account.Passwd,
        })
        self.assertRedirects(response, reverse("store_legacy_login"), fetch_redirect_response=False)
        self.assertNotIn("store_account_id", self.client.session)

    def test_logout_requires_post_and_clears_login(self):
        self.set_store_session()
        self.assertEqual(self.client.get(reverse("store_logout")).status_code, 405)
        self.assertIn("store_account_id", self.client.session)
        response = self.client.post(reverse("store_logout"))
        self.assertRedirects(response, reverse("store_home"), fetch_redirect_response=False)
        self.assertNotIn("store_account_id", self.client.session)

    def test_delete_requires_post_and_explicit_confirmation(self):
        self.set_store_session()
        self.assertEqual(self.client.get(reverse("store_account_delete")).status_code, 405)
        response = self.client.post(reverse("store_account_delete"))
        self.assertRedirects(response, reverse("store_home"), fetch_redirect_response=False)
        self.assertTrue(Register.objects.filter(pk=self.account.pk).exists())
        self.assertIn("store_account_id", self.client.session)

    def test_delete_removes_only_the_current_session_account(self):
        self.set_store_session()
        response = self.client.post(reverse("store_account_delete"), {
            "confirm_delete": "DELETE",
            "id": self.other_account.pk,
            "store_account_id": self.other_account.pk,
        })
        self.assertRedirects(response, reverse("store_home"), fetch_redirect_response=False)
        self.assertFalse(Register.objects.filter(pk=self.account.pk).exists())
        self.assertTrue(Register.objects.filter(pk=self.other_account.pk).exists())
        self.assertNotIn("store_account_id", self.client.session)

    def test_legacy_account_can_delete_only_itself(self):
        self.set_store_session(kind="player", account=self.legacy_account)
        response = self.client.post(reverse("store_account_delete"), {"confirm_delete": "DELETE"})
        self.assertRedirects(response, reverse("store_home"), fetch_redirect_response=False)
        self.assertFalse(player.objects.filter(pk=self.legacy_account.pk).exists())
        self.assertTrue(Register.objects.filter(pk=self.account.pk).exists())

    def test_anonymous_account_deletion_requires_login(self):
        response = self.client.post(reverse("store_account_delete"), {"confirm_delete": "DELETE"})
        self.assertRedirects(response, reverse("store_login"), fetch_redirect_response=False)
        self.assertTrue(Register.objects.filter(pk=self.account.pk).exists())

    def test_account_mutations_enforce_csrf(self):
        self.set_store_session()
        protected_client = Client(enforce_csrf_checks=True)
        protected_client.cookies = self.client.cookies
        for route in ("store_logout", "store_account_delete"):
            with self.subTest(route=route):
                response = protected_client.post(reverse(route), {"confirm_delete": "DELETE"})
                self.assertEqual(response.status_code, 403)
                self.assertTrue(Register.objects.filter(pk=self.account.pk).exists())
                self.assertIn("store_account_id", protected_client.session)

    def management_routes(self):
        return (
            reverse("store_admin_panel"),
            reverse("store_approvals"),
            reverse("store_account_edit", args=[self.account.pk]),
            reverse("store_account_update", args=[self.account.pk]),
            reverse("store_admin_account_delete", args=[self.account.pk]),
            reverse("store_account_approve", args=[self.account.pk]),
        )

    def staff_login(self):
        staff = get_user_model().objects.create(
            username="staff-manager", is_staff=True, is_active=True,
        )
        self.client.force_login(staff)

    def test_anonymous_and_club_members_cannot_access_management(self):
        for identity in ("anonymous", "club-member"):
            if identity == "club-member":
                self.set_store_session()
            for route in self.management_routes():
                for method in (self.client.get, self.client.post):
                    with self.subTest(identity=identity, route=route, method=method.__name__):
                        response = method(route)
                        self.assertEqual(response.status_code, 302)
                        self.assertTrue(response.url.startswith(reverse("admin:login") + "?next="))
                        self.assertTrue(Register.objects.filter(pk=self.account.pk, appr=1).exists())

    def test_authenticated_nonstaff_django_user_cannot_manage_accounts(self):
        member = get_user_model().objects.create(username="ordinary-member", is_staff=False)
        self.client.force_login(member)
        for route in self.management_routes():
            with self.subTest(route=route):
                response = self.client.post(route)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse("admin:login") + "?next="))

    def test_staff_can_view_management_and_approve_by_post(self):
        self.staff_login()
        for route in ("store_admin_panel", "store_approvals"):
            self.assertEqual(self.client.get(reverse(route)).status_code, 200)
        self.assertEqual(self.client.get(reverse("store_account_edit", args=[self.account.pk])).status_code, 200)
        Register.objects.filter(pk=self.account.pk).update(appr=0)
        response = self.client.post(reverse("store_account_approve", args=[self.account.pk]))
        self.assertRedirects(response, reverse("store_approvals"), fetch_redirect_response=False)
        self.account.refresh_from_db()
        self.assertEqual(self.account.appr, 1)

    def test_staff_get_cannot_change_delete_or_approve_accounts(self):
        self.staff_login()
        Register.objects.filter(pk=self.account.pk).update(appr=0)
        for route in ("store_account_update", "store_admin_account_delete", "store_account_approve"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route, args=[self.account.pk]), {
                    "a1": "UnexpectedChange", "a2": "changed@example.test", "a3": "1234567890",
                    "a4": "ChangedDummy!4", "a5": "22", "a6": "Midfielder",
                })
                self.assertEqual(response.status_code, 405)
                self.account.refresh_from_db()
                self.assertEqual(self.account.name, "ExamplePlayer")
                self.assertEqual(self.account.appr, 0)

    def test_staff_can_update_and_delete_by_post(self):
        self.staff_login()
        response = self.client.post(reverse("store_account_update", args=[self.account.pk]), {
            "a1": "UpdatedPlayer", "a2": "updated@example.test", "a3": "1234567890",
            "a4": "UpdatedDummy!4", "a5": "22", "a6": "Midfielder",
        })
        self.assertRedirects(response, reverse("store_admin_panel"), fetch_redirect_response=False)
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "UpdatedPlayer")
        self.assertEqual(self.account.email, "updated@example.test")
        self.assertEqual(self.account.age, 22)
        response = self.client.post(reverse("store_admin_account_delete", args=[self.account.pk]))
        self.assertRedirects(response, reverse("store_admin_panel"), fetch_redirect_response=False)
        self.assertFalse(Register.objects.filter(pk=self.account.pk).exists())
        self.assertTrue(Register.objects.filter(pk=self.other_account.pk).exists())

    def test_staff_account_mutations_require_csrf(self):
        self.staff_login()
        protected_client = Client(enforce_csrf_checks=True)
        protected_client.cookies = self.client.cookies
        for route in ("store_account_update", "store_admin_account_delete", "store_account_approve"):
            with self.subTest(route=route):
                response = protected_client.post(reverse(route, args=[self.account.pk]))
                self.assertEqual(response.status_code, 403)
                self.assertTrue(Register.objects.filter(pk=self.account.pk, appr=1).exists())
