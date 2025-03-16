import firebaseaio
import asyncio
from config import FIREBASE_DATABASE_URL, FIREBASE_CREDENTIALS_PATH

# Firebase configuration
config = {
    "apiKey": "AIzaSyBQMoP4uoWd7bwZBYcWy7NZ59lqN0gp1C4",
    "databaseURL": FIREBASE_DATABASE_URL,
    "serviceAccount": FIREBASE_CREDENTIALS_PATH
}

# Initialize Firebase
async def initialize_firebase():
    firebase = firebaseaio.initialize_app(config)
    return firebase

# Simulate updates to Firebase
async def add_data_to_database(firebase):
    # Get the database instance
    db = firebase.database()

    # Define the data to add
    data = {
        "users/Son/": {
            "name": "Mortimer 'Morty' Smith"
        },
        "User/Tri/": {
            "name": "Rick Sanchez"
        }
    }

    # Update the database with the data
    await db.update(data)
    print("Data added successfully")

# async def get_data(firebase):
#     db = firebase.database()
#     users = await db.child("User").get()
#     print(users.val())

async def main():
    # Initialize Firebase
    firebase = await initialize_firebase()

    # Add data to the database
    await add_data_to_database(firebase)
    # await get_data(firebase)

asyncio.run(main())
