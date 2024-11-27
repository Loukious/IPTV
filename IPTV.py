import sys
import base64
import json
import os
import threading
import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QScrollArea,
    QPushButton, QWidget, QMessageBox, QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt
# Check if running in a Nuitka onefile environment
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    dll_path = os.path.join(sys._MEIPASS, "Libs")  # Temporary extraction path
else:
    dll_path = os.path.join(os.path.dirname(__file__), "Libs")  # Development path

os.environ["PATH"] = dll_path + os.pathsep + os.environ["PATH"]
import mpv

class Stream:
    def __init__(self):
        self.baseURL = "https://a501.variety-buy.store/api/"
        self.session = requests.session()
        self.session.headers = {
            "User-Agent": "okhttp/3.12.8",
            "accept": "application/json"
        }

    def getCategories(self):
        url = f"{self.baseURL}categories"
        r = self.session.get(url)
        cats = self.decrypt(r.text, r.headers["t"])
        for cat in cats["data"]:
            if cat["child_count"] > 0:
                url = f"{self.baseURL}categories/{cat['id']}"
                r = self.session.get(url)
                cats["data"].extend(self.decrypt(r.text, r.headers["t"])["data"])
                cats["data"].remove(cat)
        return cats["data"]

    def decrypt(self, s, passcode):
        passcode = "c!xZj+N9&G@Ev@vw" + passcode
        s = base64.b64decode(s.encode('ascii')).decode('ascii')

        result = ""
        for i in range(len(s)):
            result += chr(ord(s[i]) ^ ord(passcode[i % len(passcode)]))
        return json.loads(result)

    def getChannels(self, category):
        url = f"{self.baseURL}categories/{category}/channels"
        r = self.session.get(url)
        return self.decrypt(r.text, r.headers["t"])

    def getStream(self, channel):
        headers = {
            "User-Agent": "okhttp/3.14.9"
        }
        url = f"https://a501.variety-buy.store/api/channel/{channel}"
        r = self.session.get(url, headers=headers)
        stream = {}
        try:
            data = self.decrypt(r.text, r.headers["t"])["data"]
            urlList = [i["url"].replace("www.elahmad.coo", "www.elahmad.com") for i in data]
            prioritizedUrlList = sorted(urlList, key=lambda x: ("t=" in x and "e=" in x), reverse=True)
            stream["urls"] = prioritizedUrlList
            stream["User-Agent"] = data[0]["headers"]["User-Agent"] if data and data[0].get("headers") and data[0]["headers"].get("User-Agent") else ""
            return stream
        except:
            return {"urls": [], "User-Agent": ""}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPTV")
        self.stream = Stream()
        self.initUI()

    def initUI(self):
        self.mainWidget = QWidget()
        self.mainLayout = QVBoxLayout(self.mainWidget)
        self.setCentralWidget(self.mainWidget)

        # Enable right-click for return functionality
        self.mainWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mainWidget.customContextMenuRequested.connect(self.onRightClick)

        # Create a group box for categories
        self.categoryGroupBox = QGroupBox("Categories")
        self.categoryLayout = QGridLayout(self.categoryGroupBox)

        categories = self.stream.getCategories()
        max_cols = 4  # Number of columns
        for i, category in enumerate(categories):
            row = i // max_cols
            col = i % max_cols
            button = QPushButton(category["name"])
            button.clicked.connect(lambda checked, c=category: self.loadChannels(c))
            self.categoryLayout.addWidget(button, row, col)

        self.mainLayout.addWidget(self.categoryGroupBox)

    def loadChannels(self, category):
        # Clear the main layout
        self.clearLayout(self.mainLayout)

        # Create a group box for channels
        self.channelGroupBox = QGroupBox(f"Channels in {category['name']}")
        self.channelLayout = QVBoxLayout(self.channelGroupBox)

        # Scroll Area for Channels
        scrollArea = QScrollArea()
        scrollWidget = QWidget()
        scrollLayout = QVBoxLayout(scrollWidget)

        channels = self.stream.getChannels(category["id"])
        for channel in channels["data"]:
            button = QPushButton(channel["name"])
            button.clicked.connect(lambda checked, ch=channel: self.playChannel(ch))
            scrollLayout.addWidget(button)

        backButton = QPushButton("Back")
        backButton.clicked.connect(self.initUI)
        scrollLayout.addWidget(backButton)

        scrollWidget.setLayout(scrollLayout)
        scrollArea.setWidget(scrollWidget)
        scrollArea.setWidgetResizable(True)

        # Add the scroll area to the group box
        self.channelLayout.addWidget(scrollArea)
        self.channelGroupBox.setLayout(self.channelLayout)

        self.mainLayout.addWidget(self.channelGroupBox)

    def playChannel(self, channel):
        stream = self.stream.getStream(channel["id"])
        if stream["urls"]:
            thread = threading.Thread(target=self.run_mpv, args=(stream, channel), daemon=True)
            thread.start()
        else:
            QMessageBox.critical(self, "Error", "No stream available for this channel")

    def run_mpv(self, stream, channel):
        player = mpv.MPV(
            input_default_bindings=True,
            input_vo_keyboard=True,
            osc=True
        )

        player.play(stream["urls"][0])
        player.user_agent = stream["User-Agent"]
        player.title = channel["name"]
        player.loop_file = "inf"

        try:
            player.wait_for_playback()
        finally:
            player.terminate()

    def onRightClick(self, pos):
        """Handle right-click event to return to categories."""
        # Check if the channelGroupBox exists in the layout
        if hasattr(self, "channelGroupBox"):
            for i in range(self.mainLayout.count()):
                item = self.mainLayout.itemAt(i)
                if item and item.widget() == self.channelGroupBox:
                    self.initUI()
                    break


    def clearLayout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self.clearLayout(item.layout())



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
