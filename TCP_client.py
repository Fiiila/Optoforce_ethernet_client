import socket
import struct
import time
from multiprocessing import Process, Value, Pipe, Event, Array
import ctypes

import numpy as np


# from cpppo.server.enip.list_identity_simple import response


def request_selector(command_num=None):
    """Request command selector

    :param command_num:
    :return:
    """
    command_selected = False if command_num is None else True
    available_commands = {"Get latest F/T reading": [0x00, [0]*19, '!B19B', '!HHHHHHHH'],
                          "Get the Newton/Newton-meter Conversion Parameters":[0x01, [0]*19, '!B19B', '!HBBIIH']}
    pairing = [*available_commands.keys()]
    command = None
    data = None
    while not command_selected:
        # Show available commands
        print("Available commands:")
        for i,c in enumerate(available_commands.keys()):
            print(f"{i}) - {c}")
        print("\n")
        # Get user input for commands
        try:
            user_input = int(input("Select command type: "))
        except Exception as e:
            print(e)
            continue
        # validate user input
        if (user_input >= 0) and (user_input < len(pairing)):
            command_num = user_input
            command_selected = True
        else:
            print(f"Command under selected number \"{user_input}\" not available.")
            continue
    # create command
    command, data, request_format, response_format = available_commands[pairing[command_num]]
    request_message = struct.pack(request_format, command, *data)
    print(request_message)

    return request_message, response_format

def tcp_subscriber(resp, host, port, req_data, stop_event):
    # request
    request_message = req_data[0]
    response_format = req_data[1]

    # Host IP and port
    HOST = host
    PORT = port
    RESPONSE_BYTES = struct.calcsize(response_format)

    # Create TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to host
        sock.connect((HOST, PORT))
        print(f"Connected to {HOST}:{PORT}")
        time.sleep(1)

        while not stop_event.is_set():
            time.sleep(0.1)
            # Send request message
            sock.sendall(request_message)

            # Wait for the response
            response = sock.recv(RESPONSE_BYTES)
            # resp[:] = response
            # print(response)
            if len(response) == RESPONSE_BYTES:

                # Parse the response based on the provided structure
                if response_format == '!HHHHHHHH':
                    header, status, fx, fy, fz, tx, ty, tz = struct.unpack(response_format, response)
                    resp[:] = [header, status, fx, fy, fz, tx, ty, tz]
                    print(f"Response (forces) received:")
                    # print(f"  Header: 0x{header:04X}")
                    # print(f"  Status: 0x{status:04X}")
                    # print(f"  Fx: {fx}")
                    # print(f"  Fy: {fy}")
                    # print(f"  Fz: {fz}")
                    # print(f"  Tx: {tx}")
                    # print(f"  Ty: {ty}")
                    # print(f"  Tz: {tz}")
                elif response_format == '!HBBIIH':
                    header, unit_force, unit_torque, counts_per_force_val, counts_per_torque_val, scale_factor = struct.unpack(response_format, response)
                    # resp.value = np.random.randint(10)
                    print(f"Response received:")
                    print(f"  Header: 0x{header:04X}")
                    print(f"  unit_force: 0x{unit_force:04X}")
                    print(f"  unit_torque: {unit_force}")
                    print(f"  counts_per_force_val: {counts_per_force_val}")
                    print(f"  counts_per_torque_val: {counts_per_torque_val}")
                    print(f"  scale_factor: {scale_factor}")
            else:
                print("Received an invalid response size. Stopping")
                print(response)
                # break
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(e)
    finally:
        sock.close()
    return


def test():
    # Device IP and port
    DEVICE_IP = "192.168.1.3"  # Replace with your device's IP address
    PORT = 49151  # Device listening on port 49151

    # Request Format (20 bytes)
    command = 0x00  # Command is always 0x00
    reserved = [0] * 19  # Reserved array of 19 zero bytes

    # Create the request message
    request_message = struct.pack('!B19B', command, *reserved)

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to the device
        sock.connect((DEVICE_IP, PORT))
        print(f"Connected to {DEVICE_IP}:{PORT}")

        # Send the request to the device
        sock.sendall(request_message)
        print("Request sent to device.")

        # Wait for the response (16 bytes)
        response = sock.recv(16)
        print(response)

        if len(response) == 16:
            # Parse the response based on the provided structure
            header, status, fx, fy, fz, tx, ty, tz = struct.unpack('!HHHHHHHH', response)

            print(f"Response received:")
            print(f"  Header: 0x{header:04X}")
            print(f"  Status: 0x{status:04X}")
            print(f"  Fx: {fx}")
            print(f"  Fy: {fy}")
            print(f"  Fz: {fz}")
            print(f"  Tx: {tx}")
            print(f"  Ty: {ty}")
            print(f"  Tz: {tz}")
        else:
            print("Received an invalid response size.")
            print(response)

    except socket.error as e:
        print(f"Error: {e}")
    finally:
        # Close the socket connection
        sock.close()
        print("Connection closed.")

def monitor(resp, stop_event):
    while not stop_event.is_set():
        print("monitor:")
        print(resp[:])
        time.sleep(1)

if __name__ == '__main__':
    host = "192.168.1.3"
    port = 49151
    stop_event = Event()
    req_msg, req_frm = request_selector(0)
    # resp = Array(ctypes.c_ubyte, range(struct.calcsize(req_frm)))
    resp = Array(ctypes.c_int16, range(8))
    # tcp_subscriber(resp=resp,host="192.168.1.3", port=49151, req_data=request_selector(1), stop_event=stop_event)
    # test()
    # resp = Value('b', 0)
    #
    subs = Process(target=tcp_subscriber, args=(resp, host, port, (req_msg, req_frm), stop_event,))
    subs.start()
    mon = Process(target=monitor, args=(resp, stop_event))
    mon.start()
    time.sleep (10)
    stop_event.set()

    subs.join()
    mon.join()