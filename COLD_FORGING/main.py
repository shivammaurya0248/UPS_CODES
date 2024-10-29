from read_plc import ModbusHelper
from weight import read_weight
import time
from sending_data import send_weight, send_production_weight, send_machine_status, fetch_machine_status
import os
import sys
import logging.config
import logging.handlers
import threading
import pika
import logging
from ingeniousLib.utils import ConfReader
from ingeniousLib import logMan
import schedule


log = logMan.ILogs('UPS_log', 'debug', True, True)

if getattr(sys, 'frozen', False):
    dirname = os.path.dirname(sys.executable)
else:
    dirname = os.path.dirname(os.path.abspath(__file__))

# if not os.path.isdir(os.path.join(dirname, 'logs')):
#     # if not os.path.isdir(os.path.join(os.path.dirname(dirname), 'logs')):
#     print("[-] logs directory doesn't exists")
#     try:
#         os.mkdir(os.path.join(dirname, 'logs'))
#         # os.mkdir(os.path.join(os.path.dirname(dirname), 'logs'))
#         print("[+] Created logs dir successfully")
#     except Exception as e:
#         print(f"[-] Can't create dir logs Error: {e}")

# logging.config.fileConfig('logging.config')
# log = logging.getLogger('UPS_log')

# region Configuration Initialization
HOST = ''
PASSWORD = ''
PORT = ''
USERNAME_ = ''
QUEUE = ''
SEND_DATA = ''
AMQP_DATA = ''
ACCESS_TOKEN = ''
MACHINE_NAME = ''
LINE_ID = ''
MACHINE_IP = ''
MACHINE_PORT = 502

CONFDIR = f"{dirname}/conf"
log.info(f"configuration directory name is {CONFDIR}")
if not os.path.isdir(CONFDIR):
    log.info("[-] conf directory doesn't exists")
    try:
        os.mkdir(CONFDIR)
        log.info("[+] Created configuration dir successfully")
    except Exception as e:
        log.error(f"[-] Can't create dir configuration Error: {e}")

machine_config_file = f"{CONFDIR}/machine_config.csv"
server_config_file = f"{CONFDIR}/server_config.csv"

obj_conf_handler = ConfReader()
if not os.path.exists(machine_config_file):
    obj_conf_handler.create_empty_csv(machine_config_file, ['MACHINE_NAME',
                                                        'ACCESS_TOKEN',
                                                        'MACHINE_IP',
                                                        'LINE_ID',
                                                        'MACHINE_PORT'
                                                            ])
if not os.path.exists(server_config_file):
    obj_conf_handler.create_empty_csv(server_config_file, ['HOST', 'PORT', 'QUEUE', 'USERNAME', 'PASSWORD'])

# reading the config file to get the machine configuration
MACHINE_INFO = obj_conf_handler.parse_conf_csv(machine_config_file)
SERVER_INFO = obj_conf_handler.parse_conf_csv(server_config_file)
log.info(MACHINE_INFO)
log.info(SERVER_INFO)

if SERVER_INFO:
    HOST = SERVER_INFO[0]['HOST']
    PORT = SERVER_INFO[0]['PORT']
    QUEUE = SERVER_INFO[0]['QUEUE']
    USERNAME_ = SERVER_INFO[0]['USERNAME']
    PASSWORD = SERVER_INFO[0]['PASSWORD']

if MACHINE_INFO:
    ACCESS_TOKEN = MACHINE_INFO[0]['ACCESS_TOKEN']
    MACHINE_NAME = MACHINE_INFO[0]['MACHINE_NAME']
    LINE_ID = MACHINE_INFO[0]['LINE_ID']
    MACHINE_IP = MACHINE_INFO[0]['MACHINE_IP']
    MACHINE_PORT = int(MACHINE_INFO[0]['MACHINE_PORT'])


print(f"HOST         [{HOST}]")
print(f"PORT         [{PORT}]")
print(f"QUEUE        [{QUEUE}]")
print(f"USERNAME     [XX-REDACTED-XX]")
print(f"PASSWORD     [XX-REDACTED-XX]")
print(f"ACCESS_TOKEN [XX-REDACTED-XX]")
print(f"MACHINE_NAME [{MACHINE_NAME}]")
print(f"LINE_ID      [{LINE_ID}]")
print(f"MACHINE_IP   [{MACHINE_IP}]")
print(f"MACHINE_PORT [{MACHINE_PORT}]")

# endregion


ob_mb = ModbusHelper(MACHINE_IP, MACHINE_PORT)

# HOST = 'iot.ithingspro.cloud'
# PASSWORD = 'Cybershot@903'
# PORT = 5672
# USERNAME_ = "admin@hisgroup.in"
# QUEUE_NAME = 'ACFG03'
SEND_DATA = True
AMQP_DATA = None

