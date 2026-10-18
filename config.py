"""
=========================================================
Project : Sridevi Enterprises
File    : config.py
Purpose : Application configuration.

Author  : Srikar
=========================================================
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv


# Always load this project's database settings, regardless of the directory
# from which Flask is started.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


def _telephone_href(phone: str) -> str:
    """
    Build a dialable tel: href from a human-formatted phone number.

    Keeps digits and a single leading "+" and drops everything a human
    reads but a dialer cannot ("+91 98765 43210" -> "tel:+919876543210"),
    so BUSINESS_PHONE can be written in whatever format reads best on the
    page without a second env var for the machine-readable form.
    """

    if not phone:
        return ""

    digits = re.sub(r"[^\d]", "", phone)
    return f"tel:+{digits}" if phone.lstrip().startswith("+") else f"tel:{digits}"


def _env_bool(name: str, default: bool) -> bool:
    """
    Read a boolean environment variable, tolerating the spellings people
    actually write in a .env file. Anything unrecognised falls back to the
    default rather than raising - a typo must never stop the site booting.
    """

    raw = os.getenv(name)
    if raw is None:
        return default

    value = raw.strip().lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    return default


def _website_href(website: str) -> str:
    """
    Build an absolute href from BUSINESS_WEBSITE, which is written for
    display ("www.example.com") and so usually has no scheme. A
    scheme-less href would otherwise be resolved as a relative path.
    """

    if not website:
        return ""

    return website if re.match(r"^https?://", website, re.IGNORECASE) else f"https://{website}"


def _whatsapp_number(raw: str) -> str:
    """
    Normalise WHATSAPP_BUSINESS_NUMBER to the bare digits wa.me expects
    ("+91 98765 43210" -> "919876543210"), or "" if it is unusable.

    The value must be written in international format with a leading "+".
    That is required rather than guessed: a 10-digit local number is a
    perfectly valid-looking string of digits, and without the country code
    wa.me would open a chat with a stranger in another country. Anything
    that is not "+", then 8-15 digits (E.164) with ordinary spacing or
    punctuation between them, is rejected - and "" switches every WhatsApp
    element off, so a typo hides the button rather than shipping a broken
    or misdirected link.
    """

    value = (raw or "").strip()
    if not value.startswith("+"):
        return ""

    remainder = value[1:]
    if re.search(r"[^\d\s().-]", remainder):
        return ""

    digits = re.sub(r"\D", "", remainder)
    if not 8 <= len(digits) <= 15 or digits.startswith("0"):
        return ""

    return digits


class Config:

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", "3307"))
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY is not set in .env file. "
            "Please add 'SECRET_KEY=your-secret-key' to .env"
        )

    # Overall request body cap (defense-in-depth). Per-file size and type are
    # validated in services/image_service.py.
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024

    # Debug mode must be explicitly enabled; defaults to False for safety.
    DEBUG = os.getenv("FLASK_DEBUG", "False").strip().lower() == "true"

    # ---------------------------------------------------------------------
    # Session cookie hardening (v1.0 Sprint 11)
    #
    # The session cookie is what authenticates every Employee/Admin request
    # and what carries the Maintenance Mode bypass, so these three flags are
    # the whole of this application's session security.
    # ---------------------------------------------------------------------

    # Never expose the session cookie to JavaScript. This is already Flask's
    # default; it is set explicitly so it cannot be silently lost if a future
    # change starts assigning app.config wholesale.
    SESSION_COOKIE_HTTPONLY = True

    # "Lax" means the browser withholds the cookie on cross-site POST/PUT/
    # DELETE (the shape every CSRF attack against this app's write endpoints
    # would take) while still sending it on ordinary top-level GET navigation
    # - so following a link to the site, including a ?maintenance_key= bypass
    # link shared over email or chat, still works normally.
    #
    # Deliberately NOT "Strict": Strict also withholds the cookie on
    # cross-site GET navigation, so an employee opening a bookmark or an
    # emailed link to /employee/dashboard would land there appearing logged
    # out, then appear logged in after any internal click. That is a
    # confusing failure for no additional protection against the attack this
    # setting exists to blunt.
    #
    # This is a partial mitigation, not CSRF protection. Real CSRF tokens are
    # deferred to v1.1 - see AI_CONTEXT.md and CHANGELOG.
    SESSION_COOKIE_SAMESITE = "Lax"

    # Only send the session cookie over HTTPS.
    #
    # Defaults to True - secure unless a deployment explicitly opts out. It is
    # deliberately NOT derived from FLASK_DEBUG: this project runs
    # FLASK_DEBUG=False in local development too (see AI_CONTEXT.md's
    # no-autoreload note), so "not DEBUG" would look correct and silently mean
    # "production" on every developer's machine.
    #
    # Local development over http://127.0.0.1:5000 must set
    # SESSION_COOKIE_SECURE=False in .env, or the browser will refuse to store
    # the cookie and login will not work. Production must leave it True; the
    # site is HTTPS-only (see DEPLOYMENT.md, Enable HTTPS). app.py logs a
    # warning at startup whenever this is False, so an accidental opt-out in
    # production is visible in the error log rather than silent.
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)

    # Application log verbosity (v1.0 Sprint 11). One of DEBUG, INFO, WARNING,
    # ERROR, CRITICAL. Defaults to INFO, which records write operations and
    # every failure without logging a line per page view. Set LOG_LEVEL=WARNING
    # on a busy production site to keep only problems. See app.py's
    # configure_logging() for where records are written (stderr, which Passenger
    # captures into the cPanel Python app error log).
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    # The application's version. This is the single source of truth: it is
    # surfaced read-only via GET /health and on the Employee Dashboard's System
    # Status panel, so a deploy can confirm the right code is actually running
    # after a Passenger restart (see AI_CONTEXT.md "Health Endpoint" and
    # DEPLOYMENT.md). Bump this string when a release ships.
    #
    # v1.0 Sprint 11 (RC-7): switched from the interim per-sprint labels
    # ("Sprint 8" ... "Sprint 10") to a real semantic version for the first
    # public release. Future releases should follow semver - v1.0.1 for fixes,
    # v1.1.0 for the deferred CSRF/feature work (see CHANGELOG.md).
    #
    # Bumped to v1.1.0: Sprint 12 (Production Stabilization) and the Invoice
    # Generator Module merge - see CHANGELOG.md "[v1.1.0]". This is the only
    # place this string is defined; GET /health, the Employee Dashboard's
    # System Status panel, and the startup log line all read it from here
    # rather than each carrying their own copy.
    APP_VERSION = "v1.1.0"

    # DEPRECATED (Invoice Generator Module merge - see AI_CONTEXT.md "Invoice
    # Generator Module (Merge)"): used to hold the separately-hosted Receipt
    # Generator project's URL, which the Employee Portal linked out to. The
    # Invoice Generator is now a module of this application (routes/receipts.py)
    # and no longer launches an external app, so nothing reads this value any
    # more. Left defined (not deleted) only so a server .env that still sets
    # INVOICE_GENERATOR_URL/RECEIPT_GENERATOR_URL doesn't need an urgent edit;
    # remove this once every deployment's .env has been cleaned up.
    INVOICE_GENERATOR_URL = (
        os.getenv("INVOICE_GENERATOR_URL", "").strip()
        or os.getenv("RECEIPT_GENERATOR_URL", "").strip()
    )

    # ---------------------------------------------------------------------
    # Invoice Generator seller details (Invoice Generator Module merge)
    #
    # The GSTIN and bank details printed on every generated invoice. Kept
    # here rather than hardcoded in templates/invoice_pdf.html so they can
    # be corrected (or set per-deployment) without touching code. The
    # showroom's address/phone are NOT duplicated here - the invoice reuses
    # Config.BUSINESS_ADDRESS / Config.BUSINESS_PHONE below, which already
    # exist as this application's single source of truth for those values.
    #
    # Deliberately optional, matching the BUSINESS_* pattern above rather
    # than SECRET_KEY's hard-fail: a missing SELLER_GSTIN should only ever
    # break invoice generation (services/gst_service.py refuses to generate
    # an invoice with a blank seller GSTIN - see there), never the whole
    # application. Crashing the entire site, customer showroom included,
    # over an invoice-only value would be a wildly disproportionate failure
    # mode for a field the customer-facing site never reads.
    SELLER_GSTIN = os.getenv("SELLER_GSTIN", "").strip()
    SELLER_BANK_ACCOUNT = os.getenv("SELLER_BANK_ACCOUNT", "").strip()
    SELLER_BANK_NAME = os.getenv("SELLER_BANK_NAME", "").strip()
    SELLER_IFSC = os.getenv("SELLER_IFSC", "").strip()

    # ---------------------------------------------------------------------
    # Public business details (v1.0 Sprint 11 - Release Candidate)
    #
    # The showroom's real-world contact information, shown on every public
    # surface that displays it: the sitewide footer, the Contact page, and
    # the standalone Maintenance Mode (503) screen. These used to be
    # hardcoded - and had drifted out of sync with each other (two
    # different email addresses, two different sets of business hours) -
    # so they are now read from the environment and rendered from one
    # source of truth. See app.py:inject_business_details().
    #
    # Every value defaults to an empty string. A template renders each
    # line ONLY when its value is set, so a deployment that has not yet
    # supplied real details shows nothing at all rather than a plausible
    # looking but fake address or phone number. Production values belong
    # in the server's own .env (never committed - see DEPLOYMENT.md
    # "Configure Environment Variables"); .env.example carries safe
    # placeholder values so a fresh development checkout still renders a
    # complete page.
    # ---------------------------------------------------------------------
    BUSINESS_ADDRESS = os.getenv("BUSINESS_ADDRESS", "").strip()
    BUSINESS_PHONE = os.getenv("BUSINESS_PHONE", "").strip()
    BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", "").strip()
    BUSINESS_WEBSITE = os.getenv("BUSINESS_WEBSITE", "").strip()
    BUSINESS_HOURS = os.getenv("BUSINESS_HOURS", "").strip()

    # Machine-readable forms, derived from the display values above so a
    # deployment only ever configures each detail once.
    BUSINESS_PHONE_HREF = _telephone_href(BUSINESS_PHONE)
    BUSINESS_WEBSITE_HREF = _website_href(BUSINESS_WEBSITE)

    # ---------------------------------------------------------------------
    # WhatsApp click-to-chat (wa.me)
    #
    # The number customers reach through the floating WhatsApp button and
    # the Product Details "Enquire on WhatsApp" button. Configured only
    # here, from the server's own .env - never hardcoded in a template -
    # so it can be replaced (e.g. a personal number swapped for a dedicated
    # business number) by editing one line and restarting, with no code
    # change. See services/whatsapp_service.py and DEPLOYMENT.md section 1.5.
    #
    # WHATSAPP_NUMBER is the validated, digits-only form, or "" when the
    # variable is unset or unusable (see _whatsapp_number above). "" means
    # no WhatsApp element and no wa.me link is rendered anywhere.
    # WHATSAPP_NUMBER_REJECTED is True only when a value was supplied but
    # failed validation, so app.py can warn about it at startup. The number
    # itself is never logged.
    #
    # This is plain click-to-chat: no WhatsApp Business API, no token, no
    # webhook. Nothing here is a secret - a wa.me link is public by nature.
    # ---------------------------------------------------------------------
    _WHATSAPP_NUMBER_RAW = os.getenv("WHATSAPP_BUSINESS_NUMBER", "").strip()
    WHATSAPP_NUMBER = _whatsapp_number(_WHATSAPP_NUMBER_RAW)
    WHATSAPP_NUMBER_REJECTED = bool(_WHATSAPP_NUMBER_RAW) and not WHATSAPP_NUMBER

    # Prefilled text for the floating button. Optional - falls back to a
    # generic greeting. The customer can edit it before sending.
    WHATSAPP_DEFAULT_MESSAGE = (
        os.getenv("WHATSAPP_DEFAULT_MESSAGE", "").strip()
        or "Hello Sridevi Enterprises, I would like to know more about your products."
    )

