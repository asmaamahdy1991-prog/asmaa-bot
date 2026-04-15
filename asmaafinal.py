import os
import asyncio

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
TTOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")  # مثال: https://your-bot.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my_super_secret_token")
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}"

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
    except Exception:
        return False


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

    text = f"""🌧⤸ بِسْـــمِ اللَّـهِ الرَّحمَـٰنِ الرَّحيـٰــم ⤹🌧

🌙وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ [العنكبوت:69].
🔰عن عائشة رضي اللَّه عنها قالَتْ: قالَ رسولُ اللَّهِ ﷺ: الَّذِي يَقْرَأُ القُرْآنَ وَهُو ماهِرٌ بِهِ معَ السَّفَرةِ الكِرَامِ البَرَرَةِ، وَالَّذِي يقرَأُ القُرْآنَ ويَتَتَعْتَعُ فِيهِ وَهُو عليهِ شَاقٌّ لَهُ أَجْران رواه مسلم.

❤️نبدأ الحلقة بعون الله تعالي❤️

غاليتي لحجز دورك اضغطي ضغطة واحدة على الخيار المناسب لكِ على الأزرار أسفل القائمة مباشرة 👇👇👇

    🌙🌧قائمة السفرة الكرام البررة 🌙

📌 حالة القائمة: {status}
"""

    text += "\n\n📚 قائمة المعلمات:\n"
    if teachers:
        for i, user in enumerate(teachers, 1):
            mark = " ✅" if user["read"] else ""
            text += f"{i}- {user['name']}{mark}\n"
    else:
        text += "لا يوجد أسماء مسجلة بعد\n"

    text += "\n📝 قائمة الطالبات:\n"
    if students:
        for i, user in enumerate(students, 1):
            mark = " ✅" if user["read"] else ""
            text += f"{i}- {user['name']}{mark}\n"
    else:
        text += "لا يوجد أسماء مسجلة بعد\n"

    text += "\n🎧 قائمة المستمعات:\n"
    if listeners:
        for i, user in enumerate(listeners, 1):
            mark = " ✅" if user["read"] else ""
            text += f"{i}- {user['name']}{mark}\n"
    else:
        text += "لا يوجد أسماء مسجلة بعد\n"

    text += """
---------------------------------•
♡اللهم لا تدع لنا ذنبًا إلا غفرته ولا مريضًا إلا شفيته ولا همًّا إلا فرجته، اللهم اجعل الحياة زيادة لنا من كل خير والموت راحة لنا من كل شر، اللهم اجعل القرآن العظيم ربيع قلوبنا ونور صدورنا وجلاء همومنا وأحزاننا، اللهم آمين 🌙🌧
(اللهم ارحم أبي وجميع موتى المسلمين)
"""
    return text


async def create_and_pin_list_message(bot: Bot, chat_id: int):
    data = get_group_data(chat_id)

    sent = await bot.send_message(
        chat_id=chat_id,
        text=build_list_text(chat_id),
        reply_markup=get_inline_keyboard()
    )

    data["list_message_id"] = sent.message_id

    try:
        await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=sent.message_id,
            disable_notification=True
        )
    except Exception:
        pass

    return sent.message_id


async def update_list_message(bot: Bot, chat_id: int):
    data = get_group_data(chat_id)
    message_id = data["list_message_id"]

    if not message_id:
        return False

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=build_list_text(chat_id),
            reply_markup=get_inline_keyboard()
        )
        return True
    except Exception as e:
        print(f"خطأ أثناء تحديث الرسالة في الجروب {chat_id}: {e}")
        return False


@dp.message(Command("start"))
async def start(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, user_id):
        await message.answer("❌ هذا البوت يعمل فقط بواسطة الأدمنز في الجروب")
        return

    await message.answer(
        "تم تفعيل لوحة تحكم الأدمن ✅",
        reply_markup=get_admin_reply_keyboard()
    )


