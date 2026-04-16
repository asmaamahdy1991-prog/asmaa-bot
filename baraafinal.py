import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types

logging.basicConfig(level=logging.INFO)

# ====== Variables ======
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

# ====== Bot ======
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====== Handlers ======
@dp.message()
async def handle_message(message: types.Message):
    await message.answer("البوت شغال ✅")

# ====== Main ======
async def main():
    print("Bot is starting with polling...")

    # مهم جدًا عشان نلغي أي webhook قديم
    await bot.delete_webhook(drop_pending_updates=True)

    # تشغيل البوت
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
