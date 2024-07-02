import RPi.GPIO as GPIO
import time
import paho.mqtt.client as mqtt
import json

# Setup
GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
GPIO.setwarnings(False)

desiccatorSensor = {
    "cylinder_top":False,
    "cylinder_bottom":False
    }

robotSensor = {
    "pick_oven": False,
    "put_oven": False,
    "pick_desiccator": False,
    "put_desiccator": False
    }

ovenSensor = {
    "door_open":False,
    "door_close":False,
    "stop":True
    }

E_STOP_PIN_IN = 24

GPIO.setup(E_STOP_PIN_IN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# MQTT Settings
BROKER = 'localhost'
PORT = 1883

# MQTT callback functions
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe('/desiccator/data')
    client.subscribe('/robot/data')
    client.subscribe('/oven/data')

def on_message(client, userdata, msg):
    global desiccatorSensor, robotSensor, ovenSensor
    payload = json.loads(msg.payload.decode('utf-8'))
    #print(f"Received message: {payload} on topic {msg.topic}")
    if (msg.topic == '/desiccator/data'):
        desiccatorSensor = payload
    if (msg.topic == '/robot/data'):
        robotSensor = payload
    if (msg.topic == '/oven/data'):
        ovenSensor = payload

# MQTT client setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_start()


#SYSTEM FLOW
while True:

    if not client.is_connected:
        time.sleep(0.25)
        continue

    #1- Open Desicator
    #top 0 , bottom 1 = open
    client.publish('/desiccator/command', 'open')
    print("1.Send command to desicator to open door, waiting feedback done open")
    time.sleep(1)
    while False==desiccatorSensor['cylinder_bottom']:
        time.sleep(0.25)

    #2- Pick From desicator
    client.publish('/robot/command', 'pick_desiccator')
    print("2.Send command to robot to pick desicator, waiting feedback done pick")
    while False==robotSensor['pick_desiccator']:
        time.sleep(0.25)
    while True==robotSensor['pick_desiccator']:
        time.sleep(0.25)

    #3- Close desicator
    #top 1 , bottom 0 = close
    client.publish('/desiccator/command', 'close')
    print("3.Send command to desiccator to close desicator, waiting feedback done close")
    time.sleep(1)
    while False==desiccatorSensor['cylinder_top']:
        time.sleep(0.25)

    #4- Open oven
    client.publish('/oven/command', 'open')
    print("4.Send command to oven to open oven, waiting feedback done open oven")
    time.sleep(0.25)
    while False==ovenSensor['door_open']:
        time.sleep(0.25)

    #5- Put oven
    client.publish('/robot/command', 'put_oven')
    print("5.Send command to robot to put oven, waiting feedback done put oven")
    while False==robotSensor['put_oven']:
        time.sleep(0.25)
    while True==robotSensor['put_oven']:
        time.sleep(0.25)

    #6- close oven
    client.publish('/oven/command', 'close') #send to oven
    print("6.Send command to oven to close oven, waiting feedback done close oven")
    time.sleep(0.25)
    while False==ovenSensor['door_close']: #checking
        time.sleep(0.25)

    # todo: send oven start
    # todo: wait for baking complete
    client.publish('/oven/command', 'start') #send to oven
    print("0.Send command to oven start, waiting oven to stop")
    while True==ovenSensor['stop']: #checking
        time.sleep(0.25)
    while False==ovenSensor['stop']: #checking
        time.sleep(0.25)

    #9- Open oven
    client.publish('/oven/command', 'open')
    print("7.Send command to oven to open oven, waiting feedback done open oven")
    time.sleep(0.25)
    while False==ovenSensor['door_open']:
        time.sleep(0.25)

    #10 - Pick oven
    client.publish('/robot/command', 'pick_oven')
    print("8.Send command to robot to pick oven, waiting feedback done pick oven")
    while False==robotSensor['pick_oven']:
        time.sleep(0.25)
    while True==robotSensor['pick_oven']:
        time.sleep(0.25)

    #11-  open desicator
    client.publish('/desiccator/command', 'open')
    print("9.Send command to desiccator to open, waiting feedback done open")
    time.sleep(1)
    while False==desiccatorSensor['cylinder_bottom']:
        time.sleep(0.25)

    #12- put desicator
    client.publish('/robot/command', 'put_desiccator')
    print("10.Send command to robot to put desicator, waiting feedback done put desicator")
    while False==robotSensor['put_desiccator']:
        time.sleep(0.25)
    while True==robotSensor['put_desiccator']:
        time.sleep(0.25)

    #13- close desicator
    client.publish('/desiccator/command', 'close')
    print("11.Send command to desiccator to close, waiting feedback done close")
    time.sleep(1)
    while False==desiccatorSensor['cylinder_top']:
        time.sleep(0.25)

    #14- w8 10s
    time.sleep(5)
    #15- loop back to 1

