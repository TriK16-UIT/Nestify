import firebase_admin
from firebase_admin import credentials, db

from config import FIREBASE_CREDENTIALS_PATH, FIREBASE_DATABASE_URL

class FirebaseHandler:
    def __init__(self):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DATABASE_URL
        })

    def get_reference(self, path):
        return db.reference(path)

    