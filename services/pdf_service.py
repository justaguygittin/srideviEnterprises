"""
=========================================================
Project : Sridevi Enterprises
File    : pdf_service.py
Purpose : Renders the Invoice Generator's printable HTML
          (templates/invoice_pdf.html) to a PDF using Playwright's headless
          Chromium.

          Replaces the standalone Receipt Generator project's xhtml2pdf,
          which renders through a limited, non-browser layout engine
          (reportlab) - see AI_CONTEXT.md "Invoice Generator Module
          (Merge)" for the concrete layout bugs that motivated the switch.
          Chromium is a real browser: the invoice template
          (templates/invoice_pdf.html) is ordinary HTML/CSS written for
          print, with no reportlab-specific workarounds.

Author  : Srikar
=========================================================
"""

import atexit
import base64
import logging
import os
import threading

from flask import current_app, render_template
from playwright.sync_api import sync_playwright

from config import Config
from services import gst_service

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """
    Raised when invoice PDF rendering fails, carrying a short, stable code
    (e.g. "PDF-02") identifying which step failed - shown to the employee
    alongside a plain-language message (routes/receipts.py) so a failure
    can be reported and looked up precisely, without needing server log
    access every time. The full original exception is always chained
    (`raise ... from error`) and still logged in full server-side via
    `logger.exception()` - the code is a pointer to that detail, not a
    replacement for it.

    Every code this class can carry is documented in ERROR_CODES.md
    (PDF-xx section) - add a row there for any new code added here.
    """

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


# A cropped, badge-only version of static/images/logo.png (no "SRIDEVI
# ENTERPRISES" wordmark) - the invoice header already prints that name as
# text right next to the image, so embedding the full stacked logo there
# would duplicate it and render as an oddly tall thumbnail. Kept as its
# own asset rather than cropping the shared sitewide logo at render time,
# so nothing here can ever affect how the navbar/footer logo looks.
_LOGO_RELATIVE_PATH = os.path.join("static", "images", "invoice_logo_badge.png")

# Optional: the proprietor's signature/stamp, printed over "Authorised
# Signatory" on the generated PDF. Not committed to this repo by default -
# a business's own signature image belongs in the deployment's own asset
# set, not in version control. If the file doesn't exist, the invoice
# still renders correctly - it simply leaves the space blank, exactly as
# it did before this image was ever added.
_SIGNATURE_RELATIVE_PATH = os.path.join("static", "images", "signature.png")

_playwright = None
_browser = None
_browser_lock = threading.Lock()


def _logo_data_uri() -> str:
    """
    Base64-embed the showroom logo directly into the invoice HTML instead
    of referencing it by a static/ URL.

    Chromium renders this HTML from an in-memory string
    (page.set_content()), which has no base URL to resolve a relative
    "static/logo.png" against - exactly the class of asset-path bug the
    standalone Receipt Generator's xhtml2pdf template had under Passenger
    (see the prior code audit: the logo silently failed to render in
    production because xhtml2pdf resolved it against the wrong working
    directory). A data: URI has no path to resolve at all, so it renders
    identically in local development, under Passenger, and inside
    Playwright's headless browser.
    """

    logo_path = os.path.join(current_app.root_path, _LOGO_RELATIVE_PATH)
    try:
        with open(logo_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except OSError:
        logger.warning("Invoice logo not found at %s - invoice will render without it.", logo_path)
        return ""


def _signature_data_uri() -> str:
    """
    Base64-embed the proprietor's signature/stamp image, if one has been
    placed at static/images/signature.png. Returns "" (not an error) when
    the file is absent, so a deployment without a signature image yet
    still renders a perfectly valid invoice - just with blank space above
    "Authorised Signatory", exactly as before this image existed.
    """

    signature_path = os.path.join(current_app.root_path, _SIGNATURE_RELATIVE_PATH)
    try:
        with open(signature_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except OSError:
        return ""


def _get_browser():
    """
    Lazily launch one shared headless Chromium instance for the life of
    this worker process, rather than paying Chromium's startup cost on
    every single PDF request. Guarded by a lock because Passenger may serve
    requests to the same process from more than one thread depending on
    its configured concurrency model - without it, two requests arriving
    at once could each see `_browser is None` and launch a second,
    wasted Chromium instance.
    """

    global _playwright, _browser
    if _browser is None:
        with _browser_lock:
            if _browser is None:  # re-check: another thread may have won the race
                _playwright = sync_playwright().start()
                _browser = _playwright.chromium.launch()
                logger.info("Playwright Chromium launched for PDF rendering.")
    return _browser


@atexit.register
def _shutdown_browser():
    """Close Chromium cleanly when this worker process exits."""

    if _browser is not None:
        try:
            _browser.close()
            _playwright.stop()
        except Exception:
            logger.exception("Error while shutting down Playwright Chromium.")


def _build_context(invoice: dict) -> dict:
    """
    Assemble every value templates/invoice_pdf.html needs, so the template
    itself never reads Config or does date/state-code formatting - matching
    this codebase's convention of preparing plain, display-ready values in
    Python (see app.py:inject_business_details()).
    """

    return {
        "invoice": invoice,
        "tax_type": gst_service.determine_tax_type(invoice["SellerState"], invoice["BuyerState"]),
        "buyer_state_name": gst_service.state_name(invoice["BuyerState"]),
        "seller_state_name": gst_service.state_name(invoice["SellerState"]),
        "invoice_number": f"{invoice['InvoiceID']:05d}",
        "invoice_date": invoice["InvoiceDate"].strftime("%d-%m-%Y"),
        "seller": {
            "name": "SRIDEVI ENTERPRISES",
            "address": Config.BUSINESS_ADDRESS,
            "phone": Config.BUSINESS_PHONE,
            "gstin": Config.SELLER_GSTIN,
            "bank_account": Config.SELLER_BANK_ACCOUNT,
            "bank_name": Config.SELLER_BANK_NAME,
            "ifsc": Config.SELLER_IFSC,
        },
        "logo_data_uri": _logo_data_uri(),
        "signature_data_uri": _signature_data_uri(),
    }


def render_invoice_pdf(invoice: dict) -> bytes:
    """
    Render one invoice (as returned by services/invoice_service.get_invoice())
    to PDF bytes using headless Chromium.

    Raises PDFGenerationError (nothing is returned) if any step fails, each
    with its own code identifying where - so a failure reported by an
    employee ("error PDF-02") points straight at the failing step instead
    of one generic message covering five different possible causes.
    """

    try:
        html = render_template("invoice_pdf.html", **_build_context(invoice))
    except Exception as error:
        raise PDFGenerationError("PDF-01", "Could not build the invoice's PDF content.") from error

    try:
        browser = _get_browser()
    except Exception as error:
        raise PDFGenerationError(
            "PDF-02", "Could not start the PDF renderer (Chromium). It may not be installed - "
            "see DEPLOYMENT.md's 'playwright install chromium' step."
        ) from error

    try:
        page = browser.new_page()
    except Exception as error:
        raise PDFGenerationError("PDF-03", "Could not open a browser page for rendering.") from error

    try:
        try:
            page.set_content(html, wait_until="load")
        except Exception as error:
            raise PDFGenerationError("PDF-04", "Chromium could not load the invoice content.") from error

        try:
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
            )
        except Exception as error:
            raise PDFGenerationError("PDF-05", "Chromium failed while converting the invoice to PDF.") from error
    finally:
        page.close()

    if not pdf_bytes:
        raise PDFGenerationError("PDF-06", "Chromium produced an empty PDF.")

    return pdf_bytes
