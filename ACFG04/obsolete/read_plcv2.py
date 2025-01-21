import time
import os
from pyModbusTCP.client import ModbusClient
# import logging.config
import logging
#
# if not os.path.isdir("./logs"):
#     print("[-] logs directory doesn't exists")
#     os.mkdir("./logs")
#     print("[+] Created logs dir successfully")

# logging.config.fileConfig('logging.config')
log = logging.getLogger('UPS_log')

# IP_ADDRESS = '192.168.102.247'
# PORT = 510
# send_data = True


class ProductionMachine:
    def __init__(self, IP='192.168.2.1', PORT=502):
        self.ip = IP
        self.port = PORT

    def connection(self):
        c = ModbusClient(host=self.ip, port=self.port, unit_id=1, auto_open=True)
        return c


    def read_machine_status(self):
        try:
            c = self.connection()
            regs = c.read_coils(8192, 1)

            log.info(f"values from register is {regs}")
            c.close()
            if not regs:
                log.warning(f"values from register is {regs}")
                a = [0]
                return a
            else:
                return regs
        except Exception as err:
            log.error(f'Error PLC disconnected {err}')


    def power_off_machine(self):
        try:
            c = self.connection()
            for i in range(5):
                log.info("[+] Trying to Turn Machine [OFF]")
                if c.write_single_coil(8193, True):
                    return True
        except Exception as err:
            log.error(f'Error PLC disconnected {err}')
        log.info("[-] Failed to Turn OFF the Machine....")



