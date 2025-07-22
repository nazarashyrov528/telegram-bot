import asyncio
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# 👤 ADMIN CONFIGURATION
ADMIN_ID = 6185683417
ALLOWED_USERS = {ADMIN_ID}

# 🗂️ Session & Scheduling Data
user_sessions = {}
waiting_for = {}
scheduled_posts = []
previous_messages = {}

# 🔧 Main Menu Keyboard
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Reklama Goýmаk", callback_data='reklama')],
        [InlineKeyboardButton("📊 Statistika", callback_data='statistika')],
        [InlineKeyboardButton("📂 Postlarym", callback_data='postlarym')]
    ])

# 🔙 Back button
def back_to_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Yza", callback_data="back_main")]
    ])

# 🚀 START Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Auto Poster boty ulanmak üçin @NazarAshyrov a yaz.Bot mugtdyr.")
        return

    await update.message.reply_text(
        "👋 Hoş geldiňiz! Aşakdaky menýulardan birini saýlaň:",
        reply_markup=main_menu_keyboard()
    )

# 🤖 BUTTON Handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ALLOWED_USERS:
        await query.edit_message_text("❌ Rugsat ýok.")
        return

    data = query.data

    if data == 'reklama':
        await query.edit_message_text(
            "📌 Post görnüşini saýlaň:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🖼 Surat", callback_data='surat'),
                    InlineKeyboardButton("✏ Tekst", callback_data='tekst')
                ],
                [InlineKeyboardButton("🔙 Yza", callback_data="back_main")]
            ])
        )

    elif data in ['surat', 'tekst']:
        user_sessions[user_id] = {'type': data}
        waiting_for[user_id] = 'photo' if data == 'surat' else 'text'
        prompt = "🖼 Surat ugradyň:" if data=='surat' else "✍ Tekst giriziň:"
        await query.edit_message_text(prompt, reply_markup=back_to_main_menu())

    elif data == 'statistika':
        kanal_sany = len({p['channel'] for p in scheduled_posts})
        post_sany = len(scheduled_posts)
        await query.edit_message_text(
            f"📊 Statistik:\n📢 Kanallar: {kanal_sany}\n📬 Postlar: {post_sany}",
            reply_markup=back_to_main_menu()
        )

    elif data == 'postlarym':
        user_posts = [p for p in scheduled_posts if p['user_id']==user_id]
        if not user_posts:
            await query.edit_message_text("📭 Siziň postlaryňyz ýok.", reply_markup=back_to_main_menu())
            return
        buttons = [
            [InlineKeyboardButton(
                f"{i+1}) {p['channel']} ({'⏸' if p.get('paused') else '▶'})", 
                callback_data=f"post_{i}"
            )] for i,p in enumerate(user_posts)
        ]
        buttons.append([InlineKeyboardButton("🔙 Yza", callback_data="back_main")])
        await query.edit_message_text("📂 Postlaryňyz:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith('post_'):
        idx = int(data.split('_')[1])
        user_posts = [p for p in scheduled_posts if p['user_id']==user_id]
        if idx >= len(user_posts): return
        post = user_posts[idx]
        real_idx = scheduled_posts.index(post)
        ctrl = [
            InlineKeyboardButton("🗑 Poz", callback_data=f"delete_{real_idx}"),
            InlineKeyboardButton("▶ Dowam" if post.get('paused') else "⏸ Duruz", callback_data=f"toggle_{real_idx}")
        ]
        reply_markup = InlineKeyboardMarkup([ctrl, [InlineKeyboardButton("🔙 Yza", callback_data="back_main")]])
        await query.edit_message_text(
            f"📤 Kanal: {post['channel']}\n🕒 Minut: {post['minute']}\n📆 Gün: {post['day']}\n📮 Ugradylan: {post['sent_count']}\n🔁 Galyan: {post['max_count']-post['sent_count']}",
            reply_markup=reply_markup
        )

    elif data.startswith('delete_'):
        idx = int(data.split('_')[1])
        if idx < len(scheduled_posts):
            scheduled_posts.pop(idx)
        await query.edit_message_text("✅ Post pozuldy.", reply_markup=back_to_main_menu())

    elif data.startswith('toggle_'):
        idx = int(data.split('_')[1])
        if idx < len(scheduled_posts):
            scheduled_posts[idx]['paused'] = not scheduled_posts[idx].get('paused', False)
        await query.edit_message_text("🔄 Status üýtgedildi.", reply_markup=back_to_main_menu())

    elif data == 'back_main':
        await query.edit_message_text(
            "👋 Baş menýu:",
            reply_markup=main_menu_keyboard()
        )

# 💬 MESSAGE Handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS: return

    if user_id in waiting_for:
        step = waiting_for[user_id]
        sess = user_sessions[user_id]

        if step == 'photo' and update.message.photo:
            sess['photo'] = update.message.photo[-1].file_id
            waiting_for[user_id] = 'caption'
            await update.message.reply_text("📝 Surata caption giriziň:")

        elif step == 'text':
            sess['text'] = update.message.text
            waiting_for[user_id] = 'minute'
            await update.message.reply_text("🕒 Her näçe minutda ugradylsyn? (mysal: 10)")

        elif step == 'caption':
            sess['caption'] = update.message.text
            waiting_for[user_id] = 'minute'
            await update.message.reply_text("🕒 Her näçe minutda ugradylsyn? (mysal: 10)")

        elif step == 'minute':
            try:
                sess['minute'] = int(update.message.text)
                waiting_for[user_id] = 'day'
                await update.message.reply_text("📅 Näçe gün dowam etsin? (mysal: 2)")
            except:
                await update.message.reply_text("⚠️ Minuty san bilen giriziň!")

        elif step == 'day':
            try:
                sess['day'] = int(update.message.text)
                waiting_for[user_id] = 'channel'
                await update.message.reply_text("📢 Haýsy kanal? (@username görnüşinde)")
            except:
                await update.message.reply_text("⚠️ Günü san bilen giriziň!")

        elif step == 'channel':
            sess['channel'] = update.message.text.strip()
            waiting_for.pop(user_id)

            # Post döretmek
            post = {
                'user_id': user_id,
                'type': sess['type'],
                'minute': sess['minute'],
                'day': sess['day'],
                'channel': sess['channel'],
                'next_time': time.time(),
                'sent_count': 0,
                'max_count': (sess['day']*24*60)//sess['minute']
            }
            if sess['type']=='surat':
                post['photo'], post['caption'] = sess['photo'], sess['caption']
            else:
                post['text'] = sess['text']
            scheduled_posts.append(post)
            await update.message.reply_text("✅ Post goşuldy, awtomat goýulýar.")

# ⏰ Scheduler
async def scheduler(app):
    while True:
        now = time.time()
        for post in scheduled_posts:
            if post.get('paused') or post['sent_count'] >= post['max_count']: 
                continue
            if now >= post['next_time']:
                try:
                    if post['channel'] in previous_messages:
                        try:
                            await app.bot.delete_message(post['channel'], previous_messages[post['channel']])
                        except:
                            pass

                    if post['type']=='surat':
                        msg = await app.bot.send_photo(post['channel'], post['photo'], caption=post['caption'])
                    else:
                        msg = await app.bot.send_message(post['channel'], post['text'])

                    previous_messages[post['channel']] = msg.message_id
                    post['sent_count'] += 1
                    post['next_time'] = now + post['minute']*60
                except Exception as e:
                    print(f"Ugradyp bolmady: {e}")
        await asyncio.sleep(30)

# ✅ MAIN START
async def main():
    app = ApplicationBuilder().token("7449661719:AAHxiVuJ0RIVU971Io2o_F5r6dvuM3WUdFI").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, message_handler))
    asyncio.create_task(scheduler(app))
    print("🤖 Bot işläp başlady...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
