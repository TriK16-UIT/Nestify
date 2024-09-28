import time
import paho.mqtt.client as mqtt
import socket
import main

def on_publish(client, userdata, mid):
    print('message published')
    
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "broker")
# client.on_publish = on_publish
client.connect('127.0.0.1', 1883)

client.loop_start()
stage = 0
while True:
    if stage == 0:
        if (main.scan_connect_bluetooth()):
            stage = 1
    else:
        # try:
            inp = input('What do you want to say to your subscriber?\n')
            msg = str(inp)
            pubMsg = client.publish(topic='rpi/broadcast', payload=msg.encode('utf-8'), qos=0)
            pubMsg.wait_for_publish()
            print(pubMsg.is_published())
        # except Exception as e:
        #     stage = 0
        #     print(e)
    # time.sleep(2)
