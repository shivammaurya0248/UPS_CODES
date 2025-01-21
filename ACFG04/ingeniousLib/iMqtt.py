import json
import paho.mqtt.client as mqtt
import sqlite3
import random
import time
import ast
import os
from .logMan import ILogs, default_dir


# ilog = ILogs('HIS_LOGS', 'info', False)


class DBHelperMqtt:
    def __init__(self, db_name, logger, default_dir=default_dir):
        self.log = logger
        self.db_path = os.path.join(default_dir, 'data')
        db_name_full = os.path.join(self.db_path, f"{db_name}_sync.db")
        self.connection = sqlite3.connect(db_name_full, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_data_table(ts INTEGER, payload STRING)""")  # sync_data_table

    # region Sync data TB database
    def add_sync_data(self, payload):
        try:
            ts = int(time.time() * 1000)
            self.cursor.execute("""
            INSERT INTO sync_data_table(ts, payload)
            VALUES(?,?)""", (ts, str(payload)))

            self.log.info(f"[+] Successful, Sync Payload Added to the database")
            self.connection.commit()
        except Exception as e:
            self.log.error(e)
            return False

    def get_sync_data(self):
        try:
            self.cursor.execute("""SELECT * FROM sync_data_table""")
            data = self.cursor.fetchmany(100)
            if len(data):
                data_payload = [{
                    "ts": item[0],
                    "payload": ast.literal_eval(item[1])
                } for item in data]
                return data_payload
        except Exception as e:
            self.log.error(e)
            return False

    def clear_sync_data(self, ts):
        try:
            self.cursor.execute("""DELETE FROM sync_data_table where ts=?""",
                                (ts,))
            self.connection.commit()
            self.log.info(f"Successful, Cleared Sync payload from the database for - {ts}")
        except Exception as e:
            self.log.error(f'Error in clear_sync_data {e} No sync Data to clear')
            return False

    # endregion


class MqttHelper(DBHelperMqtt):
    def __init__(self, db_name, broker, logger, port=1883, qos=2, username='', password=''):
        super().__init__(db_name, logger)
        self.username = username
        self.password = password
        self.qos = qos
        self.port = port
        self.broker = broker
        self.client_mqtt = None
        self.send_data_fl = True
        self.initiate()
        self.sync_fl = True
        self.log = logger

    def initiate(self,):
        client_id = f"client-{random.randint(0, 43430)}-{random.randint(0, 50000)}"
        client_mqtt = mqtt.Client(client_id)
        client_mqtt.on_connect = self.on_connect
        client_mqtt.on_message = self.on_message
        if self.username:
            client_mqtt.username_pw_set(self.username, self.password)
        try:
            self.log.info(f"[*] Trying connection to {self.broker}")
            client_mqtt.connect(self.broker, self.port, clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY, keepalive=60)
        except Exception as e:
            self.log.error(f"[-] Unable to connect to mqtt broker {e}")

        try:
            client_mqtt.loop_start()
        except Exception as e:
            self.log.error(f"[-] Error while starting loop {e}")
        self.client_mqtt = client_mqtt
        return client_mqtt

    def on_message(self, client, userdata, message):
        self.log.info(f"Received message - {message.payload.decode('utf-8')}")
        # return message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log.info("Connected to MQTT Broker!")

        else:
            self.log.error("Failed to connect, return code %d\n", rc)

    def publish_payload(self, payload, topic_pub):
        if self.send_data_fl:
            result = [None, None]  # set the result to None
            try:
                payload_str = json.dumps(payload)
                self.log.info(f"[+] publishing_data")
                self.log.info(payload)
                result = self.client_mqtt.publish(topic_pub, payload_str, qos=self.qos)  # try to publish the data if publish gives exception
                self.log.info(f"result is {result}")
            except:
                try:
                    self.log.error(f"Error Publishing data result is {result}")
                    self.client_mqtt.disconnect()  # try to disconnect the client
                    self.log.info(f"[+] Disconnected from Broker")
                    time.sleep(2)
                except:
                    pass
                self.log.error(f"[-] is client connected {self.client_mqtt.is_connected()}")
                if not self.client_mqtt.is_connected():  # if client is not connected
                    self.log.info(f"[+] Retrying....")
                    for _ in range(5):
                        self.client_mqtt = self.initiate()     # retry to connect to the broker
                        time.sleep(1)
                        if self.client_mqtt.is_connected():  # if connected: break
                            break
            # result: [0, 1]
            status = result[0]

            if self.sync_fl:
                if status == 0:  # if status is 0 (ok)
                    self.log.info(f"[+] Send `{result}` to topic `{topic_pub}`")
                    sync_data = self.get_sync_data()  # get all the data from the sync payload db
                    if sync_data:  # if sync_data present
                        for i in sync_data:  # for every payload
                            if i:  # if payload is not empty
                                ts = i.get("ts")  # save timestamp
                                sync_payload = json.dumps(i.get("payload"))
                                sync_result = self.client_mqtt.publish(topic_pub, sync_payload, qos=self.qos)  # send payload
                                if sync_result[0] == 0:  # if payload sent successful remove that payload from db
                                    self.clear_sync_data(ts)
                                else:  # else break from the loop
                                    self.log.error("[-] Can't send sync_payload")
                                    break
                else:
                    self.log.error(f"[-] Failed to send message to topic {topic_pub}")
                    self.add_sync_data(payload)  # if status is not 0 (ok) then add the payload to the database
