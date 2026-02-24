import sys
import json
import struct
import subprocess

def send_message(proc, msg_dict):
    message = json.dumps(msg_dict).encode('utf-8')
    proc.stdin.write(struct.pack('@I', len(message)))
    proc.stdin.write(message)
    proc.stdin.flush()

def read_message(proc):
    raw_length = proc.stdout.read(4)
    if not raw_length or len(raw_length) < 4:
        return None
    msg_length = struct.unpack('@I', raw_length)[0]
    message = proc.stdout.read(msg_length).decode('utf-8')
    return message

proc = subprocess.Popen(
    ["./host.sh"], 
    stdin=subprocess.PIPE, 
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE # Capture stderr too to see if yt-dlp complains
)

# Send download message
send_message(proc, {
    "action": "download",
    "url": "https://www.youtube.com/watch?v=BaW_jenozKc", # short video
    "format": "best"
})

while True:
    msg = read_message(proc)
    if msg is None:
        print("HOST DISCONNECTED!")
        break
    print("Received:", msg)

err = proc.stderr.read().decode('utf-8')
if err:
    print("STDERR:", err)

