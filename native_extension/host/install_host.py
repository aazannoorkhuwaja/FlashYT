#!/usr/bin/env python3
import os
import sys
import platform
import json
import stat

HOST_NAME = "com.aazan.ytdl"
HOST_DESCRIPTION = "Native Messaging Host for One-Click YouTube Downloader"

def install():
    """
    Automatically detects the OS (Windows, macOS, Linux) and registers
    the Native Messaging JSON manifest into the correct Chrome/Brave 
    registry key or directory path.
    """
    current_dir = os.path.abspath(os.path.dirname(__file__))
    host_path = os.path.join(current_dir, "host.py")
    
    # Ensure the host script is genuinely executable on Unix
    if platform.system() != 'Windows':
        st = os.stat(host_path)
        os.chmod(host_path, st.st_mode | stat.S_IEXEC)
        
    print(f"\n========================================================")
    print(f"  Native Messaging Host Setup: {HOST_NAME}")
    print(f"========================================================")
    print("To allow Chrome/Brave to talk to this Python script,")
    print("we need the 32-character Extension ID assigned by your browser.")
    print("\nHow to find it:")
    print("  1. Open your browser and go to: chrome://extensions")
    print("  2. Enable 'Developer mode' (top right corner)")
    print("  3. Click 'Load unpacked' and select the 'extension' folder")
    print("  4. Copy the newly generated 32-character 'ID:' string")
    print("     (e.g., aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa)")
    print("========================================================\n")
    
    while True:
        ext_id = input("Paste your 32-character Extension ID here: ").strip()
        if len(ext_id) == 32 and ext_id.isalpha() and ext_id.islower():
            break
        print("\n[!] Invalid ID. It must be exactly 32 lowercase letters.")
        print("Please copy it directly from your chrome://extensions page.\n")

    # Build the required Native Messaging Manifest
    manifest = {
        "name": HOST_NAME,
        "description": HOST_DESCRIPTION,
        "path": host_path,
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{ext_id}/"
        ]
    }
    
    system = platform.system()
    
    if system == 'Windows':
        # Windows requires a batch wrapper because Chrome struggles invoking raw .py files via stdio
        bat_path = os.path.join(current_dir, "host.bat")
        with open(bat_path, 'w') as f:
            f.write(f'@echo off\r\n"{sys.executable}" "{host_path}" %*')
        manifest["path"] = bat_path
        
        # Write the JSON manifest to the current directory
        manifest_path = os.path.join(current_dir, f"{HOST_NAME}.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=4)
            
        import winreg
        print("Registering Windows Registry Keys...")
        
        # Register for Google Chrome
        try:
            key_path = rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
            winreg.CloseKey(key)
            print("  [+] Chrome registered.")
        except Exception as e:
            print(f"  [-] Failed to register Chrome: {e}")
            
        # Register for Brave
        try:
            key_path = rf"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\{HOST_NAME}"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
            winreg.CloseKey(key)
            print("  [+] Brave registered.")
        except Exception:
            print("  [-] Brave not found or failed to register.")
            
    elif system == 'Darwin':  # macOS
        print("Registering macOS Directories...")
        
        # macOS needs a shell wrapper to ensure the correct Python virtual environment is used
        sh_path = os.path.join(current_dir, "host.sh")
        with open(sh_path, 'w') as f:
            f.write(f'#!/bin/bash\n"{sys.executable}" "{host_path}" "$@"')
        os.chmod(sh_path, os.stat(sh_path).st_mode | stat.S_IEXEC)
        manifest["path"] = sh_path
        
        home = os.path.expanduser('~')
        
        # Chrome
        chrome_dir = os.path.join(home, "Library/Application Support/Google/Chrome/NativeMessagingHosts")
        os.makedirs(chrome_dir, exist_ok=True)
        with open(os.path.join(chrome_dir, f"{HOST_NAME}.json"), 'w') as f:
            json.dump(manifest, f, indent=4)
        print("  [+] Chrome registered.")
            
        # Brave
        brave_dir = os.path.join(home, "Library/Application Support/BraveSoftware/Brave-Browser/NativeMessagingHosts")
        os.makedirs(brave_dir, exist_ok=True)
        with open(os.path.join(brave_dir, f"{HOST_NAME}.json"), 'w') as f:
            json.dump(manifest, f, indent=4)
        print("  [+] Brave registered.")
        
    elif system == 'Linux':
        print("Registering Linux Directories...")
        
        # Linux needs a shell wrapper to ensure the correct Python virtual environment is used
        sh_path = os.path.join(current_dir, "host.sh")
        with open(sh_path, 'w') as f:
            f.write(f'#!/bin/bash\n"{sys.executable}" "{host_path}" "$@"')
        os.chmod(sh_path, os.stat(sh_path).st_mode | stat.S_IEXEC)
        manifest["path"] = sh_path
        
        home = os.path.expanduser('~')
        
        # Chrome
        chrome_dir = os.path.join(home, ".config/google-chrome/NativeMessagingHosts")
        os.makedirs(chrome_dir, exist_ok=True)
        with open(os.path.join(chrome_dir, f"{HOST_NAME}.json"), 'w') as f:
            json.dump(manifest, f, indent=4)
        print("  [+] Chrome registered.")
            
        # Chromium
        chromium_dir = os.path.join(home, ".config/chromium/NativeMessagingHosts")
        os.makedirs(chromium_dir, exist_ok=True)
        with open(os.path.join(chromium_dir, f"{HOST_NAME}.json"), 'w') as f:
            json.dump(manifest, f, indent=4)
        print("  [+] Chromium registered.")
            
        # Brave
        brave_dir = os.path.join(home, ".config/BraveSoftware/Brave-Browser/NativeMessagingHosts")
        os.makedirs(brave_dir, exist_ok=True)
        with open(os.path.join(brave_dir, f"{HOST_NAME}.json"), 'w') as f:
            json.dump(manifest, f, indent=4)
        print("  [+] Brave registered.")

    print(f"\n✅ Installation complete for {system}.")
    print("\nCRITICAL NEXT STEP:")
    print(f"You MUST open {HOST_NAME}.json (or host.py's install script) and replace 'YOUR_EXTENSION_ID_HERE'")
    print("with the 32-character Extension ID assigned by your browser after loading the unpacked extension!")

if __name__ == '__main__':
    install()
