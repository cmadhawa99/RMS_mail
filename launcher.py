import webview
import requests
import sys
import ctypes
import base64
import os

# REPLACE THIS with your actual Server IP
SERVER_URL = "http://192.168.1.10:8000"
APP_TITLE = "City Council Management Portal"


class Api:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def save_excel_file(self, filename, data_base64):
        """
        This function is called from JavaScript.
        It opens a Windows 'Save As' dialog and writes the file.
        """
        try:
            # 1. Decode the Base64 string back to bytes
            file_bytes = base64.b64decode(data_base64)

            # 2. Open Save Dialog
            # 'create_file_dialog' returns a tuple/list of strings
            result = self.window.create_file_dialog(
                webview.SAVE_DIALOG,
                directory='',
                save_filename=filename,
                file_types=('Excel Files (*.xlsx)', 'All files (*.*)')
            )

            # 3. Save the file if user didn't cancel
            if result:
                # Handle path (pywebview can return a string or list depending on version)
                save_path = result if isinstance(result, str) else result[0]

                with open(save_path, 'wb') as f:
                    f.write(file_bytes)

                return {"status": "success", "message": "File saved successfully!"}

            return {"status": "cancelled", "message": "Save cancelled."}

        except Exception as e:
            return {"status": "error", "message": str(e)}


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

    # Initialize API
    api = Api()

    # Create window with the API attached
    window = webview.create_window(
        APP_TITLE,
        url=SERVER_URL,
        width=1200,
        height=800,
        resizable=True,
        confirm_close=True,
        js_api=api  # <--- Connects Python to the Web Page
    )

    # Give the API access to the window (so it can open dialogs)
    api.set_window(window)

    webview.start()


if __name__ == '__main__':
    main()