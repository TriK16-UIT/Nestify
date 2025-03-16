from config import HUB_ID, NOROOM_ID
import asyncio
from logging_setup import logger
import json

class DeviceManager:
    def __init__(self, mqtt_handler, firebase_handler):
        self.mqtt_handler = mqtt_handler
        self.firebase_handler = firebase_handler
        self.list_of_devices = []

    def setup_device_stream(self):
        self.firebase_handler.stream("Device", self.device_handler)

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

    def device_handler(self, message):
        print(message["event"]) # put
        print(message["path"]) # /-K7yGTTEp7O549EzTYtI
        print(message["data"]) # {'title': 'firebaseaio', "body": "etc..."}
        path_parts = message["path"].split('/')

        device_id = path_parts[1]
        data = message["data"]
        event = message["event"]
        topic = f"{HUB_ID}/{device_id}"

        device_entry = next((entry for entry in self.list_of_devices if entry[0] == device_id), None)

        if not device_entry:
            return

        if event == "patch":
            async def patch_status():
                payload = json.dumps(data)
                await self.mqtt_handler.publish(topic, payload)

            asyncio.run(patch_status())
            logger.info(f"Published current {data} for {device_id} to MQTT topic {topic}")
            
        if data is None:
            self.list_of_devices.remove(device_entry)
            async def disconnect_device():
                payload = json.dumps({"status": "disconnect"})
                await self.mqtt_handler.publish(topic, payload)
                await self.mqtt_handler.unsubscribe(topic)

            asyncio.run(disconnect_device())

        elif len(path_parts) > 2:
            attribute = path_parts[2]

            if attribute in ["status", "dim", "colour", "speed"]:
                async def update_status():
                    payload = json.dumps({attribute: data})
                    await self.mqtt_handler.publish(topic, payload)

                asyncio.run(update_status())
                logger.info(f"Published current {attribute}: {data} for {device_id} to MQTT topic {topic}")
            elif attribute == "device_name" and isinstance(data, str):
                self.list_of_devices.remove(device_entry)
                self.list_of_devices.append((device_id, data))
                logger.info(f"Change current name {device_entry[1]} of {device_entry[0]} to {data}")

    async def control_device(self, action, device_name, is_id=False):
        try:
            if is_id:
                # Find device by ID
                chosen_id, chosen_name = next((id, name) for id, name in self.get_list_of_devices() if id == device_name)
                logger.info(f"Controlling device {chosen_name} with data {action} from given ID")
            else:
                # Find device by name
                chosen_id, chosen_name = next((id, name) for id, name in self.get_list_of_devices() if name.lower() == device_name.lower())
                logger.info(f"Controlling device {chosen_name} with data {action} from given name")

            # Update multiple fields in Firebase
            await self.firebase_handler.update_data(f'Device/{chosen_id}', action)

            logger.info(f"Device {chosen_name} updated successfully with data: {action}")
        except StopIteration:
            logger.error(f"Device {device_name} not found.")