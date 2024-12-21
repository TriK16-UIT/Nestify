# Example of adding a scenario
from firebase_handler import FirebaseHandler
firebase_handler = FirebaseHandler()

# Define a new scenario
scenario_id = "Scenario3"
hub_id = "Hub1"
name = "Afternoon Routine"
time = "15:00"
actions = [
    {"device_name": "Light 1", "action": "off"}
]

# Add the scenario to Firebase
firebase_handler.add_scenario(scenario_id, hub_id, name, time, actions)
