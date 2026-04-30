import asyncio
import logging
import os
from datetime import datetime
import pytz
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
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


def get_arabic_date():
    tz = pytz.timezone("Asia/Riyadh")
    now = datetime.now(tz)

    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M")

    return date, time


async def is_group_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


def make_user_link(user_id: int, name: str):
    return f'<a href="tg://user?id={user_id}">{escape(name)}</a>'


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


def build_list_text(chat_id: int):
    data = get_group_data(chat_id)
    status = "🟢 مفتوحة" if data["is_open"] else "🔴 مغلقة"

    date, time = get_arabic_date()

    teachers, students, listeners = [], [], []

    for user in data["attendance"].values():
        name = make_user_link(user["id"], user["name"])

        if user.get("read"):
            name += " ✅"

        if user["type"] == "teacher":
            teachers.append(f"👑 <b>{name}</b>")
        elif user["type"] == "listener":
            listeners.append(name)
        else:
            students.append(name)

    text = f"""📅 {date}
⏱ {time}

📌 حالة القائمة: {status}

📚 المعلمات:
"""
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(teachers)]) or "لا يوجد"

    text += "\n\n📝 الطالبات:\n"
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(students)]) or "لا يوجد"

    text += "\n\n🎧 المستمعات:\n"
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(listeners)]) or "لا يوجد"

    return text


async def create_and_pin_list(chat_id):
    msg = await bot.send_message(
        chat_id,
        build_list_text(chat_id),
        reply_markup=get_inline_keyboard(),
        parse_mode="HTML"
    )
    get_group_data(chat_id)["list_message_id"] = msg.message_id

    try:
        await bot.pin_chat_message(chat_id, msg.message_id)
    except:
        pass


async def send_new_bottom(chat_id):
    msg = await bot.send_message(
        chat_id,
        build_list_text(chat_id),
        reply_markup=get_inline_keyboard(),
        parse_mode="HTML"
    )
    get_group_data(chat_id)["bottom_message_id"] = msg.message_id


async def update_all(chat_id):
    await create_and_pin_list(chat_id)


# ================= START =================

@dp.message(Command("start"))
async def start(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return await message.answer("❌ للأدمن فقط")

    await message.answer("♻️ جاري التحديث...", reply_markup=ReplyKeyboardRemove())
    await message.answer("✅ تم التفعيل")

    await create_and_pin_list(message.chat.id)


# ================= أوامرك الجديدة =================

@dp.message(F.text == "كمل")
async def continue_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return

    await send_new_bottom(message.chat.id)


@dp.message(F.text == "بدء قايمة جديده")
async def new_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return

    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = False

    await send_new_bottom(message.chat.id)


# ================= BUTTONS =================

@dp.callback_query()
async def buttons(c: CallbackQuery):
    chat_id = c.message.chat.id
    user_id = c.from_user.id
    name = c.from_user.full_name

    data = get_group_data(chat_id)

    if c.data == "open_list":
        data["is_open"] = True

    elif c.data == "close_list":
        data["is_open"] = False

    elif c.data == "send_bottom":
        await send_new_bottom(chat_id)

    elif c.data == "register":
        if data["is_open"]:
            data["attendance"][user_id] = {"id": user_id, "name": name, "type": "student", "read": False}

    elif c.data == "teacher":
        if data["is_open"]:
            data["attendance"][user_id] = {"id": user_id, "name": name, "type": "teacher", "read": False}

    elif c.data == "listener":
        if data["is_open"]:
            data["attendance"][user_id] = {"id": user_id, "name": name, "type": "listener", "read": False}

    elif c.data == "read":
        if user_id in data["attendance"]:
            data["attendance"][user_id]["read"] = True

    elif c.data == "delete_name":
        data["attendance"].pop(user_id, None)

    await create_and_pin_list(chat_id)
    await c.answer("تم")


# ================= IGNORE =================

@dp.message()
async def ignore(message: Message):
    pass


# ================= RUN =================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
