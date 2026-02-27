import struct
import json
import subprocess
import os

def test_host():
    host_path = os.path.abspath("host/host.py")
    process = subprocess.Popen(
        ["python3", host_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )

    def send_msg(msg):
        json_msg = json.dumps(msg).encode('utf-8')
        process.stdin.write(struct.pack('<I', len(json_msg)))
        process.stdin.write(json_msg)
        process.stdin.flush()

    def read_msg():
        raw_length = process.stdout.read(4)
        if not raw_length:
            return None
        length = struct.unpack('<I', raw_length)[0]
        msg = process.stdout.read(length).decode('utf-8')
        return json.loads(msg)

    print("--- Sending Ping ---")
    send_msg({"type": "ping"})
    response = read_msg()
    print("Response:", response)

    print("\n--- Sending Prefetch ---")
    send_msg({"type": "prefetch", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    response = read_msg()
    print("Response Type:", response.get("type"))
    if response.get("type") == "prefetch_result":
        print("Title:", response.get("title"))
        print("Quality Count:", len(response.get("qualities", [])))

    # Shutdown
    process.terminate()
    process.wait()
    print("\n--- Host Terminated ---")

if __name__ == "__main__":
    test_host()
