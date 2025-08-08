# handlers/inline.py
from telebot import types
import uuid
from database import USER_DB
import sqlite3
from config import logger

def register_inline(bot):
    @bot.inline_handler(lambda query: query.query == "")
    def inline_start(query):
        try:
            user_id = query.from_user.id
            with sqlite3.connect(USER_DB) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT first_name FROM users WHERE user_id = ?', (user_id,))
                user = cursor.fetchone()
            if not user:
                results = [
                    types.InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title="خطا",
                        input_message_content=types.InputTextMessageContent(
                            "اول وارد ربات @Rez4InARowBot شو و دستور /start رو بزن تا به عنوان کاربر بازی شناخته بشی  😊"
                        )
                    )
                ]
                bot.answer_inline_query(query.id, results, cache_time=1)
                return
            user_name = user[0]
            results = [
                types.InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title="شروع بازی دو نفره 🎮",
                    input_message_content=types.InputTextMessageContent(
                        f"{user_name} می‌خواد یه بازی دو نفره ۴ در یک ردیف انجام بده، کی پایه‌ست؟ 😎"
                    ),
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("پایه‌م! 💪", callback_data=f"join_{user_id}")
                    )
                )
            ]
            bot.answer_inline_query(query.id, results, cache_time=0)
        except Exception as e:
            logger.error(f"Error in inline_start: {e}")
