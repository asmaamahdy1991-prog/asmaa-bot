import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

groups_data = {}


def get_group_data(chat_id: int):
    if chat_id not in groups_data:
        groups_data[chat_id] = {
            "is_open": False,
            "attendance": {},
            "list_message_id": None,
            "bottom_message_id": None,
        }
    return groups_data[chat_id]


async def is_group_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        print("is_group_admin error:", repr(e))
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
            [
                InlineKeyboardButton(text="📤 إرسال لآخر الدردشة", callback_data="send_bottom"),
            ],
        ]
    )


def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 عرض القائمة")],
            [
                KeyboardButton(text="🔄 تحديث القائمة"),
                KeyboardButton(text="🆕 بدء حلقة جديدة"),
            ],
            [KeyboardButton(text="📤 إرسال القائمة")],
        ],
        resize_keyboard=True,
    )


def build_list_text(chat_id: int):
    data = get_group_data(chat_id)

    status = "🟢 مفتوحة" if data["is_open"] else "🔴 مغلقة"

    teachers = []
    students = []
    listeners = []

    for user in data["attendance"].values():
        name = user["name"]

        if user.get("read", False):
            name += " ✅"

        if user["type"] == "teacher":
            teachers.append(name)
        elif user["type"] == "listener":
            listeners.append(name)
        else:
            students.append(name)
text = f"""🌧━━━━━━━━━━━━━━━━━━🌧
⤸ بِسْـــمِ اللَّـهِ الرَّحمَـٰنِ الرَّحيـٰــم ⤹
🌧━━━━━━━━━━━━━━━━━━🌧

🌙 ﴿ وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا ﴾  
📖 [العنكبوت: 69]

🔰 قال رسول الله ﷺ:
"الَّذِي يَقْرَأُ القُرْآنَ وَهُوَ ماهِرٌ بِهِ معَ السَّفَرةِ الكِرَامِ،
وَالَّذِي يقرَأُ القُرْآنَ ويَتَتَعْتَعُ فِيهِ وَهُو عليهِ شَاقٌّ لَهُ أَجْران"
📚 رواه مسلم

❤️ نبدأ الحلقة بعون الله تعالى ❤️

📌 غاليتي:
لحجز دورك اضغطي ضغطة واحدة على الخيار المناسب لكِ 👇

🌙━━━━━━━━━━━━━━━━━━🌙
📖 قائمة السفرة الكرام البررة 📖
🌙━━━━━━━━━━━━━━━━━━🌙

📌 حالة القائمة: {status}

"""
   

    text += "📚 المعلمات:\n"
    text += "\n".join([f"{i + 1}- {name}" for i, name in enumerate(teachers)]) or "لا يوجد"

    text += "\n\n📝 الطالبات:\n"
    text += "\n".join([f"{i + 1}- {name}" for i, name in enumerate(students)]) or "لا يوجد"

    text += "\n\n🎧 المستمعات:\n"
    text += "\n".join([f"{i + 1}- {name}" for i, name in enumerate(listeners)]) or "لا يوجد"

    return text


async def create_and_pin_list(chat_id: int):
    data = get_group_data(chat_id)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=build_list_text(chat_id),
        reply_markup=get_inline_keyboard(),
    )

    data["list_message_id"] = msg.message_id

    try:
        await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=msg.message_id,
            disable_notification=True,
        )
    except Exception as e:
        print("pin_chat_message error:", repr(e))


async def send_new_bottom(chat_id: int):
    data = get_group_data(chat_id)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=build_list_text(chat_id),
        reply_markup=get_inline_keyboard(),
    )

    data["bottom_message_id"] = msg.message_id


async def update_pinned(chat_id: int):
    data = get_group_data(chat_id)

    if not data["list_message_id"]:
        return False

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=data["list_message_id"],
            text=build_list_text(chat_id),
            reply_markup=get_inline_keyboard(),
        )
        return True
    except Exception as e:
        error_text = str(e).lower()

        if "message is not modified" in error_text:
            return True

        data["list_message_id"] = None
        print("update_pinned error:", repr(e))
        return False


async def update_bottom(chat_id: int):
    data = get_group_data(chat_id)

    if not data["bottom_message_id"]:
        return False

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=data["bottom_message_id"],
            text=build_list_text(chat_id),
            reply_markup=get_inline_keyboard(),
        )
        return True
    except Exception as e:
        error_text = str(e).lower()

        if "message is not modified" in error_text:
            return True

        data["bottom_message_id"] = None
        print("update_bottom error:", repr(e))
        return False


async def update_all(chat_id: int):
    updated = await update_pinned(chat_id)

    if not updated:
        await create_and_pin_list(chat_id)

    await update_bottom(chat_id)


