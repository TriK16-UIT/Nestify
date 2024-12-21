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

    def get_scenarios(self, hub_id):
        scenarios_ref = self.get_reference('Scenarios')
        all_scenarios = scenarios_ref.get()

        if all_scenarios is None:
            return {}

        hub_scenarios = {sid: scenario for sid, scenario in all_scenarios.items() if scenario.get('HubID') == hub_id}
        return hub_scenarios
    # For testing purpose only
    def add_scenario(self, scenario_id, hub_id, name, time, actions):
        scenario_ref = self.get_reference(f'Scenarios/{scenario_id}')
        scenario_data = {
            'HubID': hub_id,
            'name': name,
            'time': time,
            'actions': actions
        }
        scenario_ref.set(scenario_data)
        print(f"Scenario {name} added to Firebase under {scenario_id}.")



    