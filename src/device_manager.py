from config import HUB_ID, NOROOM_ID
import asyncio
import json
import datetime
import threading

class DeviceManager:
    def __init__(self, mqtt_handler, storage_handler, firebase_handler, logging_handler):
        self.mqtt_handler = mqtt_handler
        self.storage_handler = storage_handler
        self.firebase_handler = firebase_handler
        self.logging_handler = logging_handler
        self.list_of_devices = []
        self.loop = asyncio.get_running_loop()

    def device_listener_callback(self, message):
        asyncio.run_coroutine_threadsafe(self.device_listener(message), self.loop)

    def setup_device_stream(self):
        self.firebase_handler.stream("Device", self.device_listener_callback)

    async def load_message_handlers_from_firebase(self):
        devices = await self.firebase_handler.get_data("Device")
        
        if devices.each():
            for device in devices.each():
                device_id = device.key()
                device_info = device.val()
                if device_info.get('HubID') == HUB_ID:
                    topic = device_info.get('topic')
                    device_name = device_info.get('device_name')
                    if topic and device_name:
                        await self.mqtt_handler.subscribe(topic)
                        self.list_of_devices.append((device_id, device_name))
                        print((device_id, device_name))

        self.mqtt_handler.add_message_handler('sensor', self.handle_sensor_device_message)
        self.mqtt_handler.add_message_handler('toggle', self.handle_toggle_device_message)
        self.mqtt_handler.add_message_handler('motion', self.handle_motion_device_message)


    def get_list_of_devices(self):
        return self.list_of_devices

    async def add_device_handler(self, device_id, device_type):
        base_name = ''
        for char in device_id:
            if char.isalpha():
                base_name += char
            else:
                break
        base_name = base_name.upper()
        print(self.list_of_devices)
        device_count = sum(1 for device in self.list_of_devices if device[1].startswith(base_name))
        unique_device_name = f"{base_name} {device_count + 1}"

        topic = f"{HUB_ID}/{device_id}"

        new_device_data = {
            'HubID': HUB_ID,
            'topic': topic,
            'device_name': unique_device_name,
            'type': device_type,
            'room_id': NOROOM_ID
        }

        if device_type == 'toggle':
            new_device_data['status'] = "OFF"

        if "light" in device_id.lower():
            new_device_data['dim'] = 10
            new_device_data['colour'] = "#FFFFFF"

        if "fan" in device_id.lower():
            new_device_data['speed'] = 10

        await self.firebase_handler.set_data(f"Device/{device_id}", new_device_data)

        await self.mqtt_handler.subscribe(topic)

        if "light" in device_id.lower():
            payload = json.dumps({
                "status": new_device_data['status'],
                "dim": new_device_data['dim'],
                "colour": new_device_data['colour']
            })
            await self.mqtt_handler.publish(topic, payload)

        if "fan" in device_id.lower():
            payload = json.dumps({
                "status": new_device_data['status'],
                "speed": new_device_data['speed'],
            })
            await self.mqtt_handler.publish(topic, payload)

        self.list_of_devices.append((device_id, unique_device_name))

    async def handle_toggle_device_message(self, topic, payload):
        device_id = topic.split('/')[-1]

        await self.firebase_handler.update_data(f'Device/{device_id}', payload)

        # status = payload.get('status')

        # if status:
        #     await self.firebase_handler.set_data(f'Device/{device_id}/status', status)

    async def handle_sensor_device_message(self, topic, payload):
        device_id = topic.split('/')[-1]

        await self.firebase_handler.update_data(f'Device/{device_id}', payload)

    async def handle_motion_device_message(self, topic, payload):
        device_id = topic.split('/')[-1]

        image_data = payload.pop('image', None)

        await self.firebase_handler.update_data(f'Device/{device_id}', payload)

        if image_data:
            image_path = f"images/{device_id}/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
            await self.storage_handler.upload_image(image_path, image_data)

    async def device_listener(self, message):
        event = message["event"]
        path = message["path"]
        data = message["data"]
        path_parts = path.strip('/').split('/')
        
        if not path_parts:
            return

        device_id = path_parts[0]
        topic = f"{HUB_ID}/{device_id}"

        device_entry = next((e for e in self.list_of_devices if e[0] == device_id), None)
        if not device_entry:
            return

        if event == "patch":
            await self.logging_handler.add_log("info", f"Update with {data} to Device {device_id}")
            payload = json.dumps(data)
            await self.mqtt_handler.publish(topic, payload)

        elif data is None:  # Deletion
            # Send disconnect before cleanup
            await self.logging_handler.add_log("info", f"Disconnect to Device {device_id}")
            await self.mqtt_handler.publish(topic, json.dumps({"status": "disconnect"}))
            self.list_of_devices.remove(device_entry)
            await self.mqtt_handler.unsubscribe(topic)

        elif len(path_parts) > 1:
            attribute = path_parts[1]
            await self.logging_handler.add_log("info", f"Update attribute {attribute} with {data} to Device {device_id}")
            
            if attribute in ["status", "dim", "colour", "speed"]:
                payload = json.dumps({attribute: data})
                await self.mqtt_handler.publish(topic, payload)
            elif attribute == "device_name" and isinstance(data, str):
                self.list_of_devices.remove(device_entry)
                self.list_of_devices.append((device_id, data))

    async def control_device(self, action, device_name, is_id=False):
        try:
            if is_id:
                # Find device by ID
                chosen_id, chosen_name = next((id, name) for id, name in self.get_list_of_devices() if id == device_name)
            else:
                # Find device by name
                chosen_id, chosen_name = next((id, name) for id, name in self.get_list_of_devices() if name.lower() == device_name.lower())

            # Update multiple fields in Firebase
            await self.firebase_handler.update_data(f'Device/{chosen_id}', action)

        except StopIteration:
            pass