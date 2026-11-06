from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from .base import *  # noqa: E402,F403
from .base import env_bool  # noqa: E402

DEBUG = env_bool("DJANGO_DEBUG", True)
