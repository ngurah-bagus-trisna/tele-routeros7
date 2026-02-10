from core.router_api import RouterAPI
from core.database import Database
from utils.formatter import format_bytes

api = RouterAPI()
db = Database()

def traffic_handler(update, context):
    # Ambil argumen (misal: 1m)
    args = context.args
    period = args[0] if args else None
    
    interfaces = api.get_interfaces()
    if not interfaces:
        update.message.reply_text("❌ Gagal mengambil data interface.")
        return

    msg = f"📊 **Laporan Trafik**\n"
    msg += f"Periode: `{period if period else 'Real-time (Total)'}`\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"

    for iface in interfaces:
        name = iface.get('name')
        curr_rx = int(iface.get('rx-byte', 0))
        curr_tx = int(iface.get('tx-byte', 0))

        if period:
            past_data = db.get_past_data(name, period)
            if past_data:
                past_rx, past_tx = past_data
                # Hitung selisih (Pemakaian = Sekarang - Dulu)
                display_rx = max(0, curr_rx - past_rx)
                display_tx = max(0, curr_tx - past_tx)
            else:
                display_rx, display_tx = 0, 0
                msg += f"⚠️ *{name}*: Data historis belum tersedia.\n"
        else:
            # Jika tanpa argumen, tampilkan total uptime
            display_rx, display_tx = curr_rx, curr_tx

        msg += f"🌐 *{name}*\n"
        msg += f"  📥 RX: `{format_bytes(display_rx)}`\n"
        msg += f"  📤 TX: `{format_bytes(display_tx)}`\n"

    update.message.reply_text(msg, parse_mode='Markdown')