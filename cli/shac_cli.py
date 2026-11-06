import sys
import asyncio
import socket
import os
import getpass

from network.channel_manager import ChannelManager
from network.channel import Channel
from cli.channel_commands import ChannelCommands
from network.client import SHACClient, parse_invitation
from network.server import SHACServer
from bootstrap.bootstrap_generator import BootstrapGenerator
from cli.theme import banner, error, info, success
from security.admin_auth import AdminAuth


class SHACCLI:

    def __init__(self):

        self.name = "shac"
        self.version = "0.1.0"

        # Core managers
        self.channel_manager = ChannelManager()

        # Command handlers
        self.channel_commands = ChannelCommands(
            self.channel_manager
        )

        self.commands = {
            "help": self.show_help,
            "h": self.show_help,
            "version": self.show_version,
            "channel": self.handle_channel,
            "c": self.handle_channel,
            "server": self.handle_server,
            "s": self.handle_server,
            "request": self.handle_request,
            "r": self.handle_request,
            "node": self.handle_node,
            "n": self.handle_node,
            "message": self.handle_message,
            "m": self.handle_message,
            "task": self.handle_task,
            "t": self.handle_task,
        }

    def run(self, arguments=None):

        if arguments is None:
            arguments = sys.argv[1:]

        if not arguments:
            self.show_help()
            return

        command = arguments[0]
        command_arguments = arguments[1:]

        handler = self.commands.get(command)

        if handler is None:

            print()
            print(
                f"shac: unknown command '{command}'"
            )
            print(
                "Run 'shac help' for available commands."
            )
            print()

            return

        handler(command_arguments)

    # --------------------------------------------------
    # CHANNEL
    # --------------------------------------------------

    def handle_channel(self, arguments):

        if not arguments:

            print()
            print(
                "Usage: shac channel <command>"
            )
            print()

            print("Commands:")
            print("  create")
            print("  list")
            print("  show <channel_id>")
            print("  revoke <channel_id>")
            print()

            return

        command = arguments[0]
        command_arguments = arguments[1:]

        handlers = {
            "create": self.create_channel,
            "list": self.channel_commands.list,
            "show": self.channel_commands.show,
            "revoke": self.channel_commands.revoke,
        }

        handler = handlers.get(command)

        if handler is None:

            print()
            print(
                f"shac: unknown channel command "
                f"'{command}'"
            )
            print()

            return

        handler(command_arguments)

    def create_channel(self, arguments):
        if len(arguments) != 1:
            print("Usage: shac channel create <server_endpoint>")
            return
        try:
            auth = AdminAuth()
            token = getpass.getpass("SHAC master token: ") if auth.exists() else None
            if auth.exists() and not auth.verify(token):
                error("Invalid SHAC master token.")
                return
            data = asyncio.run(self._create_remote_channel(arguments[0], token))
            channel = Channel(
                channel_id=data["channel_id"],
                credential=data["credential"],
                transport_type=data["transport"],
                endpoint=data["endpoint"],
            )
            banner("SHAC CHANNEL CREATED")
            success(f"Channel ID: {channel.channel_id}")
            info(f"Server: {channel.endpoint}")
            print(f"Master credential: {channel.credential}")
            print()
            bootstrap_command = BootstrapGenerator(channel, "").generate()
            print("Share this bootstrap command with your friend:")
            print(bootstrap_command)
            print()
            info("The friend only needs Python installed; no SHAC codebase is required.")
            print()
            print("After the friend pastes the command, run:")
            print(f"python -m cli.shac_cli request list {channel.endpoint} {channel.channel_id}")
            print("Then accept using the displayed request_id:")
            print(
                f"python -m cli.shac_cli request accept {channel.endpoint} "
                f"{channel.channel_id} {channel.credential} <request_id>"
            )
        except (OSError, ValueError, KeyError) as exception:
            error(str(exception))

    async def _create_remote_channel(self, endpoint, admin_token=None):
        client = SHACClient(endpoint)
        await client.connect()
        try:
            return await client.create_channel(admin_token)
        finally:
            await client.close()

    def handle_server(self, arguments):
        if not arguments or arguments[0] not in {"start", "s"}:
            print("Usage: shac server start [host] [port] [advertise_host]")
            print("       shac server start --lan [port] [lan_ip]")
            print("       shac server start --internet [port] [public_host]")
            return
        if len(arguments) > 1 and arguments[1] == "--lan":
            host = "0.0.0.0"
            port = int(arguments[2]) if len(arguments) > 2 else 8765
            advertise_host = arguments[3] if len(arguments) > 3 else self._detect_lan_ip()
            transport_type = "lan"
        elif len(arguments) > 1 and arguments[1] == "--internet":
            host = "0.0.0.0"
            port = int(arguments[2]) if len(arguments) > 2 else 8765
            if len(arguments) < 4:
                error("Internet mode requires a public IP or DNS host to advertise.")
                print("Usage: python -m cli.shac s start --internet 8765 public.example.com")
                return
            advertise_host = arguments[3]
            transport_type = "internet"
        else:
            host = arguments[1] if len(arguments) > 1 else "127.0.0.1"
            port = int(arguments[2]) if len(arguments) > 2 else 8765
            advertise_host = arguments[3] if len(arguments) > 3 else host
            transport_type = "lan"
        try:
            auth = AdminAuth()
            if not auth.exists():
                token = auth.create()
                banner("SHAC MASTER TOKEN CREATED")
                success("Save this token. It protects the owner controls.")
                print(token)
                print()
            else:
                token = getpass.getpass("SHAC master token: ")
                if not auth.verify(token):
                    error("Invalid SHAC master token.")
                    return
            asyncio.run(self._run_server(host, port, advertise_host, transport_type, token))
        except KeyboardInterrupt:
            info("Server stopped.")
        except OSError as exception:
            if getattr(exception, "winerror", None) == 10048 or getattr(exception, "errno", None) == 10048:
                error(f"Port {port} is already in use.")
                info("Press Ctrl+C in the existing SHAC server terminal, or start another port:")
                print(f"python -m cli.shac_cli s start --lan {port + 1} {advertise_host}")
            else:
                error(str(exception))

    @staticmethod
    def _detect_lan_ip():
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
        except OSError:
            return socket.gethostbyname(socket.gethostname())
        finally:
            probe.close()

    async def _run_server(self, host, port, advertise_host, transport_type="lan", admin_token=None):
        server = SHACServer(
            host,
            port,
            advertise_host,
            transport_type=transport_type,
            admin_token=admin_token,
        )
        await server.start()
        banner("SHAC NETWORK SERVER")
        success(f"Listening on {host}:{server.port}")
        info(f"Invitations will use: {advertise_host}:{server.port}")
        if transport_type == "internet":
            info("Internet mode uses raw TCP. Forward this port to the server or run on a public host.")
            info("TLS is required before exposing this endpoint to untrusted networks.")
        info("Use /allow or /reject for the oldest pending friend request.")
        info("Type messages to broadcast to all accepted friends.")
        await server.run_master_console()

    def handle_request(self, arguments):
        if not arguments or arguments[0] not in {"list", "accept", "reject", "l", "a", "x"}:
            print("Usage: shac request list <endpoint> <channel_id>")
            print("       shac request accept <endpoint> <channel_id> <credential> <request_id>")
            print("       shac request reject <endpoint> <channel_id> <credential> <request_id>")
            return
        command = {"l": "list", "a": "accept", "x": "reject"}.get(arguments[0], arguments[0])
        try:
            if command == "list":
                endpoint, channel_id = arguments[1:3]
                result = asyncio.run(self._request(endpoint, "list_requests", {"channel_id": channel_id}))
                for item in result["payload"]["requests"]:
                    state = "connected" if item.get("connected") else "disconnected"
                    info(
                        f"{item['request_id']}  {item['node_name']}  "
                        f"{item['node_id']}  [{state}]"
                    )
                if not result["payload"]["requests"]:
                    info("No pending requests.")
                return
            endpoint, channel_id, credential, request_id = arguments[1:5]
            result = asyncio.run(self._request(endpoint, f"{command}_request", {
                "channel_id": channel_id,
                "credential": credential,
                "request_id": request_id,
            }))
            if result["type"] == "error":
                error(result["payload"]["error"])
            else:
                success(f"Request {request_id} {command}ed.")
        except (IndexError, ValueError, OSError) as exception:
            error(str(exception))

    def handle_node(self, arguments):
        if not arguments or arguments[0] not in {"join", "j"} or len(arguments) < 3:
            print("Usage: shac node join <endpoint> <invitation> [node_name]")
            return
        endpoint, invitation_value = arguments[1:3]
        node_name = arguments[3] if len(arguments) > 3 else "friend"
        try:
            asyncio.run(self._run_node(endpoint, invitation_value, node_name))
        except (ValueError, OSError) as exception:
            error(str(exception))

    async def _run_node(self, endpoint, invitation_value, node_name):
        client = SHACClient(endpoint)
        await client.connect()
        invitation = parse_invitation(invitation_value)
        response = await client.join(invitation, node_name)
        if response["type"] != "join_pending":
            error(response["payload"].get("error", "Join failed."))
            await client.close()
            return
        banner("SHAC JOIN REQUEST")
        info(f"Request ID: {response['payload']['request_id']}")
        info("Waiting for the master to accept or reject this request...")
        async for event in client.listen():
            if event["type"] == "join_accepted":
                success("Join accepted. Communication channel is active.")
            elif event["type"] == "join_rejected":
                error(event["payload"].get("error", "Join rejected."))
                break
            elif event["type"] == "message":
                info(f"{event['payload']['from']}: {event['payload']['text']}")

    def handle_message(self, arguments):
        if not arguments or arguments[0] not in {"send", "s"} or len(arguments) < 5:
            print("Usage: shac message send <endpoint> <channel_id> <credential> <text>")
            return
        endpoint, channel_id, credential = arguments[1:4]
        text = " ".join(arguments[4:])
        result = asyncio.run(self._request(endpoint, "send_message", {
            "channel_id": channel_id,
            "credential": credential,
            "text": text,
        }))
        if result["type"] == "error":
            error(result["payload"]["error"])
        else:
            success(f"Message sent to {result['payload']['recipients']} active node(s).")

    def handle_task(self, arguments):
        if len(arguments) < 6 or arguments[0] not in {"send", "s"}:
            print("Usage: shac t send <endpoint> <channel_id> <credential> <node_id|all> <action> [json_arguments]")
            print("Example: shac t send ... all browser.search {\"query\":\"Python networking\"}")
            return
        endpoint, channel_id, credential, target, action = arguments[1:6]
        import json
        try:
            task_arguments = json.loads(" ".join(arguments[6:])) if len(arguments) > 6 else {}
            result = asyncio.run(self._request(endpoint, "task_request", {
                "channel_id": channel_id,
                "credential": credential,
                "target": None if target == "all" else target,
                "action": action,
                "arguments": task_arguments,
            }))
            if result["type"] == "error":
                error(result["payload"]["error"])
            else:
                success(f"Task {result['payload']['task_id']} sent to {result['payload']['recipients']} node(s).")
        except (ValueError, OSError) as exception:
            error(str(exception))

    async def _request(self, endpoint, message_type, payload):
        client = SHACClient(endpoint)
        await client.connect()
        try:
            return await client.request(message_type, payload)
        finally:
            await client.close()

    # --------------------------------------------------
    # HELP
    # --------------------------------------------------

    def show_help(self, arguments=None):

        banner("SHAC NETWORKING")
        print("Shared Hybrid Agent Computing")
        print()

        print("Usage:")
        print("  shac <command>")
        print(f"  path: {os.getcwd()}")
        print()

        print("Commands:")
        print()

        print("  channel")
        print("      Manage local channels.")
        print()

        print("  s start --lan [port] [lan_ip]")
        print("      Start a server reachable by devices on the same Wi-Fi/LAN.")
        print()

        print("  s start --internet [port] [public_host]")
        print("      Start the raw TCP Internet endpoint and advertise its public host.")
        print()

        print("  c create <server_endpoint>")
        print("      Create a channel and print a paste-ready friend command.")
        print()

        print("  n j <endpoint> <invitation> [name]")
        print("      Paste an invitation and request channel access.")
        print()

        print("  r list|accept|reject")
        print("      Manual request control; server console now uses /allow or /reject.")
        print()

        print("  m s <endpoint> <channel_id> <credential> <text>")
        print("      Send a message to accepted nodes.")
        print()

        print("  t send <endpoint> <channel_id> <credential> <node_id|all> <action> [json]")
        print("      Send a consented task request; the node must approve it.")
        print()

        print("LAN test sequence:")
        print("  1. Device A: shac server start --lan 8765 <DEVICE_A_LAN_IP>")
        print("  2. Device A: shac channel create <DEVICE_A_LAN_IP>:8765")
        print("  3. Device B: paste the printed standalone 'python -c ...' command.")
        print("  4. Device A: shac request list <endpoint> <channel_id>")
        print("  5. Device A: shac request accept <endpoint> <channel_id> <credential> <request_id>")
        print("  6. Device A: shac message send <endpoint> <channel_id> <credential> hello")

        print("  help")
        print("      Show this help message.")
        print()

        print("  version")
        print("      Show SHAC version.")
        print()

    # --------------------------------------------------
    # VERSION
    # --------------------------------------------------

    def show_version(self, arguments=None):

        print(
            f"SHAC version {self.version}"
        )


def main():

    cli = SHACCLI()
    cli.run()


if __name__ == "__main__":
    main()