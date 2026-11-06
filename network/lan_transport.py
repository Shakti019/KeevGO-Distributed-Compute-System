import asyncio
import socket
from logging import exception
from network.connection_manager import ConnectionManager

class LANTransport:
    @staticmethod
    def get_lan_ips():
        ips = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                ips.append(ip)
        except Exception:
            pass

        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith("127.") and ip not in ips:
                    ips.append(ip)
        except Exception:
            pass

        return ips if ips else ["127.0.0.1"]

    @staticmethod
    def get_lan_ip():
        ips = LANTransport.get_lan_ips()
        return ips[0] if ips else "127.0.0.1"

    def __init__ (self):
        self.reader=None
        self.writer=None
        self.connected=False
        self.remote_address=None

    async def connect(self, address):
        if self.connected:
            raise exception("LAN cobbection is already established.")
        host, port= address.split(":")
        print(f"Connecting to {host}:{port}...")
        try:
            self.reader, self.writer= await asyncio.open_connection(host, int(port))
            self.connected=True
            self.remote_address=address
            print(f"Connected to {host}:{port}.")
        except ConnectionRefusedError:
            raise exception(f"Connection to {host}:{port} refused.")
        except TimeoutError:
            raise exception(f"Connection to {host}:{port} timed out.")  


    async def send(self, message):
        if not self.connected:
            raise exception("LAN connection is not established.")
        data=message+"\n"
        self.writer.write(data.encode())
        await self.writer.drain()

    async def receive(self):
        if not self.connected:
            raise exception("LAN connection is not established.")
        data=await self.reader.readline()
        if not data:
            self.connected=False
            return None
        return data.decode("utf-8").strip()
    async def close(self):
        if self.connected:
            self.writer.close()
            await self.writer.wait_closed()
            self.connected=False
            print(f"Connection to {self.remote_address} closed.")

    def is_connected(self):
        return self.connected
    def get_remote_address(self):
        return self.remote_address