# if not os.path.isdir("./logs"):
#     log.info("[-] logs directory doesn't exists")
#     os.mkdir("./logs")
#     log.info("[+] Created logs dir successfully")
# dirname = os.path.dirname(os.path.abspath(__file__))
#
# logging.config.fileConfig('logging.config')
# log = logging.getLogger('UPS_log')
# GL_TROLLEY_WEIGHT__SEND = True
# GL_TROLLEY_WEIGHT__STATUS = 'status from rabbit mq button status from dashboard'
# GL_PUSH_BUTTON__STATUS = 'stop machine'
# WORK_ORDER = False
# TROLLEY_WEIGHT = 0
start_time = None
timer_started = False
machine_status = True
SEND_STATUS = False
PREV_TROLLEY_WEIGHT = 0
STOP_PRODUCTION = False
SEND_FALSE = False

# region New GLOBAL VARIABLES
FL_FIRST_RUN_QUEUE_EMPTY = True
FL_PRODUCTION_START = False
GL_LAST_PROD_SEND_TIME = time.time()
FL_PRODUCTION_PREV_STATUS = False
GL_PREV_WEIGHT = None

# we kept 2.5 as sample rate to compensate for the other program delays to send data at every 5sec
PRODUCTION_SAMPLE_RATE_SEC = 2.5
SPIKE_THRESHOLD_KG = 1
SPIKE_DURATION_THRESHOLD_SEC = 3
FL_SPIKE_OCCURRED = False
GL_WEIGHT_TO_SEND = 0

# msg key dict here keys are stored as value and msg is dictionaryKeys
# when msg is received send weight with its value as its key
MSG_KEY_DICT = {
    "Send Trolley Weight": "trolley_weight",
    "SEND SCRAP PIECE": "process_scrap_weight",
    "SEND END PIECE": "coil_end_piece_weight",
    "SEND TRIMMING": "trimming_weight",
}
# endregion



