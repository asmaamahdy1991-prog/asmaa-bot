import asyncio
import json
import logging
import os
from datetime import datetime
from html import escape

import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

# 1. إعداد السجلات (Logging)
logging.basicConfig(level=logging.INFO)

# 2. جلب التوكن وتعريف البوت والـ Dispatcher (الترتيب هنا هو الحل لخطأ الصورة)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing! تأكد من إضافته في إعدادات Railway")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_FILE = "groups.json"

# =======================
# 📦 تخزين البيانات (Storage)
# =======================

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(groups_data, f, ensure_ascii=False, indent=2)

groups_data = load_data()

def get_group(chat_id: int):
    cid = str(chat_id)
    if cid not in groups_data:
        groups_data[cid] = {
            "is_open": False,
            "attendance": {},
            "list_message_id": None,
        }
    return groups_data[cid]

# =======================
# ⏰ الوقت والتحقق (Helpers)
# =======================

def get_time():
    tz = pytz.timezone("Asia/Riyadh")
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

async def is_admin(chat_id: int, user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        return m.status in ["administrator", "creator"]
    except:
        return False

# =======================
# 👇 الواجهة (UI & Building)
# =======================

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
            [InlineKeyboardButton(text="❌ حذف", callback_data="del")],
            [
                InlineKeyboardButton(text="🔓 فتح", callback_data="open"),
                InlineKeyboardButton(text="🔒 غلق", callback_data="close"),
            ],
        ]
    )

def build(chat_id: int):
    data = get_group(chat_id)
    date, time = get_time()
    status = "🟢 مفتوحة" if data["is_open"] else "🔴 مغلقة"
    teachers, students, listeners = [], [], []

    for u in data["attendance"].values():
        name = f'<a href="tg://user?id={u["id"]}">{escape(u["name"])}</a>'
        if u.get("read"):
            name += " ✅"
        
        if u["type"] == "teacher":
            teachers.append(name)
        elif u["type"] == "listener":
            listeners.append(name)
        else:
            students.append(name)

    return f"""
📅 {date}
⏱ {time}

📌 الحالة: {status}

📚 المعلمات:
{chr(10).join(teachers) if teachers else "لا يوجد"}

📝 الطالبات:
{chr(10).join(students) if students else "لا يوجد"}

🎧 المستمعات:
{chr(10).join(listeners) if listeners else "لا يوجد"}
"""

async def send_list(chat_id: int):
    msg = await bot.send_message(
        chat_id,
        build(chat_id),
        reply_markup=keyboard(),
        parse_mode="HTML",
    )
    get_group(chat_id)["list_message_id"] = msg.message_id
    save_data()

# =======================
# 🚀 الأوامر (Commands)
# =======================

@dp.message(Command("start"))
async def start(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    g = get_group(message.chat.id)
    g["attendance"].clear()
    g["is_open"] = True
    save_data()
    await send_list(message.chat.id)

@dp.message(F.text.in_({"بدء قائمة جديده", "بدء قايمة جديده"}))
async def new_list(message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    g = get_group(message.chat.id)
    g["attendance"].clear()
    g["is_open"] = True
    save_data()
    await send_list(message.chat.id)

@dp.message(F.text == "كمل")
async def send_bottom(message: Message):
    # تحديث معرف الرسالة عند استخدام "كمل" لضمان استمرار التحديث على أحدث رسالة
    msg = await message.answer(build(message.chat.id), reply_markup=keyboard(), parse_mode="HTML")
    get_group(message.chat.id)["list_message_id"] = msg.message_id
    save_data()

# =======================
# 🎛 الأزرار (Buttons)
# =======================

@dp.callback_query()
async def handler(call: CallbackQuery):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    name = call.from_user.full_name
    g = get_group(chat_id)

    if call.data == "open":
        if not await is_admin(chat_id, user_id):
            return await call.answer("للمشرفين فقط ❌", show_alert=True)
        g["is_open"] = True
        await call.answer("تم الفتح")

    elif call.data == "close":
        if not await is_admin(chat_id, user_id):
            return await call.answer("للمشرفين فقط ❌", show_alert=True)
        g["is_open"] = False
        await call.answer("تم الإغلاق")

    elif call.data == "reg":
        if not g["is_open"]: return await call.answer("القائمة مغلقة", show_alert=True)
        if str(user_id) in g["attendance"]: return await call.answer("أنت مسجل بالفعل")
        g["attendance"][str(user_id)] = {"id": user_id, "name": name, "type": "student", "read": False}
        await call.answer("تم التسجيل")

    elif call.data == "teacher":
        if not g["is_open"]: return await call.answer("القائمة مغلقة", show_alert=True)
        if str(user_id) in g["attendance"]: return await call.answer("أنت مسجل بالفعل")
        g["attendance"][str(user_id)] = {"id": user_id, "name": name, "type": "teacher", "read": False}
        await call.answer("تم تسجيل معلمة")

    elif call.data == "listen":
        if not g["is_open"]: return await call.answer("القائمة مغلقة", show_alert=True)
        if str(user_id) in g["attendance"]: return await call.answer("أنت مسجل بالفعل")
        g["attendance"][str(user_id)] = {"id": user_id, "name": name, "type": "listener", "read": False}
        await call.answer("تم تسجيل مستمعة")

    elif call.data == "read":
        if str(user_id) not in g["attendance"]: return await call.answer("سجل أولاً", show_alert=True)
        g["attendance"][str(user_id)]["read"] = True
        await call.answer("تم التحديث")

    elif call.data == "del":
        g["attendance"].pop(str(user_id), None)
        await call.answer("تم الحذف")

    save_data()
    # تحديث الرسالة الحالية
    try:
        await call.message.edit_text(text=build(chat_id), reply_markup=keyboard(), parse_mode="HTML")
    except:
        pass

# =======================
# ▶️ التشغيل (Run)
# =======================

async def main():
    logging.info("البوت بدأ العمل...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