@dp.message(F.text == "📋 عرض القائمة")
async def show_list_button(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, user_id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return

    data = get_group_data(chat_id)

    if not data["list_message_id"]:
        await create_and_pin_list_message(bot, chat_id)
        await message.answer("تم إنشاء القائمة وتثبيتها 📌")
        return

    updated = await update_list_message(bot, chat_id)

    if not updated:
        await create_and_pin_list_message(bot, chat_id)
        await message.answer("تمت إعادة إنشاء القائمة وتثبيتها 📌")
    else:
        await message.answer("تم تحديث القائمة الحالية ✅")


@dp.message(F.text == "🔄 تحديث القائمة")
async def refresh_list(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, user_id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return

    data = get_group_data(chat_id)

    if not data["list_message_id"]:
        await create_and_pin_list_message(bot, chat_id)
        await message.answer("لم تكن هناك قائمة، فتم إنشاؤها وتثبيتها 📌")
        return

    updated = await update_list_message(bot, chat_id)
    if updated:
        await message.answer("تم تحديث القائمة 🔄")
    else:
        await create_and_pin_list_message(bot, chat_id)
        await message.answer("تعذر تحديث القائمة القديمة، فتم إنشاء واحدة جديدة 📌")


@dp.message(F.text == "🆕 بدء حلقة جديدة")
async def new_session(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, user_id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return

    data = get_group_data(chat_id)
    data["attendance"].clear()
    data["is_open"] = False

    if data["list_message_id"]:
        updated = await update_list_message(bot, chat_id)
        if updated:
            await message.answer("تم بدء حلقة جديدة 🆕 وتم مسح الأسماء")
        else:
            await create_and_pin_list_message(bot, chat_id)
            await message.answer("تم بدء حلقة جديدة وإنشاء قائمة جديدة 📌")
    else:
        await create_and_pin_list_message(bot, chat_id)
        await message.answer("تم بدء حلقة جديدة وإنشاء القائمة 📌")


@dp.callback_query(F.data == "open_list")
async def open_list(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    if not await is_group_admin(bot, chat_id, user_id):
        await callback.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
        return

    data = get_group_data(chat_id)
    data["is_open"] = True

    await callback.answer("تم فتح القائمة ✅", show_alert=True)
    await update_list_message(bot, chat_id)


@dp.callback_query(F.data == "close_list")
async def close_list(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    if not await is_group_admin(bot, chat_id, user_id):
        await callback.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
        return

    data = get_group_data(chat_id)
    data["is_open"] = False

    await callback.answer("تم غلق القائمة 🔒", show_alert=True)
    await update_list_message(bot, chat_id)


@dp.callback_query(F.data == "register")
async def register_student(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    name = callback.from_user.full_name

    data = get_group_data(chat_id)

    if not data["is_open"]:
        await callback.answer("القائمة مغلقة 🔒", show_alert=True)
        return

    data["attendance"][user_id] = {
        "name": name,
        "read": False,
        "type": "student"
    }

    await callback.answer("تم تسجيلك في قائمة الطالبات ✅", show_alert=True)
    await update_list_message(bot, chat_id)


@dp.callback_query(F.data == "teacher")
async def register_teacher(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    name = callback.from_user.full_name

    data = get_group_data(chat_id)

    if not data["is_open"]:
        await callback.answer("القائمة مغلقة 🔒", show_alert=True)
        return

    data["attendance"][user_id] = {
        "name": name,
        "read": False,
        "type": "teacher"
    }

    await callback.answer("تم تسجيلك في قائمة المعلمات 📚", show_alert=True)
    await update_list_message(bot, chat_id)


@dp.callback_query(F.data == "listener")
async def register_listener(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    name = callback.from_user.full_name

    data = get_group_data(chat_id)

    if not data["is_open"]:
        await callback.answer("القائمة مغلقة 🔒", show_alert=True)
        return

    data["attendance"][user_id] = {
        "name": name,
        "read": False,
        "type": "listener"
    }

    await callback.answer("تم تسجيلك في قائمة المستمعات 🎧", show_alert=True)
    await update_list_message(bot, chat_id)


@dp.callback_query(F.data == "read")
async def mark_read(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    data = get_group_data(chat_id)

    if not data["is_open"]:
        await callback.answer("القائمة مغلقة 🔒", show_alert=True)
        return

    if user_id not in data["attendance"]:
        await callback.answer("يجب تسجيل اسمك أولًا", show_alert=True)
        return

    data["attendance"][user_id]["read"] = True
    await callback.answer("تم وضع علامة ✅ بجوار اسمك", show_alert=True)
    await update_list_message(bot, chat_id)


@dp.callback_query(F.data == "delete_name")
async def delete_name(callback: CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id

    data = get_group_data(chat_id)

    if user_id in data["attendance"]:
        del data["attendance"][user_id]
        await callback.answer("تم حذف اسمك من القائمة ❌", show_alert=True)
        await update_list_message(bot, chat_id)
    else:
        await callback.answer("اسمك غير موجود في القائمة", show_alert=True)


@dp.message(Command("reset"))
async def reset_list(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_group_admin(bot, chat_id, user_id):
        await message.answer("❌ هذا الأمر للأدمن فقط")
        return

    data = get_group_data(chat_id)
    data["attendance"].clear()
    data["is_open"] = False

    if data["list_message_id"]:
        updated = await update_list_message(bot, chat_id)
        if updated:
            await message.answer("تم مسح جميع الأسماء وإغلاق القائمة ❌")
        else:
            await create_and_pin_list_message(bot, chat_id)
            await message.answer("تمت إعادة إنشاء القائمة بعد المسح 📌")
    else:
        await create_and_pin_list_message(bot, chat_id)
        await message.answer("تم إنشاء قائمة جديدة فارغة 📌")


# =========================
# Webhook startup/shutdown
# =========================
async def on_startup(bot: Bot):
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True,
    )
    print(f"Webhook set to: {WEBHOOK_URL}")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await bot.session.close()
    print("Webhook deleted")


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

    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))


if __name__ == "__main__":
    main()
