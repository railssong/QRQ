import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebhookBot")

# Переменные окружения
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Flask app
app = Flask(__name__)

# Telegram Application
application = ApplicationBuilder().token(TOKEN).build()

# Хэндлер для изображений
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Фото получено!")

application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Запуск и инициализация бота
@app.before_first_request
def init_bot():
    import asyncio

    async def setup():
        await application.initialize()
        await application.start()
        await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook/telegram")
        logger.info(f"Webhook установлен: {WEBHOOK_URL}/webhook/telegram")

    asyncio.run(setup())

# Обработка Telegram Webhook
@app.post("/webhook/telegram")
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK"
