# UNESWA WiFi AutoConnect

A tool that handles university WiFi connection and proxy setup automatically. Built to solve the common problem where your browser works fine on campus but package managers and command-line tools fail because they don't pick up the proxy settings.

## Why this exists

When you connect to campus WiFi, browsers usually work right away through the captive portal or proxy. But if you try to run `apt update`, `dnf install`, or `pacman -Syu`, they'll fail because they don't use the same proxy settings as your browser.

This happens because different systems handle proxies differently:

- **Ubuntu/Debian**: Usually picks up environment variables or NetworkManager settings. A simple shell export often works.
- **Arch**: Follows environment variables pretty well. System-wide changes in `/etc/environment` usually do the trick.
- **Fedora/RHEL/CentOS**: DNF ignores user-level proxy settings completely. You have to edit `/etc/dnf/dnf.conf` or it won't work at all.
- **Windows**: Registry settings for Internet Explorer/Edge, plus WinHTTP for system services and CLI tools.

The code handles all these cases so you don't have to remember which config file to edit for your particular setup.

## Supported platforms
- **Windows 10/11** - Requires administrator privileges (UAC prompt on startup)
  - Windows 11: Tries the native connection method first, then falls back to the traditional approach if needed
- **Linux** - NetworkManager-based distros (Ubuntu, Debian, Fedora, Arch, Manjaro)

## Features
- **One-click setup** - WiFi, proxy, and device registration in one go
- **Automatic credential storage** - No manual prompts after first connection
  - Windows: Native WLAN API for PEAP/MSCHAPv2 credentials
  - Linux: NetworkManager connection profiles
- **Cross-platform proxy configuration** - Works with browsers and package managers
- **siSwati/English UI** - Language toggle for local users
- **Saved credentials** - Student ID and birthday remembered between sessions
- **Dark mode only** - Better for lab environments

## Important notes

### Windows
- **Administrator privileges required** - The app will prompt for UAC elevation on startup
- **Windows 11 connection behavior**: The app first tries the native Windows connection method. If that doesn't work within 15 seconds, it automatically switches to the traditional credential storage method. This gives you the best chance of connecting without manual intervention.
- First WiFi connection may require manual credential entry due to Windows security policies
- Credential Guard on Windows 11 22H2+ prevents automatic credential storage (this is a Windows security feature, not a bug)

### Fedora/RHEL/CentOS
DNF ignores user-session proxies and needs `/etc/dnf/dnf.conf` configuration. The app handles this automatically using pkexec.

## Quick start

### Windows
1. Install Python 3.8+ and dependencies:
```powershell
pip install -r requirements.txt
```

2. Run the app (will prompt for admin):
```powershell
python main.py
```

### Linux
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
python main.py
```

No sudo needed - pkexec will prompt when system changes are required.

## What the app modifies
The app makes targeted, reversible changes:
- **WiFi profiles** - Adds WPA2-Enterprise profile for uniswawifi-students
- **Proxy settings** - Windows registry or Linux environment variables
- **Shell configs** - Adds proxy exports to `.bashrc`, `.zshrc`, etc. (with backups)
- **DNF config** - Fedora/RHEL only, adds proxy line to `/etc/dnf/dnf.conf`

All changes are scoped to UNESWA settings. Other networks and configs remain untouched. Use "Reset UNESWA Only" to remove all changes.

## Project structure
```
AutoConnect/
├── main.py                 # Entry point launcher
├── src/
│   ├── main.py            # Application entry point
│   ├── config/            # Settings and translations
│   ├── network/           # WiFi, proxy, registration logic
│   ├── ui/                # CustomTkinter GUI
│   └── utils/             # System utilities
├── requirements.txt       # Python dependencies
└── docs/                  # Additional documentation
```

## Security and privacy
- **WiFi credentials** - Stored by OS (Windows WLAN API / NetworkManager)
- **Cached credentials** - Student ID and birthday saved locally:
  - Windows: `%APPDATA%\UNESWAWiFi\credentials.json`
  - Linux: `~/.config/uneswa-wifi/credentials.json`
- **Password format** - Generated as `Uneswa` + birthday (ddmmyyyy)
- **Removal** - Use "Reset UNESWA Only" to clear all stored data

## Troubleshooting
- **Browsers work but package managers fail** - This is why the app exists. Run "Complete Setup" to fix proxy for all tools.
- **Windows credential prompts** - First connection may require manual entry. Check "Remember credentials" when prompted.
- **Fedora DNF fails** - The app should handle this automatically. Check logs for pkexec prompts.
- **System diagnostics** - Run `python main.py --check` to see detailed system info.

## Contributing
Pull requests welcome. Focus on real student pain points. Test on actual hardware when possible.

## License
MIT

---

Update — 2025-10-14

What changed and why
- Windows PAC: The app now uses the official university PAC script: http://www.uniswa.sz/uniswa/uniswaproxy.pac when PAC mode is enabled. Before, the code accidentally pointed PAC to the raw proxy host/port, which isn’t how PAC works.
- WinHTTP (Windows services): There’s an option to also set the WinHTTP proxy (system services and some tools use this). It’s on by default in the settings. If you don’t want it, flip WINDOWS_SETTINGS["configure_winhttp"] to False.
- Linux elevation: You don’t need to run the app with sudo anymore. When a privileged step is required (editing /etc/dnf/dnf.conf, restarting NetworkManager), the app will ask for permission using pkexec. This is cleaner and safer than running the entire GUI as root.
- Housekeeping: Removed the old ad‑hoc test scripts from the repo.

Notes for humans (not automation)
- If you see a password prompt pop up on Linux when enabling/disabling the proxy on Fedora/RHEL/CentOS — that’s pkexec doing its job for a single action.
- If you use Windows PAC in your browser and CLI tools still don’t follow it, that’s normal. CLI tools often ignore browser PAC and look at either the manual proxy or WinHTTP. That’s why the app can also set WinHTTP.
- The previous README line that said “you may need to run the proxy setup parts with sudo” is outdated with this change. Don’t start the app with sudo. Let pkexec handle the single steps that require it.

If something feels off, open an issue and paste the last ~30 lines of the log file from the logs/ folder.

---

**ICT Society - University of Eswatini**  
Built by students, for students. Pass it on if it helps you get online faster.