from mock_chrome import *
import time

proc = subprocess.Popen(
    ["./host.sh"], 
    stdin=subprocess.PIPE, 
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

send_message(proc, {
    "action": "download",
    "url": "https://www.youtube.com/watch?v=BaW_jenozKc",
    "format": "best"
})

while True:
    try:
        raw = proc.stdout.read(4)
        if not raw: break
        print("Raw length buffer:", repr(raw))
        length = struct.unpack('@I', raw)[0]
        data = proc.stdout.read(length)
        print("Data:", data.decode('utf-8'))
    except Exception as e:
        print("READ ERROR:", e)
        break

print("ERRORS:", proc.stderr.read().decode('utf-8'))
