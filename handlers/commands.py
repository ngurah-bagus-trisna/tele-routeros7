# handlers/commands.py
import logging
import os
from datetime import datetime
import config
from core.router_api import RouterAPI
from core.database import Database
from utils.formatter import format_bytes
from utils.decorators import restricted

api = RouterAPI()
db = Database()

@restricted
async def traffic_handler(update, context):
    args = context.args
    period = args[0] if args else None
    
    interfaces = api.get_interfaces()
    if interfaces is None:
        # Tambahkan await di sini
        await update.message.reply_text("❌ Gagal mengambil data interface.")
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
                display_rx = max(0, curr_rx - past_rx)
                display_tx = max(0, curr_tx - past_tx)
            else:
                display_rx, display_tx = 0, 0
                msg += f"⚠️ *{name}*: Data {period} belum ada.\n"
        else:
            display_rx, display_tx = curr_rx, curr_tx

        msg += f"🌐 *{name}*\n"
        msg += f"  📥 RX: `{format_bytes(display_rx)}`\n"
        msg += f"  📤 TX: `{format_bytes(display_tx)}`\n\n"

    # Tambahkan await di sini (baris 48 yang bermasalah di log kamu)
    await update.message.reply_text(msg, parse_mode='Markdown')

@restricted
async def backup_handler(update, context):
    """Handle /backup command - backup router configuration"""
    try:
        # Send status message
        status_msg = await update.message.reply_text(
            "⏳ Memulai backup router...",
            parse_mode='Markdown'
        )
        
        # Trigger backup
        logging.info("Triggering router backup...")
        backup_result = api.backup_router()
        
        if backup_result is None:
            await status_msg.edit_text(
                "❌ Gagal memicu backup router. Pastikan router API accessible.",
                parse_mode='Markdown'
            )
            return
        
        await status_msg.edit_text(
            "⏳ Download backup file dari router...",
            parse_mode='Markdown'
        )
        
        # Download backup file
        backup_file_path = api.download_backup()
        
        if backup_file_path is None:
            await status_msg.edit_text(
                "❌ Gagal download backup file. Pastikan file tersedia di router.",
                parse_mode='Markdown'
            )
            return
        
        # Check file size
        file_size = os.path.getsize(backup_file_path)
        max_size = getattr(config, 'MAX_BACKUP_SIZE_MB', 50) * 1024 * 1024  # Default 50MB
        
        if file_size > max_size:
            await status_msg.edit_text(
                f"❌ File backup terlalu besar: {format_bytes(file_size)} (max: {format_bytes(max_size)})",
                parse_mode='Markdown'
            )
            # Clean up
            os.remove(backup_file_path)
            return
        
        # Send file to user
        await status_msg.edit_text(
            "⏳ Mengirim file backup...",
            parse_mode='Markdown'
        )
        
        router_info = api.get_system_identity()
        router_name = router_info.get('name', 'MikroTik-Router') if router_info else 'MikroTik-Router'
        
        # Create descriptive filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{router_name}_backup_{timestamp}.backup"
        
        with open(backup_file_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=backup_filename,
                caption=f"✅ **Backup Berhasil**\n"
                        f"Router: `{router_name}`\n"
                        f"Ukuran: `{format_bytes(file_size)}`\n"
                        f"Waktu: `{timestamp}`",
                parse_mode='Markdown'
            )
        
        # Delete status message
        await status_msg.delete()
        
        logging.info(f"✅ Backup file sent: {backup_filename} ({format_bytes(file_size)})")
        
        # Clean up temp file
        os.remove(backup_file_path)
        
    except Exception as e:
        logging.error(f"❌ Error in backup handler: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            parse_mode='Markdown'
        )

@restricted
async def dhcp_handler(update, context):
    """Handle /dhcp command - show current DHCP leases"""
    try:
        dhcp_leases = api.get_dhcp_leases()
        
        if not dhcp_leases:
            await update.message.reply_text("❌ Gagal mengambil data DHCP lease.")
            return
        
        msg = f"📋 **DHCP Leases** ({len(dhcp_leases)} active)\n"
        msg += "━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, lease in enumerate(dhcp_leases[:20], 1):  # Limit to 20 to avoid message too long
            ip = lease.get('address', 'N/A')
            mac = lease.get('mac-address', 'N/A')
            hostname = lease.get('host-name', 'N/A')
            active = "✅" if lease.get('active') else "❌"
            expires = lease.get('expires-after', 'N/A')
            
            msg += f"{i}. {active} **{hostname}**\n"
            msg += f"   IP: `{ip}`\n"
            msg += f"   MAC: `{mac}`\n"
            msg += f"   Expires: `{expires}s`\n\n"
        
        if len(dhcp_leases) > 20:
            msg += f"... dan {len(dhcp_leases) - 20} lainnya"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"❌ Error in dhcp handler: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@restricted
async def hotspot_handler(update, context):
    """Handle /hotspot command - show current hotspot active users"""
    try:
        sessions = api.get_hotspot_sessions()
        
        if not sessions:
            await update.message.reply_text("❌ Gagal mengambil data hotspot sessions.")
            return
        
        msg = f"🔓 **Active Hotspot Users** ({len(sessions)} online)\n"
        msg += "━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, session in enumerate(sessions[:20], 1):  # Limit to 20
            username = session.get('name', 'N/A')
            ip = session.get('address', 'N/A')
            mac = session.get('mac-address', 'N/A')
            
            msg += f"{i}. 👤 **{username}**\n"
            msg += f"   IP: `{ip}`\n"
            msg += f"   MAC: `{mac}`\n\n"
        
        if len(sessions) > 20:
            msg += f"... dan {len(sessions) - 20} lainnya"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"❌ Error in hotspot handler: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@restricted
async def interface_handler(update, context):
    """Handle /interface command - show all interface status"""
    try:
        interfaces = api.get_interfaces_detail()
        
        if not interfaces:
            await update.message.reply_text("❌ Gagal mengambil data interface.")
            return
        
        msg = f"🔌 **Interface Status** ({len(interfaces)} total)\n"
        msg += "━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, iface in enumerate(interfaces[:25], 1):  # Limit to 25
            name = iface.get('name', 'N/A')
            running = iface.get('running', False)
            disabled = iface.get('disabled', False)
            speed = iface.get('link-speed', 'N/A')
            rx_error = iface.get('rx-error', 0)
            tx_error = iface.get('tx-error', 0)
            rx_drop = iface.get('rx-drop', 0)
            tx_drop = iface.get('tx-drop', 0)
            
            # Status indicator
            status_icon = "🟢" if (running and not disabled) else "🔴"
            status_text = "UP" if (running and not disabled) else "DOWN"
            
            msg += f"{i}. {status_icon} **{name}** `{status_text}`\n"
            msg += f"   ⚡ Speed: `{speed}`\n"
            
            # Errors info if any
            if rx_error > 0 or tx_error > 0:
                msg += f"   ❌ Errors - RX: `{rx_error}` TX: `{tx_error}`\n"
            if rx_drop > 0 or tx_drop > 0:
                msg += f"   📉 Drops - RX: `{rx_drop}` TX: `{tx_drop}`\n"
            
            msg += "\n"
        
        if len(interfaces) > 25:
            msg += f"... dan {len(interfaces) - 25} lainnya"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"❌ Error in interface handler: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")