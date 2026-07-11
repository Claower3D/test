import winreg
import shlex
import os

def get_default_browser_path():
    try:
        # Get ProgId of default HTTP handler
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        
        # Get command for that ProgId
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as key:
            command = winreg.QueryValueEx(key, "")[0]
            
        # Parse the command to extract the executable path
        parts = shlex.split(command)
        if parts:
            exe_path = parts[0]
            if os.path.exists(exe_path):
                return exe_path
    except Exception as e:
        print(f"Error getting default browser: {e}")
    return None

print(f"Default browser path: {get_default_browser_path()}")
