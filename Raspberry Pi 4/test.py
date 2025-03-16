# # Example of adding a scenario
# from firebase_handler import FirebaseHandler
# firebase_handler = FirebaseHandler()

# # Define a new scenario
# scenario_id = "Scenario3"
# hub_id = "Hub1"
# name = "Afternoon Routine"
# time = "15:00"
# actions = [
#     {"device_name": "Light 1", "action": "off"}
# ]

# # Add the scenario to Firebase
# firebase_handler.add_scenario(scenario_id, hub_id, name, time, actions)

import firebaseaio
import asyncio
import datetime
from firebase_admin import credentials
from config import FIREBASE_DATABASE_URL, FIREBASE_CREDENTIALS_PATH

config = {
    "apiKey": "AIzaSyBQMoP4uoWd7bwZBYcWy7NZ59lqN0gp1C4",
    "databaseURL": FIREBASE_DATABASE_URL,
    "serviceAccount": FIREBASE_CREDENTIALS_PATH
}

async def initialize_firebase():
    firebase = firebaseaio.initialize_app(config)
    return firebase

# async def add_data_to_database(firebase):
#     # Get the database instance
#     db = firebase.database()

#     # Define the data to add
#     data = {
#         "users/Morty/": {
#             "name": "Mortimer 'Morty' Smith"
#         },
#         "users/Rick/": {
#             "name": "Rick Sanchez"
#         }
#     }

#     # Update the database with the data
#     await db.update(data)
#     print("Data added successfully")

# # async def get_data(firebase):
# #     db = firebase.database()
# #     users = await db.child("User").get()
# #     print(users.val())

# async def main():
#     # Initialize Firebase
#     firebase = await initialize_firebase()

#     # Add data to the database
#     await add_data_to_database(firebase)
#     # await get_data(firebase)

# Run the main function
def stream_handler(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    print(timestamp)
    print("Event:", message["event"])  # e.g., "put" or "patch"
    print("Path:", message["path"])    # e.g., "/users/Morty"
    print("Data:", message["data"])    # The data at the specified path

async def main():
    # Initialize Firebase
    firebase = await initialize_firebase()

    # Get the database instance
    db = firebase.database()
    print("Listening to changes at 'users/'...")

    # Start listening to changes at "users/"
    my_stream = db.child("users").stream(stream_handler)
    my_stream1 = db.child("User").stream(stream_handler)

    try:
        while True:
            await asyncio.sleep(1)  # Keep the loop alive while checking for updates
    except KeyboardInterrupt:
        print("\nStream stopped by user.")
        my_stream.close() 
        my_stream1.close() # Ensure the stream is closed properly when stopping

# Run the async main function
asyncio.run(main())