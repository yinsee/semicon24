import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import json
import serial

# MQTT Settings
BROKER = '192.168.0.42'
PORT = 1883
DEVICE_NAME = 'desiccator'
COMMAND_TOPIC = f'/{DEVICE_NAME}/command'
DATA_TOPIC = f'/{DEVICE_NAME}/data'

# GPIO Pins
LIMIT_SWITCH_PINS = [11, 5, 6, 26]
CYLINDER_TOP_PIN = 10
CYLINDER_BOTTOM_PIN = 23
CYLINDER_EXTEND_PIN = 14
CYLINDER_RETRACT_PIN = 17
DHT_SENSOR_PIN = 9  # The GPIO pin connected to the DHT sensor
GAS_PIN = 2
ALARM_PIN = 3
CURTAIN_PIN = 27

previous_status = None
sensor_status = None
temperature = None
humidity = None

TEMPERATURE_THRESHOLD = 40
HUMIDITY_THRESHOLD = 50
HUMIDITY_ALARM_THRESHOLD = 70

# Initial GPIO setup
GPIO.setmode(GPIO.BCM)
for pin in LIMIT_SWITCH_PINS + [CYLINDER_TOP_PIN, CYLINDER_BOTTOM_PIN, CURTAIN_PIN]:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

for pin in [CYLINDER_EXTEND_PIN, CYLINDER_RETRACT_PIN, ALARM_PIN, GAS_PIN]:
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(COMMAND_TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    print(f"Received message: {payload} on topic {msg.topic}")

    if payload == 'close':
        GPIO.output(CYLINDER_EXTEND_PIN, GPIO.HIGH)
        GPIO.output(CYLINDER_RETRACT_PIN, GPIO.LOW)
    elif payload == 'open':
        GPIO.output(CYLINDER_EXTEND_PIN, GPIO.LOW)
        GPIO.output(CYLINDER_RETRACT_PIN, GPIO.HIGH)

    elif payload == 'gas_on':
        GPIO.output(GAS_PIN, GPIO.HIGH)
    elif payload == 'gas_off':
        GPIO.output(GAS_PIN, GPIO.LOW)

    elif payload == 'alarm_on':
        GPIO.output(ALARM_PIN, GPIO.HIGH)
    elif payload == 'alarm_off':
        GPIO.output(ALARM_PIN, GPIO.LOW)

    else:
        print("Unknown command")

# non blocking read from arduino
def read_arduino():
    global humidity, temperature

    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').rstrip()
        if line.startswith('Temperature: '):
            temperature = float(line.split(' ')[1])
        elif line.startswith('Humidity: '):
            humidity = float(line.split(' ')[1])

# update sensor payload and publish if changed
def publish_sensor_status(client):
    global sensor_status

    sensor_status = {
        "limit_switches": [GPIO.input(pin) for pin in LIMIT_SWITCH_PINS],
        "cylinder_top": GPIO.input(CYLINDER_TOP_PIN),
        "cylinder_bottom": GPIO.input(CYLINDER_BOTTOM_PIN),
        "safety_curtain": GPIO.input(CURTAIN_PIN),
        "temperature": temperature,
        "humidity": humidity,
        "alarm": GPIO.input(ALARM_PIN),
        "gas": GPIO.input(GAS_PIN),
    }

    if sensor_status != previous_status:
        client.publish(DATA_TOPIC, json.dumps(sensor_status), retain=True)
        print(f"Published sensor status: {sensor_status}")

# connect arduino serial for environment sensor
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
ser.reset_input_buffer()

# MQTT client setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_start()

# Main loop
try:
    while True:

        if client.is_connected() == False:
            continue

        read_arduino()

        # check temperature and turn on alarm if needed
        if temperature is not None:
            if temperature >= TEMPERATURE_THRESHOLD:
                GPIO.output(ALARM_PIN, GPIO.HIGH)

        # check humidity and pump gas if needed
        if humidity is not None:
            if humidity > HUMIDITY_THRESHOLD:
                GPIO.output(GAS_PIN, GPIO.HIGH)

            if humidity > HUMIDITY_ALARM_THRESHOLD:
                GPIO.output(ALARM_PIN, GPIO.HIGH)


        # alarm if curtain triggered
        if GPIO.input(CURTAIN_PIN) == GPIO.LOW:
            GPIO.output(ALARM_PIN, GPIO.HIGH)

        # stop door if finished
        if (GPIO.input(CYLINDER_EXTEND_PIN) == GPIO.HIGH and GPIO.input(CYLINDER_TOP_PIN) == GPIO.HIGH and GPIO.input(CYLINDER_BOTTOM_PIN) == GPIO.LOW):
            GPIO.output(CYLINDER_EXTEND_PIN, GPIO.LOW)
        if (GPIO.input(CYLINDER_RETRACT_PIN) == GPIO.HIGH and GPIO.input(CYLINDER_TOP_PIN) == GPIO.LOW and GPIO.input(CYLINDER_BOTTOM_PIN) == GPIO.HIGH):
            GPIO.output(CYLINDER_RETRACT_PIN, GPIO.LOW)

        publish_sensor_status(client)
        previous_status = sensor_status


        time.sleep(0.2)

except KeyboardInterrupt:
    print("Exiting program")

finally:
    client.loop_stop()
    client.disconnect()
    # GPIO.cleanup()
