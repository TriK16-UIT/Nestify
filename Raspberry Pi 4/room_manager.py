from config import HUB_ID
from logging_setup import logger

class RoomManager:
    def __init__(self, firebase_handler):
        self.firebase_handler = firebase_handler
        self.list_of_rooms = []

    def get_list_of_rooms(self):
        return self.list_of_rooms

    def get_devices_in_room(self, room_name):
        room_id = next(room_id for room_id, name in self.list_of_rooms if name == room_name)
        
        # Retrieve devices from Firebase that belong to this room
        device_ref = self.firebase_handler.get_reference('Device')
        devices = device_ref.get()

        if not devices:
            return []

        devices_in_room = [
            device_info['device_name']
            for device_id, device_info in devices.items()
            if device_info.get('room_id') == room_id
        ]

        return devices_in_room

    def load_rooms_from_firebase(self):
        room_ref = self.firebase_handler.get_reference('Room')
        rooms = room_ref.get()

        if rooms:
            for room_id, room_info in rooms.items():
                if room_info.get('HubID') == HUB_ID:
                    room_name = room_info.get('name')
                    if room_name:
                        self.list_of_rooms.append((room_id, room_name))
                        print((room_id, room_name))

    def handle_room_change(self, event):
        path_parts = event.path.split('/')

        room_id = path_parts[1]
        data = event.data

        print(data)
        print(path_parts)

        room_entry = next((entry for entry in self.list_of_rooms if entry[0] == room_id), None)

        if len(path_parts) == 2 and all(part == '' for part in path_parts):
            for room_id, room_info in data.items():
                if room_id not in [room[0] for room in self.list_of_rooms]:
                    if room_info.get('HubID') == HUB_ID: 
                        room_name = room_info.get('name')  
                        if room_name: 
                            self.list_of_rooms.append((room_id, room_name)) 
                            print("hehe")

        if data is None:
            # Room deleted
            if room_entry:
                logger.info(f"Room {room_id} deleted")
                self.list_of_rooms.remove(room_entry)

        elif len(path_parts) > 2:
            attribute = path_parts[2]

            if attribute == "name" and isinstance(data, str):
                # Room name changed
                if room_entry:
                    self.list_of_rooms.remove(room_entry)
                    self.list_of_rooms.append((room_id, data))
                    logger.info(f"Changed room name for {room_id} to {data}")
