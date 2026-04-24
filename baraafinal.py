from aiogram.filters import Command

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
