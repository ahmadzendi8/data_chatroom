import os
import psycopg2
import json
from datetime import datetime, timedelta, timezone
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Konfigurasi Database ---
PGHOST = os.environ.get("PGHOST", "")
PGPORT = os.environ.get("PGPORT", "")
PGUSER = os.environ.get("PGUSER", "")
PGPASSWORD = os.environ.get("PGPASSWORD", "")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "")
TOKEN = os.environ.get("TOKEN", "")

# --- Helper: UTC ke WIB ---
def utc_to_wib(dt_utc):
    WIB = timezone(timedelta(hours=7))
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(WIB)

# --- Query Database ---
def search_by_time_range(start_str, end_str, username=None, limit=1000):
    conn = psycopg2.connect(
        dbname=POSTGRES_DB,
        user=PGUSER,
        password=PGPASSWORD,
        host=PGHOST,
        port=PGPORT
    )
    c = conn.cursor()
    query = "SELECT username, content, timestamp FROM chat WHERE timestamp_wib >= %s AND timestamp_wib <= %s"
    params = [start_str, end_str]
    if username:
        query += " AND LOWER(username) = %s"
        params.append(username.lower())
    query += " ORDER BY timestamp LIMIT %s"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    c.close()
    conn.close()
    hasil = []
    for row in rows:
        hasil.append({
            "username": row[0],
            "content": row[1],
            "timestamp": row[2]
        })
    return hasil

# --- Handler /data ---
async def data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.message.text.replace('/data', '', 1).strip()
    if not args:
        await update.message.reply_text(
            "Format: \n 1. /data waktu_awal,waktu_akhir\n 2. /data waktu_awal,waktu_akhir,username\n"
            "Contoh:\n/data 2025-08-17 10:00:00,2025-08-17 11:00:00\n"
            "atau\n/data 2025-08-17 10:00:00,2025-08-17 11:00:00,ahmadkholiln75"
            "\n\n 📌data terbatas❗️❗️❗️ tidak bisa cek riwayat terlalu jauh"
        )
        return
    parts = [s.strip() for s in args.split(',')]
    if len(parts) < 2:
        await update.message.reply_text("Format salah! Minimal: /data waktu_awal,waktu_akhir")
        return
    start_str, end_str = parts[0], parts[1]
    username = parts[2] if len(parts) > 2 else None
    hasil = search_by_time_range(start_str, end_str, username)
    if not hasil:
        await update.message.reply_text("Tidak ada chat pada rentang waktu tersebut.")
        return

    # Penamaan file hasil
    if username:
        safe_username = "".join(c for c in username if c.isalnum() or c in ('_', '-')).strip()
        filename = f"hasil_{safe_username}.txt"
    else:
        filename = f"hasil_{update.message.from_user.id}.txt"

    # Simpan ke file TXT: [tanggal] username: content
    with open(filename, "w", encoding="utf-8") as f:
        for chat in hasil:
            try:
                chat_time_utc = datetime.utcfromtimestamp(int(chat["timestamp"]))
                waktu_wib = utc_to_wib(chat_time_utc).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                waktu_wib = ""
            f.write(f"[{waktu_wib}] {chat.get('username')}: {chat.get('content')}\n")
        f.write(f"\nTotal chat: {len(hasil)}\n")
    with open(filename, "rb") as f:
        await update.message.reply_document(document=InputFile(f), filename=filename)
    # Hapus file setelah dikirim
    try:
        os.remove(filename)
    except Exception as e:
        print(f"Gagal menghapus file {filename}: {e}")
        
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Gunakan perintah:\n"
        "1. cari data berdasarkan waktu\n/data waktu_awal,waktu_akhir\n"
        "Contoh:\n/data 2025-08-17 10:00:00,2025-08-17 11:00:00\n"
        "2. jika cari berdasarkan username\n/data waktu_awal,waktu_akhir,username\n"
        "Contoh:\n/data 2025-08-17 10:00:00,2025-08-17 11:00:00,ahmadkholiln75"
        "\n\n 📌data terbatas❗️❗️❗️ tidak bisa cek riwayat terlalu jauh"
    )

# --- Setup Bot Telegram ---
if __name__ == "__main__":
    app_telegram = ApplicationBuilder().token(TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("data", data_command))
    print("Bot Telegram aktif...")
    app_telegram.run_polling()
