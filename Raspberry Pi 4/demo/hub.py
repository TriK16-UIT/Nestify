import firebase_admin
from firebase_admin import credentials, db
import time
import bluetooth
import socket
import paho.mqtt.client as mqtt
import json

HubID='Hub1'
message_handlers = {}
list_of_devices = []

cred = credentials.Certificate("credentials/tri-credentialkey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://home-automation-f869d-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

def on_connect(client, userdata, flags, rc):
    global flag_connected
    flag_connected = 1
    print("Connected to MQTT server")

def on_disconnect(client, userdata, rc):
    global flag_connected
    flag_connected = 0
    print("Disconnected from MQTT server")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    if 'type' in payload:
        payload = json.loads(payload)
        print(f"Message received on topic {topic}: {payload}")
        if payload['type'] in message_handlers:
            message_handlers[payload['type']](topic, payload)

def load_message_handlers_from_firebase():   
    device_ref = db.reference('Device')
    devices = device_ref.get()

    if devices:
        for device_id, device_info in devices.items():
            if device_info.get('HubID') == HubID:
                topic = device_info.get('topic')
                device_type = device_info.get('type')
                if topic and device_type:
                    mqtt_client.subscribe(topic)
                    list_of_devices.append(device_id)
                    print(f"Subscribed to topic: {topic}")

    message_handlers['sensor'] = handle_sensor_device_message
    message_handlers['toggle'] = handle_toggle_device_message

def add_device_handler(device_name, device_type):
    device_ref = db.reference('Device')
    topic = f"{HubID}/{device_name}"
    if device_type == 'toggle':
        new_device_ref = device_ref.child(f'{device_name}')
        new_device_ref.set({
            'HubID': HubID,
            'topic': topic,
            'type': device_type,
            'status': ""
        })
    elif device_type == 'sensor':
        new_device_ref = device_ref.child(f'{device_name}')
        new_device_ref.set({
            'HubID': HubID,
            'topic': topic,
            'type': device_type
        })

    mqtt_client.subscribe(topic)
    print(f"Subscribed to topic: {topic} with handler: {message_handlers[device_type]}")


def create_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, f'{HubID}')
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect('127.0.0.1', 1883)
    client.loop_start()
    return client

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

def connect_device(ssid, password, addr, name):
    host = get_local_ip()
    port = 1
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

    try:
        s.connect((addr, port))
        print(f"Connecting to {name}.")
    except socket.error:
        print(f"Failed to connect to {name} at {addr}. Error: {socket.error}")
    finally:
        print(f"Succesfully connected! Sending Wifi information...")
        s.send(bytes(ssid, 'UTF-8'))
        s.send(bytes("|", 'utf-8'))
        s.send(bytes(password, 'utf-8'))
        s.send(bytes("|", 'utf-8'))
        s.send(bytes(get_local_ip(), 'utf-8'))
        s.send(bytes("|", 'utf-8'))
        s.send(bytes(HubID, 'utf-8'))
        s.close()

def scan_for_devices():
    print("Wait for scanning Bluetooth Devices")

    nearby_devices = bluetooth.discover_devices(lookup_names=True)
    scanned_devices = []
    
    print("Found {} devices.".format(len(nearby_devices)))

    if nearby_devices == 0:
        return ""

    for addr, name in nearby_devices:
        device_info = {
            'addr': addr,
            'name': name
        }
        scanned_devices.append(device_info)

    return scanned_devices

def handle_toggle_device_message(topic, payload):
    device_id = topic.split('/')[-1]

    status_ref = db.reference(f'Device/{device_id}/status')

    status = payload.get('status')

    if status:
        status_ref.set(status)
        print(f"Updated {device_id} status to {status} in Firebase")

def handle_sensor_device_message(topic, payload):
    device_id = topic.split('/')[-1]

    device_ref = db.reference(f'Device/{device_id}')
    device_ref.update(payload)

    print(f"Updated sensor data for {device_id} in Firebase with payload: {payload}")


def handle_device_change(event):
    print(event.path)
    print(event.data)

    path_parts = event.path.split('/')
    
    device_id = path_parts[1]
    data = event.data
    topic = f"{HubID}/{device_id}"

    if device_id not in list_of_devices:
        return

    if data is None:
        print(f"Device {device_id} deleted")
        list_of_devices.remove(device_id)

        # send msg to device
        pubMsg = mqtt_client.publish(topic, payload="disconnect".encode('utf-8'), qos=2)
        pubMsg.wait_for_publish()

        mqtt_client.unsubscribe(topic)
        print(f"Unsubscribed to {topic}")
    elif len(path_parts) > 2 and path_parts[2] == "status":
        pubMsg = mqtt_client.publish(topic, payload=data.encode('utf-8'), qos=2)
        pubMsg.wait_for_publish()
        print(f"Published current status {data} for {device_id} to MQTT topic {topic}")

def listen_for_commands():
    global mqtt_client
    mqtt_client = create_mqtt_client()
    command_ref = db.reference(f'Hub/{HubID}/command')

    load_message_handlers_from_firebase()

    device_ref = db.reference('Device')
    device_ref.listen(handle_device_change)

    while True:
        command = command_ref.get()
        if command == "scanning":
            scanned_devices_ref = db.reference(f'Hub/{HubID}/scanned_devices')
            scanned_devices_ref.set(scan_for_devices())
            command_ref.set("idle")
        elif command == "connecting":
            ssid = db.reference(f'Hub/{HubID}/ssid').get()
            password = db.reference(f'Hub/{HubID}/password').get()
            chosen_device_ref = db.reference(f'Hub/{HubID}/chosen_device')
            chosen_device_info = chosen_device_ref.get()
            connect_device(ssid, password, chosen_device_info['addr'], chosen_device_info['name'])
            device_type = None
            if "LED" in chosen_device_info['name'] or "FAN" in chosen_device_info['name']:
                device_type = 'toggle'
            elif "SENSOR" in chosen_device_info['name']:
                device_type = 'sensor'
            add_device_handler(chosen_device_info['name'], device_type)
            list_of_devices.append(chosen_device_info['name'])
            print(list_of_devices)
            command_ref.set("idle")

if __name__ == "__main__":
    listen_for_commands()
