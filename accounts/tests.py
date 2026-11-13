from django.test import TestCase
from django.urls import reverse

from .models import CustomUser


PASSWORD = "FixIT-Staff-Test-Password-58!"


class RegistrationTests(TestCase):
    def setUp(self):
        self.signup_url = reverse("signup")
        self.valid_data = {
            "username": "newstaff",
            "email": "newstaff@example.com",
            "first_name": "New",
            "last_name": "Staff",
            "phone": "555-0101",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }

    def test_registration_creates_staff_with_hashed_password(self):
        response = self.client.post(self.signup_url, self.valid_data, follow=True)

        self.assertRedirects(response, reverse("login"))
        user = CustomUser.objects.get(username="newstaff")
        self.assertEqual(user.role, CustomUser.Role.STAFF)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)
        self.assertContains(response, "Your staff account has been created")

    def test_registration_rejects_missing_or_invalid_email(self):
        for email in ("", "not-an-email"):
            with self.subTest(email=email):
                response = self.client.post(
                    self.signup_url,
                    {**self.valid_data, "email": email},
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "email")
                self.assertFalse(
                    CustomUser.objects.filter(username="newstaff").exists()
                )

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        CustomUser.objects.create_user(
            username="existing",
            email="staff@example.com",
            password=PASSWORD,
        )

        response = self.client.post(
            self.signup_url,
            {**self.valid_data, "email": "STAFF@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            self.signup_url,
            {**self.valid_data, "password2": "Different-FixIT-Password-58!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The two password fields didn’t match.")
        self.assertFalse(CustomUser.objects.filter(username="newstaff").exists())

    def test_registration_rejects_duplicate_username(self):
        CustomUser.objects.create_user(
            username="newstaff",
            email="existing@example.com",
            password=PASSWORD,
        )

        response = self.client.post(self.signup_url, self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists.")


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="staff",
            email="staff@example.com",
            password=PASSWORD,
        )

    def test_login_succeeds_with_email_and_shows_success_message(self):
        response = self.client.post(
            reverse("login"),
            {"username": "STAFF@example.com", "password": PASSWORD},
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(response, "You are now logged in.")

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            reverse("login"),
            {"username": "staff@example.com", "password": "incorrect"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email or password.")

    def test_logout_ends_session_and_shows_message(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"), follow=True)

        self.assertRedirects(response, reverse("login"))
        self.assertContains(response, "You have been logged out.")
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            dashboard_response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )


class ProfileTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="staff",
            email="staff@example.com",
            password=PASSWORD,
        )
        self.other_user = CustomUser.objects.create_user(
            username="another",
            email="another@example.com",
            password=PASSWORD,
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('profile')}",
        )

    def test_profile_displays_only_the_logged_in_users_information(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("profile"))

        self.assertContains(response, self.user.email)
        self.assertNotContains(response, self.other_user.email)

    def test_profile_update_changes_only_the_logged_in_user(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile_edit"),
            {
                "first_name": "Updated",
                "last_name": "Staff",
                "email": "updated@example.com",
                "phone": "555-0133",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(response, "Your profile has been updated.")
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.phone, "555-0133")
        self.assertEqual(self.other_user.email, "another@example.com")

    def test_profile_update_rejects_another_users_email(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile_edit"),
            {
                "first_name": "",
                "last_name": "",
                "email": self.other_user.email,
                "phone": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "staff@example.com")


class StaffAdminTests(TestCase):
    def test_superuser_can_create_a_manager_from_django_admin(self):
        admin_user = CustomUser.objects.create_superuser(
            username="root",
            email="root@example.com",
            password=PASSWORD,
        )
        self.client.force_login(admin_user)

        add_url = reverse("admin:accounts_customuser_add")
        response = self.client.get(add_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            add_url,
            {
                "username": "shopmanager",
                "email": "manager@example.com",
                "role": CustomUser.Role.MANAGER,
                "phone": "555-0177",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 302)
        manager = CustomUser.objects.get(username="shopmanager")
        self.assertEqual(manager.role, CustomUser.Role.MANAGER)
        self.assertTrue(manager.check_password(PASSWORD))
