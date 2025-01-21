import time
import requests
from pyModbusTCP.client import ModbusClient
import logging
import serial
import serial.tools.list_ports
import minimalmodbus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)

IP_ADDRESS = '192.168.1.5'
PORT = 510
send_data = True
ACCESS_TOKEN = 'HE30t5JS6d1i3AI0CRLg'
host_ip = 'iot.ithingspro.cloud'
HOST = "http://iot.ithingspro.cloud:8080/api/v1/HE30t5JS6d1i3AI0CRLg/telemetry"
headers = {"Content-Type": 'application/json'}

# Initialize product counts
Upper_Plate_Count = 0
Lower_Plate_Count = 0
total_product_count = 0


def Connection():
    c = ModbusClient(host=IP_ADDRESS, port=PORT, unit_id=1, auto_open=True)
    return c


def get_serial_port():
    try:
        ports = serial.tools.list_ports.comports()
        usb_ports = [p.device for p in ports if "USB" in p.description]
        log.info(usb_ports)
        if len(usb_ports) < 1:
            raise Exception("Could not find USB ports")
        return usb_ports[0]
    except Exception as e:
        log.error(f"[-] Error Can't Open Port {e}")
        return None


def Reading_data():
    try:
        c = Connection()
        log.info(f'PLC Connected..')
        regs = c.read_discrete_inputs(5, 2)
        c.close()
        if not regs:
            return [0, 0]
        else:
            return regs
    except Exception as err:
        log.error(f'Error PLC disconnected {err}')
        return [0, 0]


def initiate_modbus(slaveId):
    com_port = None
    for i in range(5):
        com_port = get_serial_port()
        if com_port:
            break
    i = int(slaveId)
    instrument = minimalmodbus.Instrument(com_port, i)
    instrument.serial.baudrate = 9600
    instrument.serial.bytesize = 8
    instrument.serial.parity = serial.PARITY_NONE
    instrument.serial.stopbits = 1
    instrument.serial.timeout = 3
    instrument.serial.close_after_each_call = True
    log.info("Modbus ID Initialized: " + str(i))
    return instrument


def read_temp():
    try:
        data_list = []

        for slave_id in [2, 3, 4, 5, 6]:
            log.info(f"[+] Getting data for slave id {slave_id}")
            reg_len = 1
            try:
                data = None
                for i in range(5):
                    mb_client = initiate_modbus(slave_id)
                    data = mb_client.read_registers(6, reg_len, 4)
                    if data:
                        break
                log.info(f"Got data {data}")
                if data is None:
                    for i in range(reg_len):
                        data_list.append(0)
                else:
                    data_list += data
            except Exception as e:
                log.error(f"[+] Failed to get data {e} slave id {slave_id}")
                for i in range(reg_len):
                    data_list.append(0)
        return data_list
        log.info(f"[*] Got data {data_list}")
    except Exception as e:
        log.error(e)


def post(payload):
    """Posting data to the server"""
    global headers
    url = f'{HOST}'

    log.info(f"Payload to send: {payload}")
    if send_data:
        try:
            request_response = requests.post(url, json=payload, headers=headers, timeout=10)
            log.info(f"Response status: {request_response.status_code}")
            log.info(f"Response content: {request_response.content}")
        except requests.exceptions.Timeout as timeout_error:
            log.error(f"Timeout error: {timeout_error}")
        except requests.exceptions.RequestException as req_error:
            log.error(f"Request exception: {req_error}")
        except Exception as error:
            log.error(f"An unexpected error occurred: {error}")


if __name__ == '__main__':
    log.info("Started....")
    previous_state = [0, 1]
    while True:
        current_state = Reading_data()  # Get the current state of the registers
        print(current_state)
        TEMP = read_temp()
        print(f'')
        if current_state[0] == 1 and previous_state[0] == 0:
            Upper_Plate_Count += 1
            log.info(f"Plate 1 completed. Total count: {Upper_Plate_Count}")

        if current_state[1] == 0 and previous_state[1] == 1:
            Lower_Plate_Count += 1
            log.info(f"Plate 2 completed. Total count: {Lower_Plate_Count}")

        # Send the combined count to the server
        print(f"Upper_Plate_Count : {Upper_Plate_Count}")
        print(f"Lowe_Plate_Count : {Lower_Plate_Count}")
        total_product_count = Upper_Plate_Count + Lower_Plate_Count
        payload = {

            "Total_Product_Count": total_product_count,
            'Temp1': TEMP[0],
            'Temp2': TEMP[1],
            'Temp3': TEMP[2],
            'Temp4': TEMP[3],
            'Temp5': TEMP[4]
        }
        post(payload)

        # Update the previous state for the next loop
        previous_state = current_state

        time.sleep(10)

