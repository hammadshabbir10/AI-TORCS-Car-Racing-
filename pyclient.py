import sys
import argparse
import socket
import driver
import os
from datetime import datetime

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Python client to connect to the TORCS SCRC server.')

    sys.stdout = sys.stderr  # Force prints to show even if output is buffered
    print("=== DEBUG: Script started ===")

    parser.add_argument('--host', action='store', dest='host_ip', default='localhost',
                        help='Host IP address (default: localhost)')
    parser.add_argument('--port', action='store', type=int, dest='host_port', default=3001,
                        help='Host port number (default: 3001)')
    parser.add_argument('--id', action='store', dest='id', default='SCR',
                        help='Bot ID (default: SCR)')
    parser.add_argument('--maxEpisodes', action='store', dest='max_episodes', type=int, default=1,
                        help='Maximum number of learning episodes (default: 1)')
    parser.add_argument('--maxSteps', action='store', dest='max_steps', type=int, default=0,
                        help='Maximum number of steps (default: 0)')
    parser.add_argument('--track', action='store', dest='track', default='Unknown',
                        help='Name of the track')
    parser.add_argument('--car', action='store', dest='car', default='Unknown',
                        help='Car model name')
    parser.add_argument('--stage', action='store', dest='stage', type=int, default=3,
                        help='Stage (0 - Warm-Up, 1 - Qualifying, 2 - Race, 3 - Unknown)')
    parser.add_argument('--logdir', action='store', dest='logdir', default='logs',
                        help='Directory to store log files (default: logs)')

    arguments = parser.parse_args()

    os.makedirs(arguments.logdir, exist_ok=True)
    logfile = os.path.join(arguments.logdir, 'telemetry_data.csv')

    print('Connecting to server host ip:', arguments.host_ip, '@ port:', arguments.host_port)
    print('Bot ID:', arguments.id)
    print('Track:', arguments.track)
    print('Car:', arguments.car)
    print('Stage:', arguments.stage)
    print('Log file:', logfile)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        print("Socket created.")
    except Exception as e:
        print(f"Socket error: {str(e)}")
        sys.exit(-1)

    shutdownClient = False
    curEpisode = 0
    verbose = True

    d = driver.Driver(arguments.stage, logfile, arguments.track, arguments.car)

    while not shutdownClient:
        print('Starting connection...')
        while True:
            print('Sending ID to server: ', arguments.id)
            buf = arguments.id + d.init()

            try:
                sock.sendto(buf.encode(), (arguments.host_ip, arguments.host_port))
                print("Sent ID successfully.")
            except socket.error as msg:
                print('Failed to send data...Exiting...')
                print(f"Error: {msg}")
                sys.exit(-1)

            try:
                buf, addr = sock.recvfrom(1000)
                buf = buf.decode()
                print("Received data from server:", buf)
            except socket.error as msg:
                print("Did not get a response from server...")
                print(f"Error: {msg}")

            if '***identified***' in buf:
                print('Received: ', buf)
                break

        currentStep = 0

        while True:
            try:
                buf, addr = sock.recvfrom(1000)
                buf = buf.decode()
                print("Received drive data: ", buf)
            except socket.error:
                print("No response... Retrying...")
                continue

            if buf and '***shutdown***' in buf:
                d.onShutDown()
                shutdownClient = True
                print('Client Shutdown')
                break

            if buf and '***restart***' in buf:
                d.onRestart()
                print('Client Restart')
                break

            currentStep += 1

            if currentStep != arguments.max_steps:
                if buf:
                    buf = d.drive(buf)
            else:
                buf = '(meta 1)'

            if buf:
                try:
                    sock.sendto(buf.encode(), (arguments.host_ip, arguments.host_port))
                    print("Command sent to server.")
                except socket.error:
                    print('Failed to send data...Exiting...')
                    sys.exit(-1)

        curEpisode += 1

        if curEpisode == arguments.max_episodes:
            shutdownClient = True

    sock.close()
    print("Client shutdown complete")
