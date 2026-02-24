import os
import json
import sys

def find_extension_id():
    appdata = os.environ.get('LOCALAPPDATA', '')
    if not appdata:
        # Fallback for Mac/Linux if run manually
        if sys.platform == 'darwin':
            appdata = os.path.expanduser('~/Library/Application Support')
        else:
            appdata = os.path.expanduser('~/.config')
            
    # Ordered paths to check: Chrome, Brave, Edge, Chromium (Linux)
    paths_to_check = [
        os.path.join(appdata, 'Google', 'Chrome', 'User Data', 'Default', 'Extensions'),
        os.path.join(appdata, 'BraveSoftware', 'Brave-Browser', 'User Data', 'Default', 'Extensions'),
        os.path.join(appdata, 'Microsoft', 'Edge', 'User Data', 'Default', 'Extensions'),
        os.path.expanduser('~/.config/google-chrome/Default/Extensions'),
        os.path.expanduser('~/.config/chromium/Default/Extensions'),
    ]

    target_name = "YouTube Native Downloader"

    for base_path in paths_to_check:
        if not os.path.exists(base_path):
            continue

        for ext_id in os.listdir(base_path):
            if len(ext_id) != 32:
                continue

            ext_dir = os.path.join(base_path, ext_id)
            if not os.path.isdir(ext_dir):
                continue

            # Extensions have version subfolders
            for version_node in os.listdir(ext_dir):
                version_dir = os.path.join(ext_dir, version_node)
                manifest_path = os.path.join(version_dir, 'manifest.json')
                
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest = json.load(f)
                            if manifest.get('name') == target_name:
                                return ext_id
                    except:
                        pass
                        
    return None

if __name__ == "__main__":
    ext_id = find_extension_id()
    if ext_id:
        # Must print EXACTLY the ID and nothing else to stdout so Inno Setup can capture it
        sys.stdout.write(ext_id)
        sys.exit(0)
    else:
        # Return cleanly but exit 1 to trigger manual text box invocation in Inno Setup
        sys.exit(1)
