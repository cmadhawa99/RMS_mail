import webview
import requests
import sys
import ctypes

# REPLACE THIS with the actual Server IP (e.g., http://192.168.1.50:8000)
SERVER_URL = "http://192.168.1.10:8000"
APP_TITLE = "City Council Management Portal"

def is_server_running(url):
    try:
        requests.get(url, timeout=3)
        return True
    except requests.ConnectionError:
        return False

def show_error(title, message):

    ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)

def main():
    if not is_server_running(SERVER_URL):
        show_error(
            "Connection Failed",
            f"Could not connect to the Server at:\n{SERVER_URL}\n\nPlease ensure the main server is turned on and try again."
        )
        sys.exit()

    webview.create_window(
        APP_TITLE,
        url=SERVER_URL,
        width=1200,
        height=800,
        resizable=True,
        confirm_close=True
    )
    webview.start()

if __name__ == '__main__':
    main()