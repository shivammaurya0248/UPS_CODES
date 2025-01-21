import serial.tools.list_ports
import serial
import logging.config
import os
import ast
import time
from sending_data import send_work_order, send_coil_data

if not os.path.isdir("./logs"):
    print("[-] logs directory doesn't exists")
    os.mkdir("./logs")
    print("[+] Created logs dir successfully")
# Set up logging configuration
logging.config.fileConfig('logging.config')
log = logging.getLogger('UPS_log')


def scaning():
    ports = serial.tools.list_ports.comports()
    port = [p.device for p in ports if "scanner" in p.hwid.lower() or "barcode" in p.hwid.lower()]
    port = port[0]
    log.info(f"[+] port {port}")

    if not port:
        log.error("No scanner or barcode device found.")
        return None  # Return None if no device is found

    log.info(port)
    baud_rate = 9600

    with serial.Serial(port, baud_rate, timeout=1) as ser:
        log.info(f"Connected to {ser.name}")
        while True:
            try:
                if ser.in_waiting > 0:
                    barcode_data = ser.readline().decode('utf-8').strip()

                    return barcode_data
            except Exception as e:
                log.error(f"Error: {e}")
                return None


def work_order_data(input_data):
    # Split the string into parts
    log.info(f"[+] Parsing Work Order Data {input_data}")

    parts = input_data.split("-")
    return parts
    # if parts and isinstance(parts, list):
        # material_code = parts[0]
        # work_order = parts[1]
        # qty = parts[2]
        # chease_wt = parts[3]
        # chese_unit = parts[4]
        # finish_wt = parts[5]
        # finish_unit = parts[6]
        # mrn_no = parts[7]
        # return material_code, work_order, qty, chease_wt, chese_unit, finish_wt, finish_unit, mrn_no
    #     return pars
    # else:
    #     return None, None, None, None, None, None, None, None


# def sending_work_order():
#     try:
#         material_code, work_order, qty, chease_wt, chese_unit, finish_wt, finish_unit, mrn_no = work_order_data()
#         work_order_payload = {
#             "line": "string",
#             "wo_number": work_order,
#             "mrn_no": mrn_no,
#             "material_code": material_code,
#             "quantity": qty,
#             "cheese_weight": chease_wt,
#             "cw_parameter": chese_unit,
#             "finish_weight": finish_wt,
#             "fw_parameter": finish_unit,
#             "machine_name": "string",
#         }
#         log.info(f'work order payload {work_order_payload}')
#         send_work_order(work_order_payload)
#         return True
#     except Exception as e:
#         log.error(f'error is in sending work order data {e}')


def check_keys(data):
    # Check if both 'rm_desc' and 'mrn_no' are in the dictionary
    if 'rm_desc' in data and 'mrn_no' in data:
        return True
    else:
        return False


if __name__ == '__main__':
    log.info("Started....")
    while True:
        scanned_input = scaning()
        FLAG = False
        try:
            input_str1 = str(scanned_input)
            log.info(f"Input String is {input_str1}")

            # clean_str = input_str1[1:-1]
            filtered_string = input_str1.replace("'{", "{").replace("}'", "}")
            log.info(f"Filtered input String is {filtered_string}")
            if '{' in filtered_string:
                parsed_data = ast.literal_eval(filtered_string)
            else:
                parsed_data = filtered_string.replace("'", "")
            log.info(parsed_data)
        except Exception as e:
            log.error(f'[-] Error in parsing Input data : {e}')
            parsed_data = None

        log.info(f"[+] Parsed Data is {parsed_data}")
        if parsed_data:
            FLAG = check_keys(parsed_data)
            log.info(f"[+] Flag is {FLAG}")
            if FLAG:
                rm_desc = parsed_data.get('rm_desc')
                mrn_no = parsed_data.get('mrn_no')
                mrn_no = f"${mrn_no}"
                log.info("[+] Fixing mrn_no")
                weight = parsed_data.get('weight')

                coil_data_payload = {'rm_desc': rm_desc,
                                     'mrn_no': mrn_no,
                                     'weight': weight
                                     }
                log.info(f"[+] Coid data payload is {coil_data_payload}")
                send_coil_data(coil_data_payload)
            else:
                try:
                    material_code, work_order, qty, chease_wt, chese_unit, finish_wt, finish_unit, mrn_no = work_order_data(
                        parsed_data)
                    work_order_payload = {
                        "line": "string",
                        "wo_number": work_order,
                        "wo_mrn_no": f"${mrn_no}",
                        "material_code": material_code,
                        "quantity": int(float(qty)),
                        "cheese_weight": chease_wt,
                        "cw_parameter": chese_unit,
                        "finish_weight": finish_wt,
                        "fw_parameter": finish_unit,
                        "machine_name": "string",
                    }
                    log.info(f'work order payload {work_order_payload}')
                    send_work_order(work_order_payload)
                except Exception as e:
                    log.error(f'[-] Error in Sending work order data: {e}')
        else:
            log.warning(f"[-] Empty or Error payload {scanned_input}")
            # sending_work_order()
        time.sleep(5)

