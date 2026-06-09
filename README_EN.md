# LocalDog 🐶

[English](README_EN.md) | [Русский](README_RU.md)

**LocalDog** is a modern, fast, and private MTProto proxy for Telegram Desktop. It runs locally on your computer, converting regular Telegram traffic into WebSocket connections, which allows bypassing network restrictions without using third-party servers.

---

## ✨ Features

- **Local Bridge**: Runs directly on your PC. No intermediate servers — your data stays yours.
- **WebSocket Tunneling**: Uses official Telegram WebSocket nodes for maximum stability.
- **Modern GUI**: Beautiful PySide6 interface with dark and light theme support.
- **Smart Sync**: Settings apply instantly, and the Telegram link updates in real-time.
- **Status Indication**: Animated status indicators and detailed traffic statistics.
- **Automation**: Auto-start and minimize-to-tray support.

---

## 🚀 How to Use (Windows)

For most users, simply download the ready-to-use `.exe` file:

1. Go to the **[Releases](https://github.com/AlexMacregar/LocalDogTelegram/releases)** section.
2. Download the latest `LocalDog.exe`.
3. Run the file (no installation required, no Python needed).
4. Click the large power button in the center of the screen.
5. Click **"Open in Telegram"** or copy the link and add the proxy in Telegram settings.

---

## 🛠 Configuration

The **Settings** tab allows you to:
- Change the listening port and address (default `127.0.0.1:443`).
- Generate a new secret key.
- Configure routing for specific Telegram Data Centers (DC).
- Enable auto-start.

*Tip: Hover over the **"?"** icons in settings for detailed information about each option.*

---

## 👨‍💻 For Developers

If you want to run the project from source code:

```bash
# Clone
git clone https://github.com/AlexMacregar/LocalDogTelegram.git
cd LocalDogTelegram

# Install dependencies
pip install -r requirements.txt

# Run
python -m localdog
```

---

## 🔒 Security and Privacy

LocalDog **does not decrypt** your messages. MTProto traffic is encrypted end-to-end between your Telegram client and Telegram servers. LocalDog only changes the "wrapper" of the traffic from TCP to WebSocket.

Read our [Security Policy](SECURITY_EN.md).

---

## 📄 License

This project is licensed under the **MIT** License. See the [LICENSE](LICENSE) file for details.

---
*Created with love for internet freedom.*
