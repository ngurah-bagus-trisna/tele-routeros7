import logging
from core.router_api import RouterAPI
from core.database import Database

api = RouterAPI()
db = Database()

# State tracking untuk event detection
last_hotspot_sessions = {}
last_dhcp_leases = {}
last_interface_states = {}  # Track interface status

def format_hotspot_login_message(username, mac_address, ip_address):
    """Format pesan untuk hotspot login"""
    msg = f"🔓 **Hotspot Login**\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"👤 Username: `{username}`\n"
    msg += f"🖥️ MAC: `{mac_address}`\n"
    msg += f"🌐 IP: `{ip_address}`\n"
    msg += f"⏰ Time: `{get_current_time()}`\n"
    return msg

def format_hotspot_logout_message(username, mac_address, ip_address):
    """Format pesan untuk hotspot logout"""
    msg = f"🔐 **Hotspot Logout**\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"👤 Username: `{username}`\n"
    msg += f"🖥️ MAC: `{mac_address}`\n"
    msg += f"🌐 IP: `{ip_address}`\n"
    msg += f"⏰ Time: `{get_current_time()}`\n"
    return msg

def format_dhcp_event_message(mac_address, ip_address, hostname, event_type, lease_time=None):
    """Format pesan untuk DHCP event"""
    event_icons = {
        "new": "🆕",
        "renew": "🔄",
        "release": "❌",
        "expired": "⏱️",
        "unknown": "❓"
    }
    icon = event_icons.get(event_type, "❓")
    
    msg = f"{icon} **DHCP {event_type.upper()}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🖥️ MAC: `{mac_address}`\n"
    msg += f"🌐 IP: `{ip_address}`\n"
    if hostname:
        msg += f"📛 Hostname: `{hostname}`\n"
    if lease_time:
        msg += f"⏳ Lease: `{lease_time}s`\n"
    msg += f"⏰ Time: `{get_current_time()}`\n"
    return msg

