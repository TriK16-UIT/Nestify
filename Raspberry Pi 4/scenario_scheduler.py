import schedule
from datetime import datetime
from logging_setup import logger

def check_and_execute_scenarios(device_manager, firebase_handler, hub_id):
    scenarios = firebase_handler.get_scenarios(hub_id)
    current_time = datetime.now().strftime("%H:%M")
    for scenario_id, scenario in scenarios.items():
        if scenario['time'] == current_time:
            logger.info(f"It's {current_time}!")
            logger.info(f"Executing scenario: {scenario['name']}")
            for action in scenario['actions']:
                device_id = action['device_id']
                action_type = action['action']
                device_manager.control_device(action_type, device_id)

def schedule_scenario_checks(device_manager, firebase_handler, hub_id):
    schedule.every().minute.do(check_and_execute_scenarios, device_manager, firebase_handler, hub_id)