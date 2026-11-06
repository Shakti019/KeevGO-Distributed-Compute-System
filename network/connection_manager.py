from network.connection import Connection

class ConnectionManager:
    def __init__ (self):
        self.connections={}
        self.transport={}
    def register_transport(self, name, transport):
        self.transport[name]=transport
        print(f"Transport {name} registered.")

    async def connect(self, transport_name, address, connection_id=None):
        if transport_name not in self.transport:
            raise Exception(f"Transport {transport_name} is not registered.")
        transport=self.transport[transport_name]
        connection=Connection(transport, connection_id)
        await connection.connect(address)
        self.connections[connection_id]=connection
        print(f"Connection {connection_id} established using transport {transport_name}.")
        return connection

    async def send(self, node_id,message):
        if node_id not in self.connections:
            raise Exception(f"Connection {node_id} does not exist.")
        connection=self.connections[node_id]
        await connection.send(message)
        print(f"Message sent to connection {node_id}.")
        return await connection.receive()

    async def receive(self, node_id):
        if node_id not in self.connections:
            raise Exception(f"Connection {node_id} does not exist.")
        connection=self.connections[node_id]
        return await connection.receive()

    async def disconnect(self, node_id):
        if node_id not in self.connections:
            raise Exception(f"Connection {node_id} does not exist.")
        connection=self.connections[node_id]
        connection.close()
        del self.connections[node_id]
        print(f"Connection {node_id} closed and removed.")

    async def get_connection(self, node_id):
        if node_id not in self.connections:
            raise Exception(f"Connection {node_id} does not exist.")
        return self.connections[node_id]

    async def is_connected(self, node_id):
        if node_id not in self.connections:
            return False
        connection=self.connections[node_id]
        return connection.connected


    async def list_connections(self):
        return list(self.connections.keys())