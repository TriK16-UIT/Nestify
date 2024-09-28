import paho.mqtt.client as mqtt
from logging_setup import logger
from config import MQTT_BROKER, MQTT_PORT, HUB_ID
import json

class MQTTHandler:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, HUB_ID)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.message_handlers = {}
        self.client.connect(MQTT_BROKER, MQTT_PORT)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        logger.info("Connected to MQTT server")

    def on_disconnect(self, client, userdata, rc):
        logger.info("Disconnected from MQTT server")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        if 'type' in payload:
            payload = json.loads(payload)
            # logger.info(f"Message received on topic {topic}: {payload}")
            if payload['type'] in self.message_handlers:
                self.message_handlers[payload['type']](topic, payload)

    def subscribe(self, topic):
        self.client.subscribe(topic)
        logger.info(f"Subscribed to topic: {topic}")

    def publish(self, topic, payload, qos=2):
        pubMsg = self.client.publish(topic, payload=payload.encode('utf-8'), qos=qos)
        pubMsg.wait_for_publish()

    def add_message_handler(self, message_type, handler):
        self.message_handlers[message_type] = handler

