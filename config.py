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

