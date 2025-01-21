import time
from pyModbusTCP.client import ModbusClient
import logging


log = logging.getLogger('UPS_log')


class ModbusHelper:
    def __init__(self, ip='192.168.2.1', port=502):
        log.info(f"[+] Machine Params are : [{ip}]:[{port}]")
        self.ip = ip
        self.port = port

    def connection(self):
        c = ModbusClient(host=self.ip, port=self.port, unit_id=1, auto_open=True)
        return c


    def read_machine_status(self):
        try:
            for _ in range(5):
                c = self.connection()
                regs = c.read_coils(8194, 1)
                log.info(f"[+] Got Machine data {regs}")
                log.debug(f"[+] Output Stop Status {c.read_coils(8193, 1)}")
                c.close()
                if not regs:
                    log.warning(f"[+] Got Machine data {regs}")
                else:
                    return regs[0]
        except Exception as err:
            log.error(f'[+] Error Machine disconnected {err}')
        return None


    def power_off_machine(self):
        try:
            c = self.connection()
            for i in range(5):
                log.info("[+] Trying to Turn Machine [OFF]")
                if c.write_single_coil(8193, True):
                    log.info(f"[+] Machine Stopped Successfully: wrote True to PLC Succesfully: Resetting Relay in 5 seconds")
                    time.sleep(5)
                    if c.write_single_coil(8193, False):
                        log.info(f"[+] Relay Resetted successfully")
                        return True
                    else:
                        log.error(f"[-] Realy Not resetted unable to write False to PLC")
                else:
                    log.error(f"[-] Failed to write False to PLC")
        except Exception as err:
            log.error(f'Error PLC disconnected {err}')
        log.info("[-] Failed to Turn OFF the Machine....")