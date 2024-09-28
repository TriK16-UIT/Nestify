import bluetooth
import socket


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '192.168.1.7'
    finally:
        s.close()
    return IP

def scan_connect_bluetooth():
    nearby_devices = bluetooth.discover_devices(lookup_names=True)
    print("Found {} devices.".format(len(nearby_devices)))

    for addr, name in nearby_devices:
        print("  {} - {}".format(addr, name))

    selected_devices = []

    while (1):
        inp = input('Choose the device you want to connect (type "done" to finish): ')
        if inp.lower() == "done":
            break
        try:
            device_index = int(inp)
            if device_index < len(nearby_devices):
                selected_devices.append(nearby_devices[device_index])
            else:
                print("Invalid device index. Please try again.")
        except ValueError:
            print("Please enter a numeric index.")

    ssid = input('SSID: ')
    password = input('PSK: ')
    host = get_local_ip()
    print(host)
    port = 1
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
   
    for addr, name in selected_devices:
        print(f"Connecting to {name} at {addr}...")
        port = 1
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        try:
            s.connect((addr, port))
            print(f"Connected to {name}.")
        except socket.error:
            print(f"Failed to connect to {name} at {addr}. Error: {socket.error}")
        finally:
            s.send(bytes(ssid, 'UTF-8'))
            s.send(bytes("|", 'utf-8'))
            s.send(bytes(password, 'utf-8'))
            s.send(bytes("|", 'utf-8'))
            s.send(bytes(get_local_ip(), 'utf-8'))
            s.close()
    return True


