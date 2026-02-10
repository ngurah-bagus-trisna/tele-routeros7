last_leases = []

def check_dhcp_events(api):
    global last_leases
    current_leases = api.get_resource("ip/dhcp-server/lease")
    
    # Logic komparasi untuk mencari user baru
    if len(current_leases) > len(last_leases):
        # Kirim notif ke telegram
        pass
    last_leases = current_leases