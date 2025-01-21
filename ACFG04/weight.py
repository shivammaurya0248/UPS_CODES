import serial.tools.list_ports
import serial
# import logging.config
import re
import time
import os
import logging

if not os.path.isdir("./logs"):
    print("[-] logs directory doesn't exists")
    os.mkdir("./logs")
    print("[+] Created logs dir successfully")
# logging.config.fileConfig('logging.config')
log = logging.getLogger('UPS_log')

ports = serial.tools.list_ports.comports()
port = [p.device for p in ports if "USB" in p.hwid or "ttyUSB" in p.device]
print(port)
PORT_WT = port[0]
#PORT_WT = '/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
log.info(PORT_WT)
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
        print(f"Got data --- {weight}")
        # eight = weight.decode("utf-8")
        weight = weight.decode('utf-8', errors='replace')
        weight = re.sub(r"[^\d\.]", "", weight)
        weight = float(weight)
        print(f"Got weight data --- {weight*10}")
        return weight
    except Exception:
        try:
            time.sleep(2)
            wt_ser.flushOutput()
            wt_ser.flushInput()
            wt_ser.flush()
            wt_ser.close()
        except:
            pass
        try:
            #PORT_WT = '/dev/ttyUSB0'
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
            print(f"Got weight data --- {weight*10}")
            return weight
        except Exception as e:
            print(f'ERROR: {e} Error in opening weight serial port')
            return 0
        


