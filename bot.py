import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BACKEND = os.getenv("BACKEND_URL", "http://localhost:3300").rstrip("/")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN belum di-set di environment")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("⚡ Auto Premium", callback_data="auto")],
        [InlineKeyboardButton("📧 Manual Magic Link", callback_data="manual")],
        [InlineKeyboardButton("📊 Statistik", callback_data="stats")],
    ]
    await update.message.reply_text(
        "🤖 *Alight Motion Farming Bot*\n\nPilih mode:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


async def cb_auto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Memproses...")
    await q.edit_message_text("⏳ Menjalankan auto premium, tunggu hingga 90 detik...")

    try:
        async with httpx.AsyncClient(timeout=150) as c:
            r = await c.post(f"{BACKEND}/api/auto", json={})
            data = r.json()
    except Exception as e:
        logger.exception("auto error")
        await q.edit_message_text(f"❌ Error backend: `{e}`", parse_mode="Markdown")
        return

    if not data.get("success"):
        await q.edit_message_text(f"❌ Gagal: {data.get('message', data)}")
        return

    d = data.get("data", {})
    text = (
        f"✅ *Akun Premium Berhasil Dibuat!*\n\n"
        f"📧 Email: `{d.get('email')}`\n"
        f"🆔 UID: `{d.get('uid')}`\n"
        f"🧾 Order: `{d.get('orderId')}`\n"
        f"📅 Valid: `{d.get('validUntil')}`\n\n"
        f"📌 *CARA LOGIN DI APLIKASI ALIGHT MOTION:*\n"
        f"1. Buka aplikasi Alight Motion di HP Anda.\n"
        f"2. Pilih menu *Login with Email*.\n"
        f"3. Masukkan email di atas: `{d.get('email')}`\n"
        f"4. Klik tombol 'Kirim Magic Link' di aplikasi.\n"
        f"5. Ketik perintah ini di bot untuk mengambil link login:\n"
        f"   `/login {d.get('email')}`\n"
        f"6. Bot akan mengirim link. Klik link tersebut dari HP yang ada aplikasinya, dan akun premium siap dipakai! 🎉"
    )
    await q.edit_message_text(text, parse_mode="Markdown")


async def cb_manual(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["mode"] = "send"
    await q.edit_message_text("Kirim email tujuan (contoh: `user@gmail.com`):", parse_mode="Markdown")


async def cb_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{BACKEND}/api/stats")
        await q.edit_message_text(f"📊 Statistik:\n`{r.text[:3500]}`", parse_mode="Markdown")
    except Exception as e:
        await q.edit_message_text(f"❌ {e}")


async def cmd_login(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) == 0:
        await update.message.reply_text("Format salah. Gunakan: `/login email@domain.com`", parse_mode="Markdown")
        return
        
    email = ctx.args[0]
    await update.message.reply_text(f"⏳ Mengecek inbox untuk `{email}`...\n_(Tunggu hingga 30 detik)_", parse_mode="Markdown")
    
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{BACKEND}/api/inbox", json={"email": email})
            data = r.json()
            
        if data.get("success") and data.get("link"):
            link = data["link"]
            oob = data.get("oobCode", "-")
            
            text = (
                f"🔗 *Link Login Ditemukan!*\n\n"
                f"📌 *Kode OOB:* `{oob}`\n\n"
                f"*Cara 1 (Otomatis via HP):*\n"
                f"Klik link di bawah ini (pastikan aplikasi Alight Motion sudah terinstall di HP ini):\n"
                f"{link}\n\n"
                f"*Cara 2 (Manual di Aplikasi):*\n"
                f"Jika link di atas malah buka browser, buka aplikasi Alight Motion -> Pilih Login -> Masukkan kode OOB di atas."
            )
            
            await update.message.reply_text(
                text,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(f"❌ Gagal: {data.get('message', 'Link belum masuk atau email salah.')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def route_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("mode")
    if mode == "send":
        await handle_email(update, ctx)
    elif mode == "verify":
        await handle_link(update, ctx)


async def handle_email(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if "@" not in email:
        await update.message.reply_text("❌ Format email salah.")
        return

    ctx.user_data["email"] = email
    ctx.user_data["mode"] = "verify"

    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{BACKEND}/api/send-link", json={"email": email})
        ok = r.status_code == 200
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        ctx.user_data["mode"] = None
        return

    await update.message.reply_text(
        f"{'✅' if ok else '❌'} {'Link terkirim' if ok else 'Gagal kirim'} ke `{email}`.\n\n"
        f"Paste URL magic link dari inbox:",
        parse_mode="Markdown",
    )


async def handle_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    email = ctx.user_data.get("email")
    ctx.user_data["mode"] = None

    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"{BACKEND}/api/verify-link",
                json={"email": email, "magicLink": link},
            )
        data = r.json()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        return

    if data.get("success") or data.get("status"):
        d = data.get("data", {})
        await update.message.reply_text(
            f"✅ Premium aktif `{email}`\nValid: `{d.get('validUntil', '-')}`",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(f"❌ Gagal: {data}")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CallbackQueryHandler(cb_auto, pattern="^auto$"))
    app.add_handler(CallbackQueryHandler(cb_manual, pattern="^manual$"))
    app.add_handler(CallbackQueryHandler(cb_stats, pattern="^stats$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))

    logger.info("Bot starting (long polling)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
