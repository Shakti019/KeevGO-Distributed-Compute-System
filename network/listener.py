import asyncio
class Listener:
    def __init__ (self, host="0.0.0.0", port=8765):
        self.host=host
        self.port=port
        self.server=None
        self.running=False
        self.connection_handler= None

    def set_connection_handler(self, handler):
        self.connection_handler=handler
    async def start(self):
        if self.running:
            raise Exception("Listener is already running.")
        if self.connection_handler is None:
            raise Exception("Connection handler is not set.")
        self.server=await asyncio.start_server(self.handle_connection, self.host, self.port)
        self.running=True
        print(f"Listener started on {self.host}:{self.port}.")

    async def handle_connection(self, reader, writer):
        address=writer.get_extra_info("peername")
        print(f"Accepted connection from {address}.")
        try:
            await self.connection_handler(reader, writer)
        except Exception as e:
            print(f"Error handling connection from {address}: {e}")
            writer.close()
            try:
                await writer.wait_closed()
            except Exception as e:
                print(f"Error closing connection from {address}: {e}")
    async def stop(self):
        if not self.running:
            return
        print("Stopping listener...")
        self.running=False
        await asyncio.sleep(0.1)  # Allow time for the server to close

        if self.server:
            self.server.close()
            await self.server.wait_closed()
        print("Listener stopped.")

    def is_running(self):
        return self.running
    def get_address(self):
        return f"{self.host}:{self.port}"
            