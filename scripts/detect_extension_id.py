import os
import json
import sys

def find_extension_id():
    appdata = os.environ.get('LOCALAPPDATA', '')
    if not appdata:
        if sys.platform == 'darwin':
            appdata = os.path.expanduser('~/Library/Application Support')
        else:
            appdata = os.path.expanduser('~/.config')
            
    profiles_to_check = [
        os.path.join(appdata, 'Google', 'Chrome', 'User Data', 'Default'),
        os.path.join(appdata, 'BraveSoftware', 'Brave-Browser', 'User Data', 'Default'),
        os.path.join(appdata, 'Microsoft', 'Edge', 'User Data', 'Default'),
        os.path.expanduser('~/.config/google-chrome/Default'),
        os.path.expanduser('~/.config/chromium/Default'),
        os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default'),
    ]

    target_name = "YouTube Native Downloader"

    for profile_path in profiles_to_check:
        if not os.path.exists(profile_path):
            continue

        # Strategy 1: Check standard packed Extensions directory
        ext_base_path = os.path.join(profile_path, 'Extensions')
        if os.path.exists(ext_base_path):
            try:
                for ext_id in os.listdir(ext_base_path):
                    if len(ext_id) != 32:
                        continue
                    ext_dir = os.path.join(ext_base_path, ext_id)
                    if not os.path.isdir(ext_dir):
                        continue
                    for version_node in os.listdir(ext_dir):
                        manifest_path = os.path.join(ext_dir, version_node, 'manifest.json')
                        if os.path.exists(manifest_path):
                            with open(manifest_path, 'r', encoding='utf-8') as f:
                                if json.load(f).get('name') == target_name:
                                    return ext_id
            except: pass

        # Strategy 2: Check Preferences file for Unpacked extensions (Developer Mode)
        prefs_path = os.path.join(profile_path, 'Preferences')
        if os.path.exists(prefs_path):
            try:
                with open(prefs_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f).get('extensions', {}).get('settings', {})
                for ext_id, ext_data in settings.items():
                    if len(ext_id) == 32 and ext_data.get('location') == 4:
                        manifest_path = os.path.join(ext_data.get('path', ''), 'manifest.json')
                        if os.path.exists(manifest_path):
                            with open(manifest_path, 'r', encoding='utf-8') as m:
                                if json.load(m).get('name') == target_name:
                                    return ext_id
            except: pass
            
    return None

if __name__ == "__main__":
    ext_id = find_extension_id()
    if ext_id:
        sys.stdout.write(ext_id)
        sys.exit(0)
    else:
        sys.exit(1)
