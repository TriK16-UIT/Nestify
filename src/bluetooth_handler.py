import asyncio
import bluetooth
import socket
from config import HUB_ID

class BluetoothHandler:
    def __init__(self):
        pass

    @staticmethod
    def get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def connect_device(self, ssid, password, addr, name):
        host = self.get_local_ip()
        port = 1
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

        try:
            s.connect((addr, port))
        except socket.error:
            return False, "Failed to connect to device"
        
        try:
            s.send(bytes(ssid, 'UTF-8'))
            s.send(bytes("|", 'utf-8'))
            s.send(bytes(password, 'utf-8'))
            s.send(bytes("|", 'utf-8'))
            s.send(bytes(self.get_local_ip(), 'utf-8'))
            s.send(bytes("|", 'utf-8'))
            s.send(bytes(HUB_ID, 'utf-8'))
            
            # Wait for confirmation or error message from device
            response = s.recv(1024).decode('utf-8')
            if "Error" in response:
                return False, response[:-1]
            else:
                return True, response[:-1]
        except Exception as e:
            return False, str(e)
        finally:
            s.close()

    async def connect_device_async(self, ssid, password, addr, name):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.connect_device, ssid, password, addr, name)

    def scan_for_devices(self):
        nearby_devices = bluetooth.discover_devices(lookup_names=True)
        scanned_devices = []

        if nearby_devices == 0:
            return ""

        for addr, name in nearby_devices:
            device_info = {
                'addr': addr,
                'name': name
            }
            scanned_devices.append(device_info)

        return scanned_devices

    async def scan_for_devices_async(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.scan_for_devices)