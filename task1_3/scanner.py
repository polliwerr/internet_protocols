import socket
import argparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Optional


class Target:
    def __init__(self, ip: str, port_range: Tuple[int, int]):
        if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", ip):
            raise ValueError("Неверный формат IP-адреса")
        self.ip = ip
        self.start = port_range[0]
        self.end = port_range[1]


class SimplePortScanner:
    def __init__(self, target: Target):
        self.target = target

    def check_tcp(self, port: int) -> Optional[str]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                s.connect((self.target.ip, port))
                return f"TCP: порт {port} открыт"
        except:
            return None

    def check_udp(self, port: int) -> Optional[str]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(1)
                s.sendto(b"ping", (self.target.ip, port))
                s.recvfrom(1024)
                return f"UDP: порт {port} открыт"
        except socket.timeout:
            return f"UDP: порт {port} возможно открыт (нет ICMP ошибки)"
        except:
            return None

    def run(self, max_threads: int = 100):
        results = []

        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            tcp_tasks = {executor.submit(self.check_tcp, p): p for p in range(self.target.start, self.target.end)}
            udp_tasks = {executor.submit(self.check_udp, p): p for p in range(self.target.start, self.target.end)}

            for task in as_completed(list(tcp_tasks) + list(udp_tasks)):
                result = task.result()
                if result:
                    results.append(result)

        return results


def parse_args():
    parser = argparse.ArgumentParser(description="TCP/UDP сканер портов")
    parser.add_argument("-i", "--ip", required=True, help="Целевой IP-адрес")
    parser.add_argument("-s", "--start", required=True, type=int, help="Начальный порт")
    parser.add_argument("-e", "--end", required=True, type=int, help="Конечный порт (НЕ включительно)")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        target = Target(args.ip, (args.start, args.end))
        scanner = SimplePortScanner(target)

        print(f"Сканирование {args.ip} с портов {args.start} по {args.end - 1}...\n")
        for line in scanner.run():
            print(line)
    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()