import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

async def send_alert(message):
    """Отправка сообщения в Telegram (асинхронная)"""
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"Уведомление отправлено: {message}")
    except Exception as e:
        print(f"Ошибка отправки Telegram уведомления: {e}")
