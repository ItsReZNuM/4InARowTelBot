# main.py
import telebot
from config import TOKEN, logger
from database import init_databases
from utils import set_bot_start_time
from handlers.commands import register_commands
from handlers.callbacks import register_callbacks
from handlers.inline import register_inline

print("✅ Bot started and polling...")

def set_commands(bot):
    commands = [
        telebot.types.BotCommand("start", "شروع ربات"),
        telebot.types.BotCommand("help", "راهنمای بازی"),
        telebot.types.BotCommand("leaderboard", "نمایش برترین‌ها"),
        telebot.types.BotCommand("alive", "چک کردن وضعیت ربات")
    ]
    try:
        bot.set_my_commands(commands)
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

def main():
    bot = telebot.TeleBot(TOKEN)

    init_databases()

    set_bot_start_time()

    register_commands(bot)
    register_callbacks(bot)
    register_inline(bot)

    set_commands(bot)

    logger.info("Starting bot polling...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")



if __name__ == "__main__":
    main()
