import asyncio
from datetime import datetime
from logging_setup import logger

async def check_and_execute_scenarios(device_manager, firebase_handler, hub_id):
    scenarios = await firebase_handler.get_scenarios(hub_id)
    current_time = datetime.now().strftime("%H:%M")
    for scenario_id, scenario_info in scenarios.items():
        if scenario_info['status'] == "ON" and scenario_info['time'] == current_time:
            logger.info(f"It's {current_time}!")
            logger.info(f"Executing scenario: {scenario_info['name']}")
            for action in scenario_info['actions']:
                device_id = action.pop('device_id')
                await device_manager.control_device(action, device_id, True)

async def run_scheduler(device_manager, firebase_handler, hub_id):
    while True:
        await check_and_execute_scenarios(device_manager, firebase_handler, hub_id)
        await asyncio.sleep(60)  # Wait for 60 seconds before checking again