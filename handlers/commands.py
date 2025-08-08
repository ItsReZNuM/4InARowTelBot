# handlers/commands.py
from telebot import types
from config import ADMIN_USER_IDS
from database import save_user, get_leaderboard
from utils import is_message_valid, check_rate_limit
from config import logger

def register_commands(bot):
    @bot.message_handler(commands=['start'])
    def start_command(message):
        try:
            if not is_message_valid(message):
                return

            user_id = message.from_user.id
            user_name = message.from_user.first_name
            username = message.from_user.username

            allowed, error_message = check_rate_limit(user_id)
            if not allowed:
                bot.send_message(user_id, error_message)
                return

            save_user(user_id, username, user_name, ADMIN_USER_IDS)

            welcome_message = f'''
🌟 سلام {user_name} به ربات ۴ در یک ردیف خوش اومدی! 🎮

🔹 می‌تونی تک‌نفره با ربات بازی کنی یا با دوستت تو حالت دو نفره! 😎
🔹 برای اطلاعات بیشتر، روی /help کلیک کن 📚
'''
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("شروع بازی 🎲", callback_data="start_game"))
            if user_id in ADMIN_USER_IDS:
                markup.add(types.InlineKeyboardButton("پیام همگانی 📢", callback_data="broadcast"))
            bot.send_message(message.chat.id, welcome_message, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            logger = __import__('config').logger
            logger.error(f"Error in start_command: {e}")

    @bot.message_handler(commands=['help'])
    def help_command(message):
        try:
            if not is_message_valid(message):
                return
            user_id = message.from_user.id
            allowed, error_message = check_rate_limit(user_id)
            if not allowed:
                bot.send_message(user_id, error_message)
                return
            help_message = '''
🎮 راهنمای بازی ۴ در یک ردیف 🎲

🔹 **حالت تک نفره**:
۱. با دستور /start ربات رو شروع کن.
۲. روی «شروع بازی» کلیک کن و یکی از سطح‌های سختی (آسان، متوسط، سخت) رو انتخاب کن.
۳. توی صفحه ۷×۷، روی دکمه‌های بالای جدول کلیک کن تا مهره‌ت (🔵) رو بندازی.
۴. ربات با مهره (🔴) باهات بازی می‌کنه.
۵. هدف: ۴ تا مهره رو به صورت افقی، عمودی یا مورب پشت هم بیار تا ببری!

🔹 **حالت دو نفره**:
۱. توی یه چت گروهی یا خصوصی، از حالت اینلاین استفاده کن و «پایه‌م!» رو بزن.
۲. هر بازیکن ۱۰ ثانیه وقت داره حرکت کنه.

🔹 **دستورات**:
- /start: شروع ربات
- /help: راهنما
- /leaderboard: نمایش برترین‌ها
- /alive: چک کردن وضعیت ربات
'''
            bot.send_message(message.chat.id, help_message, parse_mode="Markdown")
        except Exception as e:
            logger = __import__('config').logger
            logger.error(f"Error in help_command: {e}")

    @bot.message_handler(commands=['alive'])
    def alive_command(message):
        try:
            if not is_message_valid(message):
                return
            user_id = message.from_user.id
            allowed, error_message = check_rate_limit(user_id)
            if not allowed:
                bot.send_message(user_id, error_message)
                return
            bot.send_message(message.chat.id, "من زنده‌ام و آماده بازی! 🤖 ۴ در یک ردیف منتظرته!")
        except Exception as e:
            logger = __import__('config').logger
            logger.error(f"Error in alive_command: {e}")

    @bot.message_handler(commands=['leaderboard'])
    def leaderboard_command(message):
        try:
            if not is_message_valid(message):
                return
            user_id = message.from_user.id
            allowed, error_message = check_rate_limit(user_id)
            if not allowed:
                bot.send_message(user_id, error_message)
                return
            leaders = get_leaderboard()
            if not leaders:
                bot.send_message(user_id, "هنوز هیچ برنده‌ای نداریم! 🏆 بازی کن و اولین باش!")
                return
            leaderboard_text = "🏆 برترین‌های بازی ۴ در یک ردیف:\n\n"
            for i, (first_name, username, score) in enumerate(leaders, 1):
                username = f"@{username}" if username and username != "ندارد" else ""
                leaderboard_text += f"{i}. {first_name} {username} - {score} امتیاز\n"
            bot.send_message(user_id, leaderboard_text)
        except Exception as e:
            logger = __import__('config').logger
            logger.error(f"Error in leaderboard_command: {e}")
