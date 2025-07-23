from config import HUB_ID
import asyncio
import threading

class RoomManager:
    def __init__(self, firebase_handler):
        self.firebase_handler = firebase_handler
        self.list_of_rooms = []
        self.loop = asyncio.get_running_loop()

    def room_listener_callback(self, message):
        asyncio.run_coroutine_threadsafe(self.room_listener(message), self.loop)

    def setup_room_stream(self):
        self.firebase_handler.stream("Room", self.room_listener_callback)

    async def get_devices_in_room(self, room_name):
        room_id = next(room_id for room_id, name in self.list_of_rooms if name.lower() == room_name.lower())
        
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

    async def room_listener(self, message):
        event = message["event"]
        path = message["path"]
        data = message["data"]
        print(event)
        print(path)
        print(data)
        path_parts = path.strip('/').split('/')
        
        if not path_parts:
            return

        room_id = path_parts[0]
        room_entry = next((entry for entry in self.list_of_rooms if entry[0] == room_id), None)

        if event == "put":
            if data is None:  # Room deleted
                if room_entry:
                    self.list_of_rooms.remove(room_entry)
            elif len(path_parts) == 1:  # Room added or full update
                if data.get('HubID') == HUB_ID:
                    room_name = data.get('name')
                    if room_name:
                        # Remove old entry if exists
                        if room_entry:
                            self.list_of_rooms.remove(room_entry)
                        self.list_of_rooms.append((room_id, room_name))

        elif event == "patch":
            if len(path_parts) == 1:
                # Handle room creation or update
                if isinstance(data, dict) and 'name' in data:
                    room_name = data.get('name')
                    
                    # For new rooms, verify HubID matches
                    if not room_entry and data.get('HubID') != HUB_ID:
                        return
                        
                    # Remove old entry if it exists
                    if room_entry:
                        self.list_of_rooms.remove(room_entry)
                        
                    # Add the room to our list
                    self.list_of_rooms.append((room_id, room_name))
        print("List of rooms: ", self.list_of_rooms)