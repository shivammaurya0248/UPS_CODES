from read_plc import Reading_data, write_machine_off
from weight import read_weight
import time
from sending_data import send_trolley_weight, send_production_weight, send_machine_status
import os
import sys
import logging.config
import logging.handlers
import threading
import pika
import logging
from ingeniousLib.utils import ConfReader

if getattr(sys, 'frozen', False):
    dirname = os.path.dirname(sys.executable)
else:
    dirname = os.path.dirname(os.path.abspath(__file__))

if not os.path.isdir(os.path.join(dirname, 'logs')):
    # if not os.path.isdir(os.path.join(os.path.dirname(dirname), 'logs')):
    print("[-] logs directory doesn't exists")
    try:
        os.mkdir(os.path.join(dirname, 'logs'))
        # os.mkdir(os.path.join(os.path.dirname(dirname), 'logs'))
        print("[+] Created logs dir successfully")
    except Exception as e:
        print(f"[-] Can't create dir logs Error: {e}")

logging.config.fileConfig('logging.config')
log = logging.getLogger('UPS_log')

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
MACHINE_IP = ''

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
    MACHINE_IP = MACHINE_INFO[0]['MACHINE_IP']

print(f"HOST         [{HOST}]")
print(f"PORT         [{PORT}]")
print(f"QUEUE        [{QUEUE}]")
print(f"USERNAME     [{USERNAME_}]")
print(f"PASSWORD     [{PASSWORD}]")
print(f"ACCESS_TOKEN [{ACCESS_TOKEN}]")
print(f"MACHINE_NAME [{MACHINE_NAME}]")
print(f"MACHINE_IP   [{MACHINE_IP}]")

#
# HOST = 'iot.ithingspro.cloud'
# PASSWORD = 'Cybershot@903'
# PORT = 5672
# USERNAME_ = "admin@hisgroup.in"
# QUEUE_NAME = 'ACFG03'
SEND_DATA = True
AMQP_DATA = None

if not os.path.isdir("./logs"):
    log.info("[-] logs directory doesn't exists")
    os.mkdir("./logs")
    log.info("[+] Created logs dir successfully")
dirname = os.path.dirname(os.path.abspath(__file__))

logging.config.fileConfig('logging.config')
log = logging.getLogger('UPS_log')
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
FL_PRODUCTION_START = False
GL_LAST_PROD_SEND_TIME = time.time()
FL_PRODUCTION_PREV_STATUS = False

# we kept 2.5 as sample rate to compensate for the other program delays to send data at every 5sec
PRODUCTION_SAMPLE_RATE = 2.5


# endregion


def receive_message(queue_name=QUEUE, host=HOST, port=PORT, username=USERNAME_, password=PASSWORD):
    global AMQP_DATA
    credentials = pika.credentials.PlainCredentials(username, password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host, port=port, credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    def callback(ch, method, properties, body):
        global AMQP_DATA
        log.info(f" [x] Received {body} ")
        AMQP_DATA = body.decode('utf-8')
        # Send acknowledgment
        ch.basic_ack(delivery_tag=method.delivery_tag)

        # added to hold consumption and stop till getting next response otherwise data will get overwritten
        while AMQP_DATA:
            time.sleep(1)
        return body

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
    log.info(' [*] Waiting for messages.')
    # Start consuming
    channel.start_consuming()


def sensor_data():
    global timer_started, start_time, machine_status, AMQP_DATA, STOP_PRODUCTION, SEND_STATUS, SEND_FALSE
    # Logic when machine is off meanse our sensor is not sensing parts then stop machine
    register_value = Reading_data()  # Function to get the value from the register
    if not register_value[0]:
        if not timer_started:
            start_time = time.time()
            timer_started = True
        else:
            if not start_time:
                start_time = time.time()
            elapsed_time = time.time() - start_time
            if elapsed_time > 20:
                machine_status = False
    else:
        # Reset timer and status if value is True
        timer_started = False
        machine_status = True
        STOP_PRODUCTION = False
    if not machine_status:
        if not SEND_FALSE:
            write_machine_off()
            STOP_PRODUCTION = True
            payload = {'machine_status': False}
            SEND_STATUS = False
            SEND_FALSE = True
            send_machine_status(payload)
    return None


# def main():
#     global AMQP_DATA, STOP_PRODUCTION, SEND_STATUS, PREV_TROLLEY_WEIGHT
#     while True:
#         sensor_data()
#         if AMQP_DATA == "Send Trolley Weight":
#             try:
#                 data = read_weight()
#                 if PREV_TROLLEY_WEIGHT != TROLLEY_WEIGHT:
#                     PREV_TROLLEY_WEIGHT = TROLLEY_WEIGHT
#                 STOP_PRODUCTION = False
#                 log.info(f'weight of trolley is {data}')
#                 AMQP_DATA = None
#                 weight_data()
#             except Exception as e:
#                 log.error(f'error in reading weight {e}')
#         # reading and sending continuous weight
#         if not STOP_PRODUCTION:
#             data = read_weight()
#             if data > 0:
#                 log.info(f'trolley weight is {TROLLEY_WEIGHT*10}')
#                 log.info(f'prev trolley weight is {PREV_TROLLEY_WEIGHT*10}')
#                 log.info(f"data is {data*10}")
#                 subtract = (PREV_TROLLEY_WEIGHT if AMQP_DATA == 'Trolley Cancelled' else TROLLEY_WEIGHT)
#                 pro_weight = data - subtract
#                 log.info(f'pro weight is {pro_weight*10}')
#                 payload = {
#                     "machine_name": "ACFG03",
#                     "inside_weight": pro_weight*10
#                 }
#                 send_production_weight(payload)
#
#                 if not SEND_STATUS:
#                     payload = {'machine_status': True}
#                     send_machine_status(payload)
#                     SEND_STATUS = True
#         # #Logic for machine off when we get command from AMQP
#         if AMQP_DATA == 'Stop Machine':
#             try:
#                 log.info('[-] TURNING OFF MACHINE')
#                 write_machine_off()
#                 payload = {'machine_status': False}
#                 send_machine_status(payload)
#                 SEND_STATUS = False
#                 STOP_PRODUCTION = True
#                 AMQP_DATA = None
#             except Exception as e:
#                 log.error(f'error is in stopping machine {e}')
#             # checking reading plc
#
#         time.sleep(5)


def main():
    global AMQP_DATA, STOP_PRODUCTION, SEND_STATUS, PREV_TROLLEY_WEIGHT, FL_PRODUCTION_START, FL_PRODUCTION_PREV_STATUS
    global GL_LAST_PROD_SEND_TIME
    with open("out.txt", "a+") as f:
        while True:
            weight = read_weight()
            weight = f"{weight}\t"
            f.write(weight)
            f.flush()
            time.sleep(0.1)



if __name__ == '__main__':
    log.info("Started....")
    THREADS = [[threading.Thread(target=main), main]]
    # for i in THREADS:
    #     try:
    #         i[0].start()
    #     except Exception as e:
    #         log.error(f"[+] Error while starting thread {e}: for function {i[1]}")

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

        #
        # thread1 = threading.Thread(target=main)
        # thread2 = threading.Thread(target=receive_message)
        #
        # # Starting threads
        # thread1.start()
        # thread2.start()
        #
        # # Wait until both threads are done
        # thread1.join()
        # thread2.join()
        #
        # log.info("Done!")