def get_current_time():
    """Dapatkan current time dalam format readable"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def check_hotspot_events(api):
    """
    Check untuk hotspot login/logout events.
    Membandingkan current active sessions dengan last state.
    Return: List of tuples (message, event_type)
    """
    global last_hotspot_sessions
    
    events = []
    
    try:
        # Ambil current active hotspot sessions
        current_sessions = api.get_hotspot_sessions()
        
        if current_sessions is None:
            logging.warning("⚠️ Gagal mengambil hotspot sessions")
            return events
        
        if not isinstance(current_sessions, list):
            logging.warning("⚠️ Hotspot sessions bukan list")
            return events
        
        # Buat dict untuk tracking (key = username:mac)
        current_dict = {}
        for session in current_sessions:
            key = f"{session.get('name', 'unknown')}:{session.get('mac-address', 'unknown')}"
            current_dict[key] = session
        
        # Detect new logins
        for key, session in current_dict.items():
            if key not in last_hotspot_sessions:
                username = session.get('name', 'unknown')
                mac = session.get('mac-address', 'unknown')
                ip = session.get('address', 'unknown')
                
                msg = format_hotspot_login_message(username, mac, ip)
                events.append((msg, "hotspot_login"))
                
                # Log ke database
                db.save_hotspot_login(username, mac, ip)
                logging.info(f"✅ Hotspot Login: {username} ({ip})")
        
        # Detect logouts
        for key in last_hotspot_sessions:
            if key not in current_dict:
                session = last_hotspot_sessions[key]
                username = session.get('name', 'unknown')
                mac = session.get('mac-address', 'unknown')
                ip = session.get('address', 'unknown')
                
                msg = format_hotspot_logout_message(username, mac, ip)
                events.append((msg, "hotspot_logout"))
                
                # Log ke database
                db.save_hotspot_logout(username, mac)
                logging.info(f"✅ Hotspot Logout: {username}")
        
        # Update last state
        last_hotspot_sessions = current_dict
        
    except Exception as e:
        logging.error(f"❌ Error checking hotspot events: {e}")
    
    return events

def check_dhcp_events(api):
    """
    Check untuk DHCP lease events (new, renew, release, expired).
    Membandingkan current leases dengan last state.
    Return: List of tuples (message, event_type)
    """
    global last_dhcp_leases
    
    events = []
    
    try:
        # Ambil current DHCP leases
        current_leases = api.get_dhcp_leases()
        
        if current_leases is None:
            logging.warning("⚠️ Gagal mengambil DHCP leases")
            return events
        
        if not isinstance(current_leases, list):
            logging.warning("⚠️ DHCP leases bukan list")
            return events
        
        # Buat dict untuk tracking (key = mac-address)
        current_dict = {}
        for lease in current_leases:
            key = lease.get('mac-address', 'unknown')
            current_dict[key] = lease
        
        # Detect new leases dan renewals
        for key, lease in current_dict.items():
            mac = lease.get('mac-address', 'unknown')
            ip = lease.get('address', 'unknown')
            hostname = lease.get('host-name', '')
            active = lease.get('active', False)
            expires_after = lease.get('expires-after', 0)
            
            if key not in last_dhcp_leases:
                # New lease
                msg = format_dhcp_event_message(mac, ip, hostname, "new", expires_after)
                events.append((msg, "dhcp_new"))
                
                # Log ke database
                db.save_dhcp_event(mac, ip, hostname, "new", expires_after)
                logging.info(f"✅ DHCP New Lease: {mac} -> {ip}")
            else:
                # Check if renewed (IP same tapi lease time updated)
                old_lease = last_dhcp_leases[key]
                old_expires = old_lease.get('expires-after', 0)
                
                if expires_after > old_expires and active:
                    msg = format_dhcp_event_message(mac, ip, hostname, "renew", expires_after)
                    events.append((msg, "dhcp_renew"))
                    
                    db.save_dhcp_event(mac, ip, hostname, "renew", expires_after)
                    logging.info(f"✅ DHCP Renew: {mac}")
        
        # Detect releases (leases yang hilang)
        for key in last_dhcp_leases:
            if key not in current_dict:
                old_lease = last_dhcp_leases[key]
                mac = old_lease.get('mac-address', 'unknown')
                ip = old_lease.get('address', 'unknown')
                hostname = old_lease.get('host-name', '')
                
                msg = format_dhcp_event_message(mac, ip, hostname, "release")
                events.append((msg, "dhcp_release"))
                
                db.save_dhcp_event(mac, ip, hostname, "release", None)
                logging.info(f"✅ DHCP Release: {mac} ({ip})")
        
        # Update last state
        last_dhcp_leases = current_dict
        
    except Exception as e:
        logging.error(f"❌ Error checking DHCP events: {e}")
    
    return events

def format_interface_down_message(interface_name, speed, rx_error, tx_error):
    """Format pesan untuk interface DOWN"""
    msg = f"🔴 **LINK DOWN**\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🔌 Interface: `{interface_name}`\n"
    if speed:
        msg += f"⚡ Last Speed: `{speed}`\n"
    if rx_error > 0 or tx_error > 0:
        msg += f"❌ RX Errors: `{rx_error}` | TX Errors: `{tx_error}`\n"
    msg += f"⏰ Time: `{get_current_time()}`\n"
    return msg

def format_interface_up_message(interface_name, speed):
    """Format pesan untuk interface UP (recovery)"""
    msg = f"🟢 **LINK UP** ✅\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"
    msg += f"🔌 Interface: `{interface_name}`\n"
    if speed:
        msg += f"⚡ Speed: `{speed}`\n"
    msg += f"⏰ Time: `{get_current_time()}`\n"
    return msg

def check_interface_events(api):
    """
    Check untuk interface status changes (link up/down).
    Return: List of tuples (message, event_type)
    """
    global last_interface_states
    
    events = []
    
    try:
        # Ambil detail semua interface
        interfaces = api.get_interfaces_detail()
        
        if interfaces is None:
            logging.warning("⚠️ Gagal mengambil interface details")
            return events
        
        if not isinstance(interfaces, list):
            logging.warning("⚠️ Interface list bukan list")
            return events
        
        # Buat dict untuk tracking (key = interface name)
        current_dict = {}
        for iface in interfaces:
            iface_name = iface.get('name')
            running = iface.get('running', False)
            disabled = iface.get('disabled', False)
            speed = iface.get('link-speed', 'N/A')
            rx_error = iface.get('rx-error', 0)
            tx_error = iface.get('tx-error', 0)
            
            # Status: "up" jika running dan tidak disabled
            status = "up" if (running and not disabled) else "down"
            
            current_dict[iface_name] = {
                'status': status,
                'running': running,
                'disabled': disabled,
                'speed': speed,
                'rx_error': rx_error,
                'tx_error': tx_error
            }
        
        # Detect interface status changes
        for iface_name, current_state in current_dict.items():
            if iface_name not in last_interface_states:
                # Interface baru detected
                logging.info(f"ℹ️ New interface detected: {iface_name} ({current_state['status']})")
            else:
                # Check if status changed
                last_state = last_interface_states[iface_name]
                
                if last_state['status'] != current_state['status']:
                    if current_state['status'] == "down":
                        # Interface DOWN
                        msg = format_interface_down_message(
                            iface_name,
                            current_state['speed'],
                            current_state['rx_error'],
                            current_state['tx_error']
                        )
                        events.append((msg, "interface_down"))
                        
                        # Log ke database
                        db.save_interface_event(
                            iface_name, "down", "down",
                            current_state['speed'],
                            current_state['rx_error'],
                            current_state['tx_error'],
                            f"disabled={current_state['disabled']}"
                        )
                        logging.warning(f"⚠️ Interface DOWN: {iface_name}")
                    
                    else:  # Interface UP (recovery)
                        msg = format_interface_up_message(iface_name, current_state['speed'])
                        events.append((msg, "interface_up"))
                        
                        # Log ke database
                        db.save_interface_event(
                            iface_name, "up", "up",
                            current_state['speed'],
                            0, 0, "interface recovered"
                        )
                        logging.info(f"✅ Interface UP: {iface_name}")
        
        # Detect interfaces yang hilang dari last state
        for iface_name in last_interface_states:
            if iface_name not in current_dict:
                # Interface hilang (mungkin dihapus)
                logging.warning(f"⚠️ Interface disappeared: {iface_name}")
        
        # Update last state
        last_interface_states = current_dict
        
    except Exception as e:
        logging.error(f"❌ Error checking interface events: {e}")
    
    return events