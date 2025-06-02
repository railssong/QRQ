
import os
import logging
import requests
import tempfile
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('WebhookBot')

# Создание Flask приложения
app = Flask(__name__)

# Глобальная переменная для хранения приложения бота
bot_application = None

# Простая обработка QR-кодов (без сложных зависимостей)
def simple_qr_processor(input_file, output_file, referral_link):
    """Простая обработка изображений - копирует исходное изображение"""
    try:
        import shutil
        shutil.copy2(input_file, output_file)
        return True, "Изображение обработано (упрощенная версия)"
    except Exception as e:
        return False, str(e)

# Обработчики команд бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        'Привет! Я бот для обработки QR-кодов.\n'
        'Отправьте мне изображение, и я его обработаю.\n'
        'Это упрощенная версия для Railway деплоя.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    await update.message.reply_text(
        'Как использовать бота:\n'
        '1. Отправьте изображение\n'
        '2. Получите обработанное изображение\n'
        '3. Используйте /start для начала работы'
    )

async def process_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка изображений"""
    status_message = await update.message.reply_text('Обрабатываю изображение...')
    
    try:
        # Получаем фото лучшего качества
        photo = update.message.photo[-1]
        
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.jpg")
            output_file = os.path.join(temp_dir, "output.jpg")
            
            # Скачиваем фото
            photo_file = await photo.get_file()
            await photo_file.download_to_drive(input_file)
            
            # Получаем реферальную ссылку
            referral_link = os.getenv("REFERRAL_LINK", "https://example.com/ref123")
            
            # Обрабатываем изображение
            result, message = simple_qr_processor(input_file, output_file, referral_link)
            
            if result:
                # Отправляем обработанное изображение
                with open(output_file, 'rb') as photo_file:
                    await update.message.reply_photo(
                        photo=photo_file,
                        caption='Изображение обработано! (Упрощенная версия для Railway)'
                    )
            else:
                await update.message.reply_text(f"Ошибка обработки: {message}")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {str(e)}")
        await update.message.reply_text(
            f"Произошла ошибка: {str(e)}\n"
            "Попробуйте другое изображение."
        )
    finally:
        await status_message.delete()

def setup_telegram_bot():
    """Настройка Telegram бота"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Токен бота не найден. Установите TELEGRAM_BOT_TOKEN в переменных окружения.")
        return None
        
    # Создаем приложение бота
    application = ApplicationBuilder().token(token).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, process_image))
    
    # Обработчик ошибок
    application.add_error_handler(
        lambda update, context: logger.error(f'Ошибка: {context.error}')
    )
    
    logger.info("Бот настроен и готов к работе")
    return application

# Обработчик webhook от Telegram
@app.route('/webhook/telegram', methods=['POST'])
async def telegram_webhook():
    """Обработка webhook запросов от Telegram"""
    global bot_application
    
    if bot_application is None:
        bot_application = setup_telegram_bot()
        if bot_application is None:
            return "Ошибка инициализации бота", 500
    
    try:
        # Получаем данные запроса
        update_data = request.json
        
        # Создаем объект Update
        update = Update.de_json(update_data, bot_application.bot)
        
        # Обрабатываем обновление
        await bot_application.process_update(update)
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return "Ошибка обработки", 500

# Настройка вебхука
@app.route('/setup-webhook', methods=['GET'])
def setup_webhook():
    """Настройка webhook с Telegram"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        return "Токен не найден", 400
    
    # Получаем URL приложения
    deployed_url = request.url_root
    if deployed_url.startswith('http://'):
        deployed_url = 'https://' + deployed_url[7:]
    
    webhook_url = f"{deployed_url}webhook/telegram"
    if webhook_url.endswith('/'):
        webhook_url = webhook_url[:-1]
    
    # Настраиваем webhook через Telegram API
    response = requests.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={"url": webhook_url}
    )
    
    if response.status_code == 200 and response.json().get("ok"):
        logger.info(f"Webhook установлен: {webhook_url}")
        return f"Webhook успешно установлен на {webhook_url}", 200
    else:
        logger.error(f"Ошибка установки webhook: {response.text}")
        return f"Ошибка установки webhook: {response.text}", 500

# Проверка статуса
@app.route('/status', methods=['GET'])
def status():
    """Проверка статуса бота"""
    return "Railway QR Bot работает!", 200

# Главная страница
@app.route('/', methods=['GET'])
def index():
    """Главная страница бота"""
    return """
    <html>
    <head>
        <title>QR Code Bot - Railway Deploy</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            .status { color: #28a745; font-weight: bold; }
            .button { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>QR Code Bot для Railway</h1>
            <p class="status">✅ Бот запущен и готов к работе!</p>
            <p>Этот бот обрабатывает изображения с QR-кодами через Telegram.</p>
            
            <h3>Настройка:</h3>
            <ol>
                <li>Убедитесь, что установлена переменная окружения <code>TELEGRAM_BOT_TOKEN</code></li>
                <li><a href="/setup-webhook" class="button">Настроить Webhook</a></li>
                <li>Отправьте сообщение боту в Telegram для проверки</li>
            </ol>
            
            <h3>Команды бота:</h3>
            <ul>
                <li><code>/start</code> - Запуск бота</li>
                <li><code>/help</code> - Справка</li>
                <li>Отправьте изображение для обработки</li>
            </ul>
            
            <p><small>Версия для Railway Deploy | <a href="/status">Проверить статус</a></small></p>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Инициализация бота
    bot_application = setup_telegram_bot()
    
    # Запуск Flask приложения
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
