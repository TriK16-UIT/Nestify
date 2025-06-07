import firebase_admin
from firebase_admin import credentials, firestore_async
from config import FIREBASE_CREDENTIALS_PATH

class FirestoreHandler:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            app = firebase_admin.initialize_app(cred)
        self.db = firestore_async.client()

    async def set_data(self, path, data):
        doc_ref = self.db.document(path)
        await doc_ref.set(data)

    async def get_data(self, path):
        doc_ref = self.db.document(path)
        return await doc_ref.get()

    async def update_data(self, path, data):
        doc_ref = self.db.document(path)
        await doc_ref.update(data)
    