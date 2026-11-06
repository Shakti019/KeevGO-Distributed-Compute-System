class Connection:
    def __init__ (self, transport, connection_id=None):
        self.transport = transport
        self.connection_id = connection_id
        self.node_id=None
        self.channel_id=None
        self.session_id=None
        self.connected=False
        self.autheticated=False
        self.authrized=False

    async def connect(self,address):
        await self.transport.connect(address)
        self.connected=True

    async def send(self,message):
        if not self.connected:
            raise Exception("Connection is not established.")
        self.transport.send(message)

    async def receive(self):
        if not self.connected:
            raise Exception("Connection is not established.")
        return await self.transport.receive()

    def close(self):
        if self.connected:
            self.transport.close()
            self.connected=False

    def __str__ (self):
        return f"Connection(id={self.connection_id}, node_id={self.node_id}, channel_id={self.channel_id}, session_id={self.session_id}, connected={self.connected}, authenticated={self.autheticated}, authorized={self.authrized})"
    