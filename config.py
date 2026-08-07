"""
=========================================================
Project : Sridevi Enterprises
File    : config.py
Purpose : Application configuration.

Author  : Srikar
=========================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# Always load this project's database settings, regardless of the directory
# from which Flask is started.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)


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

    # Human-readable build/sprint label, surfaced read-only via GET /health so a
    # deploy can confirm the right code is actually running after a Passenger
    # restart (Sprint 8 Review - see AI_CONTEXT.md "Health Endpoint"). Bump this
    # string when a new sprint/release ships.
    APP_VERSION = "Sprint 10"

    # Base URL of the separately-hosted invoice-generation project (its own Flask
    # app, not part of this codebase - see AI_CONTEXT.md; that project itself is
    # still named "Receipt Generator" and is NOT being renamed). Left unset until
    # a deployment URL exists; the Employee Portal shows a graceful "unavailable"
    # message when this is empty rather than guessing a URL.
    #
    # v1.0 Sprint 3: renamed from RECEIPT_GENERATOR_URL to INVOICE_GENERATOR_URL
    # (display-terminology rename only). The old env var name is still read as a
    # fallback so existing deployments keep working without an immediate .env
    # change; prefer INVOICE_GENERATOR_URL in new configuration.
    INVOICE_GENERATOR_URL = (
        os.getenv("INVOICE_GENERATOR_URL", "").strip()
        or os.getenv("RECEIPT_GENERATOR_URL", "").strip()
    )

