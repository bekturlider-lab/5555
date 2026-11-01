import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / ".env")


def admin_environment():
    if os.environ.get("ADMIN_DATABASE_URL"):
        os.environ["DATABASE_URL"] = os.environ["ADMIN_DATABASE_URL"]
