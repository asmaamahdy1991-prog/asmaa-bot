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
        }
    return groups_data[chat_id]

async def is_group_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False

def get_inline_keyboard() -> InlineKeyboardMarkup:
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

def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 عرض القائمة")],
            [KeyboardButton(text="🔄 تحديث القائمة"), KeyboardButton(text="🆕 بدء حلقة جديدة")],
            [KeyboardButton(text="📤 إرسال القائمة")],   # تم تغيير النص هنا
        ],
        resize_keyboard=True,
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

    text = f"📌 حالة القائمة: {status}\n\n📚 المعلمات:\n"
    text += "\n".join(f"{i+1}- {u['name']}" for i, u in enumerate(teachers)) or "لا يوجد\n"
    text += "\n\n📝 الطالبات:\n"
    text += "\n".join(f"{i+1}- {u['name']}" for i, u in enumerate(students)) or "لا يوجد\n"
    text += "\n\n🎧 المستمعات:\n"
    text += "\n".join(f"{i+1}- {u['name']}" for i, u in enumerate(listeners)) or "لا يوجد\n"
    return text

async def create_and_pin_list_message(chat_id: int):
    data = get_group_data(chat_id)
    sent = await bot.send_message(
        chat_id=chat_id,
        text=build_list_text(chat_id),
        reply_markup=get_inline_keyboard(),
    )
    data["list_message_id"] = sent.message_id
    try:
        await bot.pin_chat_message(chat_id, sent.message_id)
    except Exception as e:
        print("pin_chat_message error:", repr(e))

async def update_list_message(chat_id: int):
    data = get_group_data(chat_id)
    message_id = data["list_message_id"]
    if not message_id:
        return False
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=build_list_text(chat_id),
            reply_markup=get_inline_keyboard(),
        )
        return True
    except Exception as e:
        if "message is not modified" in str(e):
            return True
        if "message to edit not found" in str(e) or "message can't be edited" in str(e):
            data["list_message_id"] = None
            return False
        print("update_list_message error:", repr(e))
        return False

@dp.message(Command("start"))
async def start(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا البوت يعمل فقط بواسطة الأدمنز في الجروب")
        return
    await message.answer("♻️ جاري تحديث لوحة الأدمن...", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "✅ تم تفعيل لوحة تحكم الأدمن",
        reply_markup=get_admin_reply_keyboard(),   # استخدام الدالة الموحدة
    )

@dp.message(F.text == "📋 عرض القائمة")
async def show_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return
    await create_and_pin_list_message(message.chat.id)
    await message.answer("📌 تم إنشاء القائمة")

@dp.message(F.text == "🔄 تحديث القائمة")
async def refresh_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return
    await create_and_pin_list_message(message.chat.id)
    await message.answer("🔄 تم إنشاء قائمة محدثة")

@dp.message(F.text == "📤 إرسال القائمة")   # تم تغيير النص هنا
async def send_list_to_bottom(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return
    await bot.send_message(
        chat_id=message.chat.id,
        text=build_list_text(message.chat.id),
        reply_markup=get_inline_keyboard(),
    )
    await message.answer("✅ تم إرسال القائمة في آخر الدردشة")

@dp.message(F.text == "🆕 بدء حلقة جديدة")
async def new_session(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الزر للأدمن فقط")
        return
    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = False
    await create_and_pin_list_message(message.chat.id)
    await message.answer("🆕 تم بدء حلقة جديدة")

@dp.message(Command("reset"))
async def reset_list(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الأمر للأدمن فقط")
        return
    data = get_group_data(message.chat.id)
    data["attendance"].clear()
    data["is_open"] = False
    await create_and_pin_list_message(message.chat.id)
    await message.answer("❌ تم مسح جميع الأسماء وإغلاق القائمة")

@dp.callback_query()
async def handle_buttons(callback: CallbackQuery):
    if not callback.message:
        await callback.answer("حدث خطأ داخلي", show_alert=True)
        return
    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name
    data = get_group_data(chat_id)

    if callback.data == "open_list":
        if not await is_group_admin(chat_id, user_id):
            await callback.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
            return
        data["is_open"] = True
        if not await update_list_message(chat_id):
            data["list_message_id"] = None
            await create_and_pin_list_message(chat_id)
        await callback.answer("✅ تم فتح القائمة")

    elif callback.data == "close_list":
        if not await is_group_admin(chat_id, user_id):
            await callback.answer("❌ هذا الزر للأدمن فقط", show_alert=True)
            return
        data["is_open"] = False
        if not await update_list_message(chat_id):
            data["list_message_id"] = None
            await create_and_pin_list_message(chat_id)
        await callback.answer("🔒 تم غلق القائمة")

    elif callback.data == "register":
        if not data["is_open"]:
            await callback.answer("❌ القائمة مغلقة", show_alert=True)
            return
        data["attendance"][user_id] = {"name": user_name, "type": "student"}
        await update_list_message(chat_id)
        await callback.answer("✅ تم تسجيلك")

    elif callback.data == "teacher":
        if not data["is_open"]:
            await callback.answer("❌ القائمة مغلقة", show_alert=True)
            return
        data["attendance"][user_id] = {"name": user_name, "type": "teacher"}
        await update_list_message(chat_id)
        await callback.answer("📚 تم تسجيلك كمعلمة")

    elif callback.data == "listener":
        if not data["is_open"]:
            await callback.answer("❌ القائمة مغلقة", show_alert=True)
            return
        data["attendance"][user_id] = {"name": user_name, "type": "listener"}
        await update_list_message(chat_id)
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
        await update_list_message(chat_id)
        await callback.answer("✅ تم وضع علامة قرأت")

    elif callback.data == "delete_name":
        if user_id in data["attendance"]:
            del data["attendance"][user_id]
            await update_list_message(chat_id)
            await callback.answer("❌ تم حذف اسمك")
        else:
            await callback.answer("الاسم غير موجود", show_alert=True)

    else:
        await callback.answer()

@dp.message()
async def fallback_message(message: Message):
    await message.answer("✅ البوت يعمل، لكن هذه الرسالة غير مخصصة له")

@dp.message(Command("sendlist"))
async def send_list_command(message: Message):
    if not await is_group_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ هذا الأمر للأدمن فقط")
        return
    await bot.send_message(
        chat_id=message.chat.id,
        text=build_list_text(message.chat.id),
        reply_markup=get_inline_keyboard(),
    )
    await message.answer("✅ تم إرسال القائمة في آخر الدردشة")

async def main():
    print("Bot is starting with polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
