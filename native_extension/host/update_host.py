with open('host.py', 'r') as f:
    orig = f.read()

import os
with open('host.py', 'w') as f:
    for line in orig.split('\n'):
        if line == 'import yt_dlp':
            f.write('import yt_dlp\nimport traceback\nimport logging\nlogging.basicConfig(filename="/tmp/ytdl_native_host.log", level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")\nlogging.debug("Host started")\n')
        elif 'send_message({"action": "error", "error": f"Critical Native Host Crash: {str(e)}"})' in line:
            f.write('            logging.error(f"Critical Native Host Crash: {traceback.format_exc()}")\n')
            f.write(line + '\n')
        elif 'except Exception as e:' in line:
            f.write(line + '\n            logging.error(f"Exception: {traceback.format_exc()}")\n')
        else:
            f.write(line + '\n')
