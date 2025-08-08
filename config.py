# config.py
import os
import logging
from dotenv import load_dotenv
from colorama import Fore, Style, init

# init colorama
init(autoreset=True)

# load env
load_dotenv()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("❌ No TOKEN found in .env file")
    exit(1)

# Admin IDs (comma separated in .env)
ADMIN_USER_IDS = [int(i) for i in os.getenv("ADMIN_USER_IDS", "").split(",") if i.strip()]

# Logging: only print ERROR and CRITICAL to terminal, with colors
class ColorFormatter(logging.Formatter):
    COLORS = {
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        log_message = super().format(record)
        return self.COLORS.get(record.levelname, '') + log_message

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.ERROR)
stream_handler.setFormatter(ColorFormatter('%(asctime)s [%(levelname)s] %(message)s'))

logging.basicConfig(level=logging.ERROR, handlers=[stream_handler])
logger = logging.getLogger(__name__)
