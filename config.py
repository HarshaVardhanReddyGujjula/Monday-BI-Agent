import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
# Check multiple possible locations for the .env file for absolute reliability
if (BASE_DIR / ".env").exists():
    load_dotenv(BASE_DIR / ".env")
elif (BASE_DIR.parent / ".env").exists():
    load_dotenv(BASE_DIR.parent / ".env")
else:
    load_dotenv()

# Configure Logging
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

# Use standard logging configuration
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger("MondayBIAgent")
logger.setLevel(LOG_LEVEL)

# Monday.com Configurations
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_BOARD_ID_DEALS = os.getenv("MONDAY_BOARD_ID_DEALS")
MONDAY_BOARD_ID_WORK_ORDERS = os.getenv("MONDAY_BOARD_ID_WORK_ORDERS")

# OpenAI Configurations
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Check for required configurations and log warning messages if missing
if not MONDAY_API_KEY:
    logger.warning("MONDAY_API_KEY is not set in the environment or .env file.")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set in the environment or .env file.")

logger.info("Configuration module successfully loaded.")