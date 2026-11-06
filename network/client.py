import json

from network.protocol import decode_message, encode_message, make_message


class SHACClient:
    def __init__(self, endpoint):
        self.host, port = endpoint.rsplit(":", 1)
        self.port = int(port)
        self.reader = None
        self.writer = None

    async def connect(self):
        import asyncio
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

    async def close(self):
        if self.writer is not None and not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()

    async def request(self, message_type, payload=None):
        request = make_message(message_type, payload)
        self.writer.write(encode_message(request))
        await self.writer.drain()
        while True:
            response = decode_message(await self.reader.readline())
            if response.get("request_id") == request["request_id"]:
                return response

    async def create_channel(self, admin_token=None):
        response = await self.request("create_channel", {"admin_token": admin_token})
        if response["type"] == "error":
            raise ValueError(response["payload"].get("error", "Channel creation failed."))
        return response["payload"]

    async def join(self, invitation, node_name):
        return await self.request("join_request", {
            "channel_id": invitation["channel_id"],
            "credential": invitation["credential"],
            "node_name": node_name,
        })

    async def listen(self):
        while True:
            line = await self.reader.readline()
            if not line:
                return
            yield decode_message(line)


def parse_invitation(value):
    if value.startswith("SWARM1."):
        from network.channel import Channel
        return Channel.parse_connection_string(value)
    return json.loads(value)