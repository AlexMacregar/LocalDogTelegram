# Contributing to LocalDog

Thank you for your interest in contributing to LocalDog! We welcome all contributions, from bug reports and feature requests to code improvements and translations.

## How to Contribute

### Reporting Bugs
If you find a bug, please open an issue on GitHub. Include:
- A clear description of the bug.
- Steps to reproduce it.
- Your operating system and Python version.
- Any relevant logs from the **Log** tab in the app.

### Suggesting Features
We love new ideas! Open an issue with the "Feature Request" tag and explain:
- What problem the feature solves.
- How you imagine it working.

### Code Contributions
1. Fork the repository.
2. Create a new branch for your feature or fix: `git checkout -b feature/my-new-feature`.
3. Make your changes.
4. Ensure your code follows the existing style (we use PySide6 for UI and asyncio for the proxy core).
5. Run the app to make sure everything works: `python -m localdog`.
6. Commit your changes: `git commit -m 'Add some feature'`.
7. Push to the branch: `git push origin feature/my-new-feature`.
8. Open a Pull Request.

## Development Setup

1. Clone the repo: `git clone https://github.com/AlexMacregar/LocalDogTelegram.git`
2. Create a virtual environment: `python -m venv .venv`
3. Activate it:
   - Windows: `.venv\Scripts\activate`
   - Linux/macOS: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the app: `python -m localdog`

## Project Structure
- `localdog/proxy/`: Core proxy logic (asyncio, MTProto, WebSockets).
- `localdog/ui/`: GUI implementation (PySide6).
- `packaging/`: Files for building standalone executables.

## Code of Conduct
Please be respectful and professional in all interactions. We aim to foster a welcoming and inclusive environment.

---
*Happy coding!*
