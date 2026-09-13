# Error Codes Reference

Canonical list of every user-facing error code shown by the application. When
an employee reports "error PDF-02" or similar, look it up here first — it
names the failing step, the likely cause, and the fix, without needing
server log access.

**Convention going forward:** any new code shown to a user (a new `flash(...,
"danger")` message with a code, a new raised exception carrying one) gets a
row added here in the same change that introduces it. A code with no entry
here is a bug in this file, not just the code itself — keep them in sync.

Full tracebacks are always logged server-side too (`logger.exception(...)`,
written to stderr — see `DEPLOYMENT.md` § on the error log). A code is a
pointer to that detail for a quick first look, not a replacement for it when
the cause isn't obvious from the table alone.

---

## PDF-xx — Invoice PDF generation (`services/pdf_service.py:render_invoice_pdf()`)

Shown on `GET /employee/invoices/<id>/pdf` when Chromium fails to produce the
PDF. Each code marks a different step of that pipeline, in the order they run.

| Code | Step | Likely cause | Fix |
|---|---|---|---|
| `PDF-01` | Building the invoice HTML (`render_template`) | A template error in `templates/invoice_pdf.html`, or bad/missing data on the `invoice` dict | Check the traceback for a Jinja error; confirm the invoice's row in `Invoices`/`InvoiceItems` has all required columns populated |
| `PDF-02` | Launching headless Chromium (`_get_browser()`) | Playwright's Chromium binary isn't installed for this environment, or failed to start | Run `playwright install chromium` in the active venv (see `DEPLOYMENT.md` § 1.3/1.5); confirm `playwright` is actually importable (`python -c "import playwright"`) in the **same** venv the running server uses |
| `PDF-03` | Opening a new browser page (`browser.new_page()`) | Chromium crashed or was killed after launching (OOM, antivirus, a stale process holding a lock) | Restart the app process; check whether a leftover `chrome.exe`/`headless_shell` process needs killing first |
| `PDF-04` | Loading the invoice content into the page (`page.set_content()`) | Malformed HTML/CSS reaching Chromium, or a `data:` URI (logo/signature image) too large/corrupt | Check the traceback; try regenerating `static/images/invoice_logo_badge.png` / `signature.png` if either was recently replaced |
| `PDF-05` | Converting the page to PDF (`page.pdf()`) | Chromium's print pipeline itself failed mid-render | Check the traceback; often transient — retry once before investigating further |
| `PDF-06` | Empty output | `page.pdf()` returned successfully but with zero bytes | Treat as `PDF-05` — something upstream produced a blank page; check the invoice's data for anything that could render as a fully empty document |
| `PDF-99` | Unexpected / uncategorized | Anything not caught by `PDFGenerationError` above | Always check the full traceback — this is the catch-all, not a specific diagnosis |

## INV-xx — Invoice creation (`routes/receipts.py:new_invoice()`)

Shown on the New Invoice form (`POST /employee/invoices/new`) when an invoice
can't be created. Unlike PDF-xx, these are shown as a form-level error banner,
not a PDF-download failure.

| Code | Meaning | Likely cause | Fix |
|---|---|---|---|
| `INV-01` | The logged-in user has no linked `Employees` row | `Users.UserID` exists but `Employees.UserID` was never set for this account (see `services/auth_service.get_employee_id_for_user()`) | Link the account to an `Employees` row, or have an admin do so |
| `INV-02` | Expected refusal from `services/invoice_service.create_invoice()` | The message text itself names the specific reason — commonly: `Config.SELLER_GSTIN` not set (see `.env`'s `SELLER_GSTIN`), or a product/model was deactivated or deleted after the form was loaded | Read the rest of the message; it's self-describing. Set `SELLER_GSTIN` in `.env`, or remove/re-select the affected product row and resubmit |
| `INV-99` | Unexpected / uncategorized | Anything not raised as a plain `ValueError` by `create_invoice()` | Always check the full traceback |

---

## Adding a new code

1. Pick the next unused number in the relevant prefix (`PDF-`, `INV-`, or a new prefix for a new module/feature).
2. Reserve `-99` in every prefix for "unexpected, uncaught" — never assign `-99` to a specific, known cause.
3. Add a row here: code, what failed, likely cause, fix. Keep the "likely cause"/"fix" columns actionable, not just a restatement of the code's name.
4. Reference this file from the code that raises/shows the error (a short comment or docstring line), so a reader lands here without having to already know it exists.
