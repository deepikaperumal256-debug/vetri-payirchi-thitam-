import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-3.1-pro-preview")
FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-3-flash-preview")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")  # empty = admin pages open (local dev)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fitbuddy.db")
