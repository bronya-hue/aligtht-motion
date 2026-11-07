import os
import logging
import httpx
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8080").rstrip("/")
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
        "🤖 <b>Alight Motion Farming Bot</b>\n\nPilih mode:\nGunakan perintah <code>/bulk [jumlah]</code> untuk farming massal.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML",
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
        await q.edit_message_text(f"❌ Error backend: <code>{e}</code>", parse_mode="HTML")
        return

    if not data.get("success"):
        await q.edit_message_text(f"❌ Gagal: {data.get('message', data)}")
        return

    d = data.get("data", {})
    text = (
        f"✅ <b>Akun Premium Berhasil Dibuat!</b>\n\n"
        f"📧 Email: <code>{d.get('email')}</code>\n"
        f"🆔 UID: <code>{d.get('uid')}</code>\n"
        f"🧾 Order: <code>{d.get('orderId')}</code>\n"
        f"📅 Valid: <code>{d.get('validUntil')}</code>\n\n"
        f"📌 <b>CARA LOGIN DI APLIKASI ALIGHT MOTION:</b>\n"
        f"1. Buka aplikasi Alight Motion di HP Anda.\n"
        f"2. Pilih menu <i>Login with Email</i>.\n"
        f"3. Masukkan email di atas: <code>{d.get('email')}</code>\n"
        f"4. Klik tombol 'Kirim Magic Link' di aplikasi.\n"
        f"5. Ketik perintah ini di bot:\n"
        f"   <code>/login {d.get('email')}</code>\n"
        f"6. Bot akan mengirim tombol link. Klik tombol tersebut, dan akun premium siap dipakai! 🎉"
    )
    await q.edit_message_text(text, parse_mode="HTML")

async def cmd_login(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) == 0:
        await update.message.reply_text("Format salah. Gunakan: <code>/login email@domain.com</code>", parse_mode="HTML")
        return
        
    email = ctx.args[0]
    msg = await update.message.reply_text(f"⏳ Mengecek inbox untuk <code>{email}</code>...", parse_mode="HTML")
    
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{BACKEND}/api/inbox", json={"email": email})
            data = r.json()
            
        if data.get("success") and data.get("link"):
            link = data["link"]
            oob = data.get("oobCode", "-")
            text = (
                f"🔗 <b>Link Login Ditemukan!</b>\n\n"
                f"📌 <b>Kode OOB:</b> <code>{oob}</code>\n\n"
                f"<b>Cara 1 (Otomatis):</b>\nKlik tombol di bawah ini dari HP Anda.\n\n"
                f"<b>Cara 2 (Manual):</b>\nJika tombol gagal, buka aplikasi Alight Motion -> Login -> Masukkan Kode OOB."
            )
            keyboard = [[InlineKeyboardButton("🔗 Buka Aplikasi Alight Motion", url=link)]]
            await msg.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await msg.edit_text(f"❌ Gagal: {data.get('message', 'Link belum masuk atau email salah.')}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")

async def cmd_bulk(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) == 0:
        await update.message.reply_text("Format: <code>/bulk [jumlah]</code>\nContoh: <code>/bulk 10</code>", parse_mode="HTML")
        return
    try:
        count = int(ctx.args[0])
        if count > 50: 
            await update.message.reply_text("Maksimal 50 akun per perintah agar server tidak down.")
            return
    except ValueError:
        await update.message.reply_text("Jumlah harus berupa angka.")
        return

    msg = await update.message.reply_text(f"⏳ Memulai bulk farming {count} akun...\nProses ini akan memakan waktu.")
    success, fail, results = 0, 0, []

    for i in range(count):
        try:
            async with httpx.AsyncClient(timeout=150) as c:
                r = await c.post(f"{BACKEND}/api/auto", json={})
                data = r.json()
            if data.get("success"):
                results.append(f"✅ {data['data']['email']}")
                success += 1
            else: fail += 1
        except: fail += 1
            
        await asyncio.sleep(10) # Jeda antar akun
        
        if (i+1) % 5 == 0 or (i+1) == count:
            await msg.edit_text(f"⏳ Proses: {i+1}/{count}\n✅ Sukses: {success}\n❌ Gagal: {fail}")

    result_text = f"🏁 <b>Bulk Selesai</b>\n✅ Sukses: {success}\n❌ Gagal: {fail}\n\n" + "\n".join(results[-10:])
    await msg.edit_text(result_text, parse_mode="HTML")

async def cb_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{BACKEND}/api/stats")
        await q.edit_message_text(f"📊 Statistik:\n<code>{r.text[:3500]}</code>", parse_mode="HTML")
    except Exception as e:
        await q.edit_message_text(f"❌ {e}")

async def route_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("mode")
    if mode == "send":
        await handle_email(update, ctx)
    elif mode == "verify":
        await handle_link(update, ctx)

async def handle_email(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if "@" not in email: return await update.message.reply_text("❌ Format email salah.")
    ctx.user_data["email"], ctx.user_data["mode"] = email, "verify"
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{BACKEND}/api/send-link", json={"email": email})
        ok = r.status_code == 200
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        ctx.user_data["mode"] = None
        return
    await update.message.reply_text(f"{'✅' if ok else '❌'} Link {'terkirim' if ok else 'gagal'}.\n\nPaste URL magic link:", parse_mode="HTML")

async def handle_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    link, email = update.message.text.strip(), ctx.user_data.get("email")
    ctx.user_data["mode"] = None
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{BACKEND}/api/verify-link", json={"email": email, "magicLink": link})
        data = r.json()
    except Exception as e: return await update.message.reply_text(f"❌ Error: {e}")
    if data.get("success") or data.get("status"):
        await update.message.reply_text(f"✅ Premium aktif <code>{email}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text(f"❌ Gagal: {data}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("bulk", cmd_bulk))
    app.add_handler(CallbackQueryHandler(cb_auto, pattern="^auto$"))
    app.add_handler(CallbackQueryHandler(cb_stats, pattern="^stats$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
