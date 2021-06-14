#!/usr/bin/env python3

import socket
import threading
import binascii
import psycopg2
import psycopg2.extras
from datetime import datetime
import uuid

from config import config

HOST = '127.0.0.1'
PORT = 12900

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))


def decode_record(data, car_id):
    """ Decode record data """

    print(int(data[:16], 16))
    timestamp = datetime.fromtimestamp(int(data[:16], 16)/1000)
    priority = int(data[16:18], 16)
    lon = int(data[18:26], 16)
    lat = int(data[26:34], 16)
    alt = int(data[34:38], 16)
    angle = int(data[38:42], 16)
    sats = int(data[42:44], 16)
    speed = int(data[44:48], 16)
    created_at = datetime.now()
    updated_at = datetime.now()

    print("Timestamp: " + str(timestamp) + "\nLat,Lon: " + str(lat) + ", " + str(lon) + "\nAltitude: " + str(alt) + "\nSats: " +  str(sats) + "\nSpeed: " + str(speed) + "\n")
    return (uuid.uuid4(), car_id, timestamp, priority, lon, lat, alt, angle, sats, speed, created_at, updated_at, data)


def check_imei(imei):
    """ Check if car with such imei is registered in database and return car id if exists"""

    car_id = None

    try:
        params = config()
        print('Connecting to the PostgreSQL database...')
        connection = psycopg2.connect(**params)
        cursor = connection.cursor()

        print('Check if imei registered')
        sql = f"SELECT id FROM car_car WHERE sim_imei = '{imei}';"
        cursor.execute(sql)
        car_id = cursor.fetchone()

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")

    return car_id


def store_records(record_data):
    """ store records to database """

    try:
        params = config()
        print('Connecting to the PostgreSQL database...')
        connection = psycopg2.connect(**params)
        cursor = connection.cursor()
        psycopg2.extras.register_uuid()

        insert_query = "INSERT INTO tracking_record (id, car_id, timestamp, priority, longitude, latitude, altitude, \
                                                     angle, satellites, speed, created_at, updated_at, request_data) VALUES %s"
        print("Store records to database")
        print(record_data)
        psycopg2.extras.execute_values(cursor, insert_query, record_data)


    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")


def parse_packet(data, car_id):
    """ Parse packet data and store it to database"""

    # parse packet
    codec = int(data[16:18], 16)
    records = int(data[18:20], 16)
    records_data = data[20:]
    fields = []

    if (codec == 0x8E):
        offset = 7
        record_size = 225
        for record in range(records):
            start = (offset  + record_size) * record
            finish = start + record_size
            print(records_data[start:finish])
            fields.append(decode_record(records_data[start:finish], car_id))

    # store records to database
    store_records(fields)

    # send records quantity to device
    return '000000' + data[18:20].decode("utf-8")


def handle_client(conn, addr):

    print(f"[NEW CONNECTION] {addr} connected.")
    imei = conn.recv(128)
    car_id = check_imei(str(imei)[10:-1])
    print(car_id)

    if car_id:
        try:
            message = '\x01'
            message = message.encode('utf-8')
            print("Send " + str(message))
            conn.send(message)

        except:
            print("Error sending reply. Maybe it's not our device")

        while True:

            try:
                data = conn.recv(2048)
                recieved = binascii.hexlify(data)
                print(recieved)
                record = binascii.unhexlify(parse_packet(recieved, car_id))
                print("Send " + str(record))
                # conn.send(record)

            except socket.error:
                print("Error Occured.")
                break

    conn.close()



def start():

    s.listen()

    print(" Server is listening ...")

    # data = b'000000000000048b8e0a00000179c6ff9830000d51ccb91cfff7ce009400460c000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000500b60004004232aa00430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c7016cf0000d51ccb91cfff7ce009400460e000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000600b60003004232a800430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c70341b0000d51ccb91cfff7ce0094004611000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000500b60003004232aa00430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c7051670000d51ccb91cfff7ce009400460e000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000500b60003004232a600430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c706eb30000d51ccb91cfff7ce0094004611000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000400b60003004232aa00430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c708bff0000d51ccb91cfff7ce0094004610000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000500b60003004232aa00430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c70a94b0000d51ccb91cfff7ce0094004611000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000400b60003004232a500430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c70c6970000d51ccb91cfff7ce0094004611000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000400b60003004232a600430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c70e3e30000d51ccb91cfff7ce0094004610000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000400b60003004232a500430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e000000000179c71012f0000d51ccb91cfff7ce0094004611000000000012000800ef0000f00000150300c800004501005100005200009800000500b5000500b60003004232ad00430fcb00440000000400f10000639f0010001ba25d00570000000000690000000000010084000000000000003e00000a0000505b'

    # parse_packet(data, 'weqewwqew')

    while True:

        conn, addr = s.accept()

        thread = threading.Thread(target=handle_client, args=(conn, addr))

        thread.start()

        print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")

print("[STARTING] server is starting...")

start()