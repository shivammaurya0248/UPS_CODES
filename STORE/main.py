from time import sleep
import serial.tools.list_ports
import serial
import os
import re
import ast
import sys
import requests
import logging.handlers
from logging.handlers import TimedRotatingFileHandler

# Setting up Rotating file logging
if getattr(sys, 'frozen', False):
    dirname = os.path.dirname(sys.executable)
else:
    dirname = os.path.dirname(os.path.abspath(__file__))

log_level = logging.INFO

FORMAT = '%(asctime)-15s %(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s'

logFormatter = logging.Formatter(FORMAT)
log = logging.getLogger("LOGS")

# Checking and creating logs directory here
log_dir = os.path.join(dirname, 'logs')
if not os.path.isdir(log_dir):
    log.info("[-] logs directory doesn't exist")
    try:
        os.mkdir(log_dir)
        log.info("[+] Created logs dir successfully")
    except Exception as e:
        log.error(f"[-] Can't create dir logs Error: {e}")

fileHandler = TimedRotatingFileHandler(os.path.join(log_dir, 'app_log'),
                                       when='midnight', interval=1)

fileHandler.setFormatter(logFormatter)
fileHandler.suffix = "%Y-%m-%d.log"
log.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)
log.setLevel(log_level)
# endregion

ports = serial.tools.list_ports.comports()
usb_ports = [p.device for p in ports if "USB" in p.description]
log.info(usb_ports)

PORT_WT = usb_ports[0]
send_data = True
ACCESS_TOKEN = '4hzxPf6jtgyvvLigEB3e'
host_ip = 'localhost'
HOST = f'http://{host_ip}:8080/api/v1/{ACCESS_TOKEN}/telemetry'
HEADERS = {'content-type': 'application/json'}

PORT_WT = 'COM1'
wt_ser = serial.Serial(
    port=PORT_WT,
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    xonxoff=False,
    timeout=1,
    write_timeout=1
)


def read_weight():
    global PORT_WT, wt_ser
    try:
        wt_ser.flushOutput()
        wt_ser.flushInput()
        wt_ser.flush()
        weight = wt_ser.read_until()
        log.info(f"Got data --- {weight}")
        weight = weight.decode("utf-8")
        weight = re.sub(r"[^\d\.]", "", weight)
        weight = float(weight)
        log.info(f"Got weight data --- {weight}")
        return weight
    except Exception:
        try:
            sleep(2)
            wt_ser.flushOutput()
            wt_ser.flushInput()
            wt_ser.flush()
            wt_ser.close()
        except:
            pass
        try:
            PORT_WT = 'COM1'
            wt_ser = serial.Serial(
                port=PORT_WT,
                baudrate=9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                xonxoff=False,
                timeout=1,
                write_timeout=1
            )
            weight = wt_ser.read_until()
            weight = weight.decode("utf-8")
            weight = re.sub(r"[^\d\.]", "", weight)
            weight = float(weight)
            log.info(f"Got weight data --- {weight}")
            return weight
        except Exception as e:
            log.error(f'ERROR: {e} Error in opening weight serial port')
            return "Error"


def post(payload):
    """posting an error in the attributes if the data is None"""
    global HEADERS
    url = f'{HOST}'
    # payload = {"Recorded_weight": Weight}
    log.info(str(payload))
    if send_data:
        try:
            request_response = requests.post(url, json=payload, headers=HEADERS, timeout=2)
            log.info(f"[+] {request_response.status_code}")
        except Exception as error:
            log.error(f"{error}")


# usb_ports = [p.device for p in ports if "USB" in p.description]
# log.info(f'every port is {usb_ports}')
#
# PORT_WT = usb_ports[0]

def read_barcode():
    ports = serial.tools.list_ports.comports()
    port = [p.device for p in ports if "USB" in p.description]
    port = port[0]
    baud_rate = 9600

    with serial.Serial(port, baud_rate, timeout=1) as ser:
        log.info(f"Connected to {ser.name}")
        while True:
            try:
                if ser.in_waiting > 0:
                    barcode_data = ser.readline().decode('ascii').strip()
                    return barcode_data
            except Exception as e:
                log.error(f"Error: {e}")
                return None


def extract_mrn_and_desc(input_str):
    # Split the string into parts
    parts = input_str.split()

    # The last part is the MRN number
    mrn_no = parts[-1]

    # The rest is the description
    rm_desc = ' '.join(parts[:-1])

    return rm_desc, mrn_no


if __name__ == '__main__':
    log.info("Started....")
    while True:
        scanner_data = read_barcode()
        log.info(f'scanner data is {scanner_data}')
        try:
            if scanner_data:
                converted_dict = ast.literal_eval(scanner_data)
                log.info(type(converted_dict))
                # Regular expression to find the dictionary part
                try:
                    # Access the dictionary values
                    rm_desc = converted_dict.get('rm_desc', '')
                    mrn_no = converted_dict.get('mrn_no', '')
                    mrn_no = '$' + mrn_no + '$'
                    print(mrn_no)
                    output = f"{rm_desc} {mrn_no}"

                    payload = {'rm_desc': rm_desc,
                               'mrn_no': str(mrn_no)}
                    post(payload)
                    log.info(f'[+] sending data of used coil {output}')
                except Exception as e:
                    log.error(f"Error converting string to dictionary: {e}")
        except Exception:
            rm_desc1, mrn_no1 = extract_mrn_and_desc(scanner_data)
            mrn_no1 = '$' + mrn_no1 + '$'

            payload1 = {'rm_desc': rm_desc1, 'mrn_no': mrn_no1}
            try:
                post(payload1)
                log.info(f'[+] sending data of new coil  {payload1}')
            except Exception as e:
                log.error(f'error is in sending mrn no {e}')
            sleep(5)
        try:
            while True:
                weight = read_weight()
                log.info(weight)
                if weight > 0:
                    # weight = float(weight)

                    log.info(f"got weight {weight}")
                    weight_payload = {'weight': weight}
                    post(weight_payload)
                    break
                sleep(1)
        except Exception as e:
            log.error(e)
        sleep(5)
