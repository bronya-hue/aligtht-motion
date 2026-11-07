import os
import logging
import httpx
import asyncio
import datetime
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

# ==========================================
# MENU UTAMA
# ==========================================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Desain menu baru yang lebih rapi
    text = (
        "🤖 <b>Alight Motion Farming Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Silakan pilih menu di bawah ini:\n\n"
        "⚡ <b>Auto Premium</b>: Buat 1 akun premium secara instan.\n"
        "🚀 <b>Bulk Farming</b>: Buat banyak akun sekaligus.\n"
        "📧 <b>Manual Login</b>: Ambil link login untuk akun yang sudah ada.\n"
    )
    kb = [
        [InlineKeyboardButton("⚡ Auto Premium", callback_data="auto")],
        [InlineKeyboardButton("🚀 Bulk Farming", callback_data="bulk_menu")],
        [InlineKeyboardButton("📧 Manual Login", callback_data="manual")],
        [InlineKeyboardButton("📊 Statistik", callback_data="stats")]
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML",
    )

# ==========================================
# FITUR AUTO PREMIUM
# ==========================================
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

# ==========================================
# FITUR BULK FARMING (TOMBOL & PROSES)
# ==========================================
async def cb_bulk_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # Set state agar bot menunggu input angka dari user
    ctx.user_data["mode"] = "bulk_amount"
    await q.edit_message_text(
        "🚀 <b>Bulk Farming</b>\n\n"
        "Silakan ketik jumlah akun yang ingin dibuat.\n"
        "Contoh: <code>10</code> (Maksimal 50 per proses)\n\n"
        "Ketik /start untuk membatalkan.",
        parse_mode="HTML"
    )

async def run_bulk_process(update: Update, ctx: ContextTypes.DEFAULT_TYPE, count: int):
    msg = await update.message.reply_text(
        f"⏳ Memulai bulk farming {count} akun...\n"
        f"Estimasi waktu: ±{count * 10} detik.\n\n"
        f"<i>Bot akan mengirim file txt jika sudah selesai.</i>", 
        parse_mode="HTML"
    )
    
    success, fail, results = 0, 0, []
    filename = f"hasil_farming_{int(datetime.datetime.now().timestamp())}.txt"

    for i in range(count):
        try:
            async with httpx.AsyncClient(timeout=150) as c:
                r = await c.post(f"{BACKEND}/api/auto", json={})
                data = r.json()
            if data.get("success"):
                d = data['data']
                results.append(f"Email: {d['email']} | UID: {d['uid']} | Order: {d['orderId']}")
                success += 1
            else: 
                fail += 1
        except: 
            fail += 1
            
        await asyncio.sleep(10) # Jeda antar akun
        
        if (i+1) % 5 == 0 or (i+1) == count:
            await msg.edit_text(
                f"⏳ Proses: {i+1}/{count}\n"
                f"✅ Sukses: {success}\n"
                f"❌ Gagal: {fail}"
            )

    instruksi = (
        "📌 CARA LOGIN DI APLIKASI ALIGHT MOTION:\n"
        "1. Buka aplikasi Alight Motion di HP Anda.\n"
        "2. Pilih menu 'Login with Email'.\n"
        "3. Masukkan SALAH SATU email dari daftar di bawah.\n"
        "4. Klik tombol 'Kirim Magic Link' di aplikasi.\n"
        "5. Ketik perintah ini di bot: /login email_yang_dipilih\n"
        "6. Bot akan mengirim tombol link. Klik tombol tersebut dari HP Anda!\n"
        "--------------------------------------------------\n\n"
    )

    with open(filename, 'w') as f:
        f.write(f"=== HASIL FARMING ALIGHT MOTION ===\n")
        f.write(f"Tanggal: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Sukses: {success}\n")
        f.write(f"Total Gagal: {fail}\n\n")
        f.write(instruksi)
        f.write("\n".join(results))

    result_text = (
        f"🏁 <b>Bulk Selesai</b>\n"
        f"✅ Sukses: {success}\n"
        f"❌ Gagal: {fail}\n\n"
        f"📌 <b>CARA LOGIN:</b>\n"
        f"1. Buka aplikasi Alight Motion -> Login with Email.\n"
        f"2. Masukkan salah satu email di file txt.\n"
        f"3. Ketik <code>/login email_tersebut</code> di bot ini.\n\n"
        f"Silakan unduh file di bawah untuk melihat daftar lengkap akun."
    )
    await msg.edit_text(result_text, parse_mode="HTML")
    
    if success > 0:
        with open(filename, 'rb') as document:
            await update.message.reply_document(
                document=document,
                filename=filename,
                caption=f"✅ Berhasil membuat {success} akun premium."
            )

# ==========================================
# FITUR LOGIN MANUAL & STATISTIK
# ==========================================
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

async def cb_manual(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["mode"] = "send"
    await q.edit_message_text("Kirim email tujuan (contoh: <code>user@gmail.com</code>):", parse_mode="HTML")

async def cb_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{BACKEND}/api/stats")
        await q.edit_message_text(f"📊 Statistik:\n<code>{r.text[:3500]}</code>", parse_mode="HTML")
    except Exception as e:
        await q.edit_message_text(f"❌ {e}")

# ==========================================
# ROUTER PESAN TEKS
# ==========================================
async def route_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = ctx.user_data.get("mode")
    
    if mode == "bulk_amount":
        ctx.user_data["mode"] = None
        try:
            count = int(update.message.text.strip())
            if count > 50:
                await update.message.reply_text("❌ Maksimal 50 akun per proses agar server tidak down.")
                return
            if count <= 0:
                await update.message.reply_text("❌ Jumlah harus lebih dari 0.")
                return
            await run_bulk_process(update, ctx, count)
        except ValueError:
            await update.message.reply_text("❌ Format salah. Harap ketik angka saja (contoh: 10).")
            
    elif mode == "send":
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

# ==========================================
# MAIN
# ==========================================
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", cmd_login))
    
    app.add_handler(CallbackQueryHandler(cb_auto, pattern="^auto$"))
    app.add_handler(CallbackQueryHandler(cb_bulk_menu, pattern="^bulk_menu$"))
    app.add_handler(CallbackQueryHandler(cb_manual, pattern="^manual$"))
    app.add_handler(CallbackQueryHandler(cb_stats, pattern="^stats$"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))

    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
