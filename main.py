import asyncio
import logging
import os
from datetime import datetime
import pytz
from html import escape

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

groups_data = {}


def get_group_data(chat_id):
    if chat_id not in groups_data:
        groups_data[chat_id] = {
            "is_open": False,
            "attendance": {},
            "list_message_id": None,
        }
    return groups_data[chat_id]


def get_arabic_date():
    tz = pytz.timezone("Asia/Riyadh")
    now = datetime.now(tz)

    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")


def make_user_link(user_id, name):
    return f'<a href="tg://user?id={user_id}">{escape(name)}</a>'


def get_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 سجل اسمي", callback_data="register"),
                InlineKeyboardButton(text="📚 معلمة", callback_data="teacher"),
            ],
            [
                InlineKeyboardButton(text="🎧 مستمعة", callback_data="listener"),
                InlineKeyboardButton(text="✅ قرأت", callback_data="read"),
            ],
            [
                InlineKeyboardButton(text="❌ حذف اسمي", callback_data="delete"),
            ],
            [
                InlineKeyboardButton(text="🔓 فتح", callback_data="open"),
                InlineKeyboardButton(text="🔒 غلق", callback_data="close"),
            ],
            [
                InlineKeyboardButton(text="📤 إرسال نسخة", callback_data="send"),
            ],
        ]
    )


def build_text(chat_id):
    data = get_group_data(chat_id)

    date, time = get_arabic_date()
    status = "🟢 مفتوحة" if data["is_open"] else "🔴 مغلقة"

    teachers, students, listeners = [], [], []

    for u in data["attendance"].values():
        name = make_user_link(u["id"], u["name"])

        if u.get("read"):
            name += " ✅"

        if u["type"] == "teacher":
            teachers.append(f"👑 <b>{name}</b>")
        elif u["type"] == "listener":
            listeners.append(name)
        else:
            students.append(name)

    text = f"""📅 {date}
⏱ {time}

🌧⤸ بِسْمِ اللَّهِ الرَّحْمٰنِ الرَّحِيم ⤹🌧

📌 حالة القائمة: {status}

📚 المعلمات:
"""
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(teachers)]) or "لا يوجد"

    text += "\n\n📝 الطالبات:\n"
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(students)]) or "لا يوجد"

    text += "\n\n🎧 المستمعات:\n"
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(listeners)]) or "لا يوجد"

    text += """
---------------------------------•
اللهم لا تدع لنا ذنبًا إلا غفرته...
"""

    return text


async def create_list(chat_id):
    msg = await bot.send_message(
        chat_id,
        build_text(chat_id),
        reply_markup=get_inline_keyboard(),
        parse_mode="HTML",
    )
    get_group_data(chat_id)["list_message_id"] = msg.message_id


async def update_list(chat_id):
    data = get_group_data(chat_id)

    if not data["list_message_id"]:
        return await create_list(chat_id)

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=data["list_message_id"],
            text=build_text(chat_id),
            reply_markup=get_inline_keyboard(),
            parse_mode="HTML",
        )
    except:
        data["list_message_id"] = None
        await create_list(chat_id)


@dp.message(Command("start"))
async def start(message: Message):
    await create_list(message.chat.id)


@dp.callback_query()
async def cb(c: CallbackQuery):
    chat_id = c.message.chat.id
    user_id = c.from_user.id
    name = c.from_user.full_name

    data = get_group_data(chat_id)

    if c.data == "open":
        data["is_open"] = True

    elif c.data == "close":
        data["is_open"] = False

    elif c.data == "register":
        if data["is_open"]:
            data["attendance"][user_id] = {
                "id": user_id,
                "name": name,
                "type": "student",
                "read": False,
            }

    elif c.data == "teacher":
        if data["is_open"]:
            data["attendance"][user_id] = {
                "id": user_id,
                "name": name,
                "type": "teacher",
                "read": False,
            }

    elif c.data == "listener":
        if data["is_open"]:
            data["attendance"][user_id] = {
                "id": user_id,
                "name": name,
                "type": "listener",
                "read": False,
            }

    elif c.data == "read":
        if user_id in data["attendance"]:
            data["attendance"][user_id]["read"] = True

    elif c.data == "delete":
        data["attendance"].pop(user_id, None)

    elif c.data == "send":
        await bot.send_message(
            chat_id,
            build_text(chat_id),
            reply_markup=get_inline_keyboard(),
            parse_mode="HTML",
        )

    await update_list(chat_id)
    await c.answer()


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
