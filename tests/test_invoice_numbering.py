"""
=========================================================
Project : Sridevi Enterprises
File    : test_invoice_numbering.py
Purpose : Integration tests for Admin Invoice Number Configuration
          (InvoiceNumber allocation, /admin/invoice-numbering, audit,
          concurrency, rollback, and that GST/price overrides and existing
          invoices are unaffected).

          Runs against the LOCAL development database only (refuses any
          non-local DB_HOST) with migrations 018-020 applied. Creates
          temporary "invnumtest_" accounts, a temporary Catalog product and
          temporary invoices, and deletes all of them - plus their audit and
          throttle rows - when finished. The sequence's NextNumber is
          restored to its value before the run, and every pre-existing
          invoice/line item is snapshotted and asserted unchanged.

          Note: InnoDB never lowers AUTO_INCREMENT, so Invoices.InvoiceID /
          InvoiceItems.ItemID on the dev database advance past the deleted
          test rows. That is internal only - customer-visible numbers come
          from InvoiceNumberSequence, which is restored.

Usage   : python -m unittest tests.test_invoice_numbering -v
Author  : Srikar
=========================================================
"""

import os
import sys
import threading
import unittest
from decimal import Decimal
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.datastructures import MultiDict  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from config import Config  # noqa: E402

if Config.DB_HOST not in ("127.0.0.1", "localhost", "::1"):
    raise SystemExit("Refusing to run: these tests only run against a local development database.")

from app import app  # noqa: E402
from database.db import execute, fetch_all, fetch_one  # noqa: E402
from services import invoice_number_service  # noqa: E402
from services.invoice_service import create_invoice, get_invoice, get_invoices, validate_invoice_form  # noqa: E402
from services.pdf_service import _build_context  # noqa: E402

PREFIX = "invnumtest_"
ADMIN_PASSWORD = "Admin-Invoice-Pass-4821"
EMP_PASSWORD = "Employee-Invoice-Pass-9137"
TEST_SELLER_GSTIN = "37ABCDE1234F1Z5"   # Andhra Pradesh (37) - test value only
CATALOG_PRICE = Decimal("1180.00")
CATALOG_GST = Decimal("18.00")


def _sequence_next() -> int:
    return int(fetch_one("SELECT NextNumber FROM InvoiceNumberSequence WHERE SequenceID = 1;")["NextNumber"])


def _highest_issued() -> int:
    row = fetch_one("SELECT MAX(InvoiceNumber) AS h FROM Invoices;")
    return int(row["h"] or 0)


def _create_account(username, role, password):
    execute(
        "INSERT INTO Users (Username, Password, Role) VALUES (%s, %s, %s);",
        (username, generate_password_hash(password), role),
    )
    user_id = fetch_one("SELECT UserID FROM Users WHERE Username = %s;", (username,))["UserID"]
    execute(
        "INSERT INTO Employees (UserID, Name, Email, Designation) VALUES (%s, %s, %s, %s);",
        (user_id, username, f"{username}@example.test", "Test"),
    )
    employee_id = fetch_one("SELECT EmployeeID FROM Employees WHERE UserID = %s;", (user_id,))["EmployeeID"]
    return user_id, employee_id


def _cleanup():
    """Delete every row this test module can have created."""

    users = fetch_all("SELECT UserID FROM Users WHERE Username LIKE %s;", (PREFIX + "%",))
    for user in users:
        user_id = user["UserID"]
        employee = fetch_one("SELECT EmployeeID FROM Employees WHERE UserID = %s;", (user_id,))
        if employee:
            invoice_ids = [r["InvoiceID"] for r in fetch_all(
                "SELECT InvoiceID FROM Invoices WHERE CreatedBy = %s;", (employee["EmployeeID"],)
            )]
            for invoice_id in invoice_ids:
                execute("DELETE FROM InvoiceItems WHERE InvoiceID = %s;", (invoice_id,))
                execute("DELETE FROM Invoices WHERE InvoiceID = %s;", (invoice_id,))
        execute("DELETE FROM InvoiceNumberAudit WHERE AdminUserID = %s;", (user_id,))
        execute("DELETE FROM PasswordResetTokens WHERE UserID = %s OR InitiatedByUserID = %s;", (user_id, user_id))
        execute("DELETE FROM Employees WHERE UserID = %s;", (user_id,))
        execute("DELETE FROM Users WHERE UserID = %s;", (user_id,))
    execute("DELETE FROM Catalog WHERE product_id LIKE %s;", (PREFIX + "%",))


class InvoiceNumberingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["SESSION_COOKIE_SECURE"] = False

        if fetch_one("SHOW TABLES LIKE 'InvoiceNumberSequence';") is None:
            raise unittest.SkipTest("Migrations 018-020 are not applied to the local database.")

        _cleanup()
        cls.start = fetch_one("SELECT UTC_TIMESTAMP() - INTERVAL 1 SECOND AS t;")["t"]
        cls.original_next = _sequence_next()
        cls.existing_invoices = fetch_all("SELECT * FROM Invoices ORDER BY InvoiceID;")
        cls.existing_items = fetch_all("SELECT * FROM InvoiceItems ORDER BY ItemID;")
        cls.existing_audit_count = fetch_one("SELECT COUNT(*) AS n FROM InvoiceNumberAudit;")["n"]

        cls.admin_user_id, cls.admin_employee_id = _create_account(PREFIX + "admin", "Admin", ADMIN_PASSWORD)
        cls.emp_user_id, cls.emp_employee_id = _create_account(PREFIX + "emp", "Employee", EMP_PASSWORD)

        execute("""
            INSERT INTO Catalog (product_id, product_name, Department, category, brand, model,
                                 base_price, offer_price, gst_percent, stock_quantity, IsActive)
            VALUES (%s, %s, 'Test', 'Test', 'TestBrand', 'TM-1', %s, %s, %s, 0, 1);
        """, (PREFIX + "p1", PREFIX + "Product", CATALOG_PRICE, CATALOG_PRICE, CATALOG_GST))
        cls.product_id = fetch_one("SELECT id FROM Catalog WHERE product_id = %s;", (PREFIX + "p1",))["id"]

        # Requested scenario uses 1001; fall back above the live sequence if
        # the dev database has already issued that many invoices.
        floor = max(cls.original_next, _highest_issued() + 1)
        cls.target = 1001 if 1001 > floor else floor + 1000

        cls.gstin_patch = mock.patch.object(Config, "SELLER_GSTIN", TEST_SELLER_GSTIN)
        cls.gstin_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.gstin_patch.stop()
        _cleanup()
        execute(
            "DELETE FROM AuthThrottle WHERE Action = %s AND CreatedAt >= %s;",
            (invoice_number_service.REAUTH_ACTION, cls.start),
        )
        execute(
            "UPDATE InvoiceNumberSequence SET NextNumber = %s, UpdatedAt = UTC_TIMESTAMP() WHERE SequenceID = 1;",
            (cls.original_next,),
        )

        assert _sequence_next() == cls.original_next, "Sequence was not restored!"
        assert fetch_all("SELECT * FROM Invoices ORDER BY InvoiceID;") == cls.existing_invoices, \
            "Existing invoices were modified!"
        assert fetch_all("SELECT * FROM InvoiceItems ORDER BY ItemID;") == cls.existing_items, \
            "Existing invoice items were modified!"
        assert fetch_one("SELECT COUNT(*) AS n FROM InvoiceNumberAudit;")["n"] == cls.existing_audit_count, \
            "Test audit rows were left behind!"

    def setUp(self):
        execute(
            "DELETE FROM AuthThrottle WHERE Action = %s AND CreatedAt >= %s;",
            (invoice_number_service.REAUTH_ACTION, self.start),
        )

    # -- helpers ---------------------------------------------------------

    def _client(self, user_id=None, role=None, username=None):
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["_csrf_token"] = "test-csrf"
            if user_id:
                sess["UserID"] = user_id
                sess["Role"] = role
                sess["Username"] = username
                sess["SessionEpoch"] = 0
        return client

    def _admin(self):
        return self._client(self.admin_user_id, "Admin", PREFIX + "admin")

    def _employee(self):
        return self._client(self.emp_user_id, "Employee", PREFIX + "emp")

    def _post_setting(self, client, value, password=ADMIN_PASSWORD, confirm=True, csrf="test-csrf"):
        data = {"next_number": value, "password": password}
        if confirm:
            data["confirm"] = "yes"
        if csrf is not None:
            data["csrf_token"] = csrf
        return client.post("/admin/invoice-numbering", data=data)

    def _set_sequence(self, value):
        """Test-only direct positioning (bypasses the Admin rules on purpose)."""
        execute("UPDATE InvoiceNumberSequence SET NextNumber = %s WHERE SequenceID = 1;", (value,))

    def _cleaned(self, buyer_state="37", unit_price=None, quantity=1, hsn="8516"):
        form = MultiDict([
            ("buyer_name", "Test Buyer"), ("buyer_address", "1 Test Street"), ("buyer_contact", ""),
            ("buyer_gstin", ""), ("buyer_contract", ""), ("consignee_same_as_buyer", "1"),
            ("consignee_contract", ""), ("buyer_state", buyer_state),
            ("product_id[]", str(self.product_id)), ("qty[]", str(quantity)), ("hsn[]", hsn),
            ("price[]", str(unit_price if unit_price is not None else CATALOG_PRICE)),
        ])
        cleaned, errors = validate_invoice_form(form)
        self.assertEqual(errors, {})
        return cleaned

    def _create(self, **kwargs):
        return create_invoice(self._cleaned(**kwargs), self.emp_employee_id)

    def _pdf_number(self, invoice_id):
        """The invoice number exactly as services/pdf_service.py hands it to invoice_pdf.html."""
        with app.app_context():
            return _build_context(get_invoice(invoice_id))["invoice_number"]

    def _audit_rows(self):
        return fetch_all(
            "SELECT * FROM InvoiceNumberAudit WHERE AdminUserID = %s ORDER BY AuditID;", (self.admin_user_id,)
        )

    # -- 1-2 set the next number, then 1001, 1002 ------------------------

    def test_01_set_next_number_then_invoice_gets_it(self):
        old_next = _sequence_next()
        response = self._post_setting(self._admin(), str(self.target))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(_sequence_next(), self.target)

        audit = self._audit_rows()[-1]
        self.assertEqual(
            (audit["OldNextNumber"], audit["NewNextNumber"], audit["HighestIssued"]),
            (old_next, self.target, _highest_issued()),
        )
        utc_now = fetch_one("SELECT UTC_TIMESTAMP() AS t;")["t"]
        self.assertLessEqual(abs((utc_now - audit["ChangedAt"]).total_seconds()), 60, "ChangedAt must be UTC")

        # Through the real New Invoice route: flash + redirect show the number.
        client = self._employee()
        response = client.post("/employee/invoices/new", data={
            "buyer_name": "Route Buyer", "buyer_address": "2 Test Street", "buyer_state": "37",
            "consignee_same_as_buyer": "1",
            "product_id[]": str(self.product_id), "qty[]": "1", "hsn[]": "8516", "price[]": str(CATALOG_PRICE),
        })
        self.assertEqual(response.status_code, 302)
        invoice = fetch_one(
            "SELECT InvoiceID, InvoiceNumber FROM Invoices WHERE CreatedBy = %s ORDER BY InvoiceID DESC LIMIT 1;",
            (self.emp_employee_id,),
        )
        self.assertEqual(invoice["InvoiceNumber"], self.target)
        self.assertTrue(response.headers["Location"].endswith(f"/employee/invoices/{invoice['InvoiceID']}"))
        page = client.get(response.headers["Location"]).get_data(as_text=True)
        self.assertIn(f"Invoice #{self.target:05d}", page)
        self.assertEqual(self._pdf_number(invoice["InvoiceID"]), f"{self.target:05d}")

        # PDF download filename uses the customer-visible number (needs
        # Playwright Chromium; skipped quietly where it isn't installed).
        response = client.get(f"/employee/invoices/{invoice['InvoiceID']}/pdf")
        if response.mimetype == "application/pdf":
            self.assertIn(f'filename="Invoice_{self.target:05d}.pdf"', response.headers["Content-Disposition"])

        # History search finds it by its customer-visible number.
        found = get_invoices({"search": f"{self.target:05d}"}, 1, 20)
        self.assertEqual([row["InvoiceNumber"] for row in found], [self.target])

    def test_02_following_invoice_gets_next_number(self):
        expected = _sequence_next()
        self.assertEqual(expected, self.target + 1)
        _, number = self._create()
        self.assertEqual(number, self.target + 1)
        self.assertEqual(_sequence_next(), self.target + 2)

    # -- 3 duplicates / used / lower / unchanged -------------------------

    def test_03_rejects_used_lower_or_unchanged_numbers(self):
        before_next, before_audit = _sequence_next(), len(self._audit_rows())
        highest = _highest_issued()
        admin = self._admin()

        for value, fragment in (
            (str(highest), "can never be reused"),          # already issued
            (str(self.target), "can never be reused"),      # used earlier in this run
            ("1", "can never be reused"),                   # far below
            (str(before_next), "no change was made"),       # same as current next
        ):
            with self.subTest(value=value):
                response = self._post_setting(admin, value)
                self.assertEqual(response.status_code, 200)
                self.assertIn(fragment, response.get_data(as_text=True))

        # Lower than the current next but above every issued number: still refused.
        self._set_sequence(highest + 50)
        response = self._post_setting(admin, str(highest + 10))
        self.assertIn("can only be increased", response.get_data(as_text=True))
        self.assertEqual(_sequence_next(), highest + 50)
        self._set_sequence(before_next)

        self.assertEqual(_sequence_next(), before_next)
        self.assertEqual(len(self._audit_rows()), before_audit)

    # -- 4 invalid input -------------------------------------------------

    def test_04_rejects_invalid_input(self):
        before_next, before_audit = _sequence_next(), len(self._audit_rows())
        admin = self._admin()
        valid = str(before_next + 5)

        for value in ("", "   ", "0", "-5", "abc", "12.5", "1e3", "+50", "100000000", "999999999999", "١٢٣"):
            with self.subTest(value=value):
                response = self._post_setting(admin, value)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(_sequence_next(), before_next)

        # Missing confirmation, missing password, wrong password, missing CSRF.
        self.assertIn("Tick the confirmation", self._post_setting(admin, valid, confirm=False).get_data(as_text=True))
        self.assertIn("Enter your password", self._post_setting(admin, valid, password="").get_data(as_text=True))
        self.assertIn("Incorrect password", self._post_setting(admin, valid, password=EMP_PASSWORD).get_data(as_text=True))
        response = self._post_setting(admin, valid, csrf=None)
        self.assertEqual(response.status_code, 302)   # @csrf_protect: friendly redirect, nothing done

        self.assertEqual(_sequence_next(), before_next)
        self.assertEqual(len(self._audit_rows()), before_audit)

        # Reauthentication is rate limited (5 wrong attempts / 15 min).
        for _ in range(5):
            self._post_setting(admin, valid, password="wrong-password-xyz")
        response = self._post_setting(admin, valid)   # correct password, but locked out
        self.assertIn("Too many incorrect password attempts", response.get_data(as_text=True))
        self.assertEqual(_sequence_next(), before_next)

    # -- 5 authorization -------------------------------------------------

    def test_05_employees_and_anonymous_are_refused(self):
        before_next = _sequence_next()
        employee = self._employee()

        self.assertEqual(employee.get("/admin/invoice-numbering").status_code, 403)
        self.assertEqual(self._post_setting(employee, str(before_next + 5), password=EMP_PASSWORD).status_code, 403)
        self.assertEqual(self._post_setting(employee, str(before_next + 5), csrf=None).status_code, 403)

        anonymous = self._client()
        response = anonymous.get("/admin/invoice-numbering")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/employee/login", response.headers["Location"])

        # Service layer re-checks the role too.
        ok, _, _ = invoice_number_service.set_next_number(self.emp_user_id, str(before_next + 5), EMP_PASSWORD, True)
        self.assertFalse(ok)
        self.assertEqual(_sequence_next(), before_next)

        # The page renders for an Admin and the nav link is Admin-only.
        self.assertEqual(self._admin().get("/admin/invoice-numbering").status_code, 200)
        self.assertNotIn("/admin/invoice-numbering", employee.get("/employee/invoices").get_data(as_text=True))

    # -- 6 concurrency ---------------------------------------------------

    def test_06_concurrent_creation_never_duplicates(self):
        start_next = _sequence_next()
        thread_count = 8
        results, failures = [], []
        barrier = threading.Barrier(thread_count)
        cleaned = self._cleaned()

        def worker():
            try:
                barrier.wait()
                results.append(create_invoice(cleaned, self.emp_employee_id)[1])
            except Exception as error:  # pragma: no cover - reported below
                failures.append(repr(error))

        threads = [threading.Thread(target=worker) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=120)

        self.assertEqual(failures, [])
        self.assertEqual(sorted(results), list(range(start_next, start_next + thread_count)))
        self.assertEqual(_sequence_next(), start_next + thread_count)

    # -- 7 existing invoices / PDFs unchanged ----------------------------

    def test_07_existing_invoices_and_pdfs_unchanged(self):
        for original in self.existing_invoices:
            with self.subTest(invoice_id=original["InvoiceID"]):
                # Migration 018 preserved the number that was printed before it.
                self.assertEqual(original["InvoiceNumber"], original["InvoiceID"])
                self.assertEqual(self._pdf_number(original["InvoiceID"]), f"{original['InvoiceID']:05d}")
                self.assertEqual(
                    fetch_one("SELECT * FROM Invoices WHERE InvoiceID = %s;", (original["InvoiceID"],)), original
                )

    # -- 8 failed creation rolls back the number -------------------------

    def test_08_failed_creation_does_not_consume_a_number(self):
        before_next = _sequence_next()
        before_count = fetch_one("SELECT COUNT(*) AS n FROM Invoices;")["n"]

        # A database error AFTER the number was allocated and the Invoices row
        # inserted: HSN longer than InvoiceItems.HSN VARCHAR(20).
        with self.assertRaises(Exception):
            self._create(hsn="H" * 40)
        self.assertEqual(_sequence_next(), before_next)
        self.assertEqual(fetch_one("SELECT COUNT(*) AS n FROM Invoices;")["n"], before_count)

        # A failure injected after allocation, before any invoice row exists.
        from services import invoice_service
        real_allocate = invoice_service.allocate_invoice_number

        def allocate_then_fail(cursor):
            real_allocate(cursor)
            raise RuntimeError("simulated failure after allocation")

        with mock.patch.object(invoice_service, "allocate_invoice_number", side_effect=allocate_then_fail):
            with self.assertRaises(RuntimeError):
                self._create()
        self.assertEqual(_sequence_next(), before_next)

        # A validation-stage refusal (product deactivated since the form
        # loaded) never even reaches allocation.
        execute("UPDATE Catalog SET IsActive = 0 WHERE id = %s;", (self.product_id,))
        try:
            with mock.patch.object(invoice_service, "allocate_invoice_number", wraps=real_allocate) as spy:
                with self.assertRaises(ValueError):
                    self._create()
                spy.assert_not_called()
        finally:
            execute("UPDATE Catalog SET IsActive = 1 WHERE id = %s;", (self.product_id,))
        self.assertEqual(_sequence_next(), before_next)
        self.assertEqual(fetch_one("SELECT COUNT(*) AS n FROM Invoices;")["n"], before_count)

        # The next successful invoice gets exactly the number the failures did not use.
        _, number = self._create()
        self.assertEqual(number, before_next)

    # -- 9 GST / calculations / price overrides unaffected ---------------

    def test_09_gst_and_price_overrides_unaffected(self):
        # Intra-state (37 -> 37), catalog price 1180 incl. 18% GST, qty 2.
        invoice_id, _ = self._create(quantity=2)
        invoice = get_invoice(invoice_id)
        self.assertEqual(
            (invoice["TaxableTotal"], invoice["CGSTTotal"], invoice["SGSTTotal"], invoice["IGSTTotal"],
             invoice["RoundOff"], invoice["GrandTotal"]),
            (Decimal("2000.00"), Decimal("180.00"), Decimal("180.00"), Decimal("0.00"),
             Decimal("0.00"), Decimal("2360.00")),
        )
        self.assertEqual(invoice["AmountInWords"], "INR Two Thousand Three Hundred Sixty Rupees Only")

        # Inter-state (37 -> 33) with a row price override of 1000.
        invoice_id, _ = self._create(buyer_state="33", unit_price=Decimal("1000.00"))
        invoice = get_invoice(invoice_id)
        item = invoice["items"][0]
        self.assertEqual(item["UnitPrice"], Decimal("1000.00"))
        self.assertEqual(
            (item["TaxableValue"], item["CGSTAmount"], item["SGSTAmount"], item["IGSTAmount"], item["LineTotal"]),
            (Decimal("847.46"), Decimal("0.00"), Decimal("0.00"), Decimal("152.54"), Decimal("1000.00")),
        )
        self.assertEqual(invoice["GrandTotal"], Decimal("1000.00"))

        # The override never writes back to Catalog.
        catalog = fetch_one("SELECT offer_price, gst_percent FROM Catalog WHERE id = %s;", (self.product_id,))
        self.assertEqual((catalog["offer_price"], catalog["gst_percent"]), (CATALOG_PRICE, CATALOG_GST))

    # -- 10 upper limit --------------------------------------------------

    def test_10_upper_limit_and_exhaustion(self):
        maximum = invoice_number_service.MAX_INVOICE_NUMBER
        response = self._post_setting(self._admin(), f"{maximum:,}")   # "99,999,999" with commas is accepted
        self.assertEqual(response.status_code, 302)
        self.assertEqual(_sequence_next(), maximum)

        _, number = self._create()
        self.assertEqual(number, maximum)
        self.assertEqual(_sequence_next(), maximum + 1)

        before_count = fetch_one("SELECT COUNT(*) AS n FROM Invoices;")["n"]
        with self.assertRaises(ValueError):
            self._create()
        self.assertEqual(_sequence_next(), maximum + 1)
        self.assertEqual(fetch_one("SELECT COUNT(*) AS n FROM Invoices;")["n"], before_count)


if __name__ == "__main__":
    unittest.main()