def receive_message(queue_name=QUEUE, host=HOST, port=PORT, username=USERNAME_, password=PASSWORD):
    global AMQP_DATA
    credentials = pika.credentials.PlainCredentials(username, password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port, credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    channel.queue_purge(queue=queue_name)
    log.warn(f"[!] Flushing queue {queue_name} at First Run...")

    def callback(ch, method, properties, body):
        global AMQP_DATA
        log.info(f"[x] Received {body}")
        AMQP_DATA = body.decode('utf-8')
        # Send acknowledgment
        ch.basic_ack(delivery_tag=method.delivery_tag)

        # added to hold consumption and stop till getting next response otherwise data will get overwritten
        return body

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
    log.info(' [*] Waiting for messages.')
    # Start consuming
    channel.start_consuming()


# def sensor_data():
#     global timer_started, start_time, machine_status, AMQP_DATA, STOP_PRODUCTION, SEND_STATUS, SEND_FALSE
#     # Logic when machine is off meanse our sensor is not sensing parts then stop machine
#     while True:
#         try:
#             register_value = Reading_data()  # Function to get the value from the register
#             if not register_value[0]:
#                 if not timer_started:
#                     start_time = time.time()
#                     timer_started = True
#                 else:
#                     if not start_time:
#                         start_time = time.time()
#                     elapsed_time = time.time() - start_time
#                     if elapsed_time > 20:
#                         machine_status = False
#             else:
#                 # Reset timer and status if value is True
#                 timer_started = False
#                 machine_status = True
#                 STOP_PRODUCTION = False
#             if not machine_status:
#                 if not SEND_FALSE:
#                     write_machine_off()
#                     STOP_PRODUCTION = True
#                     payload = {'machine_status': False}
#                     SEND_STATUS = False
#                     SEND_FALSE = True
#                     send_machine_status(payload)
#         except Exception as e:
#             log.error(f"[-] Error while reading and sending sensor data")
#         time.sleep(0.5)


# def sensor_data():
#     global timer_started, start_time, machine_status, AMQP_DATA, STOP_PRODUCTION, SEND_STATUS, SEND_FALSE
#     # Logic when machine is off meanse our sensor is not sensing parts then stop machine
#     while True:
#         try:
#             register_value = ob_mb.read_machine_status()  # Function to get the value from the register
#             log.info(f"[+] Machine Status is {register_value}")
#
#         except Exception as e:
#             log.error(f"[-] Error while reading and sending sensor data {e}")
#         time.sleep(0.1)

class MachineStatus:
    def __init__(self):
        self.prev_status = None
        self.last_sent_time = time.time()


    def read_and_send_mc_status(self):
        global timer_started, start_time, machine_status, AMQP_DATA, STOP_PRODUCTION, SEND_STATUS, SEND_FALSE
        while True:
            try:
                curr_machine_status = ob_mb.read_machine_status()  # Function to get the value from the register
                log.info(f"[+] Machine Status is {curr_machine_status}")
                if curr_machine_status is not None:
                    if curr_machine_status != self.prev_status or (time.time() - self.last_sent_time) > 15:
                        self.prev_status = curr_machine_status
                        send_machine_status({'machine_status': curr_machine_status})
                        fetch_machine_status(MACHINE_NAME, curr_machine_status)

                else:
                    log.error(f"Error Communicating with machine")

            except Exception as e:
                log.error(f"[-] Error while reading and sending sensor data {e}")
            time.sleep(2)



def check_spike(input_list: list[int|float], spike_threshold: int|float) -> bool:
    """
    input_list: list of numbers to find spike in
    spike_threshold: threshold to determine spike in given input_list
    """
    for i, j in zip(input_list[:-1], input_list[1:]):
        if abs(j - i) > spike_threshold:
            return True
    return False



def main():
    global AMQP_DATA, STOP_PRODUCTION, SEND_STATUS, PREV_TROLLEY_WEIGHT, FL_PRODUCTION_START, FL_PRODUCTION_PREV_STATUS
    global GL_LAST_PROD_SEND_TIME, GL_PREV_WEIGHT, FL_SPIKE_OCCURRED, GL_WEIGHT_TO_SEND
    log.info("[+] Main function started")
    while True:
        # sensor_data()
        weight = read_weight()
        log.info(f"[+] Curr Weight is [{weight}]")
        if AMQP_DATA in ["Send Trolley Weight", "SEND SCRAP PIECE", "SEND END PIECE", "SEND TRIMMING"]:
            # in any msg arrive from the amqp sending its weight to the telemetry
            try:
                weight = read_weight()
                weight_payload = {
                    f"{MSG_KEY_DICT.get(AMQP_DATA, "unknown")}": weight
                }
                if send_weight(weight_payload):
                    log.info(f"[+] {MSG_KEY_DICT.get(AMQP_DATA, "unknown")} weight Sent Succcessfully {weight_payload}")
                else:
                    log.error(f"[-] Failed to send {MSG_KEY_DICT.get(AMQP_DATA, "unknown")}  Weight : {weight}")
                time.sleep(0.1)
            except Exception as e:
                log.error(f'error in reading weight {e}')
                time.sleep(1)

        elif AMQP_DATA in ["TROLLEY CHANGED", "TROLLEY CANCELLED", "CONTINUE PRODUCTION"]:
            FL_PRODUCTION_START = True
            GL_LAST_PROD_SEND_TIME = time.time()
            GL_PREV_WEIGHT = None
        #
        # elif AMQP_DATA == "TROLLEY CANCELLED":
        #     pass

        elif AMQP_DATA in ["COMPLETE WORK ORDER", "PAUSE PRODUCTION"] :
            # if work order is complete or user has requested to change the bin we will stop sending the production data
            # to not cause issues with actual running data
            FL_PRODUCTION_START = False
            GL_PREV_WEIGHT = None

        elif AMQP_DATA == 'Stop Machine':
            try:
                log.info('[-] TURNING OFF MACHINE')
                machine_off = ob_mb.power_off_machine()
                if machine_off:
                    payload = {'machine_status': False}
                    send_machine_status(payload)
                STOP_PRODUCTION = True
                GL_PREV_WEIGHT = None
            except Exception as e:
                log.error(f'error is in stopping machine {e}')

        else:
            pass
        AMQP_DATA = None

        if FL_PRODUCTION_START:
            read_start_time = time.time()
            weight_data = []
            while (time.time() - read_start_time) < SPIKE_DURATION_THRESHOLD_SEC:
                weight = read_weight()
                log.info(f"[+] Production Weight is [{weight}]")
                weight_data.append(weight)
                time.sleep(0.1)
            FL_SPIKE_OCCURRED = check_spike(weight_data, SPIKE_THRESHOLD_KG)
            if not FL_SPIKE_OCCURRED:
                GL_WEIGHT_TO_SEND = weight_data[-1]

            log.info(f"[+] {weight_data}")
        if not FL_SPIKE_OCCURRED:
            if FL_PRODUCTION_START or FL_PRODUCTION_PREV_STATUS:
                if (time.time() - GL_LAST_PROD_SEND_TIME) > PRODUCTION_SAMPLE_RATE_SEC or FL_PRODUCTION_START != FL_PRODUCTION_PREV_STATUS:
                    log.info("[+] Sending Data to server")
                    payload = {
                        # "machine_name": "ACFG03",
                        "machine_name": MACHINE_NAME,
                        "inside_weight": GL_WEIGHT_TO_SEND
                    }
                    send_production_weight(payload)
                    GL_LAST_PROD_SEND_TIME = time.time()
                    GL_WEIGHT_TO_SEND = 0
            FL_PRODUCTION_PREV_STATUS = FL_PRODUCTION_START
        else:
            log.info(f"[-] SPIKE OCCURRED ")
        time.sleep(.5)


if __name__ == '__main__':
    ob_mc_status = MachineStatus()
    log.info("Started....")
    THREADS = [
        [threading.Thread(target=main), main],
        [threading.Thread(target=receive_message), receive_message],
        [threading.Thread(target=ob_mc_status.read_and_send_mc_status), ob_mc_status.read_and_send_mc_status]
    ]

    while True:
        for thread in THREADS:
            if not thread[0].is_alive():
                try:
                    thread[0].join()
                    thread[0] = threading.Thread(target=thread[1])
                    thread[0].start()
                except Exception as e:
                    log.error(f"[-] Exception Running Thread: {e} : For {thread[1]}")
                    thread[0] = threading.Thread(target=thread[1])
                    thread[0].start()
            time.sleep(1)