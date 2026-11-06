import asyncio
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from network.server import SHACServer
from network.channel import Channel
from network.lan_transport import LANTransport
from security.admin_auth import AdminAuth
from bootstrap.bootstrap_generator import BootstrapGenerator


class SwarmBridge(QObject):
    """
    Bridge connecting the background asyncio SHACServer thread 
    with the PyQt6 main thread via Qt signals.
    """
    log_emitted = pyqtSignal(str, str)         # (level, message)
    state_updated = pyqtSignal(dict)           # state metadata dictionary
    node_requested = pyqtSignal(str, str)      # (node_id, address)
    task_response_received = pyqtSignal(dict)  # task result dict

    def __init__(self):
        super().__init__()
        self.server = None
        self.channel = None
        self.loop = None
        self.loop_thread = None
        self.admin_auth = AdminAuth()
        self.admin_token = None
        self.admin_authenticated = False
        self.server_running = False

        self.poll_timer = QTimer()
        self.poll_timer.setInterval(1000)
        self.poll_timer.timeout.connect(self._on_poll_timer)

    def _on_poll_timer(self):
        if self.server_running:
            self.emit_state()

    def authenticate_admin(self, token: str) -> bool:
        if not self.admin_auth.exists():
            created_token = self.admin_auth.create()
            self.admin_token = created_token
            self.admin_authenticated = True
            return True
        
        self.admin_token = token
        self.admin_authenticated = self.admin_auth.verify(token)
        return self.admin_authenticated

    def start_server(self, host: str, port: int, mode: str = "lan"):
        if self.server_running:
            return

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            listen_host = "0.0.0.0" if (host == "0.0.0.0" or not host) else host
            adv_host = LANTransport.get_lan_ip() if (host == "0.0.0.0" or not host) else host

            try:
                self.server = SHACServer(
                    host=listen_host,
                    port=port,
                    advertise_host=adv_host,
                    transport_type=mode,
                    admin_token=self.admin_token
                )
                self.server.on_state_change = self.emit_state
                self.server.on_chat_received = lambda sender, text: self.log_emitted.emit("CHAT", f"{sender}: {text}")
                self.server.on_task_response = lambda resp: self.task_response_received.emit(resp)
                if self.channel:
                    self.server.channels[self.channel.channel_id] = self.channel
                    self.server.active_channel_id = self.channel.channel_id

                self.loop.run_until_complete(self.server.start())
                self.server_running = True
                self.emit_state()
                self.log_emitted.emit("SUCCESS", f"SHAC Server listening on {listen_host}:{port} (Advertising {adv_host}:{port})")

                self.loop.run_forever()
            except Exception as e:
                self.server_running = False
                self.emit_state()
                self.log_emitted.emit("ERROR", f"Failed to start server on port {port}: {e}")

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        self.poll_timer.start()
        self.log_emitted.emit("INFO", f"SHAC Server starting on {host}:{port} ({mode.upper()})")

    def stop_server(self):
        if not self.server_running or not self.server or not self.loop:
            return

        self.poll_timer.stop()
        async def _shutdown():
            if hasattr(self.server, 'stop'):
                await self.server.stop()
            self.loop.stop()

        asyncio.run_coroutine_threadsafe(_shutdown(), self.loop)
        self.server_running = False
        self.emit_state()
        self.log_emitted.emit("INFO", "SHAC Server stopped successfully.")

    def create_channel(self, endpoint: str):
        if not self.admin_token:
            self.log_emitted.emit("ERROR", "Admin authentication token required to create channel.")
            return None
        
        parts = endpoint.split(":")
        host_part = parts[0] if len(parts) > 0 else "0.0.0.0"
        port_part = parts[1] if len(parts) > 1 else "8765"

        if host_part in ("0.0.0.0", "127.0.0.1", "localhost", ""):
            actual_ip = LANTransport.get_lan_ip()
            if actual_ip:
                host_part = actual_ip

        resolved_endpoint = f"{host_part}:{port_part}"

        self.channel = Channel.create(transport_type="auto", endpoint=resolved_endpoint)
        if self.server:
            self.server.channels[self.channel.channel_id] = self.channel
            self.server.active_channel_id = self.channel.channel_id

        generator = BootstrapGenerator(self.channel, "")
        bootstrap_cmd = generator.generate()
        self.emit_state()
        self.log_emitted.emit("SUCCESS", f"Created Channel {self.channel.channel_id} for LAN endpoint {resolved_endpoint}")
        return bootstrap_cmd

    def approve_node(self, request_id: str):
        if self.server and self.loop:
            asyncio.run_coroutine_threadsafe(self.server.approve_pending(request_id), self.loop)
            self.log_emitted.emit("SUCCESS", f"Approved join request {request_id}")

    def reject_node(self, request_id: str):
        if self.server and self.loop:
            asyncio.run_coroutine_threadsafe(self.server.reject_pending(request_id), self.loop)
            self.log_emitted.emit("WARNING", f"Rejected join request {request_id}")

    def send_task(self, target_node: str, action: str, params: dict):
        if not self.server or not self.loop or not self.channel:
            self.log_emitted.emit("ERROR", "Cannot dispatch task: Server or active channel is offline.")
            return

        target = None if target_node.lower() in ("all", "all nodes", "") else target_node
        asyncio.run_coroutine_threadsafe(
            self.server.send_task_from_master(
                self.channel.channel_id,
                self.channel.credential,
                target,
                action,
                params
            ),
            self.loop
        )
        self.log_emitted.emit("INFO", f"Dispatched task '{action}' ({params}) to target '{target_node}'")

    def send_chat(self, text: str):
        if self.server and self.loop:
            ch_id = self.channel.channel_id if self.channel else self.server.active_channel_id
            asyncio.run_coroutine_threadsafe(self.server.broadcast(ch_id, text), self.loop)
            self.log_emitted.emit("CHAT", f"Master: {text}")

    def emit_state(self):
        active_nodes = []
        pending_nodes = []
        if self.server:
            for session in getattr(self.server, 'sessions', []):
                if session.accepted:
                    peer = session.writer.get_extra_info('peername') if session.writer else ("127.0.0.1", 0)
                    addr_str = f"{peer[0]}:{peer[1]}" if peer else "N/A"
                    active_nodes.append({
                        "id": session.node_id or "NODE",
                        "addr": addr_str,
                        "status": "Accepted"
                    })

            for req_id, req in getattr(self.server, 'pending', {}).items():
                pending_nodes.append({
                    "id": req_id,
                    "addr": f"{req.get('node_name', 'Node')} ({req.get('channel_id', '')})",
                    "status": "Pending"
                })

        state = {
            "server_running": self.server_running,
            "host": self.server.host if self.server else "",
            "port": self.server.port if self.server else 8765,
            "channel_id": self.channel.channel_id if self.channel else "None",
            "active_nodes": active_nodes,
            "pending_nodes": pending_nodes,
            "admin_authenticated": self.admin_authenticated
        }
        self.state_updated.emit(state)
