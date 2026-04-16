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
    ErrorEvent,
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
    except Exception as e:
        print("is_group_admin error:", repr(e))
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

    text = f"""📌 حالة القائمة: {status}

📚 المعلمات:
"""
    if teachers:
        for i, user in enumerate(teachers, 1):
            text += f"{i}- {user['name']}\n"
    else:
        text += "لا يوجد\n"

    text += "\n📝 الطالبات:\n"
    if students:
        for i, user in enumerate(students, 1):
            text += f"{i}- {user['name']}\n"
    else:
        text += "لا يوجد\n"

    text += "\n🎧 المستمعات:\n"
    if listeners:
        for i, user in enumerate(listeners, 1):
            text += f"{i}- {user['name']}\n"
    else:
        text += "لا يوجد\n"

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
    except Exception as e:
        print("pin_chat_message error:", repr(e))


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
    except Exception as e:
        print("update_list_message error:", repr(e))


# =========================
# أوامر الأدمن
# =========================
@dp.message(Command("start"))
async def start(message: Message, bot: Bot):
    try:
        if not await is_group_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("❌ هذا البوت يعمل فقط بواسطة الأدمنز في الجروب")
            return

        await message.answer(
            "✅ تم تفعيل لوحة تحكم الأدمن",
            reply_markup=get_admin_reply_keyboard()
        )
    except Exception as e:
        print("start error:", repr(e))
        await message.answer("حدث خطأ داخلي")


@dp.message(F.text.contains("عرض القائمة"))
async def show_list(message: Message, bot: Bot):
    try:
        if not await is_group_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("❌ هذا الزر للأدمن فقط")
            return

        data = get_group_data(message.chat.id)

        if not data["list_message_id"]:
            await create_and_pin_list_message(bot, message.chat.id)
            await message.answer("📌 تم إنشاء القائمة")
        else:
            await update_list_message(bot, message.chat.id)
            await message.answer("✅ تم تحديث القائمة")
    except Exception as e:
        print("show_list error:", repr(e))
        await message.answer("حدث خطأ داخلي")


@dp.message(F.text.contains("تحديث القائمة"))
async def refresh_list(message: Message, bot: Bot):
    try:
        if not await is_group_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("❌ هذا الزر للأدمن فقط")
            return

        await update_list_message(bot, message.chat.id)
        await message.answer("🔄 تم تحديث القائمة")
    except Exception as e:
        print("refresh_list error:", repr(e))
        await message.answer("حدث خطأ داخلي")


@dp.message(F.text.contains("بدء حلقة جديدة"))
async def new_session(message: Message, bot: Bot):
    try:
        if not await is_group_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("❌ هذا الزر للأدمن فقط")
            return

        data = get_group_data(message.chat.id)
        data["attendance"].clear()
        data["is_open"] = False

        if data["list_message_id"]:
            await update_list_message(bot, message.chat.id)
        else:
            await create_and_pin_list_message(bot, message.chat.id)

        await message.answer("🆕 تم بدء حلقة جديدة")
    except Exception as e:
        print("new_session error:", repr(e))
        await message.answer("حدث خطأ داخلي")


@dp.message(Command("reset"))
async def reset_list(message: Message, bot: Bot):
    try:
        if not await is_group_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("❌ هذا الأمر للأدمن فقط")
            return

        data = get_group_data(message.chat.id)
        data["attendance"].clear()
        data["is_open"] = False

        if data["list_message_id"]:
            await update_list_message(bot, message.chat.id)
        else:
            await create_and_pin_list_message(bot, message.chat.id)

        await message.answer("❌ تم مسح جميع الأسماء وإغلاق القائمة")
    except Exception as e:
        print("reset_list error:", repr(e))
        await message.answer("حدث خطأ داخلي")


# =========================
# معالجة أزرار Inline
# =========================
@dp.callback_query()
async def handle_buttons(callback: CallbackQuery, bot: Bot):
    try:
        if not callback.message:
            await callback.answer("حدث خطأ داخلي", show_alert=True)
            return

        chat_id = callback.message.chat.id
        user_id = callback.from_user.id
        user_name = callback.from_user.full_name

        data = get_group_data(chat_id)

        if callback.data == "open_list":
            if not await is_group_admin(bot, chat_id, user_id):
                await callback.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
                return

            data["is_open"] = True
            await update_list_message(bot, chat_id)
            await callback.answer("✅ تم فتح القائمة")

        elif callback.data == "close_list":
            if not await is_group_admin(bot, chat_id, user_id):
                await callback.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
                return

            data["is_open"] = False
            await update_list_message(bot, chat_id)
            await callback.answer("🔒 تم غلق القائمة")

        elif callback.data == "register":
            if not data["is_open"]:
                await callback.answer("❌ القائمة مغلقة", show_alert=True)
                return

            data["attendance"][user_id] = {
                "name": user_name,
                "type": "student",
            }
            await update_list_message(bot, chat_id)
            await callback.answer("✅ تم تسجيلك")

        elif callback.data == "teacher":
            if not data["is_open"]:
                await callback.answer("❌ القائمة مغلقة", show_alert=True)
                return

            data["attendance"][user_id] = {
                "name": user_name,
                "type": "teacher",
            }
            await update_list_message(bot, chat_id)
            await callback.answer("📚 تم تسجيلك كمعلمة")

        elif callback.data == "listener":
            if not data["is_open"]:
                await callback.answer("❌ القائمة مغلقة", show_alert=True)
                return

            data["attendance"][user_id] = {
                "name": user_name,
                "type": "listener",
            }
            await update_list_message(bot, chat_id)
            await callback.answer("🎧 تم تسجيلك كمستمعة")

        elif callback.data == "read":
            if not data["is_open"]:
                await callback.answer("❌ القائمة مغلقة", show_alert=True)
                return

            if user_id not in data["attendance"]:
                await callback.answer("❌ سجلي اسمك أولًا", show_alert=True)
                return

            if not data["attendance"][user_id]["name"].endswith(" ✅"):
                data["attendance"][user_id]["name"] += " ✅"

            await update_list_message(bot, chat_id)
            await callback.answer("✅ تم وضع علامة قرأت")

        elif callback.data == "delete_name":
            if user_id in data["attendance"]:
                del data["attendance"][user_id]
                await update_list_message(bot, chat_id)
                await callback.answer("❌ تم حذف اسمك")
            else:
                await callback.answer("الاسم غير موجود", show_alert=True)

        else:
            await callback.answer()

    except Exception as e:
        print("Callback error:", repr(e))
        try:
            await callback.answer("حدث خطأ داخلي", show_alert=True)
        except Exception:
            pass


# =========================
# Global Error Handler
# =========================
@dp.errors()
async def global_error_handler(event: ErrorEvent):
    print("GLOBAL ERROR:", repr(event.exception))
    return True


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
