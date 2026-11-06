SHAC
====

SHAC now has two interfaces over the same networking core:

- Desktop UI: dark, resizable Tkinter control panel.
- Terminal CLI: short commands, colored status output, server logs, and chat.

## SHAC owner security

The first SHAC launch creates a local owner token in `.shac-master-token`. The token is stored as a SHA-256 digest and is required for owner-side server startup and remote channel creation. Save the token when it is shown; friend bootstrap strings never contain it. If the token is lost, stop SHAC and remove `.shac-master-token` to create a new one.

This owner token protects the SHAC control plane. It does not replace friend approval: every node task still requires explicit approval on that node.

## Desktop UI

From the project folder:

```powershell
.\.venv\Scripts\python.exe gui_pyqt/app.py
```

The UI provides:

- Start and stop LAN server controls.
- LAN address and port configuration.
- Channel creation and one-click bootstrap copy.
- Connected device and pending request status.
- Allow/reject controls for friend requests.
- Broadcast chat and live log panels.
- Integrated command palette with `s`, `c`, `allow`, `reject`, `nodes`, and `help`.
- LAN/Internet transport selector with separate local and public endpoint fields.
- Channel details showing the generated transport type.

The UI uses only Python's standard library, including Tkinter.

## Themed CLI

Open the command guide:

```powershell
python -m cli.shac
```

Start a LAN server:

```powershell
python -m cli.shac s start --lan 8765 10.47.4.81
```

Create a channel:

```powershell
python -m cli.shac c create 10.47.4.81:8765
```

## Internet raw TCP mode

The same machine-to-machine relay can bind to all interfaces and advertise a public host:

```powershell
python -m cli.shac s start --internet 8765 public.example.com
python -m cli.shac c create public.example.com:8765
```

This uses the existing newline-delimited SHAC protocol directly over TCP; it does not use HTTP or a third-party package. For a home computer, forward TCP `8765` from the router to this machine. If you do not control the router, run the SHAC server on a public VPS instead. Internet mode is currently raw TCP and should be protected with TLS before production or untrusted use.

The channel command prints a self-contained `python -c ...` bootstrap command. A friend can paste it into PowerShell without installing SHAC or cloning this repository.

LAN and Internet channel strings are generated from the same protocol but carry different transport metadata:

- `lan`: advertises the computer's local Wi-Fi address.
- `internet`: advertises the configured public IP or DNS host.

All other behavior is shared: join approval, heartbeat, messaging, task consent, logs, and node management.

When a friend requests access, the server console accepts:

```text
y       allow oldest pending request
n       reject oldest pending request
/nodes  show accepted nodes
/help   show server chat commands
/quit   stop the server
```

Type normal text at `master>` to broadcast to every accepted node in the active channel. Friends can send replies from their bootstrap chat prompt.

## Consented task requests

The networking layer now supports audited task requests without executing arbitrary remote code. Send a request to one node or all nodes:

```powershell
python -m cli.shac t send 10.47.4.81:8765 SWARM-XXXX MASTER-CREDENTIAL all file.create '{"path":"example.txt"}'
```

The friend sees an approval prompt in the bootstrap window. The server records the request and response in `shac.log`. At this stage, the request is consent and audit only; browser control, file workers, process execution, and AI training workers are deliberately not installed yet.

The first restricted worker is `browser.search`. After the friend approves, the standalone runtime opens the search in the friend's default browser:

```powershell
python -m cli.shac t send 10.47.4.81:8765 SWARM-XXXX MASTER-CREDENTIAL all browser.search '{"query":"Python asyncio networking"}'
```

This does not read browser history, cookies, passwords, page contents, or downloads. It only opens the explicitly requested search URL and returns the URL in the audit log.

## Connection health

Accepted connections use a standard-library heartbeat. The server sends periodic `ping` frames, clients return `pong`, and sessions that stop responding are disconnected and recorded in `shac.log` as `heartbeat_timeout` events. This improves LAN reliability and is required before Internet relay mode.

## LAN checklist

1. Keep both devices on the same Wi-Fi network.
2. Use the host's LAN IPv4 address, not `127.0.0.1`.
3. Allow inbound TCP `8765` in Windows Firewall.
4. Start the server before creating a channel.
5. Use the same endpoint port for channel creation and the generated invitation.

## Phone timeout troubleshooting

If the phone reports a timeout, first confirm that the server is actually listening:

```powershell
python -m cli.shac s start --lan 8765 10.47.4.81
```

Keep that terminal open. In a second PowerShell window, run:

```powershell
Test-NetConnection 10.47.4.81 -Port 8765
```

The result must contain `TcpTestSucceeded : True` before testing from the phone.

If it is `False`, open PowerShell **as Administrator** and create the inbound rule:

```powershell
New-NetFirewallRule -DisplayName "SHAC LAN 8765" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow -Profile Any
```

The current Wi-Fi network may be marked `Public`. For a trusted private home network, you can change only the active Wi-Fi profile:

```powershell
Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private
```

Do not use `127.0.0.1` in the phone invitation. Use the computer's current Wi-Fi IPv4 address, for example `10.47.4.81`. Guest Wi-Fi and router AP/client isolation can still block phone-to-computer traffic even when the firewall is configured; test with the phone and computer on the same non-guest network.

