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
        }
    return groups_data[chat_id]


def get_time():
    tz = pytz.timezone("Asia/Riyadh")
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")


async def is_admin(chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


def make_link(user_id, name):
    return f'<a href="tg://user?id={user_id}">{escape(name)}</a>'


def keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 سجل", callback_data="reg"),
                InlineKeyboardButton(text="📚 معلمة", callback_data="teacher"),
            ],
            [
                InlineKeyboardButton(text="🎧 مستمعة", callback_data="listen"),
                InlineKeyboardButton(text="✅ قرأت", callback_data="read"),
            ],
            [
                InlineKeyboardButton(text="❌ حذف", callback_data="del"),
            ],
            [
                InlineKeyboardButton(text="🔓 فتح", callback_data="open"),
                InlineKeyboardButton(text="🔒 غلق", callback_data="close"),
            ],
        ]
    )


def build(chat_id):
    data = get_group_data(chat_id)
    date, time = get_time()

    status = "🟢 مفتوحة" if data["is_open"] else "🔴 مغلقة"

    t, s, l = [], [], []

    for u in data["attendance"].values():
        name = make_link(u["id"], u["name"])
        if u["read"]:
            name += " ✅"

        if u["type"] == "teacher":
            t.append(name)
        elif u["type"] == "listener":
            l.append(name)
        else:
            s.append(name)

    text = f"""📅 {date}
⏱ {time}

📌 الحالة: {status}

📚 المعلمات:
"""
    text += "\n".join(t) or "لا يوجد"

    text += "\n\n📝 الطالبات:\n"
    text += "\n".join(s) or "لا يوجد"

    text += "\n\n🎧 المستمعات:\n"
    text += "\n".join(l) or "لا يوجد"

    return text


async def send_list(chat_id):
    msg = await bot.send_message(
        chat_id,
        build(chat_id),
        reply_markup=keyboard(),
        parse_mode="HTML",
    )
    get_group_data(chat_id)["list_message_id"] = msg.message_id


async def update(chat_id):
    data = get_group_data(chat_id)
    if not data["list_message_id"]:
        return

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=data["list_message_id"],
            text=build(chat_id),
            reply_markup=keyboard(),
            parse_mode="HTML",
        )
    except:
        pass


# ================= START =================

@dp.message(Command("start"))
async def start(m: Message):
    if not await is_admin(m.chat.id, m.from_user.id):
        return

    data = get_group_data(m.chat.id)
    data["attendance"].clear()
    data["is_open"] = True
    data["list_message_id"] = None

    await send_list(m.chat.id)


# ================= أوامر =================

@dp.message(F.text == "كمل")
async def send_bottom(m: Message):
    if not await is_admin(m.chat.id, m.from_user.id):
        return

    await bot.send_message(
        m.chat.id,
        build(m.chat.id),
        reply_markup=keyboard(),
        parse_mode="HTML",
    )


@dp.message(F.text.in_({"بدء قايمة جديده", "بدء قائمة جديده"}))
async def new_list(m: Message):
    if not await is_admin(m.chat.id, m.from_user.id):
        return

    data = get_group_data(m.chat.id)
    data["attendance"].clear()
    data["is_open"] = True
    data["list_message_id"] = None

    await send_list(m.chat.id)


# ================= BUTTONS =================

@dp.callback_query()
async def btn(c: CallbackQuery):
    if not c.message:
        return

    chat = c.message.chat.id
    uid = c.from_user.id
    name = c.from_user.full_name

    data = get_group_data(chat)

    if c.data == "open":
        data["is_open"] = True

    elif c.data == "close":
        data["is_open"] = False

    elif c.data == "reg":
        if not data["is_open"]:
            return await c.answer("مغلقة", True)

        if uid in data["attendance"]:
            return await c.answer("مسجلة", True)

        data["attendance"][uid] = {
            "id": uid,
            "name": name,
            "type": "student",
            "read": False,
        }

    elif c.data == "teacher":
        if not data["is_open"]:
            return await c.answer("مغلقة", True)

        data["attendance"][uid] = {
            "id": uid,
            "name": name,
            "type": "teacher",
            "read": False,
        }

    elif c.data == "listen":
        if not data["is_open"]:
            return await c.answer("مغلقة", True)

        data["attendance"][uid] = {
            "id": uid,
            "name": name,
            "type": "listener",
            "read": False,
        }

    elif c.data == "read":
        if uid not in data["attendance"]:
            return await c.answer("سجلي أولًا", True)

        data["attendance"][uid]["read"] = True

    elif c.data == "del":
        data["attendance"].pop(uid, None)

    await c.answer("تم")
    await update(chat)


@dp.message()
async def ignore(m: Message):
    pass


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
