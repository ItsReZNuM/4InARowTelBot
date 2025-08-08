# utils.py
from time import time
from datetime import datetime
from pytz import timezone
from config import logger

# message tracker for rate limiting: {user_id: {'count', 'last_time', 'temp_block_until'}}
message_tracker = {}

# bot start time (set on startup)
bot_start_time = None

def set_bot_start_time():
    global bot_start_time
    bot_start_time = datetime.now(timezone('Asia/Tehran')).timestamp()
    logger = __import__('config').logger
    logger.error if False else None  

def is_message_valid(message):
    # message.date is integer timestamp from Telegram (seconds)
    global bot_start_time
    if bot_start_time is None:
        return True
    message_time = message.date
    if message_time < bot_start_time:
        # old message
        return False
    return True

def check_rate_limit(user_id):
    current_time = time()
    if user_id not in message_tracker:
        message_tracker[user_id] = {'count': 0, 'last_time': current_time, 'temp_block_until': 0}

    if current_time < message_tracker[user_id]['temp_block_until']:
        remaining = int(message_tracker[user_id]['temp_block_until'] - current_time)
        return False, f"شما به دلیل ارسال پیام زیاد تا {remaining} ثانیه نمی‌تونید پیام بفرستید 😕"

    if current_time - message_tracker[user_id]['last_time'] > 1:
        message_tracker[user_id]['count'] = 0
        message_tracker[user_id]['last_time'] = current_time

    message_tracker[user_id]['count'] += 1
    if message_tracker[user_id]['count'] > 2:
        message_tracker[user_id]['temp_block_until'] = current_time + 30
        return False, "شما بیش از حد پیام فرستادید! تا ۳۰ ثانیه نمی‌تونید پیام بفرستید 😕"

    return True, ""
