import os
import logging
# import logging.config
import requests

# logging.config.fileConfig('logging.config')
log = logging.getLogger('UPS_log')
# region definding global var's
access_token = 'C8JvY5UFPCwI1f7NuGWC'#C8JvY5UFPCwI1f7NuGWC
host = 'iot.ithingspro.cloud'
HEADERS = {"Content-Type": "application/json"}
GL_SEND_DATA = True
API = 'https://iot.ithingspro.cloud/api/v1/C8JvY5UFPCwI1f7NuGWC/telemetry'
PRODUCTION_WEIGHT_API = 'https://iot.ithingspro.cloud/ups/api/v1/forging/update_weight'
MACHINE_STATUS_API = 'https://iot.ithingspro.cloud/ups/api/v1/general/get_machine_status/'


def send_weight(payload: dict):
    if GL_SEND_DATA:
        try:
            send_req = requests.post(API, json=payload, headers=HEADERS, timeout=2)
            log.info(payload)
            log.info(send_req.status_code)
            log.info(send_req.text)
            send_req.raise_for_status()
            return True
        except Exception as e:
            log.info(f"[-] Error in sending data of trolley weight TO API, {e}")
            return False


def send_production_weight(DATA: dict):
    if GL_SEND_DATA:
        try:
            send_req = requests.post(PRODUCTION_WEIGHT_API, json=DATA, headers=HEADERS, timeout=2)
            log.info(DATA)
            log.info(send_req.status_code)
            log.info(send_req.text)
            send_req.raise_for_status()
        except Exception as e:
            log.info(f"[-] Error in sending data of production weight TO API, {e}")


def send_work_order(DATA: dict):
    if GL_SEND_DATA:
        try:
            send_req = requests.post(API, json=DATA, headers=HEADERS, timeout=2)
            log.info(DATA)
            log.info(send_req.status_code)
            send_req.raise_for_status()
        except Exception as e:
            log.info(f"[-] Error in sending data of work order TO API, {e}")


def send_coil_data(DATA: dict):
    if GL_SEND_DATA:
        try:
            send_req = requests.post(API, json=DATA, headers=HEADERS, timeout=2)
            log.info(DATA)
            log.info(send_req.status_code)
            send_req.raise_for_status()
        except Exception as e:
            log.info(f"[-] Error in sending data of coil TO API, {e}")


def send_machine_status(DATA: dict):
    if GL_SEND_DATA:
        try:
            send_req = requests.post(API, json=DATA, headers=HEADERS, timeout=3)
            log.info(DATA)
            log.info(send_req.status_code)
            log.info(send_req.text)
            send_req.raise_for_status()
        except Exception as e:
            log.info(f"[-] Error in sending data of machine status TO telemetry, {e}")

def fetch_machine_status(machine_name, machine_status):
    if GL_SEND_DATA:
        try:
            url = f"{MACHINE_STATUS_API}?machine_name={machine_name}&machine_status={machine_status}"
            log.info(f"[+] Getting latest \"should be\" status from : {url}")
            send_req = requests.get(url, headers=HEADERS, timeout=3)
            log.info(send_req.status_code)
            log.info(send_req.text)
            send_req.raise_for_status()
        except Exception as e:
            log.info(f"[-] Error in sending data of machine status TO telemetry, {e}")