@dp.message(Command("start"))
async def start(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا البوت يعمل فقط بواسطة الأدمنز في الجروب")
        return

    await message.answer(
        "♻️ جاري تحديث لوحة الأدمن...",
        reply_markup=ReplyKeyboardRemove(),
    )

    await message.answer(
        "✅ تم تفعيل لوحة تحكم الأدمن",
        reply_markup=get_admin_keyboard(),
    )


@dp.message(Command("sendlist"))
async def send_list_command(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الأمر للأدمن فقط")
        return

    await send_new_bottom(message.chat.id)
    await message.answer("✅ تم إرسال القائمة في آخر الدردشة")


@dp.message(Command("reset"))
async def reset_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الأمر للأدمن فقط")
        return

    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = False
    data["bottom_message_id"] = None

    await update_all(message.chat.id)
    await message.answer("❌ تم مسح جميع الأسماء وإغلاق القائمة")


@dp.message(F.text == "📋 عرض القائمة")
async def show_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return

    await send_new_bottom(message.chat.id)
    await message.answer("📋 تم إرسال القائمة في آخر الدردشة")


@dp.message(F.text == "🔄 تحديث القائمة")
async def refresh(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return

    await update_all(message.chat.id)
    await message.answer("🔄 تم تحديث القائمة")


@dp.message(F.text == "📤 إرسال القائمة")
async def send_bottom_btn(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return

    await send_new_bottom(message.chat.id)
    await message.answer("✅ تم إرسال القائمة في آخر الدردشة")


@dp.message(F.text == "🆕 بدء حلقة جديدة")
async def new_session(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return

    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = False
    data["bottom_message_id"] = None

    await update_all(message.chat.id)
    await message.answer("🆕 تم بدء حلقة جديدة")


@dp.callback_query()
async def buttons(c: CallbackQuery):
    if not c.message:
        await c.answer("حدث خطأ", show_alert=True)
        return

    chat_id = c.message.chat.id
    user_id = c.from_user.id
    name = c.from_user.full_name

    data = get_group_data(chat_id)

    if c.data == "open_list":
        if not await is_group_admin(chat_id, user_id):
            await c.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
            return

        data["is_open"] = True
        await update_all(chat_id)
        await c.answer("✅ تم فتح القائمة")
        return

    if c.data == "close_list":
        if not await is_group_admin(chat_id, user_id):
            await c.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
            return

        data["is_open"] = False
        await update_all(chat_id)
        await c.answer("🔒 تم غلق القائمة")
        return

    if c.data == "send_bottom":
        if not await is_group_admin(chat_id, user_id):
            await c.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
            return

        await send_new_bottom(chat_id)
        await c.answer("✅ تم إرسال القائمة في آخر الدردشة")
        return

    if c.data == "register":
        if not data["is_open"]:
            await c.answer("❌ القائمة مغلقة", show_alert=True)
            return

        if user_id in data["attendance"]:
            await c.answer("❌ تم تسجيلك بالفعل", show_alert=True)
            return

        data["attendance"][user_id] = {
            "name": name,
            "type": "student",
            "read": False,
        }

        await update_all(chat_id)
        await c.answer("✅ تم تسجيلك")
        return

    if c.data == "teacher":
        if not data["is_open"]:
            await c.answer("❌ القائمة مغلقة", show_alert=True)
            return

        if user_id in data["attendance"]:
            await c.answer("❌ تم تسجيلك بالفعل", show_alert=True)
            return

        data["attendance"][user_id] = {
            "name": name,
            "type": "teacher",
            "read": False,
        }

        await update_all(chat_id)
        await c.answer("📚 تم تسجيلك كمعلمة")
        return

    if c.data == "listener":
        if not data["is_open"]:
            await c.answer("❌ القائمة مغلقة", show_alert=True)
            return

        if user_id in data["attendance"]:
            await c.answer("❌ تم تسجيلك بالفعل", show_alert=True)
            return

        data["attendance"][user_id] = {
            "name": name,
            "type": "listener",
            "read": False,
        }

        await update_all(chat_id)
        await c.answer("🎧 تم تسجيلك كمستمعة")
        return

    if c.data == "read":
        if not data["is_open"]:
            await c.answer("❌ القائمة مغلقة", show_alert=True)
            return

        if user_id not in data["attendance"]:
            await c.answer("❌ سجلي اسمك أولًا", show_alert=True)
            return

        if data["attendance"][user_id].get("read", False):
            await c.answer("❌ لقد ضغطتِ قرأت بالفعل", show_alert=True)
            return

        data["attendance"][user_id]["read"] = True

        await update_all(chat_id)
        await c.answer("✅ تم تسجيل قرأت")
        return

    if c.data == "delete_name":
        if user_id in data["attendance"]:
            del data["attendance"][user_id]
            await update_all(chat_id)
            await c.answer("❌ تم حذف اسمك")
        else:
            await c.answer("الاسم غير موجود", show_alert=True)
        return

    await c.answer()


@dp.message()
async def fallback_message(message: Message):
    await message.answer("✅ البوت يعمل، لكن هذه الرسالة غير مخصصة له")


async def main():
    print("Bot is starting with polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
