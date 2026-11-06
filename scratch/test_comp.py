import base64
import zlib
from network.channel import Channel
from bootstrap.bootstrap_generator import BootstrapGenerator

c = Channel.create('lan', '10.0.0.1:8765')
bg = BootstrapGenerator(c)
inv = bg._encoded_invitation()
script = bg._runtime_script().replace('{INVITATION}', inv)
zb64 = base64.b64encode(zlib.compress(script.encode('utf-8'), 9)).decode('ascii')
cmd = f'python -c "import base64,zlib;exec(zlib.decompress(base64.b64decode(\'{zb64}\')))"'

print("Old raw length:", len(bg.generate()))
print("New compressed length:", len(cmd))
