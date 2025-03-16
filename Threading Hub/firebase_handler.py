import firebaseaio
import asyncio
import datetime
from config import FIREBASE_API_KEY, FIREBASE_CREDENTIALS_PATH, FIREBASE_DATABASE_URL

class FirebaseHandler:
    def __init__(self):
        self.config = {
            "apiKey": FIREBASE_API_KEY,
            "databaseURL": FIREBASE_DATABASE_URL,
            "serviceAccount": FIREBASE_CREDENTIALS_PATH
        }
        self.firebase = firebaseaio.initialize_app(self.config)

    def get_reference(self, path):
        return self.firebase.database().child(path)

    async def set_data(self, path, data):
        ref = self.get_reference(path)
        return await ref.set(data)

    async def get_data(self, path):
        ref = self.get_reference(path)
        return await ref.get()

    async def update_data(self, path, data):
        ref = self.get_reference(path)
        return await ref.update(data)

    async def get_scenarios(self, hub_id):
        all_scenarios = await self.get_data("Scenarios")
        if all_scenarios is None:
            return {}

        hub_scenarios = {}
        for scenario in all_scenarios.each():
            scenario_key = scenario.key()  # Get the key of the scenario
            scenario_value = scenario.val()  # Get the value of the scenario
            
            if scenario_value.get('HubID') == hub_id:
                hub_scenarios[scenario_key] = scenario_value

        return hub_scenarios

    def stream(self, path, stream_handler):
        ref = self.get_reference(path)
        ref.stream(stream_handler)




