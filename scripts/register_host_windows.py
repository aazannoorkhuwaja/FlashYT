import os
import sys
import json
from datetime import datetime

try:
    import winreg
except ImportError:
    winreg = None

# Windows Registry Keys for Native Messaging
CHROME_REG_KEY = r"Software\Google\Chrome\NativeMessagingHosts\com.youtube.native.ext"
BRAVE_REG_KEY = r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.youtube.native.ext"

def log_install(msg):
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return
    log_dir = os.path.join(appdata, 'YouTubeNativeExt')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'install.log')
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except:
        pass
    print(msg, file=sys.stderr)

def write_registry(key_path, manifest_path):
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
            log_install(f"✓ Created registry key: HKCU\\{key_path} -> {manifest_path}")
    except Exception as e:
        log_install(f"✗ Failed to write registry key: HKCU\\{key_path}: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        log_install(f"✗ Invalid arguments. Usage: {sys.argv[0]} <install_dir> <extension_id>")
        sys.exit(1)

    install_dir = sys.argv[1]
    extension_id = sys.argv[2]
    
    if len(extension_id) != 32:
        log_install(f"✗ Invalid extension ID length: '{extension_id}'")
        sys.exit(1)

    # 1. Read template manifest
    template_path = os.path.join(install_dir, 'com.youtube.native.ext.json')
    if not os.path.exists(template_path):
        log_install(f"✗ Manifest template not found: {template_path}")
        sys.exit(1)

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception as e:
        log_install(f"✗ Failed to read manifest template: {e}")
        sys.exit(1)

    # 2. Modify manifest dynamically
    host_exe_path = os.path.join(install_dir, 'host.exe')
    
    # If running from source (not installed), fallback to python host.py
    if not os.path.exists(host_exe_path):
        host_exe_path = os.path.abspath(os.path.join(install_dir, '..', 'host', 'host.py'))
        if sys.executable.endswith('pythonw.exe'):
            manifest['path'] = os.path.join(os.path.dirname(sys.executable), 'python.exe')
            if 'allowed_origins' in manifest: 
                # Optional: For python scripts, we might need a bat wrapper on windows natively,
                # but for this script we assume Inno Setup drops host.exe correctly.
                # If we're testing this standalone, we just patch the path for logging
                pass
        
    # Strictly enforce that the path uses backslashes for Windows Native Messaging
    manifest['path'] = host_exe_path.replace('/', '\\')
    manifest['allowed_origins'] = [f"chrome-extension://{extension_id}/"]

    # 3. Write final manifest to %APPDATA%
    appdata = os.environ.get('APPDATA')
    if not appdata:
        log_install("✗ APPDATA environment variable not found.")
        sys.exit(1)
        
    target_dir = os.path.join(appdata, 'YouTubeNativeExt')
    os.makedirs(target_dir, exist_ok=True)
    target_manifest_path = os.path.join(target_dir, 'com.youtube.native.ext.json')

    try:
        with open(target_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        log_install(f"✓ Wrote dynamic manifest with ID '{extension_id}' and path '{manifest['path']}' to {target_manifest_path}")
    except Exception as e:
        log_install(f"✗ Failed to write final manifest: {e}")
        sys.exit(1)

    # 4. Write Registry Keys
    write_registry(CHROME_REG_KEY, target_manifest_path)
    write_registry(BRAVE_REG_KEY, target_manifest_path)

    log_install("✓ Host registration completed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
