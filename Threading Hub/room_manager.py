from config import HUB_ID
from logging_setup import logger

class RoomManager:
    def __init__(self, firebase_handler):
        self.firebase_handler = firebase_handler
        self.list_of_rooms = []

    def setup_room_stream(self):
        self.firebase_handler.stream("Room", self.room_handler)

    async def get_devices_in_room(self, room_name):
        room_id = next(room_id for room_id, name in self.list_of_rooms if name == room_name)
        
        # Retrieve devices from Firebase that belong to this room
        devices = await self.firebase_handler.get_data("Device")

        devices_in_room = []

        if devices.each():
            for device in devices.each():
                device_id = device.key()
                device_info = device.val()
                if device_info.get('room_id') == room_id:
                    devices_in_room.append((device_info['device_name'], device_info['type']))

        # devices_in_room = [
        #     device_info['device_name']
        #     for device_id, device_info in devices.items()
        #     if device_info.get('room_id') == room_id
        # ]

        return devices_in_room

    async def load_rooms_from_firebase(self):
        rooms = await self.firebase_handler.get_data("Room")

        if rooms.each():
            for room in rooms.each():
                room_id = room.key()
                room_info = room.val()
                if room_info.get('HubID') == HUB_ID:
                    room_name = room_info.get('name')
                    if room_name:
                        self.list_of_rooms.append((room_id, room_name))
                        print((room_id, room_name))

    def get_list_of_rooms(self):
        return self.list_of_rooms

    def room_handler(self, message):
        path_parts = message["path"].split('/')

        room_id = path_parts[1]
        data = message["data"]

        room_entry = next((entry for entry in self.list_of_rooms if entry[0] == room_id), None)

        if not room_entry:
            return

        # Room added
        if len(path_parts) == 2 and all(part == '' for part in path_parts):
            for room_id, room_info in data.items():
                if room_id not in [room[0] for room in self.list_of_rooms]:
                    if room_info.get('HubID') == HUB_ID: 
                        room_name = room_info.get('name')  
                        if room_name: 
                            logger.info(f"Room {room_id} added")
                            self.list_of_rooms.append((room_id, room_name)) 

        if data is None:
            # Room deleted
            logger.info(f"Room {room_id} deleted")
            self.list_of_rooms.remove(room_entry)

        elif len(path_parts) > 2:
            attribute = path_parts[2]

            if attribute == "name" and isinstance(data, str):
                # Room name changed
                if room_entry:
                    self.list_of_rooms.remove(room_entry)
                    self.list_of_rooms.append((room_id, data))
                    logger.info(f"Changed room name of {room_id} to {data}")
