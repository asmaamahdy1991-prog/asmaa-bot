import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application


# =========================
# إعدادات عامة
# =========================
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")

WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_super_secret_token")
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

print("BOT_TOKEN loaded:", bool(TOKEN))
print("BASE_URL loaded:", BASE_URL)

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")
if not BASE_URL:
    raise ValueError("BASE_URL is missing")

dp = Dispatcher()


# =========================
# بيانات كل جروب
# =========================
groups_data = {}


def get_group_data(chat_id: int):
    if chat_id not in groups_data:
        groups_data[chat_id] = {
            "is_open": False,
            "attendance": {},
            "list_message_id": None,
        }
    return groups_data[chat_id]


async def is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# =========================
# الكيبوردات
# =========================
def get_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 سجل اسمي", callback_data="register"),
                InlineKeyboardButton(text="📚 حلقة المعلمة", callback_data="teacher"),
            ],
            [
                InlineKeyboardButton(text="🎧 مستمعة", callback_data="listener"),
                InlineKeyboardButton(text="✅ قرأت", callback_data="read"),
            ],
            [
                InlineKeyboardButton(text="❌ احذف اسمي", callback_data="delete_name"),
            ],
            [
                InlineKeyboardButton(text="🔓 فتح القائمة", callback_data="open_list"),
                InlineKeyboardButton(text="🔒 غلق القائمة", callback_data="close_list"),
            ],
        ]
    )


def get_admin_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 عرض القائمة")],
            [KeyboardButton(text="🔄 تحديث القائمة"), KeyboardButton(text="🆕 بدء حلقة جديدة")],
        ],
        resize_keyboard=True
    )


# =========================
# بناء النص
# =========================
def build_list_text(chat_id: int) -> str:
    data = get_group_data(chat_id)
    attendance = data["attendance"]
    is_open = data["is_open"]

    status = "🟢 مفتوحة" if is_open else "🔴 مغلقة"

    teachers = []
    students = []
    listeners = []

    for user in attendance.values():
        if user["type"] == "teacher":
            teachers.append(user)
        elif user["type"] == "listener":
            listeners.append(user)
        else:
            students.append(user)

    text = f"📌 حالة القائمة: {status}\n\n"

    text += "📚 المعلمات:\n"
    text += "\n".join([u["name"] for u in teachers]) or "لا يوجد"

    text += "\n\n📝 الطالبات:\n"
    text += "\n".join([u["name"] for u in students]) or "لا يوجد"

    text += "\n\n🎧 المستمعات:\n"
    text += "\n".join([u["name"] for u in listeners]) or "لا يوجد"

    return text


# =========================
# إنشاء وتحديث القائمة
# =========================
async def create_and_pin_list_message(bot: Bot, chat_id: int):
    data = get_group_data(chat_id)

    sent = await bot.send_message(
        chat_id=chat_id,
        text=build_list_text(chat_id),
        reply_markup=get_inline_keyboard()
    )

    data["list_message_id"] = sent.message_id

    try:
        await bot.pin_chat_message(chat_id, sent.message_id)
    except:
        pass


async def update_list_message(bot: Bot, chat_id: int):
    data = get_group_data(chat_id)

    if not data["list_message_id"]:
        return

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=data["list_message_id"],
            text=build_list_text(chat_id),
            reply_markup=get_inline_keyboard()
        )
    except:
        pass


# =========================
# أوامر
# =========================
@dp.message(Command("start"))
async def start(message: Message, bot: Bot):
    if not await is_group_admin(bot, message.chat.id, message.from_user.id):
        await message.answer("❌ هذا البوت للأدمن فقط")
        return

    await message.answer("تم التفعيل", reply_markup=get_admin_reply_keyboard())


# 🔥 تم إصلاح المشكلة هنا (بدل == استخدم contains)
@dp.message(F.text.contains("عرض القائمة"))
async def show_list(message: Message, bot: Bot):
    await create_and_pin_list_message(bot, message.chat.id)


@dp.message(F.text.contains("تحديث القائمة"))
async def refresh_list(message: Message, bot: Bot):
    await update_list_message(bot, message.chat.id)


@dp.message(F.text.contains("بدء حلقة جديدة"))
async def new_session(message: Message, bot: Bot):
    data = get_group_data(message.chat.id)
    data["attendance"] = {}
    await update_list_message(bot, message.chat.id)
    await message.answer("✅ تم بدء حلقة جديدة")


# =========================
# Webhook
# =========================
async def on_startup(bot: Bot):
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
    )
    print("Webhook set:", WEBHOOK_URL)


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await bot.session.close()


def main():
    bot = Bot(token=TOKEN)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


if __name__ == "__main__":
    main()
