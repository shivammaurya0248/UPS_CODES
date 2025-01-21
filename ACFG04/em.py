import requests
import schedule
import serial
import minimalmodbus
import time
import struct
import os
import datetime
import logging
import logging.handlers
from logging.handlers import TimedRotatingFileHandler
from ingeniousLib.utils import ConfReader
from pprint import pprint
import serial.tools.list_ports

# Setting up Rotating file logging
dirname = os.path.dirname(os.path.abspath(__file__))


log_level = logging.INFO

FORMAT = ('%(asctime)-15s %(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')

logFormatter = logging.Formatter(FORMAT)
log = logging.getLogger("HIS_EM_LOGS")

# checking and creating logs directory here
if not os.path.isdir("./logs"):
    log.info("[-] logs directory doesn't exists")
    try:
        os.mkdir("./logs")
        log.info("[+] Created logs dir successfully")
    except Exception as e:
        log.error(f"[-] Can't create dir logs Error: {e}")

fileHandler = TimedRotatingFileHandler(os.path.join(dirname, f'logs/em_log'),
                                       when='midnight', interval=1)
fileHandler.setFormatter(logFormatter)
fileHandler.suffix = "%Y-%m-%d.log"
log.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)
log.setLevel(log_level)


# region Configuration Initialization
HOST = 'iot.ithingspro.cloud'
LINE_ID = '1'

# endregion

# Setting up Rotating file logging
dirname = os.path.dirname(os.path.abspath(__file__))

#  Every -- Seconds send data to server
SAMPLE_RATE = 5
# To Stop sending data to server
GL_SEND_DATA = True


HEADERS = {"Content-Type": 'application/json'}
EMS_HOST = f'https://{HOST}/ups/api/v1/ems/create_update_ems_data/'


machine_info = {
    'METER1': {
        'type_': 'EM',
        'machine_name':'ACFG04',
        'unitId': 1,
        'start_reg': 3960,
        'reg_length': 2,
        'pName': ['start_kwh', 'end_kwh'],
    },
}


def initiate(slaveId):
    com_port = None
    for _ in range(5):
        try:
            ports = serial.tools.list_ports.comports()
            usb_ports = [p.device for p in ports if "USB" in p.description]
            log.info(usb_ports)
            com_port = usb_ports[1]
            break
        except Exception as e:
            log.info(f"[-] Error Can't Open Port {e}")
            com_port = None
            time.sleep(1)
    # com_port = '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AB0PN5N1-if00-port0'
    i = int(slaveId)
    instrument = minimalmodbus.Instrument(com_port, i)
    instrument.serial.baudrate = 19200
    instrument.serial.bytesize = 8
    instrument.serial.parity = serial.PARITY_EVEN
    instrument.serial.stopbits = 1
    instrument.serial.timeout = 3
    instrument.serial.close_after_each_call = True
    log.info(f'Modbus ID Initialized: {i}')
    return instrument


def decode_ieee(val_int):
    return struct.unpack("f", struct.pack("I", val_int))[0]


def word_list_to_long(val_list, big_endian=True):
    # allocate list for long int
    long_list = [None] * int(len(val_list) / 2)
    # fill registers list with register items
    for i, item in enumerate(long_list):
        if big_endian:
            long_list[i] = (val_list[i * 2] << 16) + val_list[(i * 2) + 1]
        else:
            long_list[i] = (val_list[(i * 2) + 1] << 16) + val_list[i * 2]
    # return long list
    return long_list


def f_list(values, bit=True):
    fist = []
    for f in word_list_to_long(values, bit):
        fist.append(round(decode_ieee(f), 3))
    # log.info(len(f_list),f_list)
    return fist


def em_values():
    global headers
    for m_name, m_info in machine_info.items():
        log.info(f">>--------{m_name}------>")
        data = None
        # data = get_em_values(m_info['unitId'], m_info['start_reg'], m_info['reg_length'], m_info['type_'])
        try:
            mb_client = initiate(m_info['unitId'])
            log.info("[+] Fetching Data...")       
            data = f_list(mb_client.read_registers(3960, 2, 3), False)
            log.info(f"[+] Got Data from machine {data}")

            payload = {
                "meter": f"{m_name}_{m_info['machine_name']}",
                "line": LINE_ID,
                "start_kwh": 0,
                "end_kwh": 0
            }
            if data:
                payload["start_kwh"] = data[0]
                payload["end_kwh"] = data[0]
                log.info(f"[+] Payload is {payload}")
                post_energy_consumption(payload)
        except Exception as e:
            log.error(e)


schedule.every(SAMPLE_RATE).seconds.do(em_values)


def post_energy_consumption(payload: dict):
    if GL_SEND_DATA:
        try:
            send_req = requests.post(EMS_HOST, json=payload, headers=HEADERS, timeout=2)
            log.info(payload)
            log.info(send_req.status_code)
            log.info(send_req.text)
            send_req.raise_for_status()
            return True
        except Exception as e:
            logging.info(f"[-] Error in sending data of trolley weight TO API, {e}")
            return False


try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    pass
except:
    time.sleep(10)
