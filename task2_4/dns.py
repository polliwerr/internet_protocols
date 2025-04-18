import socket
import threading
import time
import pickle

CACHE_FILE = "cache.db"
DNS_PORT = 1025
UPSTREAM_DNS = ("8.8.8.8", 53)
SUPPORTED_TYPES = {
    "0001": "A",
    "001c": "AAAA",
    "0002": "NS",
    "000c": "PTR"
}

class DNSCache:
    def __init__(self):
        self.store = {}
        self._load()

    def _load(self):
        try:
            with open(CACHE_FILE, 'rb') as f:
                self.store = pickle.load(f)
        except:
            self.store = {}

    def save(self):
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(self.store, f)

    def set(self, name, rtype, data, ttl):
        expire = time.time() + ttl
        self.store[(name, rtype)] = {'data': data, 'expire': expire}

    def get(self, name, rtype):
        entry = self.store.get((name, rtype))
        if entry and time.time() < entry['expire']:
            return entry['data']
        self.store.pop((name, rtype), None)
        return None

    def cleanup(self):
        now = time.time()
        self.store = {k: v for k, v in self.store.items() if v['expire'] > now}

class DNSParser:
    @staticmethod
    def parse_question(data):
        offset = 12
        questions = []
        qdcount = int.from_bytes(data[4:6], 'big')
        for _ in range(qdcount):
            labels = []
            while data[offset] != 0:
                length = data[offset]
                labels.append(data[offset + 1:offset + 1 + length].decode())
                offset += length + 1
            offset += 1
            qtype = data[offset:offset + 2].hex()
            qclass = data[offset + 2:offset + 4].hex()
            questions.append({
                "name": ".".join(labels),
                "type": qtype,
                "class": qclass
            })
            offset += 4
        return questions

    @staticmethod
    def parse_response(data):
        def read_name(data, pos):
            labels = []
            jumped = False
            jump_pos = 0
            while True:
                length = data[pos]
                if length & 0xC0 == 0xC0:
                    if not jumped:
                        jump_pos = pos + 2
                    pointer = int.from_bytes(data[pos:pos+2], 'big') & 0x3FFF
                    pos = pointer
                    jumped = True
                elif length == 0:
                    pos += 1
                    break
                else:
                    labels.append(data[pos+1:pos+1+length].decode())
                    pos += length + 1
            return ".".join(labels), (jump_pos if jumped else pos)

        records = []
        offset = 12
        qdcount = int.from_bytes(data[4:6], 'big')
        ancount = int.from_bytes(data[6:8], 'big')
        nscount = int.from_bytes(data[8:10], 'big')
        arcount = int.from_bytes(data[10:12], 'big')

        for _ in range(qdcount):
            while data[offset] != 0:
                offset += data[offset] + 1
            offset += 5

        def read_records(count, offset):
            results = []
            for _ in range(count):
                name, offset = read_name(data, offset)
                rtype = data[offset:offset+2].hex()
                rclass = data[offset+2:offset+4].hex()
                ttl = int.from_bytes(data[offset+4:offset+8], 'big')
                rdlength = int.from_bytes(data[offset+8:offset+10], 'big')
                rdata = data[offset+10:offset+10+rdlength]
                if rtype == "0001":
                    val = socket.inet_ntoa(rdata)
                elif rtype == "001c":
                    val = socket.inet_ntop(socket.AF_INET6, rdata)
                elif rtype in {"0002", "000c"}:
                    val, _ = read_name(data, offset + 10)
                else:
                    val = None
                if val:
                    results.append((name, rtype, val, ttl))
                offset += 10 + rdlength
            return results, offset

        out = []
        for count in [ancount, nscount, arcount]:
            r, offset = read_records(count, offset)
            out.extend(r)
        return out

class DNSServer:
    def __init__(self):
        self.cache = DNSCache()
        self._start_cleanup()

    def _start_cleanup(self):
        def loop():
            while True:
                self.cache.cleanup()
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()

    def serve(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", DNS_PORT))
        while True:
            data, addr = sock.recvfrom(512)
            threading.Thread(target=self._handle, args=(data, addr, sock)).start()

    def _handle(self, data, addr, sock):
        questions = DNSParser.parse_question(data)
        for q in questions:
            if q["type"] not in SUPPORTED_TYPES:
                continue
            cached = self.cache.get(q["name"], q["type"])
            if cached and q["type"] == "0001":
                response = self._build_response(data, cached)
                sock.sendto(response, addr)
                return
            response = self._forward(data)
            if response:
                records = DNSParser.parse_response(response)
                for name, rtype, val, ttl in records:
                    if rtype in SUPPORTED_TYPES:
                        self.cache.set(name, rtype, val, ttl or 300)
                sock.sendto(response, addr)

    def _forward(self, query):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.sendto(query, UPSTREAM_DNS)
            return s.recv(512)
        except:
            return None

    def _build_response(self, query, ip):
        header = query[:2] + b'\x81\x80' + query[4:6] + b'\x00\x01' + b'\x00\x00\x00\x00'
        question = query[12:]
        answer = b'\xc0\x0c' + b'\x00\x01\x00\x01' + b'\x00\x00\x00\x3c' + b'\x00\x04' + socket.inet_aton(ip)
        return header + question + answer

if __name__ == "__main__":
    server = DNSServer()
    try:
        server.serve()
    except KeyboardInterrupt:
        server.cache.save()