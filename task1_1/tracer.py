import json
import re
import subprocess
from urllib import request, error
from prettytable import PrettyTable

ip_regex = re.compile(r'\d{1,3}(?:\.\d{1,3}){3}')
not_resolve_node = 'traceroute: unknown host'
tracing_route = 'traceroute to'
time_limit = '* * *'


def get_console_tracer(hostname):
    try:
        return subprocess.Popen(
            ['traceroute', hostname],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        ).stdout.readline
    except Exception as e:
        print(f'ошибка при запуске traceroute: {e}')
        return iter([])


def get_ip_info(ip):
    try:
        with request.urlopen(f'http://ipinfo.io/{ip}/json') as response:
            return json.load(response)
    except error.HTTPError:
        return {}
    except Exception as e:
        print(f'ошибка при получении информации об IP {ip}: {e}')
        return {}


def get_list_ip(address):
    tracer = get_console_tracer(address)
    ip_list = []
    seen_start_ip = None
    timeout_counter = 0

    for line in iter(tracer, b''):
        try:
            line = line.decode('cp866')[4:].strip()
        except UnicodeDecodeError:
            continue

        if not line:
            continue
        if not_resolve_node in line:
            print(not_resolve_node)
            break
        if tracing_route in line:
            print(line)
            match = ip_regex.findall(line)
            if match:
                seen_start_ip = match[0]
            continue
        if time_limit in line:
            timeout_counter += 1
            if timeout_counter >= 3:
                break
            continue

        match = ip_regex.findall(line)
        if not match:
            continue

        ip = match[0]
        if ip == seen_start_ip:
            break

        print(f'{line} -> IP: {ip}')
        ip_list.append(ip)
        timeout_counter = 0

    return ip_list


def get_table(ip_list):
    table = PrettyTable(['№', 'IP', 'AS', 'Country', 'Provider'])

    for idx, ip in enumerate(ip_list, 1):
        info = get_ip_info(ip)

        org = info.get('org', '*')
        asn = org.split()[0] if org != '*' else '*'
        provider = ' '.join(org.split()[1:]) if org != '*' else '*'

        table.add_row([
            idx,
            info.get('ip', ip),
            asn,
            info.get('country', '*'),
            provider
        ])

    return table


def main():
    hostname = input('введите доменное имя или IP адрес: ')
    ip_list = get_list_ip(hostname)

    if not ip_list:
        print('IP-адреса не найдены.')
        return

    table = get_table(ip_list)
    print(table)


if __name__ == '__main__':
    main()