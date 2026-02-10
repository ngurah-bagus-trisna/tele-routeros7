import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import config
from core.router_api import RouterAPI
from core.database import Database
from handlers.commands import traffic_handler
from utils.formatter import format_bytes

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Inisialisasi API dan DB
api = RouterAPI()
db = Database()

async def collect_traffic_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job otomatis yang berjalan berkala untuk menyimpan snapshot trafik ke SQLite.
    Data ini yang digunakan untuk menghitung selisih /traffic 1h, 1d, 1m.
    """
    logging.info("Mengambil snapshot trafik harian...")
    interfaces = api.get_interfaces()
    
    if interfaces and isinstance(interfaces, list):
        for iface in interfaces:
            name = iface.get('name')
            rx = int(iface.get('rx-byte', 0))
            tx = int(iface.get('tx-byte', 0))
            db.save_snapshot(name, rx, tx)
        logging.info(f"Berhasil menyimpan snapshot untuk {len(interfaces)} interface.")
    else:
        logging.error("Gagal mengambil data interface untuk snapshot.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log error yang terjadi pada bot."""
    logging.error(f"Exception while handling an update: {context.error}")

def main():
    # 1. Bangun Application
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # 2. Daftarkan Command Handlers
    # Pastikan traffic_handler di handlers/commands.py sudah menerima parameter (update, context)
    application.add_handler(CommandHandler("traffic", traffic_handler))

    # 3. Setup Job Queue (Background Task)
    job_queue = application.job_queue
    
    # Jalankan snapshot setiap 1 jam (3600 detik)
    # Jalankan pertama kali 10 detik setelah bot nyala
    job_queue.run_repeating(collect_traffic_job, interval=3600, first=10)

    # 4. Tambahkan Error Handler
    application.add_error_handler(error_handler)

    # 5. Jalankan Bot
    print("🚀 MikroTik Bot started...")
    application.run_polling()

if __name__ == '__main__':
    main()