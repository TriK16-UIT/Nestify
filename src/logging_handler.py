import datetime
from config import HUB_ID

class LoggingHandler:
    def __init__(self, firestore_handler):
        self.firestore_handler = firestore_handler

    async def add_log(self, level, message):
        now = datetime.datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')

        # First check if the document exists
        doc_path = f"logs/{HUB_ID}"
        doc_result = await self.firestore_handler.get_data(doc_path)
        
        if doc_result.exists:
            # Document exists, update it
            doc_update = {
                "has_logs": True,
                "last_updated": datetime.datetime.now().isoformat()
            }
            await self.firestore_handler.update_data(doc_path, doc_update)
        else:
            # Document doesn't exist, create it
            doc_data = {
                "hub_id": HUB_ID,
                "has_logs": True,
                "created_at": datetime.datetime.now().isoformat(),
                "last_updated": datetime.datetime.now().isoformat()
            }
            await self.firestore_handler.set_data(doc_path, doc_data)
        
        # Then add the log entry
        log_entry = {
            "level": level,
            "message": message,
            "timestamp": timestamp,
            "created_at": datetime.datetime.now().isoformat()
        }

        log_path = f"logs/{HUB_ID}/entries/{timestamp}"
        await self.firestore_handler.set_data(log_path, log_entry)
        