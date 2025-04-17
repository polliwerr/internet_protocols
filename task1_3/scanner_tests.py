import subprocess
import time
import threading
import socket

from scanner import SimplePortScanner, Target


def run_tcp_server(port: int):
    subprocess.Popen(["python3", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def udp_echo_server(port: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", port))
    while True:
        data, addr = s.recvfrom(1024)
        s.sendto(b"echo", addr)


def udp_silent_server(port: int):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", port))
    while True:
        s.recvfrom(1024)


def start_threaded_server(target_func, port: int):
    thread = threading.Thread(target=target_func, args=(port,), daemon=True)
    thread.start()
    return thread


def run_scan(port_start: int, port_end: int):
    target = Target("127.0.0.1", (port_start, port_end))
    scanner = SimplePortScanner(target)
    return scanner.run()


def main():
    print("Запуск тестов для сканера TCP/UDP...\n")

    tcp_open = 9090
    tcp_closed = 9091
    udp_open = 9123
    udp_silent = 9124
    udp_closed = 9125

    print("Запуск TCP-сервера...")
    run_tcp_server(tcp_open)

    print("Запуск UDP-сервера (ответчик)...")
    start_threaded_server(udp_echo_server, udp_open)

    print("Запуск UDP-сервера (молчаливый)...")
    start_threaded_server(udp_silent_server, udp_silent)

    time.sleep(2)

    print("\nСканируем...\n")
    results = run_scan(min(tcp_open, udp_open), max(udp_closed, udp_silent) + 1)

    for line in results:
        print(line)

    print("\nТестирование завершено.")


if __name__ == "__main__":
    main()