import requests
import schedule
import serial
import minimalmodbus
import time
import struct

host = 'iot.ithingspro.cloud'  # put ip and port of the HIS application
access_tokens = ('kkVGiDPRYLZGkTN25V7m',)  # access token from the device in HIS application
slave_Id_VS = [2, 3, 4, 5, 6]  # slave address of the vibration sensor
headers = {"Content-Type": 'application/json'}
sample_time = 15
send_data = True

parameterName = ['Temp1', 'Temp2', 'Temp3', 'Temp4', 'Temp5']


def initiate(slaveId):
    global instrument
    com_port = '/dev/ttyACM0'
    i = int(slaveId)
    instrument = minimalmodbus.Instrument(com_port, i)
    instrument.serial.baudrate = 9600
    instrument.serial.bytesize = 8
    instrument.serial.parity = serial.PARITY_NONE
    instrument.serial.stopbits = 1
    instrument.serial.timeout = 3
    instrument.serial.close_after_each_call = True
    print('initiate Successful for Slave ID: ' + str(i))
    return (instrument)


def sensorValues():
    global headers, access_tokens, slave_Id_VS

    for i in slave_Id_VS:
        data = getSensorValues(i)  # All sensors have values starting from 6 to 10
        try:
            postSensorValues(data, access_tokens[i])
        except Exception as e:
            print(e)


schedule.every(sample_time).seconds.do(sensorValues)


def readSensorValues(instrument):
    try:
        values = instrument.read_registers(6, 1, 4)
        print(values)
        return (values)
    except Exception as e:
        print(e)
        values = 0
        return (values)


def getSensorValues(slaveId):
    a = initiate(slaveId)
    data = readSensorValues(a)
    return data


def postSensorValues(data, accessToken):
    global headers, parameterName, host
    f_list = data
    url = 'http://' + host + '/api/v1/' + accessToken + '/telemetry'
    payload = {}
    for index, value in enumerate(data):
        payload[parameterName[index]] = value

    print(payload)
    if send_data:
        r12 = requests.post(url, json=payload, headers=headers)
        print(r12.status_code)
        print(r12.text)


try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except Exception as e:
    print(e)
