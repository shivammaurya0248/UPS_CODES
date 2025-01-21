import ast
import struct
from pandas import read_csv, DataFrame
from .logMan import ILogs


class ConfReader:
    """
    This class Defines multiple parsers
    parse_conf_equal
        This parses the files that have content like:-
        temp=1
        dir='/logs/'

    parse_conf_json
        This parses the files that have contents like
        {
            'temp':1,
            'dir:'/logs',
        }

    parse_conf_csv
        This Parses CSV files like
        machine_id, id, data
        marc1, 1, 'asdf'
        marc2, 2, 'qwer'

    All parsers returns dictionary except parse_conf_csv it returns list of dictionaries

    :Author: Shivam maurya
    organisation: Ingenious Techzoid
    """

    def __init__(self):
        self.ilog = ILogs('main', 'info', False)

    def parse_conf_equal(self, filename: str) -> dict:
        """
        parse_conf_equal
            This parses the files that have content like:-
                temp=1
                dir='/logs/'
        :param filename:
        :return:
        """
        json_obj = {}
        try:
            with open(filename, 'r') as f:
                for i in f.readlines():
                    data = i.split('=')
                    if len(data) < 2:
                        continue
                    key, value = data
                    key = key.strip()
                    value = value.strip()
                    if key[0] == '#':
                        continue
                    json_obj[key] = value
        except Exception as e:
            self.ilog.error(f"[-] Unable to read conf {e}")

        return json_obj

    def parse_conf_json(self, filename):
        """
        parse_conf_json
            This parses the files that have contents like
                {
                    'temp':1,
                    'dir:'/logs',
                }
        :param filename:
        :return:
        """
        json_obj = {}
        try:
            with open(filename, 'r') as f:
                data = f.readlines()
                if data:
                    sum = ''
                    for i in data:
                        sum += i.replace("\n", '').strip()
                    json_obj = ast.literal_eval(sum)
        except Exception as e:
            self.ilog.error(f"[-] Unable to read conf {e}")

        return json_obj

    def parse_conf_csv(self, filename):
        """
        It is a generic csv reader and it give a list of objects (dicts basically)
        with the header name as keys

        :param filename:
        :return:
        """
        list_of_objects = []
        try:
            print(filename)
            data = read_csv(filename)
            keys = data.keys()
            for row_index in range(len(data)):
                list_of_objects.append(
                    dict(
                        zip(
                            keys,
                            [i for i in data.loc[row_index]]
                        )
                    )
                )
        except Exception as e:
            self.ilog.error(f"[-] Unable to read config csv {filename} {e}")

        return list_of_objects

    def create_empty_csv(self, file_path, headers):
        """
        Create an empty CSV file with specified headers using pandas.

        Parameters:
        - file_path (str): The path to the CSV file.

        Returns:
        - None
        """

        # Create an empty DataFrame with the specified headers
        df = DataFrame(columns=headers)

        # Write the DataFrame to a CSV file
        df.to_csv(file_path, index=False)


class Conversions:
    """
    don't get scared fellas this class isn't that much of a demon as it seems

    some functions are here that are just converting one type of value to other
    like integer -> float

    I didn't made this class But I reversed it ;)
    Author: Shivam Maurya
    organisation: Ingenious Techzoid
    """

    def int_to_ieee_float(self, val_int):
        """
        This Class converts 32 bit integer to IEEE 754 Floating point number (~.~) does that sound scary
        remember we are just converting
            32 bit integer to 32 bit float

        :param val_int:
        :return:
        """

        return struct.unpack("f", struct.pack("I", val_int))[0]

    def word_list_to_long(self, val_list, big_endian=True):
        """
        This is a little bit tricky function

        here we give it a list of 16 bit integers and it converts them to 32 bit integer
        i.e.:-
            if we gave it a list of 4 16 bit values it will give us 2 32 bit values

            there are two modes
            little and big endian

        little endian
            stores MSB last
        big endian
            stores MSB first

        so here we try different oredering to see what endian system we are getting data from

        :param val_list:
        :param big_endian:
        :return:
        """

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

    def f_list(self, values, big_endian=True) -> list[float]:
        """
        It converts the list of integer values to a list of float values

        :param values:
        :param big_endian:
        :return:
        """

        fist = []
        for f in self.word_list_to_long(values, big_endian):
            fist.append(round(self.int_to_ieee_float(f), 3))
        # log.info(len(f_list),f_list)
        return fist

    def payload_compare(self, new_paylaod, old_paylaod):
        out_dict = {}
        for key, value in new_paylaod.items():
            if old_paylaod.get(key) != value:
                out_dict[key] = value
        return out_dict
