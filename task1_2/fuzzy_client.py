import socket
import struct
import datetime


def request_fuzzy_time(server_addr=('127.0.0.1', 9123)):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(b'query_time', server_addr)
        packet, _ = sock.recvfrom(48)
        sec, frac = struct.unpack('!II', packet)
        raw_timestamp = sec + frac / 2**32
        return datetime.datetime.fromtimestamp(raw_timestamp)


if __name__ == '__main__':
    try:
        while True:
            input("Нажмите Enter для получения времени...")
            dt = request_fuzzy_time()
            print(f"[Искажённое время]: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
    except KeyboardInterrupt:
        print("\n[Клиент завершён]")