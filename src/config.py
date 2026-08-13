"""Centralized environment configuration for the Retail SQL Data Analyst Agent."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

TIGER_AI_GATEWAY_URL = os.getenv("TIGER_AI_GATEWAY_URL")
TIGER_AI_GATEWAY_API_KEY = os.getenv("TIGER_AI_GATEWAY_API_KEY")
TIGER_AI_GATEWAY_MODEL = os.getenv("TIGER_AI_GATEWAY_MODEL")
