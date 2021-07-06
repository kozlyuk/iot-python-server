#!/usr/bin/env python3

import socket
import threading
import binascii
import psycopg2
import psycopg2.extras
from datetime import datetime

from configparser import ConfigParser
from config import config
from teltonika import codec8, codec8e


def parse_config(envfile='.env', section='server'):
    """ parsing env file """

    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(envfile)

    # get section, default to server
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            if param[0] == 'host':
                host = param[1]
            if param[0] == 'port':
                port = int(param[1])
    else:
        host='127.0.0.1'
        port=12900

    return host, port


def check_imei(imei):
    """ Check if car with such imei is registered in database and return car id if exists"""

    car_id = None

    try:
        params = config()
        connection = psycopg2.connect(**params)
        cursor = connection.cursor()

        sql = f"SELECT id FROM car_car WHERE sim_imei = '{imei}';"
        cursor.execute(sql)
        car_id = cursor.fetchone()

        if car_id:
            print("IMEI registered. Car id:", car_id)
        else:
            print("IMEI not registered:", imei)

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()

    return car_id


def store_records(record_data, car_id):
    """ store records to database """

    try:
        succeed = False
        params = config()
        connection = psycopg2.connect(**params)
        cursor = connection.cursor()
        psycopg2.extras.register_uuid()

        # # getting last record
        # last_record_querry = f"SELECT is_parked FROM tracking_record WHERE car_id={car_id} ORDER BY timestamp DESC  LIMIT 1"
        # is_parked =

        insert_query = "INSERT INTO tracking_record (id, car_id, timestamp, priority, \
                                                     longitude, latitude, altitude, \
                                                     angle, satellites, speed, \
                                                     event_id, is_parked, io_elements, \
                                                     created_at, updated_at) \
                                                     VALUES %s"
        print("Store records to database" + "\n")
        psycopg2.extras.execute_values(cursor, insert_query, record_data)

        connection.commit()

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

    else:
        succeed = True

    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
        return succeed


def parse_packet(data, car_id):
    """ Parse packet data and store it to database"""

    # parse packet
    codec = int(data[16:18], 16)

    # parse packet for teltonika codec 8 extended
    if (codec == 8):
        fields, response = codec8(data, car_id)
    elif (codec == 0x8E):
        fields, response = codec8e(data, car_id)
    else:
        print('This codec is not implemented:', codec)

    # store records to database
    if store_records(fields, car_id):
        # send records quantity to device
        return response


def handle_client(conn, addr):
    """ thread function communicating with device """

    print(f"[NEW CONNECTION] {addr} connected.")
    imei = conn.recv(128)
    car_id = check_imei(str(imei)[10:-1])

    if car_id:
        try:
            message = '\x01'
            message = message.encode('utf-8')
            conn.send(message)

        except:
            print("Error sending reply. Maybe it's not our device")

        while True:

            try:
                data = conn.recv(2048)
                recieved = binascii.hexlify(data)
                record = binascii.unhexlify(parse_packet(recieved, car_id))
                conn.send(record)

            except socket.error:
                print("Error Occured.")
                break

    conn.close()


def start():
    """ main function """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host, port = parse_config()
    s.bind((host, port))

    s.listen()
    print(f"Server is listening on {host}:{port}")

    while True:
        try:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")
        except KeyboardInterrupt:
            try:
                if conn:
                    conn.close()
            except: pass
            break

print("[STARTING] server is starting...")

start()
