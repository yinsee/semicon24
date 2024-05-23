#!/usr/bin/env python3
import serial

temperature = None
humidity = None

if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.reset_input_buffer()
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            if line.startswith('Temperature: '):
                temperature = float(line.split(' ')[1])
            elif line.startswith('Humidity: '):
                humidity = float(line.split(' ')[1])
            print(f'Temperature: {temperature}°C, Humidity: {humidity}%')