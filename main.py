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
    mecca_tz = pytz.timezone("Asia/Riyadh")
    now = datetime.now(mecca_tz)

    days = {
        "Saturday": "السبت",
        "Sunday": "الأحد",
        "Monday": "الإثنين",
        "Tuesday": "الثلاثاء",
        "Wednesday": "الأربعاء",
        "Thursday": "الخميس",
        "Friday": "الجمعة",
    }

    months = {
        "January": "يناير",
        "February": "فبراير",
        "March": "مارس",
        "April": "أبريل",
        "May": "مايو",
        "June": "يونيو",
        "July": "يوليو",
        "August": "أغسطس",
        "September": "سبتمبر",
        "October": "أكتوبر",
        "November": "نوفمبر",
        "December": "ديسمبر",
    }

    day_name = days[now.strftime("%A")]
    month_name = months[now.strftime("%B")]

    date_str = f"{day_name} - {now.day} {month_name} {now.year}"

    hour = now.hour
    minute = now.strftime("%M")

    if hour == 0:
        hour = 12
        period = "صباحًا"
    elif hour < 12:
        period = "صباحًا"
    elif hour == 12:
        period = "مساءً"
    else:
        hour -= 12
        period = "مساءً"

    time_str = f"{hour}:{minute} {period}"

    return date_str, time_str


async def is_group_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
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


def make_user_link(user_id: int, name: str):
    safe_name = escape(name)
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'


def build_list_text(chat_id: int):
    data = get_group_data(chat_id)

    status = "🟢 مفتوحة" if data["is_open"] else "🔴 مغلقة"
    date_str, time_str = get_arabic_date()

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

    total = len(data["attendance"])

    text = f"""📅 {date_str}
⏱ {time_str}

🌧⤸ بِسْـــمِ اللَّـهِ الرَّحمَـٰنِ الرَّحيـٰــم ⤹🌧

🌙وَالَّذِينَ جَاهَدُوا فِينَا لَنَهْدِيَنَّهُمْ سُبُلَنَا وَإِنَّ اللَّهَ لَمَعَ الْمُحْسِنِينَ [العنكبوت:69].

🔰عن عائشة رضي اللَّه عنها قالَتْ: قالَ رسولُ اللَّهِ ﷺ:الَّذِي يَقْرَأُ القُرْآنَ وَهُو ماهِرٌ بِهِ معَ السَّفَرةِ الكِرَامِ البَرَرَةِ،
وَالَّذِي يقرَأُ القُرْآنَ ويَتَتَعْتَعُ فِيهِ وَهُو عليهِ شَاقٌّ لَهُ أَجْران .رواه مسلم.

❤️نبدأ الحلقة بعون الله تعالي❤️

غاليتي لحجز دورك اضغطي ضغطة واحدة 👇👇👇

🌙🌧 قائمة السفرة الكرام البررة 🌙

📌 حالة القائمة: {status}
🔢 عدد المسجلات: {total}

━━━━━━━━━━━━━━

📚 المعلمات:
"""
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(teachers)]) or "لا يوجد"

    text += "\n\n📝 الطالبات:\n"
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(students)]) or "لا يوجد"

    text += "\n\n🎧 المستمعات:\n"
    text += "\n".join([f"{i+1}- {n}" for i, n in enumerate(listeners)]) or "لا يوجد"

    text += """
---------------------------------•
♡اللهم لا تدع لنا ذنبًا إلا غفرته ولا مريضًا إلا شفيته ولا همًّا إلا فرجته، اللهم اجعل الحياة زيادة لنا من كل خير والموت راحة لنا من كل شر، اللهم اجعل القرآن العظيم ربيع قلوبنا ونور صدورنا وجلاء همومنا وأحزاننا، اللهم آمين 🌙🌧
(اللهم ارحم أبي وجميع موتى المسلمين)
"""

    return text


async def create_and_pin_list(chat_id: int):
    data = get_group_data(chat_id)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=build_list_text(chat_id),
        reply_markup=get_inline_keyboard(),
        parse_mode="HTML",
    )

    data["list_message_id"] = msg.message_id

    try:
        await bot.pin_chat_message(chat_id, msg.message_id, disable_notification=True)
    except:
        pass


