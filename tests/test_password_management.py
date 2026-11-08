"""
=========================================================
Project : Sridevi Enterprises
File    : test_password_management.py
Purpose : Integration tests for Password Management (change password,
          forgot/reset password, Admin-assisted reset, CSRF, rate limits,
          session invalidation).

          Runs against the LOCAL development database only (refuses any
          non-local DB_HOST). Creates temporary "pwtest_" accounts and
          deletes them - plus every token/throttle row they produced - when
          finished. Existing accounts are snapshotted and asserted unchanged.
          Email is never sent: send_email is replaced with a capture stub.

Usage   : python -m unittest tests.test_password_management -v
Author  : Srikar
=========================================================
"""

import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import check_password_hash, generate_password_hash  # noqa: E402

from config import Config  # noqa: E402

if Config.DB_HOST not in ("127.0.0.1", "localhost", "::1"):
    raise SystemExit("Refusing to run: these tests only run against a local development database.")

from app import app  # noqa: E402
from database.db import execute, fetch_all, fetch_one  # noqa: E402
from services import email_service, password_service  # noqa: E402
from services.auth_service import authenticate_employee  # noqa: E402

PREFIX = "pwtest_"
EMP_PASSWORD = "Employee-Old-Pass-91"
ADMIN_PASSWORD = "Admin-Old-Pass-7342"
NEW_PASSWORD = "Brand-New-Secret-2026"
LINK_PATTERN = re.compile(r"(https?://\S+/employee/reset-password/(\S+))")


def _create_account(username, role, password, email):
    execute(
        "INSERT INTO Users (Username, Password, Role) VALUES (%s, %s, %s);",
        (username, generate_password_hash(password), role),
    )
    user_id = fetch_one("SELECT UserID FROM Users WHERE Username = %s;", (username,))["UserID"]
    if email is not False:
        execute(
            "INSERT INTO Employees (UserID, Name, Email, Designation) VALUES (%s, %s, %s, %s);",
            (user_id, username, email, "Test"),
        )
    return user_id


def _cleanup():
    ids = [r["UserID"] for r in fetch_all("SELECT UserID FROM Users WHERE Username LIKE %s;", (PREFIX + "%",))]
    for user_id in ids:
        execute("DELETE FROM PasswordResetTokens WHERE UserID = %s OR InitiatedByUserID = %s;", (user_id, user_id))
        execute("DELETE FROM Employees WHERE UserID = %s;", (user_id,))
        execute("DELETE FROM Users WHERE UserID = %s;", (user_id,))


class PasswordManagementTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["SESSION_COOKIE_SECURE"] = False

        cls.start = fetch_one("SELECT UTC_TIMESTAMP() - INTERVAL 1 SECOND AS t;")["t"]
        cls.existing_snapshot = fetch_all(
            "SELECT UserID, Password, SessionEpoch, Role FROM Users WHERE Username NOT LIKE %s ORDER BY UserID;",
            (PREFIX + "%",),
        )

        _cleanup()
        cls.emp_id = _create_account(PREFIX + "emp", "Employee", EMP_PASSWORD, "pwtest.emp@example.test")
        cls.emp2_id = _create_account(PREFIX + "emp2", "Employee", EMP_PASSWORD, "pwtest.emp2@example.test")
        cls.admin_id = _create_account(PREFIX + "admin", "Admin", ADMIN_PASSWORD, "pwtest.admin@example.test")
        cls.noemail_id = _create_account(PREFIX + "noemail", "Employee", EMP_PASSWORD, "")
        cls.dup1_id = _create_account(PREFIX + "dup1", "Employee", EMP_PASSWORD, "pwtest.shared@example.test")
        cls.dup2_id = _create_account(PREFIX + "dup2", "Employee", EMP_PASSWORD, "PwTest.Shared@example.test")

    @classmethod
    def tearDownClass(cls):
        _cleanup()
        execute("DELETE FROM AuthThrottle WHERE CreatedAt >= %s;", (cls.start,))
        after = fetch_all(
            "SELECT UserID, Password, SessionEpoch, Role FROM Users WHERE Username NOT LIKE %s ORDER BY UserID;",
            (PREFIX + "%",),
        )
        assert after == cls.existing_snapshot, "Existing accounts were modified!"

    def setUp(self):
        # Fresh rate-limit state and known passwords for every test.
        execute("DELETE FROM AuthThrottle WHERE CreatedAt >= %s;", (self.start,))
        self.setUp_new_account_cleanup()
        for user_id, password in (
            (self.emp_id, EMP_PASSWORD), (self.emp2_id, EMP_PASSWORD), (self.admin_id, ADMIN_PASSWORD),
        ):
            execute("UPDATE Users SET Password = %s, Role = %s, SessionEpoch = 0 WHERE UserID = %s;", (
                generate_password_hash(password), "Admin" if user_id == self.admin_id else "Employee", user_id,
            ))

        self.sent = []
        self.patches = [
            mock.patch.object(Config, "SMTP_HOST", "smtp.example.test"),
            mock.patch.object(Config, "SMTP_SENDER", "no-reply@example.test"),
            mock.patch.object(Config, "PUBLIC_BASE_URL", "https://www.example.test"),
            mock.patch.object(email_service, "send_email", side_effect=self._capture_email),
            mock.patch.object(password_service, "dispatch_in_background", side_effect=lambda f, *a: f(*a)),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in self.patches:
            patcher.stop()

    # -- helpers ---------------------------------------------------------

    def _capture_email(self, to_address, subject, body):
        self.sent.append({"to": to_address, "subject": subject, "body": body})

    def _client(self):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["_csrf_token"] = "test-csrf"
        return client

    def _login(self, username, password, client=None):
        client = client or self._client()
        response = client.post("/employee/login", data={
            "username": username, "password": password, "csrf_token": "test-csrf",
        })
        # Login clears the session (and its CSRF token); a browser gets a fresh
        # token from the next page it renders - the test sets a known one.
        with client.session_transaction() as sess:
            sess["_csrf_token"] = "test-csrf"
        return client, response

    def _logged_in(self, client):
        with client.session_transaction() as sess:
            return bool(sess.get("UserID"))

    def _last_link(self):
        match = LINK_PATTERN.search(self.sent[-1]["body"])
        return match.group(1), match.group(2)

    def _use_link(self, client, token):
        client.get(f"/employee/reset-password/{token}")
        with client.session_transaction() as sess:
            sess["_csrf_token"] = "test-csrf"
        return client.post("/employee/reset-password", data={
            "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD, "csrf_token": "test-csrf",
        })

    def _password_ok(self, user_id, password):
        row = fetch_one("SELECT Password FROM Users WHERE UserID = %s;", (user_id,))
        return check_password_hash(row["Password"], password)

    # -- 1-3 change password ---------------------------------------------

    def test_01_employee_changes_password(self):
        client, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        response = client.post("/employee/account/password", data={
            "current_password": EMP_PASSWORD, "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD, "csrf_token": "test-csrf",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("/employee/login", response.headers["Location"])
        self.assertTrue(self._password_ok(self.emp_id, NEW_PASSWORD))
        self.assertFalse(self._logged_in(client))
        stored = fetch_one("SELECT Password FROM Users WHERE UserID = %s;", (self.emp_id,))["Password"]
        self.assertTrue(stored.startswith(("scrypt:", "pbkdf2:")))

    def test_02_wrong_current_password_rejected(self):
        client, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        response = client.post("/employee/account/password", data={
            "current_password": "not-the-password", "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD, "csrf_token": "test-csrf",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Current password is incorrect", response.data)
        self.assertTrue(self._password_ok(self.emp_id, EMP_PASSWORD))

    def test_03_confirmation_mismatch_and_policy_rejected(self):
        client, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        response = client.post("/employee/account/password", data={
            "current_password": EMP_PASSWORD, "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD + "x", "csrf_token": "test-csrf",
        })
        self.assertIn(b"do not match", response.data)
        response = client.post("/employee/account/password", data={
            "current_password": EMP_PASSWORD, "new_password": "short", "confirm_password": "short",
            "csrf_token": "test-csrf",
        })
        self.assertIn(b"at least 12 characters", response.data)
        self.assertTrue(self._password_ok(self.emp_id, EMP_PASSWORD))

    # -- 4-9 forgot / reset -----------------------------------------------

    def test_04_to_09_reset_flow(self):
        client = self._client()
        response = client.post("/employee/forgot-password", data={
            "email": "PWTEST.emp@example.test ", "csrf_token": "test-csrf",
        })
        self.assertIn(b"If that email address belongs to an account", response.data)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["to"], "pwtest.emp@example.test")
        link, token = self._last_link()
        self.assertTrue(link.startswith("https://www.example.test/"))  # 19: HTTPS link

        # Only the hash is stored.
        self.assertIsNone(fetch_one("SELECT TokenID FROM PasswordResetTokens WHERE TokenHash = %s;", (token,)))

        # 5: valid token works; landing redirect hides the token from the URL.
        landing = client.get(f"/employee/reset-password/{token}")
        self.assertEqual(landing.status_code, 302)
        self.assertTrue(landing.headers["Location"].endswith("/employee/reset-password"))
        response = self._use_link(client, token)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self._password_ok(self.emp_id, NEW_PASSWORD))

        # 7: reused token rejected.
        response = self._use_link(self._client(), token)
        self.assertIn(b"invalid, has expired, or has already been used", response.data)

        # 8: invalid token rejected.
        response = self._use_link(self._client(), "this-is-not-a-real-token")
        self.assertIn(b"invalid, has expired", response.data)

        # 9: log in with the new password; old one fails.
        client, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        self.assertFalse(self._logged_in(client))
        client, _ = self._login(PREFIX + "emp", NEW_PASSWORD)
        self.assertTrue(self._logged_in(client))

    def test_06_expired_token_rejected(self):
        token = password_service.issue_reset_token(self.emp_id, "Employee")
        execute(
            "UPDATE PasswordResetTokens SET ExpiresAt = UTC_TIMESTAMP() - INTERVAL 1 MINUTE WHERE UserID = %s;",
            (self.emp_id,),
        )
        response = self._use_link(self._client(), token)
        self.assertIn(b"invalid, has expired", response.data)
        self.assertTrue(self._password_ok(self.emp_id, EMP_PASSWORD))

    def test_06b_expiry_is_30_minutes_and_new_token_revokes_old(self):
        first = password_service.issue_reset_token(self.emp_id, "Employee")
        row = fetch_one(
            "SELECT TIMESTAMPDIFF(SECOND, CreatedAt, ExpiresAt) AS s FROM PasswordResetTokens "
            "WHERE UserID = %s ORDER BY TokenID DESC LIMIT 1;", (self.emp_id,),
        )
        self.assertEqual(row["s"], 30 * 60)
        second = password_service.issue_reset_token(self.emp_id, "Employee")
        self.assertIsNone(password_service.get_valid_reset_token(first))
        self.assertIsNotNone(password_service.get_valid_reset_token(second))

    def test_04b_unknown_and_ambiguous_email_generic_response(self):
        for email in ("nobody@example.test", "pwtest.shared@example.test"):
            response = self._client().post("/employee/forgot-password", data={
                "email": email, "csrf_token": "test-csrf",
            })
            self.assertIn(b"If that email address belongs to an account", response.data)
        self.assertEqual(self.sent, [])

    # -- 10-11 admin-assisted reset ----------------------------------------

    def test_10_admin_initiates_employee_reset(self):
        client, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        page = client.get("/admin/employees")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b"scrypt:", page.data)
        response = client.post(f"/admin/employees/{self.emp2_id}/reset-password",
                               data={"csrf_token": "test-csrf"}, follow_redirects=True)
        self.assertIn(b"A password reset link was emailed", response.data)
        self.assertEqual(self.sent[-1]["to"], "pwtest.emp2@example.test")
        self.assertIn("administrator has started", self.sent[-1]["body"])
        # The admin's page never contains the link/token.
        _, token = self._last_link()
        self.assertNotIn(token.encode(), response.data)
        row = fetch_one(
            "SELECT InitiatedByUserID FROM PasswordResetTokens WHERE UserID = %s ORDER BY TokenID DESC LIMIT 1;",
            (self.emp2_id,),
        )
        self.assertEqual(row["InitiatedByUserID"], self.admin_id)  # audit trail
        self.assertTrue(self._password_ok(self.emp2_id, EMP_PASSWORD))  # password untouched

    def test_10b_admin_reset_refused_for_missing_or_ambiguous_email(self):
        client, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        for user_id, expected in ((self.noemail_id, b"has no registered email"),
                                  (self.dup1_id, b"shares its registered email")):
            response = client.post(f"/admin/employees/{user_id}/reset-password",
                                   data={"csrf_token": "test-csrf"}, follow_redirects=True)
            self.assertIn(expected, response.data)
        self.assertEqual(self.sent, [])

    def test_10c_admin_cannot_reset_admin_accounts(self):
        ok, message = password_service.admin_initiate_reset(self.emp_id, self.admin_id, lambda t: "/x/" + t)
        self.assertFalse(ok)
        self.assertEqual(self.sent, [])

    def test_11_unauthorized_users_cannot_initiate_reset(self):
        anonymous = self._client().post(f"/admin/employees/{self.emp2_id}/reset-password",
                                        data={"csrf_token": "test-csrf"})
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/employee/login", anonymous.headers["Location"])
        client, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        self.assertEqual(client.get("/admin/employees").status_code, 403)
        forbidden = client.post(f"/admin/employees/{self.emp2_id}/reset-password", data={"csrf_token": "test-csrf"})
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(self.sent, [])

    # -- 12-14 admin password + role separation -----------------------------

    def test_12_admin_changes_own_password(self):
        client, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        response = client.post("/employee/account/password", data={
            "current_password": ADMIN_PASSWORD, "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD, "csrf_token": "test-csrf",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self._password_ok(self.admin_id, NEW_PASSWORD))

    def test_13_admin_recovers_by_email(self):
        self._client().post("/employee/forgot-password", data={
            "email": "pwtest.admin@example.test", "csrf_token": "test-csrf",
        })
        self.assertEqual(self.sent[-1]["to"], "pwtest.admin@example.test")
        _, token = self._last_link()
        self.assertEqual(self._use_link(self._client(), token).status_code, 302)
        self.assertTrue(self._password_ok(self.admin_id, NEW_PASSWORD))
        row = fetch_one(
            "SELECT UserRole FROM PasswordResetTokens WHERE UserID = %s ORDER BY TokenID DESC LIMIT 1;",
            (self.admin_id,),
        )
        self.assertEqual(row["UserRole"], "Admin")

    def test_14_tokens_are_role_bound(self):
        # A token minted with the wrong role for an account never validates.
        self.assertIsNone(password_service.get_valid_reset_token(
            password_service.issue_reset_token(self.admin_id, "Employee")))
        self.assertIsNone(password_service.get_valid_reset_token(
            password_service.issue_reset_token(self.emp_id, "Admin")))
        # An Employee token stops working if the account becomes an Admin.
        token = password_service.issue_reset_token(self.emp_id, "Employee")
        execute("UPDATE Users SET Role = 'Admin' WHERE UserID = %s;", (self.emp_id,))
        self.assertIsNone(password_service.redeem_reset_token(token, NEW_PASSWORD))
        self.assertTrue(self._password_ok(self.emp_id, EMP_PASSWORD))

    # -- 15 existing accounts ------------------------------------------------

    def test_15_existing_hash_format_authenticates(self):
        user = authenticate_employee(PREFIX + "emp", EMP_PASSWORD)
        self.assertIsNotNone(user)
        self.assertNotIn("Password", user)
        self.assertIsNone(authenticate_employee(PREFIX + "emp", "wrong-password-here"))
        # A pre-existing session issued before SessionEpoch existed stays valid.
        client = self._client()
        with client.session_transaction() as sess:
            sess.update({"UserID": self.emp_id, "Username": PREFIX + "emp", "Role": "Employee"})
        self.assertEqual(client.get("/employee/dashboard").status_code, 200)

    def test_15b_login_with_email(self):
        # Registered email works, trimmed and case-insensitive.
        client, _ = self._login("  PwTest.Emp@Example.test ", EMP_PASSWORD)
        self.assertTrue(self._logged_in(client))
        with client.session_transaction() as sess:
            self.assertEqual(sess["Username"], PREFIX + "emp")
        # Wrong password by email fails.
        client, response = self._login("pwtest.emp@example.test", "wrong-password-xyz")
        self.assertFalse(self._logged_in(client))
        self.assertIn(b"Invalid username/email or password", response.data)
        # An email shared by two accounts logs into neither; username still works.
        client, _ = self._login("pwtest.shared@example.test", EMP_PASSWORD)
        self.assertFalse(self._logged_in(client))
        client, _ = self._login(PREFIX + "dup1", EMP_PASSWORD)
        self.assertTrue(self._logged_in(client))
        # Unknown email fails.
        client, _ = self._login("nobody@example.test", EMP_PASSWORD)
        self.assertFalse(self._logged_in(client))

    def test_15c_username_and_email_share_one_login_limit(self):
        for index in range(10):
            identifier = PREFIX + "emp" if index % 2 else "pwtest.emp@example.test"
            self._login(identifier, "wrong-password-xyz")
        for identifier in (PREFIX + "emp", "pwtest.emp@example.test"):
            client, response = self._login(identifier, EMP_PASSWORD)
            self.assertIn(b"Too many failed login attempts", response.data)
            self.assertFalse(self._logged_in(client))

    # -- 16 session invalidation ---------------------------------------------

    def test_16_password_change_ends_other_sessions(self):
        device_a, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        device_b, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        self.assertEqual(device_b.get("/employee/dashboard").status_code, 200)
        device_a.post("/employee/account/password", data={
            "current_password": EMP_PASSWORD, "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD, "csrf_token": "test-csrf",
        })
        response = device_b.get("/employee/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/employee/login", response.headers["Location"])

    def test_16b_reset_ends_existing_sessions(self):
        device, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        token = password_service.issue_reset_token(self.emp_id, "Employee")
        self.assertIsNotNone(password_service.redeem_reset_token(token, NEW_PASSWORD))
        self.assertEqual(device.get("/employee/dashboard").status_code, 302)

    # -- 17 rate limiting + CSRF -----------------------------------------------

    def test_17_csrf_required(self):
        client = self._client()
        response = client.post("/employee/login", data={
            "username": PREFIX + "emp", "password": EMP_PASSWORD, "csrf_token": "wrong",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self._logged_in(client))
        client, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        client.post("/employee/account/password", data={
            "current_password": EMP_PASSWORD, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD,
        })
        self.assertTrue(self._password_ok(self.emp_id, EMP_PASSWORD))
        admin, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        admin.post(f"/admin/employees/{self.emp2_id}/reset-password", data={})
        self.assertEqual(self.sent, [])
        self.assertIn(b'name="csrf_token"', self._client().get("/employee/login").data)

    def test_17b_login_rate_limited(self):
        for _ in range(10):
            self._login(PREFIX + "emp", "wrong-password-xyz")
        client, response = self._login(PREFIX + "emp", EMP_PASSWORD)
        self.assertIn(b"Too many failed login attempts", response.data)
        self.assertFalse(self._logged_in(client))

    def test_17c_reset_request_rate_limited(self):
        for _ in range(3):
            self._client().post("/employee/forgot-password", data={
                "email": "pwtest.emp@example.test", "csrf_token": "test-csrf"})
        response = self._client().post("/employee/forgot-password", data={
            "email": "pwtest.emp@example.test", "csrf_token": "test-csrf"})
        self.assertIn(b"Too many reset requests", response.data)
        self.assertEqual(len(self.sent), 3)

    def test_17d_change_password_rate_limited(self):
        client, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        for _ in range(5):
            client.post("/employee/account/password", data={
                "current_password": "bad-guess-000", "new_password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD, "csrf_token": "test-csrf"})
        response = client.post("/employee/account/password", data={
            "current_password": EMP_PASSWORD, "new_password": NEW_PASSWORD,
            "confirm_password": NEW_PASSWORD, "csrf_token": "test-csrf"})
        self.assertIn(b"Too many incorrect attempts", response.data)
        self.assertTrue(self._password_ok(self.emp_id, EMP_PASSWORD))

    # -- 18-19 email configuration ---------------------------------------------

    def test_18_missing_email_config_fails_safely(self):
        count_sql = "SELECT COUNT(*) AS c FROM PasswordResetTokens WHERE UserID IN (%s, %s);"
        before = fetch_one(count_sql, (self.emp_id, self.emp2_id))["c"]
        with mock.patch.object(Config, "SMTP_HOST", ""):
            response = self._client().post("/employee/forgot-password", data={
                "email": "pwtest.emp@example.test", "csrf_token": "test-csrf"})
            self.assertIn(b"currently unavailable", response.data)
            ok, message = password_service.admin_initiate_reset(self.admin_id, self.emp2_id, lambda t: "/x/" + t)
            self.assertFalse(ok)
            self.assertIn("not configured", message)
        self.assertEqual(self.sent, [])
        # No token was created, so nothing could be exposed as a fallback.
        self.assertEqual(fetch_one(count_sql, (self.emp_id, self.emp2_id))["c"], before)

    def test_18b_delivery_failure_revokes_admin_link(self):
        with mock.patch.object(email_service, "send_email", side_effect=OSError("smtp down")):
            ok, message = password_service.admin_initiate_reset(self.admin_id, self.emp2_id, lambda t: "/x/" + t)
        self.assertFalse(ok)
        self.assertIn("could not be delivered", message)
        self.assertIsNone(fetch_one(
            "SELECT TokenID FROM PasswordResetTokens WHERE UserID = %s AND RevokedAt IS NULL AND UsedAt IS NULL;",
            (self.emp2_id,)))

    def test_19_plain_http_base_url_refused_in_production(self):
        with mock.patch.object(Config, "PUBLIC_BASE_URL", "http://www.example.test"), \
                mock.patch.object(Config, "DEBUG", False):
            self.assertFalse(email_service.is_email_configured())
            self.assertIsNone(email_service.public_base_url())

    # -- Add Employee (Admin) ----------------------------------------------------

    def _add_employee(self, client, **overrides):
        data = {
            "username": PREFIX + "new", "name": "New Hire", "email": "pwtest.new@example.test",
            "phone": "+91 90000 00000", "designation": "Sales Executive", "csrf_token": "test-csrf",
        }
        data.update(overrides)
        return client.post("/admin/employees/add", data=data, follow_redirects=True)

    def test_21_admin_adds_employee_who_sets_own_password(self):
        admin, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        self.assertEqual(admin.get("/admin/employees/add").status_code, 200)
        response = self._add_employee(admin, email=" PwTest.New@Example.test ")
        self.assertIn(b"was created. A link to set their password was emailed", response.data)

        row = fetch_one(
            "SELECT u.UserID, u.Role, u.Password, e.Name, e.Email, e.Phone, e.Designation FROM Users u "
            "JOIN Employees e ON e.UserID = u.UserID WHERE u.Username = %s;", (PREFIX + "new",),
        )
        self.assertEqual(row["Role"], "Employee")
        self.assertEqual(row["Email"], "pwtest.new@example.test")
        self.assertEqual((row["Name"], row["Designation"]), ("New Hire", "Sales Executive"))
        self.assertTrue(row["Password"].startswith(("scrypt:", "pbkdf2:")))  # unusable random hash

        mail = self.sent[-1]
        self.assertEqual(mail["to"], "pwtest.new@example.test")
        self.assertIn("Set up your", mail["subject"])
        _, token = self._last_link()
        self.assertNotIn(token.encode(), response.data)  # the admin never sees the link
        audit = fetch_one(
            "SELECT InitiatedByUserID FROM PasswordResetTokens WHERE UserID = %s;", (row["UserID"],))
        self.assertEqual(audit["InitiatedByUserID"], self.admin_id)

        # The new employee sets a password from the link, then logs in by email.
        self.assertEqual(self._use_link(self._client(), token).status_code, 302)
        client, _ = self._login("pwtest.new@example.test", NEW_PASSWORD)
        self.assertTrue(self._logged_in(client))
        self.assertEqual(client.get("/employee/dashboard").status_code, 200)
        self.assertEqual(client.get("/admin/employees").status_code, 403)

    def test_22_add_employee_validation(self):
        admin, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        cases = (
            ({"username": PREFIX + "emp"}, b"already taken"),
            ({"username": PREFIX.upper() + "EMP"}, b"already taken"),
            ({"username": "pwtest_x@y"}, b"no spaces or @"),
            ({"username": "ab"}, b"3-50 characters"),
            ({"email": "pwtest.emp@example.test"}, b"already uses this email"),
            ({"email": "not-an-email"}, b"valid email"),
            ({"email": ""}, b"Email is required"),
            ({"name": ""}, b"Full name is required"),
            ({"phone": "call me"}, b"valid phone"),
        )
        for overrides, expected in cases:
            response = self._add_employee(admin, **overrides)
            self.assertIn(expected, response.data, overrides)
        self.assertIsNone(fetch_one("SELECT UserID FROM Users WHERE Username = %s;", (PREFIX + "new",)))
        self.assertEqual(self.sent, [])

    def test_23_add_employee_requires_admin_and_csrf(self):
        anonymous = self._client().post("/admin/employees/add", data={"csrf_token": "test-csrf"})
        self.assertIn("/employee/login", anonymous.headers["Location"])
        employee, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        self.assertEqual(employee.get("/admin/employees/add").status_code, 403)
        self.assertEqual(self._add_employee(employee).status_code, 403)
        admin, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        self._add_employee(admin, csrf_token="wrong")
        self.assertIsNone(fetch_one("SELECT UserID FROM Users WHERE Username = %s;", (PREFIX + "new",)))

    def test_24_add_employee_without_email_config_creates_nothing(self):
        admin, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        with mock.patch.object(Config, "SMTP_HOST", ""):
            response = self._add_employee(admin)
        self.assertIn(b"outgoing email is not configured", response.data)
        self.assertIsNone(fetch_one("SELECT UserID FROM Users WHERE Username = %s;", (PREFIX + "new",)))

    def test_25_add_employee_delivery_failure_keeps_account_revokes_link(self):
        admin, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        with mock.patch.object(email_service, "send_email", side_effect=OSError("smtp down")):
            response = self._add_employee(admin)
        self.assertIn(b"could not be delivered", response.data)
        row = fetch_one("SELECT UserID FROM Users WHERE Username = %s;", (PREFIX + "new",))
        self.assertIsNotNone(row)
        self.assertIsNone(fetch_one(
            "SELECT TokenID FROM PasswordResetTokens WHERE UserID = %s AND RevokedAt IS NULL AND UsedAt IS NULL;",
            (row["UserID"],)))

    def setUp_new_account_cleanup(self):
        user = fetch_one("SELECT UserID FROM Users WHERE Username = %s;", (PREFIX + "new",))
        if user:
            execute("DELETE FROM PasswordResetTokens WHERE UserID = %s;", (user["UserID"],))
            execute("DELETE FROM Employees WHERE UserID = %s;", (user["UserID"],))
            execute("DELETE FROM Users WHERE UserID = %s;", (user["UserID"],))

    # -- 20 existing portal still works ------------------------------------------

    def test_20_existing_pages_still_work(self):
        client, _ = self._login(PREFIX + "admin", ADMIN_PASSWORD)
        for path in ("/employee/dashboard", "/employee/products", "/employee/inventory",
                     "/employee/departments", "/employee/enquiries", "/employee/customers",
                     "/employee/account/password", "/admin/employees", "/health"):
            self.assertEqual(client.get(path).status_code, 200, path)
        dashboard = client.get("/employee/dashboard").data
        self.assertIn(b"/admin/employees", dashboard)
        employee, _ = self._login(PREFIX + "emp", EMP_PASSWORD)
        self.assertNotIn(b"/admin/employees", employee.get("/employee/dashboard").data)
        self.assertEqual(self._client().get("/employee/forgot-password").status_code, 200)
        logout = employee.get("/employee/logout")
        self.assertEqual(logout.status_code, 302)


if __name__ == "__main__":
    unittest.main(verbosity=2)
