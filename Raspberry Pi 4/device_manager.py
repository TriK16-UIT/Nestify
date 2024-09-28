from config import HUB_ID
from logging_setup import logger

class DeviceManager:
    def __init__(self, mqtt_handler, firebase_handler):
        self.mqtt_handler = mqtt_handler
        self.firebase_handler = firebase_handler
        self.list_of_devices = []

    def load_message_handlers_from_firebase(self):
        device_ref = self.firebase_handler.get_reference('Device')
        devices = device_ref.get()
        
        if devices:
            for device_id, device_info in devices.items():
                if device_info.get('HubID') == HUB_ID:
                    topic = device_info.get('topic')
                    device_name = device_info.get('device_name')
                    if topic and device_name:
                        self.mqtt_handler.subscribe(topic)
                        self.list_of_devices.append((device_id, device_name))
                        print((device_id, device_name))

        self.mqtt_handler.add_message_handler('sensor', self.handle_sensor_device_message)
        self.mqtt_handler.add_message_handler('toggle', self.handle_toggle_device_message)

    def get_list_of_devices(self):
        return self.list_of_devices

    # def add_device_handler(self, device_name, device_type):
    #     device_ref = self.firebase_handler.get_reference('Device')
    #     topic = f"{HUB_ID}/{device_name}"
    #     if device_type == 'toggle':
    #         new_device_ref = device_ref.child(f'{device_name}')
    #         new_device_ref.set({
    #             'HubID': HUB_ID,
    #             'topic': topic,
    #             'type': device_type,
    #             'status': ""
    #         })
    #     elif device_type == 'sensor':
    #         new_device_ref = device_ref.child(f'{device_name}')
    #         new_device_ref.set({
    #             'HubID': HUB_ID,
    #             'topic': topic,
    #             'type': device_type
    #         })

    #     self.mqtt_handler.subscribe(topic)
    #     self.list_of_devices.append(device_name)
    #     # logger.info(f"Subscribed to topic: {topic}")

    def add_device_handler(self, device_id, device_type):
        base_name = ''
        for char in device_id:
            if char.isalpha():
                base_name += char
            else:
                break
        base_name = base_name.upper()

        device_count = sum(1 for device in self.list_of_devices if device.startswith(base_name))
        unique_device_name = f"{base_name} {device_count + 1}"

        device_ref = self.firebase_handler.get_reference('Device')
        topic = f"{HUB_ID}/{device_id}"

        new_device_data = {
            'HubID': HUB_ID,
            'topic': topic,
            'device_name': unique_device_name,
            'type': device_type
        }

        if device_type == 'toggle':
            new_device_data['status'] = ""

        new_device_ref = device_ref.child(device_id)
        new_device_ref.set(new_device_data)

        self.mqtt_handler.subscribe(topic)
        self.list_of_devices.append((device_id, unique_device_name))

    def handle_toggle_device_message(self, topic, payload):
        device_id = topic.split('/')[-1]

        status_ref = self.firebase_handler.get_reference(f'Device/{device_id}/status')

        status = payload.get('status')

        if status:
            status_ref.set(status)

    def handle_sensor_device_message(self, topic, payload):
        device_id = topic.split('/')[-1]

        device_ref = self.firebase_handler.get_reference(f'Device/{device_id}')
        device_ref.update(payload)

    def handle_device_change(self, event):
        path_parts = event.path.split('/')

        device_id = path_parts[1]
        data = event.data
        topic = f"{HUB_ID}/{device_id}"

        device_entry = next((entry for entry in self.list_of_devices if entry[0] == device_id), None)

        if not device_entry:
            return

        if data is None:
            logger.info(f"Device {device_id} deleted")
            self.list_of_devices.remove(device_entry)
            self.mqtt_handler.publish(topic, "disconnect")
            self.mqtt_handler.client.unsubscribe(topic)
            logger.info(f"Unsubscribed to {topic}")

        elif len(path_parts) > 2:
            attribute = path_parts[2]

            if attribute == "status":
                self.mqtt_handler.publish(topic, data)
                # logger.info(f"Published current status {data} for {device_id} to MQTT topic {topic}")
            elif attribute == "device_name" and isinstance(data, str):
                self.list_of_devices.remove(device_entry)
                self.list_of_devices.append((device_id, data))
                logger.info(f"Change current name {device_entry[1]} of {device_entry[0]} to {data}")
