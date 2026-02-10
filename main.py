import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import config
from core.router_api import RouterAPI
from core.database import Database
from handlers.commands import traffic_handler, backup_handler, dhcp_handler, hotspot_handler, interface_handler
from handlers.events import check_hotspot_events, check_dhcp_events, check_interface_events
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

async def check_hotspot_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job untuk monitoring hotspot login/logout events.
    Deteksi user baru login atau logout dan kirim notifikasi.
    """
    try:
        logging.debug("Checking hotspot events...")
        events = check_hotspot_events(api)
        
        if events and config.NOTIFICATION_ENABLED:
            for message, event_type in events:
                # Kirim notifikasi ke semua ALLOWED_USERS
                if config.SEND_TO_ALLOWED_USERS:
                    for user_id in config.ALLOWED_USERS:
                        try:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=message,
                                parse_mode='Markdown'
                            )
                            logging.info(f"✅ Notification sent to {user_id}: {event_type}")
                        except Exception as e:
                            logging.error(f"❌ Failed to send notification to {user_id}: {e}")
    except Exception as e:
        logging.error(f"❌ Error in hotspot job: {e}")

async def check_dhcp_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job untuk monitoring DHCP lease events.
    Deteksi new lease, renewal, release dan kirim notifikasi.
    """
    try:
        logging.debug("Checking DHCP events...")
        events = check_dhcp_events(api)
        
        if events and config.NOTIFICATION_ENABLED:
            for message, event_type in events:
                # Kirim notifikasi ke semua ALLOWED_USERS
                if config.SEND_TO_ALLOWED_USERS:
                    for user_id in config.ALLOWED_USERS:
                        try:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=message,
                                parse_mode='Markdown'
                            )
                            logging.info(f"✅ Notification sent to {user_id}: {event_type}")
                        except Exception as e:
                            logging.error(f"❌ Failed to send notification to {user_id}: {e}")
    except Exception as e:
        logging.error(f"❌ Error in DHCP job: {e}")

async def check_interface_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Job untuk monitoring interface status changes (link up/down).
    """
    try:
        logging.debug("Checking interface events...")
        events = check_interface_events(api)
        
        if events and config.NOTIFICATION_ENABLED:
            for message, event_type in events:
                # Kirim notifikasi ke semua ALLOWED_USERS
                if config.SEND_TO_ALLOWED_USERS:
                    for user_id in config.ALLOWED_USERS:
                        try:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=message,
                                parse_mode='Markdown'
                            )
                            logging.info(f"✅ Notification sent to {user_id}: {event_type}")
                        except Exception as e:
                            logging.error(f"❌ Failed to send notification to {user_id}: {e}")
    except Exception as e:
        logging.error(f"❌ Error in interface job: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log error yang terjadi pada bot."""
    logging.error(f"Exception while handling an update: {context.error}")

def main():
    # 1. Bangun Application
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # 2. Daftarkan Command Handlers
    application.add_handler(CommandHandler("traffic", traffic_handler))
    application.add_handler(CommandHandler("backup", backup_handler))
    application.add_handler(CommandHandler("dhcp", dhcp_handler))
    application.add_handler(CommandHandler("hotspot", hotspot_handler))
    application.add_handler(CommandHandler("interface", interface_handler))

    # 3. Setup Job Queue (Background Task)
    job_queue = application.job_queue
    
    # Traffic snapshot - Jalankan setiap 1 jam (3600 detik)
    # Jalankan pertama kali 10 detik setelah bot nyala
    job_queue.run_repeating(
        collect_traffic_job,
        interval=3600,
        first=10,
        name="traffic_snapshot"
    )
    
    # Hotspot monitoring - Jalankan setiap CHECK_INTERVAL detik
    # Jalankan pertama kali 5 detik setelah bot nyala
    hotspot_interval = getattr(config, 'HOTSPOT_CHK_INTERVAL', 30)
    job_queue.run_repeating(
        check_hotspot_job,
        interval=hotspot_interval,
        first=5,
        name="hotspot_check"
    )
    
    # DHCP monitoring - Jalankan setiap CHECK_INTERVAL detik
    # Jalankan pertama kali 6 detik setelah bot nyala
    dhcp_interval = getattr(config, 'DHCP_CHK_INTERVAL', 30)
    job_queue.run_repeating(
        check_dhcp_job,
        interval=dhcp_interval,
        first=6,
        name="dhcp_check"
    )
    
    # Interface monitoring - Jalankan setiap CHECK_INTERVAL detik
    # Jalankan pertama kali 7 detik setelah bot nyala
    interface_interval = getattr(config, 'INTERFACE_CHK_INTERVAL', 30)
    job_queue.run_repeating(
        check_interface_job,
        interval=interface_interval,
        first=7,
        name="interface_check"
    )

    # 4. Tambahkan Error Handler
    application.add_error_handler(error_handler)

    # 5. Jalankan Bot
    logging.info("🚀 MikroTik Bot started...")
    logging.info(f"✅ Hotspot check interval: {hotspot_interval}s")
    logging.info(f"✅ DHCP check interval: {dhcp_interval}s")
    logging.info(f"✅ Interface check interval: {interface_interval}s")
    logging.info(f"✅ Notifications: {'ENABLED' if config.NOTIFICATION_ENABLED else 'DISABLED'}")
    
    application.run_polling()

if __name__ == '__main__':
    main()