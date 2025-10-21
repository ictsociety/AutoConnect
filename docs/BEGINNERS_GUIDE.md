# UNESWA WiFi AutoConnect — Beginner’s Guide

Updated: 2025-10-14

What this project does 
- Helps your laptop connect to the UNESWA Wi‑Fi.
- Adds the campus proxy for browsers and tools that need it, so the internet actually works on campus.
- (Optional) Registers your device on the university’s netreg portal so you’re allowed through the gate.

You can run the app, type your Student ID and birthday (formatted as explained in the app), hit Complete Setup, and it does the boring parts for you.

Sections in the project (and what they do)

1) Wi‑Fi (src/network/wifi_manager.py)
- Windows: Builds a Wi‑Fi profile for the uniswawifi-students network and stores your WPA2‑Enterprise credentials in Windows the same way the OS would if you typed them in manually. Under the hood, it calls the Windows WLAN API (the built‑in Wi‑Fi system). You’ll see “XML” in the code — that’s just the format Windows uses to describe network profiles.
- Linux: Uses NetworkManager (nmcli) to create a connection for the SSID with the right EAP settings (PEAP + MSCHAPv2) and your username/password. It enables autoconnect so you don’t have to re‑do it every boot.

1) Proxy (src/network/proxy_manager.py)
- Why this matters: On campus, normal browsing might work, but downloads and package managers (dnf/apt/pacman) can fail unless your system knows to go through the proxy.
- Windows:
  - Manual proxy: Writes the proxy host/port into the Windows Internet settings (this is stored in the “Windows registry”, which is basically a big key‑value database Windows uses for settings).
  - PAC (Proxy Auto‑Config): You can also point Windows to a PAC URL. A PAC file is a tiny script that tells your computer which proxy to use for which websites. The project now uses the official university PAC URL.
  - WinHTTP (system services): Some command‑line tools and services don’t look at browser settings at all. Windows has a separate “WinHTTP” proxy setting for those. The project can set it automatically so those tools also work.
- Linux:
  - Exports proxy variables in your shell (http_proxy/https_proxy) so your terminal and many apps pick them up.
  - For Fedora/RHEL/CentOS, it edits /etc/dnf/dnf.conf to add a proxy line because DNF ignores your session env vars. This edit is done using pkexec so you don’t have to run the whole app as root.
  - Tries to set desktop proxy preferences for GNOME/KDE where possible.

1) Device Registration (src/network/device_registry.py)
- Some networks make you “register” your device/browser before letting traffic through. The app tries the netreg page first, fills obvious fields (username/password), and falls back to a legacy endpoint if the newer page is being fussy.
- If registration isn’t needed where you are, it just won’t find a portal and moves on.

1) UI (src/ui/main_window.py)
- A simple window with fields for Student ID and birthday, buttons for each task, and a tiny log area that tells you what just happened.
- There’s a language toggle (English/siSwati), keyboard shortcuts, and a status bar showing if Wi‑Fi and proxy are set up.

What are the “Windows registry” and “XML profiles”?
- The Windows registry is where Windows stores a lot of system and app settings. Think of it like a system settings database. To enable the proxy, we write values into a specific place in that database for your user account.
- Windows uses XML documents to define Wi‑Fi profiles (what the SSID is, what kind of security it has, and so on). The app creates one of these with the right flags and gives it to Windows. You don’t have to read or edit the XML yourself; the app handles it.

What is a PAC file?
- PAC stands for Proxy Auto‑Config. It’s a small script (usually ending in .pac) that tells your computer “use the proxy for these sites, connect directly for those”. Browsers know how to use PAC files. Some command‑line tools do not.

Why does Linux ask for a password sometimes?
- Editing files under /etc or restarting system services needs admin rights. Instead of telling you to run the whole app with sudo (which is clunky and not great for a GUI), the app uses pkexec to ask for permission only when it’s absolutely necessary. You’ll see a prompt when it needs that.

Troubleshooting tips
- Wi‑Fi connects but the internet still doesn’t work:
  - On Windows, check that either the manual proxy or the PAC is set. If your command‑line tools still fail, the WinHTTP proxy might need to be set — the app can do that.
  - On Linux, Fedora/RHEL/CentOS often need that dnf.conf proxy line added; the app will try to add it and might ask for your password via pkexec.
- Registration pages timing out:
  - Try again on campus Wi‑Fi. Some portals only answer from inside campus.
- If something breaks, look in the logs/ folder for a timestamped log and paste the last lines into your bug report.

What changed on 2025‑10‑14 (in human words)
- The Windows PAC setting now points to the real PAC script hosted by the university.
- There’s an option to also configure the WinHTTP proxy so command‑line tools behave.
- On Linux, editing system files and restarting NetworkManager now happens via pkexec. You don’t need to start the app with sudo anymore.

Keep your expectations honest
- The campus network isn’t always consistent. Sometimes browsers work while CLI tools don’t. This project tries to bridge those gaps without making you learn all the knobs. If you’re curious, the source is right here; it’s all straightforward Python.
