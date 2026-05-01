import asyncio
import logging
import os
from datetime import datetime
from html import escape

import pytz
from aiogram import Bot, Dispatcher, F
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


async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False


def make_link(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{escape(name)}</a>'


def keyboard() -> InlineKeyboardMarkup:
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
            [InlineKeyboardButton(text="❌ حذف", callback_data="del")],
            [
                InlineKeyboardButton(text="🔓 فتح", callback_data="open"),
                InlineKeyboardButton(text="🔒 غلق", callback_data="close"),
            ],
        ]
    )


def build(chat_id: int) -> str:
    data = get_group_data(chat_id)
    date, time = get_time()

    status = "🟢 مفتوحة" if data["is_open"] else "🔴 مغلقة"

    teachers, students, listeners = [], [], []

    for user in data["attendance"].values():
        name = make_link(user["id"], user["name"])
        if user["read"]:
            name += " ✅"

        if user["type"] == "teacher":
            teachers.append(name)
        elif user["type"] == "listener":
            listeners.append(name)
        else:
            students.append(name)

    text = f"""📅 {date}
⏱ {time}

📌 الحالة: {status}

📚 المعلمات:
"""
    text += "\n".join(teachers) or "لا يوجد"

    text += "\n\n📝 الطالبات:\n"
    text += "\n".join(students) or "لا يوجد"

    text += "\n\n🎧 المستمعات:\n"
    text += "\n".join(listeners) or "لا يوجد"

    return text


async def send_list(chat_id: int):
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
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            logging.error(f"Update error: {e}")


@dp.message(Command("start"))
async def start(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return

    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = True
    data["list_message_id"] = None

    await send_list(message.chat.id)


@dp.message(F.text == "كمل")
async def send_bottom(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return

    await bot.send_message(
        message.chat.id,
        build(message.chat.id),
        reply_markup=keyboard(),
        parse_mode="HTML",
    )


@dp.message(F.text.in_({"بدء قايمة جديده", "بدء قائمة جديده"}))
async def new_list(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return

    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = True
    data["list_message_id"] = None

    await send_list(message.chat.id)


@dp.callback_query()
async def handle_buttons(callback: CallbackQuery):
    if not callback.message:
        return

    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    full_name = callback.from_user.full_name

    data = get_group_data(chat_id)

    if callback.data == "open":
        data["is_open"] = True

    elif callback.data == "close":
        data["is_open"] = False

    elif callback.data == "reg":
        if not data["is_open"]:
            await callback.answer("القائمة مغلقة", show_alert=True)
            return

        if user_id in data["attendance"]:
            await callback.answer("أنتِ مسجلة بالفعل", show_alert=True)
            return

        data["attendance"][user_id] = {
            "id": user_id,
            "name": full_name,
            "type": "student",
            "read": False,
        }

    elif callback.data == "teacher":
        if not data["is_open"]:
            await callback.answer("القائمة مغلقة", show_alert=True)
            return

        data["attendance"][user_id] = {
            "id": user_id,
            "name": full_name,
            "type": "teacher",
            "read": False,
        }

    elif callback.data == "listen":
        if not data["is_open"]:
            await callback.answer("القائمة مغلقة", show_alert=True)
            return

        data["attendance"][user_id] = {
            "id": user_id,
            "name": full_name,
            "type": "listener",
            "read": False,
        }

    elif callback.data == "read":
        if user_id not in data["attendance"]:
            await callback.answer("سجلي أولًا", show_alert=True)
            return

        data["attendance"][user_id]["read"] = True

    elif callback.data == "del":
        data["attendance"].pop(user_id, None)
await update(chat)
await c.answer("تم")


@dp.message()
async def ignore(_: Message):
    pass


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
