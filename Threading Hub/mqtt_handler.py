from aiomqtt import Client, MqttError
from logging_setup import logger
from config import MQTT_BROKER, MQTT_PORT, HUB_ID
import json
import asyncio

class MQTTHandler:
    def __init__(self):
        self.client = None
        self.message_handlers = {}
        self.loop = asyncio.get_event_loop()
        self.start_task = self.loop.create_task(self.start())

    async def connect(self):
        try:
            self.client = Client(MQTT_BROKER, MQTT_PORT, identifier=HUB_ID)
            await self.client.__aenter__()
            logger.info("Connected to MQTT server")
        except MqttError as e:
            raise

    async def disconnect(self):
        if self.client:
            await self.client.__aexit__()
            logger.info("Disconnected from MQTT server")
    
    async def subscribe(self, topic):
        if self.client:
            await self.client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")

    async def unsubscribe(self, topic):
        if self.client:
            await self.client.unsubscribe(topic)
            logger.info(f"Unsubscribed to topic: {topic}")

    async def publish(self, topic, payload, qos=2):
        if self.client:
            await self.client.publish(topic, payload=payload.encode('utf-8'), qos=qos)
            logger.info(f"Published to {topic}: {payload}")

    async def listen_for_messages(self):
        if self.client:
            async for message in self.client.messages:
                topic = message.topic.value
                payload = message.payload.decode('utf-8')
                if 'type' in payload:
                    payload = json.loads(payload)
                    if payload['type'] in self.message_handlers:
                        await self.message_handlers[payload['type']](topic, payload)

    def add_message_handler(self, message_type, handler):
        self.message_handlers[message_type] = handler

    async def start(self):
        await self.connect()
        asyncio.create_task(self.listen_for_messages())

    async def stop(self):
        await self.disconnect()
        