async def send_new_bottom(chat_id: int):
    data = get_group_data(chat_id)

    msg = await bot.send_message(
        chat_id=chat_id,
        text=build_list_text(chat_id),
        reply_markup=get_inline_keyboard(),
        parse_mode="HTML",
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
            parse_mode="HTML",
        )
        return True
    except:
        data["list_message_id"] = None
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
            parse_mode="HTML",
        )
        return True
    except:
        data["bottom_message_id"] = None
        return False


async def update_all(chat_id: int):
    if not await update_pinned(chat_id):
        await create_and_pin_list(chat_id)
    await update_bottom(chat_id)


@dp.message(Command("start"))
async def start(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return await message.answer("❌ للأدمن فقط")

    await message.answer("♻️ جاري التحديث...", reply_markup=ReplyKeyboardRemove())
    await message.answer("✅ تم التفعيل")
    await create_and_pin_list(message.chat.id)


@dp.message(F.text == "كمل")
async def continue_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return

    await send_new_bottom(message.chat.id)


@dp.message(F.text == "بدء قائمة جديده")
async def new_list_text(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return

    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = False
    data["bottom_message_id"] = None

    await send_new_bottom(message.chat.id)


@dp.message(F.text == "📋 عرض القائمة")
async def show_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return
    await send_new_bottom(message.chat.id)


@dp.message(F.text == "🔄 تحديث القائمة")
async def refresh(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return
    await update_all(message.chat.id)


@dp.message(F.text == "📤 إرسال القائمة")
async def send_bottom_btn(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return
    await send_new_bottom(message.chat.id)


@dp.message(F.text == "🆕 بدء حلقة جديدة")
async def new_session(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        return

    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = False
    data["bottom_message_id"] = None

    await update_all(message.chat.id)


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
            return await c.answer("❌ للأدمن فقط", show_alert=True)
        data["is_open"] = True

    elif c.data == "close_list":
        if not await is_group_admin(chat_id, user_id):
            return await c.answer("❌ للأدمن فقط", show_alert=True)
        data["is_open"] = False

    elif c.data == "send_bottom":
        if not await is_group_admin(chat_id, user_id):
            return await c.answer("❌ للأدمن فقط", show_alert=True)
        await send_new_bottom(chat_id)

    elif c.data == "register":
        if not data["is_open"]:
            return await c.answer("❌ مغلقة", show_alert=True)
        if user_id in data["attendance"]:
            return await c.answer("❌ مسجلة بالفعل", show_alert=True)

        data["attendance"][user_id] = {
            "id": user_id,
            "name": name,
            "type": "student",
            "read": False,
        }

    elif c.data == "teacher":
        if not data["is_open"]:
            return await c.answer("❌ مغلقة", show_alert=True)
        if user_id in data["attendance"]:
            return await c.answer("❌ مسجلة بالفعل", show_alert=True)

        data["attendance"][user_id] = {
            "id": user_id,
            "name": name,
            "type": "teacher",
            "read": False,
        }

    elif c.data == "listener":
        if not data["is_open"]:
            return await c.answer("❌ مغلقة", show_alert=True)
        if user_id in data["attendance"]:
            return await c.answer("❌ مسجلة بالفعل", show_alert=True)

        data["attendance"][user_id] = {
            "id": user_id,
            "name": name,
            "type": "listener",
            "read": False,
        }

    elif c.data == "read":
        if user_id not in data["attendance"]:
            return await c.answer("❌ سجلي أولًا", show_alert=True)
        if data["attendance"][user_id]["read"]:
            return await c.answer("❌ تم بالفعل", show_alert=True)

        data["attendance"][user_id]["read"] = True

    elif c.data == "delete_name":
        data["attendance"].pop(user_id, None)

    await update_all(chat_id)
    await c.answer("تم")


@dp.message()
async def ignore_unknown_messages(message: Message):
    pass


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
