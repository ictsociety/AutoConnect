re# Contributors Guide (No Coding Experience Required)

Updated: 2025-10-14

This guide is for anyone who wants to help but doesn’t write code every day. You can make a big difference by testing features, improving documentation, translating text, or helping spot where students get stuck.

What this project is
- A simple app that connects your device to UNESWA Wi‑Fi, sets up the campus proxy, and registers your device if needed.
- The app is small on purpose. It focuses on what students actually need when they’re stuck.

How you can contribute (without coding)
1) Real-world testing
- Try the app on campus or a campus-like network
- Write down exactly what worked and what didn’t
- Copy the last ~30 lines of the log from the logs/ folder when something breaks
- If you’re on Linux, note the distribution and version (e.g., Ubuntu 22.04, Fedora 41)
- If you’re on Windows, note Windows 10/11 and any special settings (VPN, antivirus that filters network, etc.)

2) Documentation improvements
- Read `README.md`, `docs/BEGINNERS_GUIDE.md`, and “ICT Society Autoconnect Short Project.md”
- If anything is confusing, unclear, or uses jargon, suggest a clearer sentence
- If you found a workaround in real life, add it to the guide with a short explanation

3) Translation
- We support English and siSwati
- If any words are off or unclear in the siSwati texts, propose changes
- The language strings live in `src/config/translations.py`
- Keep the tone consistent with the rest of the app (simple, helpful)

4) UX feedback
- Open the app and pretend you’ve never seen it
- Which button names are unclear?
- Which message made you stop and think “wait… what?”
- Suggest better labels or phrasing (short is good)

5) Test the “edge” cases
- Slow Wi‑Fi
- Wrong password the first time
- Switching from manual proxy to PAC on Windows
- Fedora/RHEL where DNF needs the proxy line
- Windows where some CLI tools ignore browser proxy (that’s why we can set WinHTTP)

Where things live (so you can mention them in issues)
- GUI: `src/ui/main_window.py`
- Wi‑Fi logic: `src/network/wifi_manager.py`
- Proxy logic: `src/network/proxy_manager.py`
- Device registration: `src/network/device_registry.py`
- Connectivity checks: `src/utils/connection_test.py`
- Config and constants: `src/config/settings.py`
- Translations: `src/config/translations.py`
- Root launcher: `main.py` (use `python main.py` to run)

Beginner-friendly description of the main modules
- GUI (main_window.py)
  - The visual window (buttons, inputs, status bar, log)
  - Has buttons for: Complete Setup, Wi‑Fi only, Proxy only, Register Device, Test Connection, Reset
  - Also has a language toggle (English/siSwati)
- Wi‑Fi (wifi_manager.py)
  - Windows: creates a Wi‑Fi profile for the campus network and stores credentials the way Windows expects
  - Linux: adds a NetworkManager connection with the right EAP settings
- Proxy (proxy_manager.py)
  - Windows: sets a manual proxy or enables PAC (automatic) using the official PAC file
  - Optionally sets a separate “WinHTTP” proxy for tools/services that ignore browser proxy
  - Linux: exports proxy environment variables and (for Fedora/RHEL/CentOS) updates DNF’s config using pkexec
- Device Registration (device_registry.py)
  - Tries to load the netreg page, finds the form, and submits credentials
  - If the form can’t be parsed, there’s a legacy endpoint fallback
- Connection Tests (connection_test.py)
  - Simple tests to see if Wi‑Fi is connected, proxy is set, and some websites respond
- Settings (settings.py)
  - Central place for SSID, proxy host/port, URLs, timeouts
  - You’ll find the official PAC URL here and Linux distro-specific behaviors

What is “Windows registry” and “PAC”? (plain language)
- Windows registry: a built‑in settings database Windows uses. We write a few proxy settings there (or point to a PAC file)
- PAC (Proxy Auto‑Config): a small script that tells the browser which proxy to use for which site. The university hosts the official PAC file; we just point to it
- WinHTTP: a separate proxy setting for background services and some tools (not the browser). We offer to set it to keep command‑line tools happy

How to file a good issue
- Title: clear and short (“DNF still not using proxy on Fedora 39”)
- Steps: what you clicked/typed
- What you expected vs what you got
- OS info: Windows 11 / Fedora 39 / Ubuntu 22.04 etc.
- Logs: last ~30 lines from `logs/`
- Screenshot only if it helps (don’t paste personal info)

How to propose a documentation change
- Tell us which file and which section
- Paste your suggested sentence/paragraph
- Keep the writing short and human (“click this”, “type that”)

How to propose a language change (siSwati/English)
- Point to a key in `src/config/translations.py` and propose a better translation
- Keep placeholders intact (like {username} or {ssid})

Safety and privacy
- The app can remember your Student ID and birthday locally to save typing; it’s a small JSON file under your user profile
- If you prefer not to store it, delete the file mentioned in the docs or use the Reset button

If you do write a little code
- Start small: tweak a label, improve a log message, fix a typo
- Always test by running `python main.py`
- If you need to edit Linux system files (like DNF config), the app will use pkexec to prompt for permission automatically

Where to start if you’re totally new
- Read: `docs/BEGINNERS_GUIDE.md`
- Skim: “ICT Society Autoconnect Short Project.md” (big picture)
- Try: Run the app and press Test Connection first — that’s a safe button
- If stuck: file an issue with a screenshot of the error and your OS info

Thank you
- This project exists to make life easier for students. Your input — even if it’s just “this button name confused me” — is useful.
- If you helped someone get online faster using this app, you already contributed.

Build notes (for contributors who want an exe)
- A simple automated build script exists at `build.ps1` for Windows. Run it from an elevated PowerShell to produce a packaged application in `build_output`.
- The repository includes a PyInstaller spec file `build_exe.spec`. You can also run `pyinstaller build_exe.spec` manually.
