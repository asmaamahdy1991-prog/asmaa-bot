# ... (نفس المكتبات السابقة)

# إضافة فحص المشرفين للأزرار الحساسة
@dp.callback_query()
async def handler(call: CallbackQuery):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    name = call.from_user.full_name
    g = get_group(chat_id)

    # حماية أزرار الإدارة
    if call.data in ["open", "close"]:
        if not await is_admin(chat_id, user_id):
            return await call.answer("هذا الأمر للمشرفين فقط ❌", show_alert=True)
        
        g["is_open"] = (call.data == "open")
        await call.answer("تم التحديث بنجاح" if call.data == "open" else "تم إغلاق القائمة")

    elif call.data == "reg":
        if not g["is_open"]:
            return await call.answer("القائمة مغلقة حالياً 🔒", show_alert=True)
        if str(user_id) in g["attendance"]:
            return await call.answer("أنتِ مسجلة بالفعل ✨", show_alert=True)
        
        g["attendance"][str(user_id)] = {"id": user_id, "name": name, "type": "student", "read": False}
        await call.answer("تم تسجيلك ✅")

    # ... (باقي المعالجات بنفس النمط)

    elif call.data == "del":
        if str(user_id) in g["attendance"]:
            g["attendance"].pop(str(user_id))
            await call.answer("تم الحذف 🗑️")
        else:
            await call.answer("لستِ مسجلة أصلاً")

    save_data()
    
    # تحديث الرسالة التي تم الضغط عليها بدلاً من الرسالة المخزنة فقط
    # لضمان استجابة البوت حتى لو كانت الرسالة قديمة
    try:
        await call.message.edit_text(
            text=build(chat_id),
            reply_markup=keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.warning(f"Update failed: {e}")

# تعديل أمر "كمل" ليصبح هو الرسالة الأساسية للتحديث
@dp.message(F.text == "كمل")
async def send_bottom(message: Message):
    # إرسال رسالة جديدة وتحديث معرف الرسالة النشطة في البيانات
    msg = await message.answer(build(message.chat.id), reply_markup=keyboard(), parse_mode="HTML")
    get_group(message.chat.id)["list_message_id"] = msg.message_id
    save_data()
