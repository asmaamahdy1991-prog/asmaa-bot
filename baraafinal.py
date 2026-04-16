import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")
if not BASE_URL:
    raise ValueError("BASE_URL is missing")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================== handlers ==================
@dp.message()
async def echo(message: types.Message):
    await message.answer("البوت شغال ✅")

# ================== main ==================
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print("Webhook set:", WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()

def main():
    app = web.Application()

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
