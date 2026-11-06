import asyncio
import secrets
import sys
import time
import uuid
import hashlib
from pathlib import Path

from network.channel import Channel
from network.protocol import decode_message, encode_message, make_message, reply


class ServerSession:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.node_id = None
        self.node_name = None
        self.channel_id = None
        self.accepted = False
        self.write_lock = asyncio.Lock()
        self.last_seen = time.monotonic()

    async def send(self, message):
        async with self.write_lock:
            self.writer.write(encode_message(message))
            await self.writer.drain()

    async def close(self):
        if not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()


class SHACServer:
    """In-memory rendezvous and relay server for the networking milestone."""

    def __init__(self, host="127.0.0.1", port=8765, advertise_host=None,
                 log_path="shac.log", transport_type="lan", admin_token=None):
        self.host = host
        self.port = port
        self.advertise_host = advertise_host or host
        self.transport_type = transport_type
        self.admin_token_digest = self._digest(admin_token) if admin_token else None
        self.server = None
        self.channels = {}
        self.sessions = set()
        self.pending = {}
        self.request_ttl = 300
        self.active_channel_id = None
        self.log_path = Path(log_path)
        self.audit_log = []
        self.heartbeat_interval = 15
        self.heartbeat_timeout = 45
        self._heartbeat_task = None
        self.on_state_change = None
        self.on_chat_received = None
        self.on_task_response = None
        self.state_file = Path(".shac-channels.json")
        self.approved_nodes = set()
        self._load_persistent_channels()

    def _load_persistent_channels(self):
        if not self.state_file.exists():
            return
        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for ch_data in data.get("channels", []):
                    ch = Channel(
                        channel_id=ch_data["channel_id"],
                        credential=ch_data["credential"],
                        transport_type=ch_data.get("transport_type", "lan"),
                        endpoint=ch_data.get("endpoint")
                    )
                    self.channels[ch.channel_id] = ch
                    self.active_channel_id = ch.channel_id
                self.approved_nodes = set(tuple(x) for x in data.get("approved_nodes", []))
        except Exception:
            pass

    def _save_persistent_channels(self):
        try:
            channels_list = [
                {
                    "channel_id": ch.channel_id,
                    "credential": ch.credential,
                    "transport_type": ch.transport_type,
                    "endpoint": ch.endpoint
                }
                for ch in self.channels.values()
            ]
            with self.state_file.open("w", encoding="utf-8") as f:
                json.dump({
                    "channels": channels_list,
                    "approved_nodes": list(self.approved_nodes)
                }, f, indent=2)
        except Exception:
            pass

    def _notify_state_change(self):
        if callable(self.on_state_change):
            try:
                self.on_state_change()
            except Exception:
                pass

    def _record(self, event, **details):
        entry = {"time": time.time(), "event": event, **details}
        self.audit_log.append(entry)
        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{entry}\n")

    @staticmethod
    def _paint(text, color):
        if not sys.stdout.isatty():
            return text
        return f"\033[{color}m{text}\033[0m"

    @classmethod
    def _log(cls, text, color="94"):
        print(cls._paint(text, color), flush=True)

    @staticmethod
    def _digest(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def start(self):
        import socket
        bind_host = self.host if (self.host and self.host != "0.0.0.0") else "0.0.0.0"
        self.server = await asyncio.start_server(
            self.handle_client, 
            host=bind_host, 
            port=self.port,
            family=socket.AF_INET,
            reuse_address=True
        )
        self.port = self.server.sockets[0].getsockname()[1]
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def serve_forever(self):
        if self.server is None:
            await self.start()
        async with self.server:
            await self.server.serve_forever()

    async def run_master_console(self):
        """Keep one console for approvals and chat across all connected nodes."""
        monitor = asyncio.create_task(self._monitor_requests())
        console = asyncio.create_task(self._console_loop())
        try:
            await asyncio.gather(self.serve_forever(), console)
        finally:
            monitor.cancel()
            console.cancel()

    async def _console_loop(self):
        self._log("[CHAT] Type a message to broadcast, /help for commands, or /quit.", "96")
        while True:
            text = await asyncio.to_thread(input, "master> ")
            command = text.strip()
            if command == "/quit":
                await self.stop()
                return
            if command == "/help":
                self._log("[CHAT] y/yes, n/no, /allow, /reject, /nodes, /use <channel_id>, /quit", "96")
                continue
            if command in {"y", "yes", "/allow"}:
                request_id = self._next_pending_request()
                if request_id:
                    await self.approve_pending(request_id)
                else:
                    self._log("[REQUEST] No pending requests.", "93")
                continue
            if command in {"n", "no", "/reject"}:
                request_id = self._next_pending_request()
                if request_id:
                    await self.reject_pending(request_id)
                else:
                    self._log("[REQUEST] No pending requests.", "93")
                continue
            if command == "/nodes":
                nodes = [
                    f"{peer.node_id} ({peer.channel_id})"
                    for peer in self.sessions
                    if peer.accepted
                ]
                self._log("[NODES] " + (", ".join(nodes) or "none"), "96")
                continue
            if command.startswith("/use "):
                self.active_channel_id = command[5:].strip()
                self._log(f"[CHAT] Active channel: {self.active_channel_id}", "96")
                continue
            if command:
                await self.broadcast(self.active_channel_id, command)

    def _next_pending_request(self):
        self._expire_requests()
        for request_id, request in self.pending.items():
            if request["session"] is not None:
                return request_id
        return None

    async def _monitor_requests(self):
        seen = set()
        while True:
            await asyncio.sleep(0.25)
            for request_id, request in list(self.pending.items()):
                if request_id in seen:
                    continue
                seen.add(request_id)
                self._log(
                    f"\n[REQUEST] {request['node_name']} wants to join "
                    f"{request['channel_id']} ({request_id})", "93",
                )
                self._log(
                    "[REQUEST] Type /allow or /reject in the master console "
                    "or type y/n (oldest pending request is selected).", "93",
                )

    async def approve_pending(self, request_id):
        request = self.pending.pop(request_id, None)
        if request is None:
            return False
        request_session = request["session"]
        if request_session is None:
            self._log(f"[REQUEST] {request_id} cannot be approved; node disconnected.", "91")
            return False
        request_session.accepted = True
        self.active_channel_id = request["channel_id"]
        self.approved_nodes.add((request["channel_id"], request["node_name"]))
        self._save_persistent_channels()
        await request_session.send(make_message("join_accepted", {
            "node_id": request["node_id"],
            "channel_id": request["channel_id"],
        }))
        self._log(
            f"[CHANNEL] {request['node_name']} connected to {request['channel_id']}",
            "92",
        )
        self._notify_state_change()
        return True

    async def reject_pending(self, request_id):
        request = self.pending.pop(request_id, None)
        if request is None:
            return False
        if request["session"] is not None:
            await request["session"].send(make_message(
                "join_rejected",
                {"error": "Request rejected by master."},
            ))
        self._log(f"[CHANNEL] Join rejected: {request['node_name']}", "91")
        self._notify_state_change()
        return True

    async def broadcast(self, channel_id, text):
        recipients = [
            peer for peer in self.sessions
            if peer.accepted and (channel_id is None or peer.channel_id == channel_id)
        ]
        for peer in recipients:
            await peer.send(make_message("message", {
                "from": "master",
                "text": text,
            }))
        self._log(f"[CHAT] delivered to {len(recipients)} node(s)", "92")

    async def stop(self):
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
        for session in list(self.sessions):
            await session.close()
        self.sessions.clear()

    async def handle_client(self, reader, writer):
        session = ServerSession(reader, writer)
        self.sessions.add(session)
        address = writer.get_extra_info("peername")
        print(f"[SERVER] Connection accepted from {address}", flush=True)
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    message = decode_message(line)
                    session.last_seen = time.monotonic()
                    print(
                        f"[SERVER] {address} -> {message['type']}",
                        flush=True,
                    )
                    await self.handle_message(session, message)
                except ValueError as error:
                    print(f"[SERVER] Invalid message from {address}: {error}", flush=True)
                    await session.send(make_message("error", {"error": str(error)}))
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as error:
            print(f"[SERVER] Peer disconnected: {address} ({error})", flush=True)
        finally:
            await self.remove_session(session)
            print(f"[SERVER] Connection closed: {address}", flush=True)

    async def handle_message(self, session, message):
        handlers = {
            "create_channel": self.create_channel,
            "join_request": self.join_request,
            "list_requests": self.list_requests,
            "accept_request": self.accept_request,
            "reject_request": self.reject_request,
            "send_message": self.send_message,
            "task_request": self.task_request,
            "task_response": self.task_response,
            "ping": self.ping,
            "pong": self.pong,
        }
        handler = handlers.get(message["type"])
        if handler is None:
            await session.send(reply(message, "error", {"error": "Unknown message type."}))
            return
        await handler(session, message)

    async def create_channel(self, session, message):
        admin_token = message["payload"].get("admin_token")
        if self.admin_token_digest and self._digest(admin_token or "") != self.admin_token_digest:
            await session.send(reply(message, "error", {"error": "Master authentication required."}))
            return
        channel = Channel.create(
            transport_type=self.transport_type,
            endpoint=f"{self.advertise_host}:{self.port}",
        )
        self.channels[channel.channel_id] = channel
        self.active_channel_id = channel.channel_id
        self._save_persistent_channels()
        print(f"[SERVER] Channel created: {channel.channel_id}", flush=True)
        await session.send(reply(message, "channel_created", {
            "channel_id": channel.channel_id,
            "credential": channel.credential,
            "transport": channel.transport_type,
            "endpoint": channel.endpoint,
        }))

    async def join_request(self, session, message):
        payload = message["payload"]
        channel = self.channels.get(payload.get("channel_id"))
        if channel is None or not channel.is_active() or channel.credential != payload.get("credential"):
            print(
                f"[SERVER] Rejected invalid join for {payload.get('channel_id')}",
                flush=True,
            )
            await session.send(reply(message, "join_rejected", {"error": "Invalid or inactive channel."}))
            return
        request_id = uuid.uuid4().hex
        node_id = f"node-{secrets.token_hex(4)}"
        node_name = payload.get("node_name") or "node"
        session.node_id = node_id
        session.node_name = node_name
        session.channel_id = channel.channel_id

        # Auto-accept if previously approved by master
        if (channel.channel_id, node_name) in self.approved_nodes:
            session.accepted = True
            await session.send(make_message("join_accepted", {
                "node_id": node_id,
                "channel_id": channel.channel_id,
            }))
            self._log(
                f"[CHANNEL] Auto-reconnected approved node: {node_name} ({node_id}) to {channel.channel_id}",
                "92",
            )
            self._notify_state_change()
            return

        self.pending[request_id] = {
            "session": session,
            "node_id": node_id,
            "node_name": node_name,
            "channel_id": channel.channel_id,
            "created_at": time.time(),
        }
        print(
            f"[SERVER] Join request pending: {request_id} "
            f"node={node_id} name={payload.get('node_name') or 'node'} "
            f"channel={channel.channel_id}",
            flush=True,
        )
        await session.send(reply(message, "join_pending", {
            "request_id": request_id,
            "node_id": node_id,
            "status": "pending",
        }))
        self._notify_state_change()

    async def list_requests(self, session, message):
        self._expire_requests()
        channel_id = message["payload"].get("channel_id")
        requests = [
            {
                key: value
                for key, value in request.items()
                if key not in {"session", "created_at"}
            }
            | {
                "request_id": request_id,
                "connected": request["session"] is not None,
            }
            for request_id, request in self.pending.items()
            if not channel_id or request["channel_id"] == channel_id
        ]
        await session.send(reply(message, "requests", {"requests": requests}))

    async def accept_request(self, session, message):
        self._expire_requests()
        request_id = message["payload"].get("request_id")
        channel_id = message["payload"].get("channel_id")
        credential = message["payload"].get("credential")
        channel = self.channels.get(channel_id)
        if channel is None or channel.credential != credential:
            await session.send(reply(message, "error", {"error": "Master channel credential is invalid."}))
            return
        request = self.pending.pop(request_id, None)
        if request is None:
            print(f"[SERVER] Accept failed; pending request IDs: {list(self.pending)}", flush=True)
            await session.send(reply(message, "error", {"error": "Join request not found or expired."}))
            return
        request_session = request["session"]
        if request_session is None:
            await session.send(reply(message, "error", {
                "error": "The node disconnected. Ask the friend to paste the bootstrap command again.",
            }))
            return
        request_session.accepted = True
        print(
            f"[SERVER] Join accepted: {request_id} node={request['node_id']} "
            f"channel={request['channel_id']}",
            flush=True,
        )
        public_request = {key: value for key, value in request.items() if key != "session"}
        await request_session.send(make_message("join_accepted", public_request))
        await session.send(reply(message, "request_accepted", public_request))

    async def reject_request(self, session, message):
        self._expire_requests()
        request_id = message["payload"].get("request_id")
        channel_id = message["payload"].get("channel_id")
        credential = message["payload"].get("credential")
        channel = self.channels.get(channel_id)
        if channel is None or channel.credential != credential:
            await session.send(reply(message, "error", {"error": "Master channel credential is invalid."}))
            return
        request = self.pending.pop(request_id, None)
        if request is None:
            await session.send(reply(message, "error", {"error": "Join request not found or expired."}))
            return
        await request["session"].send(make_message("join_rejected", {"error": "Request rejected by master."}))
        print(
            f"[SERVER] Join rejected: {request_id} node={request['node_id']} "
            f"channel={request['channel_id']}",
            flush=True,
        )
        public_request = {key: value for key, value in request.items() if key != "session"}
        await session.send(reply(message, "request_rejected", public_request))

    async def send_message(self, session, message):
        payload = message["payload"]
        if session.accepted:
            self._record(
                "message_received",
                node_id=session.node_id,
                channel_id=session.channel_id,
                text=payload.get("text", ""),
            )
            print(
                f"[CHAT] {session.node_id}: {payload.get('text', '')}",
                flush=True,
            )
            if callable(self.on_chat_received):
                try:
                    sender = session.node_name or session.node_id or "node"
                    self.on_chat_received(sender, payload.get("text", ""))
                except Exception:
                    pass
        channel = self.channels.get(payload.get("channel_id"))
        is_master = channel is not None and channel.credential == payload.get("credential")
        if not session.accepted and not is_master:
            await session.send(reply(message, "error", {"error": "Node is not accepted."}))
            return
        recipients = [
            peer for peer in self.sessions
            if peer.accepted and (session.channel_id is None or peer.channel_id == session.channel_id)
            and peer.channel_id == payload.get("channel_id")
            and (not payload.get("target") or peer.node_id == payload["target"])
        ]
        outbound = make_message("message", {"from": session.node_id or "master", "text": payload.get("text", "")})
        for peer in recipients:
            await peer.send(outbound)
        await session.send(reply(message, "message_sent", {"recipients": len(recipients)}))

    async def task_request(self, session, message):
        payload = message["payload"]
        channel = self.channels.get(payload.get("channel_id"))
        is_master = channel is not None and channel.credential == payload.get("credential")
        if not is_master:
            await session.send(reply(message, "error", {"error": "Master credential is invalid."}))
            return
        target = payload.get("target")
        recipients = [
            peer for peer in self.sessions
            if peer.accepted and peer.channel_id == payload.get("channel_id")
            and (not target or peer.node_id == target)
        ]
        task_id = uuid.uuid4().hex
        task = make_message("task_request", {
            "task_id": task_id,
            "action": payload.get("action", "unknown"),
            "arguments": payload.get("arguments", {}),
            "from": "master",
        })
        for peer in recipients:
            await peer.send(task)
        self._record("task_requested", task_id=task_id, channel_id=payload.get("channel_id"),
                     target=target, action=payload.get("action"), recipients=len(recipients))
        await session.send(reply(message, "task_sent", {
            "task_id": task_id,
            "recipients": len(recipients),
        }))

    async def send_task_from_master(self, channel_id, credential, target, action, arguments):
        """Send a task from a trusted local GUI without opening a second network client."""
        request = make_message("task_request", {
            "channel_id": channel_id,
            "credential": credential,
            "target": target,
            "action": action,
            "arguments": arguments,
        })
        class MasterSession:
            async def send(self, _message):
                return None
        await self.task_request(MasterSession(), request)
        return request["request_id"]

    async def task_response(self, session, message):
        if not session.accepted:
            await session.send(reply(message, "error", {"error": "Node is not accepted."}))
            return
        payload = message["payload"]
        self._record("task_response", task_id=payload.get("task_id"), node_id=session.node_id,
                     node_name=session.node_name, status=payload.get("status"),
                     result=payload.get("result"), action=payload.get("action"))
        self._log(
            f"[TASK] {session.node_id} -> {payload.get('task_id')} "
            f"{payload.get('status')}",
            "92" if payload.get("status") == "accepted" else "91",
        )
        if callable(self.on_task_response):
            try:
                self.on_task_response({
                    "task_id": payload.get("task_id"),
                    "node_id": session.node_id,
                    "node_name": session.node_name,
                    "status": payload.get("status"),
                    "result": payload.get("result", ""),
                    "action": payload.get("action", "")
                })
            except Exception:
                pass

    async def ping(self, session, message):
        await session.send(reply(message, "pong"))

    async def pong(self, session, message):
        session.last_seen = time.monotonic()

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            now = time.monotonic()
            for session in list(self.sessions):
                if now - session.last_seen > self.heartbeat_timeout:
                    self._record(
                        "heartbeat_timeout",
                        node_id=session.node_id,
                        channel_id=session.channel_id,
                    )
                    self._log(
                        f"[HEARTBEAT] disconnected {session.node_id or 'unregistered'}",
                        "91",
                    )
                    await session.close()
                    continue
                try:
                    await session.send(make_message("ping"))
                except (ConnectionResetError, BrokenPipeError, OSError):
                    await session.close()

    async def remove_session(self, session):
        self.sessions.discard(session)
        for request_id, request in self.pending.items():
            if request["session"] is session:
                request["session"] = None
                print(
                    f"[SERVER] Pending request retained after disconnect: {request_id}",
                    flush=True,
                )

    def _expire_requests(self):
        now = time.time()
        for request_id, request in list(self.pending.items()):
            if now - request["created_at"] > self.request_ttl:
                del self.pending[request_id]
                print(f"[SERVER] Join request expired: {request_id}", flush=True)