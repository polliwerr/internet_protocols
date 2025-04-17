import socket
import struct
import configparser
import datetime


class FuzzyClockServer:
    def __init__(self, config_path='settings.ini'):
        self._load_config(config_path)
        self.host = '127.0.0.1'
        self.port = 9123

    def _load_config(self, path):
        parser = configparser.ConfigParser()
        parser.read(path)
        self.time_shift = int(parser.get('clock', 'distortion', fallback='0'))
        self.reference_host = parser.get('clock', 'source', fallback='time.windows.com')

    def _retrieve_reference_time(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            request_packet = b'\x1b' + b'\0' * 47
            sock.settimeout(2)
            sock.sendto(request_packet, (self.reference_host, 123))
            raw_data, _ = sock.recvfrom(48)

        ntp_time_part = raw_data[40:]
        seconds, fraction = struct.unpack('!II', ntp_time_part)
        timestamp = seconds + fraction / 2**32
        return timestamp

    def _apply_distortion(self, base_time):
        return base_time + self.time_shift

    def _build_response(self, distorted_time):
        ntp_epoch_offset = 2208988800
        ntp_seconds = int(distorted_time - ntp_epoch_offset)
        fractional = int((distorted_time - int(distorted_time)) * 2**32)
        return struct.pack('!II', ntp_seconds, fractional)

    def launch(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
            listener.bind((self.host, self.port))
            print(f"Сервер слушает на {self.host}:{self.port}\n")

            while True:
                try:
                    payload, client_address = listener.recvfrom(1024)
                    print(
                        f"Запрос от {client_address[0]}:{client_address[1]}")

                    reference_time = self._retrieve_reference_time()
                    adjusted = self._apply_distortion(reference_time)
                    reply = self._build_response(adjusted)
                    listener.sendto(reply, client_address)

                    # Печатаем реальное и искажённое время
                    real_time_str = datetime.datetime.fromtimestamp(
                        reference_time).strftime("%Y-%m-%d %H:%M:%S")
                    fake_time_str = datetime.datetime.fromtimestamp(
                        adjusted).strftime("%Y-%m-%d %H:%M:%S")

                    print(f"Реальное время   : {real_time_str}")
                    print(
                        f"Искажённое время: {fake_time_str} (смещение {self.time_shift} сек)\n")

                except Exception as err:
                    print(f"[!] Ошибка: {err}")


if __name__ == "__main__":
    server = FuzzyClockServer()
    server.launch()