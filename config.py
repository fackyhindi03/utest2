import os
from dotenv import load_dotenv

load_dotenv()

API_ID   = int(os.getenv("API_ID",   0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN= os.getenv("BOT_TOKEN", "")
API_BASE = os.getenv("API_BASE",   "")

if not (API_ID and API_HASH and BOT_TOKEN and API_BASE):
    raise RuntimeError(
      "API_ID, API_HASH, BOT_TOKEN and API_BASE must be set in .env"
    )
