#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Main UI Window
ICT Society Initiative - University of Eswatini

Dark-themed application window for UNESWA Wi‑Fi setup.
Handles student authentication, Wi‑Fi connection, proxy configuration, and device registration.
"""

import customtkinter as ctk
import tkinter.messagebox as msgbox
import threading
import time
from typing import Optional, Callable
from pathlib import Path

from src.config import (
    APP_NAME,
    VERSION,
    UI_THEME,
    UI_COLOR_THEME,
    UI_WINDOW_SIZE,
    UI_RESIZABLE,
    STATUS_MESSAGES,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES,
    PASSWORD_FORMAT_HINT,
    MONITOR_INTERVAL,
    SCROLLABLE_FRAME_CORNER_RADIUS,
    SCROLLBAR_BUTTON_COLOR,
    SCROLLBAR_BUTTON_HOVER_COLOR,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
)

from src.network import network_manager
from src.utils import (
    is_admin,
    can_configure_network,
    get_os_type,
    get_distro_id,
    system_info,
    run_quick_test,
)
from src.utils.credentials import save_credentials, load_credentials

# Translations for key UI labels (English + siSwati)
TRANSLATIONS = {
    "en": {
        "language": "Language",
        "student_credentials_title": "Student credentials",
        "student_id": "Student ID:",
        "birthday": "Birthday:",
        "birthday_hint": PASSWORD_FORMAT_HINT,
        "complete_setup": "Complete setup (Ctrl+Enter / F5)",
        "wifi_only": "WiFi only",
        "proxy_only": "Proxy only",
        "register_device": "Register device",
        "test_connection": "Test connection (Ctrl+T)",
        "reset_uneswa": "Reset UNESWA only (Ctrl+R)",
        "activity_log": "Activity log",
    },
    "ss": {
        "language": "Lulwimi",
        "student_credentials_title": "Tincumo tekungena",
        "student_id": "Inombolo Yemfundzi:",
        "birthday": "Lusuku Lwekutalwa:",
        "birthday_hint": PASSWORD_FORMAT_HINT,  # keep original hint text for now
        "complete_setup": "Cwedza kwalungiselela",
        "wifi_only": "WiFi kuphela",
        "proxy_only": "Proxy kuphela",
        "register_device": "Bhalisa lidivaysi",
        "test_connection": "Hlola kuxhumeka",
        "reset_uneswa": "Buyisela UNESWA kuphela",
        "activity_log": "Umbhalo wekwentiwa",
    },
}




class StatusBar(ctk.CTkFrame):
    """Status bar showing connection information"""

    def __init__(self, parent):
        super().__init__(parent)

        self.wifi_status = ctk.CTkLabel(self, text="WiFi: Disconnected", anchor="w")
        self.wifi_status.pack(side="left", padx=(10, 20))

        self.proxy_status = ctk.CTkLabel(
            self, text="Proxy: Not configured", anchor="w"
        )
        self.proxy_status.pack(side="left", padx=(0, 20))

        self.overall_status = ctk.CTkLabel(
            self, text="Status: Not connected", anchor="e", font=ctk.CTkFont(weight="bold")
        )
        self.overall_status.pack(side="right", padx=(0, 10))

    def update_status(self, wifi_connected: bool, proxy_configured: bool):
        """Update status indicators"""
        # WiFi status
        if wifi_connected:
            self.wifi_status.configure(text="WiFi: Connected")
        else:
            self.wifi_status.configure(text="WiFi: Disconnected")

        # Proxy status
        if proxy_configured:
            self.proxy_status.configure(text="Proxy: Configured")
        else:
            self.proxy_status.configure(text="Proxy: Not configured")

        # Overall status
        if wifi_connected and proxy_configured:
            self.overall_status.configure(text="Status: Fully connected")
        elif wifi_connected:
            self.overall_status.configure(text="Status: Partially connected")
        else:
            self.overall_status.configure(text="Status: Not connected")


class CredentialsFrame(ctk.CTkFrame):
    """Frame for entering student credentials"""

    def __init__(self, parent, translator: Optional[Callable[[str], str]] = None):
        super().__init__(parent)
        # Lambda is a quick way to create a tiny function without using 'def'.
        # Here: if no translator is provided, use a lambda that just returns the key unchanged.
        # This is like saying: translator = lambda k: k  (a function that returns its input)
        self._t = translator or (lambda k: k)

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="x", padx=20, pady=15)

        # Title
        self.title_label = ctk.CTkLabel(
            self.content_frame,
            text=self._t("student_credentials_title"),
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.title_label.pack(pady=(0, 15))

        # Student ID
        self.student_id_label = ctk.CTkLabel(self.content_frame, text=self._t("student_id"))
        self.student_id_label.pack(anchor="w")
        
        self.student_id_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.student_id_frame.pack(fill="x", pady=(5, 10))
        # Mask Student ID by default (shared labs/screens). Users can toggle visibility.
        self.student_id_entry = ctk.CTkEntry(
            self.student_id_frame, placeholder_text="e.g., 2021/1234 or 20211234", show="*"
        )
        self.student_id_entry.pack(side="left", fill="x", expand=True)
        
        self.student_id_visible = False
        self.student_id_toggle = ctk.CTkButton(
            self.student_id_frame,
            text="Show",
            width=60,
            command=self._toggle_student_id_visibility,
        )
        self.student_id_toggle.pack(side="right", padx=(10, 0))

        # Lambda creates a small inline function. When user presses Enter in Student ID field,
        # this lambda receives the event (e) and moves focus to the birthday field.
        # Without lambda, we'd need to define a separate function just for this one line.
        self.student_id_entry.bind("<Return>", lambda e: self.birthday_entry.focus())

        # Birthday
        self.birthday_label = ctk.CTkLabel(
            self.content_frame, text=self._t("birthday")
        )
        self.birthday_label.pack(anchor="w", pady=(10, 0))
        
        self.birthday_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.birthday_frame.pack(fill="x", pady=5)
        
        self.birthday_entry = ctk.CTkEntry(
            self.birthday_frame, 
            placeholder_text="e.g., 010199 or 01011999 (1st Jan 1999)",
            show="*"
        )
        self.birthday_entry.pack(side="left", fill="x", expand=True)
        
        self.birthday_visible = False
        self.birthday_toggle = ctk.CTkButton(
            self.birthday_frame,
            text="Show",
            width=60,
            command=self._toggle_birthday_visibility,
        )
        self.birthday_toggle.pack(side="right", padx=(10, 0))

        # Bind Enter key to validate and focus complete setup
        self.birthday_entry.bind("<Return>", self._handle_birthday_enter)

        # Validation info
        self.info_label = ctk.CTkLabel(
            self.content_frame,
            text=self._t("birthday_hint"),
            text_color="gray60",
            font=ctk.CTkFont(size=11),
        )
        self.info_label.pack(pady=10)

    def _toggle_student_id_visibility(self):
        self.student_id_visible = not self.student_id_visible
        if self.student_id_visible:
            self.student_id_entry.configure(show="")
            self.student_id_toggle.configure(text="Hide")
        else:
            self.student_id_entry.configure(show="*")
            self.student_id_toggle.configure(text="Show")
    
    def _toggle_birthday_visibility(self):
        self.birthday_visible = not self.birthday_visible
        if self.birthday_visible:
            self.birthday_entry.configure(show="")
            self.birthday_toggle.configure(text="Hide")
        else:
            self.birthday_entry.configure(show="*")
            self.birthday_toggle.configure(text="Show")

    def _handle_birthday_enter(self, event):
        """Handle Enter key in birthday field"""
        # Validate and trigger setup if valid
        valid, message = self.validate_credentials()
        if valid:
            # Focus will be handled by the complete setup action
            # Reach up to the main window to trigger the action; avoids passing callbacks
            # through multiple frames. Ugly but works for this small UI.
            self.master.master._do_complete_setup()  # Navigate up to main window
        else:
            # Show validation error briefly
            import tkinter.messagebox as msgbox

            msgbox.showerror("Invalid Input", message)

    def get_credentials(self) -> tuple[str, str]:
        """Get entered credentials"""
        return (self.student_id_entry.get().strip(), self.birthday_entry.get().strip())

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate credential format
        
        We do basic checks here (not empty), then delegate to the network layer
        for detailed validation. This keeps the validation logic in one place.
        """
        student_id, birthday = self.get_credentials()

        if not student_id:
            return False, "Student ID is required"

        if not birthday:
            return False, "Birthday is required"
        # Delegate to network layer normalization/validation so behavior is consistent
        try:
            from src.network.wifi_manager import validate_wifi_credentials

            valid, message = validate_wifi_credentials(student_id, birthday)
            if valid:
                return True, "Credentials are valid"
            else:
                return False, message
        except Exception as e:
            return False, str(e)

    def apply_language(self, t: Callable[[str], str]):
        """Apply translated texts to labels and placeholders"""
        self._t = t
        self.title_label.configure(text=t("student_credentials_title"))
        self.student_id_label.configure(text=t("student_id"))
        self.birthday_label.configure(text=t("birthday"))
        self.info_label.configure(text=t("birthday_hint"))
        # Placeholders
        self.student_id_entry.configure(placeholder_text="e.g., 2021/1234 or 20211234")
        self.birthday_entry.configure(
            placeholder_text="e.g., 010199 or 01011999 (1st Jan 1999)"
        )


class ActionButtonsFrame(ctk.CTkFrame):
    """Frame containing action buttons"""

    def __init__(self, parent, callbacks: dict, translator: Optional[Callable[[str], str]] = None):
        super().__init__(parent)
        self.callbacks = callbacks
        # Lambda fallback: if no translator provided, return the key as-is
        self._t = translator or (lambda k: k)

        # Main setup button
        self.setup_btn = ctk.CTkButton(
            self,
            text=self._t("complete_setup"),
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            command=self.callbacks.get("complete_setup"),
        )
        self.setup_btn.pack(fill="x", padx=20, pady=(15, 10))

        # Individual action buttons frame
        individual_frame = ctk.CTkFrame(self)
        individual_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            individual_frame,
            text="Individual Actions:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(pady=(10, 5))

        # Button grid for better alignment
        btn_grid = ctk.CTkFrame(individual_frame, fg_color="transparent")
        btn_grid.pack(fill="x", padx=10, pady=5)
        btn_grid.grid_columnconfigure((0, 1, 2), weight=1)

        self.wifi_btn = ctk.CTkButton(
            btn_grid, text=self._t("wifi_only"), command=self.callbacks.get("wifi_only")
        )
        self.wifi_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.proxy_btn = ctk.CTkButton(
            btn_grid, text=self._t("proxy_only"), command=self.callbacks.get("proxy_only")
        )
        self.proxy_btn.grid(row=0, column=1, padx=5, sticky="ew")

        self.register_btn = ctk.CTkButton(
            btn_grid,
            text=self._t("register_device"),
            command=self.callbacks.get("register_device"),
        )
        self.register_btn.grid(row=0, column=2, padx=5, sticky="ew")

        # Second row in grid
        self.test_btn = ctk.CTkButton(
            btn_grid,
            text=self._t("test_connection"),
            command=self.callbacks.get("test_connection"),
        )
        self.test_btn.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

        self.reset_btn = ctk.CTkButton(
            btn_grid,
            text=self._t("reset_uneswa"),
            text_color="orange",
            command=self.callbacks.get("reset_all"),
        )
        self.reset_btn.grid(row=1, column=2, padx=5, pady=10, sticky="ew")

    def set_buttons_enabled(self, enabled: bool):
        """Enable/disable all buttons"""
        state = "normal" if enabled else "disabled"

        for btn in [
            self.setup_btn,
            self.wifi_btn,
            self.proxy_btn,
            self.register_btn,
            self.test_btn,
            self.reset_btn,
        ]:
            btn.configure(state=state)

    def apply_language(self, t: Callable[[str], str]):
        self._t = t
        self.setup_btn.configure(text=t("complete_setup"))
        self.wifi_btn.configure(text=t("wifi_only"))
        self.proxy_btn.configure(text=t("proxy_only"))
        self.register_btn.configure(text=t("register_device"))
        self.test_btn.configure(text=t("test_connection"))
        self.reset_btn.configure(text=t("reset_uneswa"))


class LogFrame(ctk.CTkFrame):
    """Frame for displaying log messages"""

    def __init__(self, parent):
        super().__init__(parent)

        # Content frame for consistent padding
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.content_frame,
            text="Activity log",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=(0, 10))

        # Log display - fixed height for scrollable container
        self.log_display = ctk.CTkTextbox(
            self.content_frame,
            height=150,
            state="disabled",
            corner_radius=6
        )
        self.log_display.pack(fill="x", pady=(0, 5))

    def add_log(self, message: str):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.log_display.configure(state="normal")
        self.log_display.insert("end", log_entry)
        self.log_display.see("end")
        self.log_display.configure(state="disabled")

    def apply_language(self, t: Callable[[str], str]):
        self.title_label.configure(text=t("activity_log"))

    def clear_log(self):
        """Clear log messages"""
        self.log_display.configure(state="normal")
        self.log_display.delete("1.0", "end")
        self.log_display.configure(state="disabled")


class UNESWAWiFiApp:
    """Main application class"""

    def __init__(self):
        # Dark mode enforcement
        ctk.set_appearance_mode(UI_THEME)
        ctk.set_default_color_theme(UI_COLOR_THEME)

        # Main window setup
        self.root = ctk.CTk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry(UI_WINDOW_SIZE)
        self.root.resizable(UI_RESIZABLE, UI_RESIZABLE)

        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        self._set_app_icon()
        self._setup_keyboard_shortcuts()

        self.os_type = get_os_type()
        self.has_admin = is_admin()
        self.can_configure = can_configure_network()

        # UI state
        self.is_running_operation = False
        self.monitor_thread = None
        self.monitor_running = False

        self._init_localization()
        self._build_header()
        self._build_main_content()
        self._build_footer()

        self._start_monitoring()
        self._update_connection_status()
        self._load_saved_credentials()
        self._apply_language_to_ui()

    # --- Localization helpers ---
    def _init_localization(self):
        self.current_language = "en"

    def _t(self, key: str) -> str:
        lang = TRANSLATIONS.get(getattr(self, "current_language", "en"), TRANSLATIONS["en"])
        return lang.get(key, TRANSLATIONS["en"].get(key, key))

    def _apply_language_to_ui(self):
        try:
            self.language_btn.configure(text=self._t("language"))
            self.credentials_frame.apply_language(self._t)
            self.buttons_frame.apply_language(self._t)
            self.log_frame.apply_language(self._t)
        except Exception:
            pass

    def _toggle_language(self):
        self.current_language = "ss" if self.current_language == "en" else "en"
        self._apply_language_to_ui()
    def _load_saved_credentials(self):
        try:
            sid, bday = load_credentials()
            if sid:
                self.credentials_frame.student_id_entry.delete(0, "end")
                self.credentials_frame.student_id_entry.insert(0, sid)
            if bday:
                self.credentials_frame.birthday_entry.delete(0, "end")
                self.credentials_frame.birthday_entry.insert(0, bday)
            if sid or bday:
                self._log("Loaded saved credentials")
        except Exception:
            pass

    def _setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for common actions"""
        # Lambda functions here convert keyboard events into method calls.
        # tkinter's bind() expects a function that takes an event parameter (e),
        # but we don't need the event - we just want to call our methods.
        # Lambda lets us write this in one line instead of defining separate functions.
        self.root.bind("<Control-Return>", lambda e: self._do_complete_setup())
        self.root.bind("<F5>", lambda e: self._do_complete_setup())
        self.root.bind("<Control-t>", lambda e: self._do_test_connection())
        self.root.bind("<Control-r>", lambda e: self._do_reset_all())
        self.root.bind("<F1>", lambda e: self._show_help())
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        self.root.bind("<Tab>", self._handle_tab_navigation)

    def _handle_tab_navigation(self, event):
        """Handle tab navigation between input fields"""
        event.widget.tk_focusNext().focus()
        return "break"

    def _show_help(self):
        """Show help dialog with keyboard shortcuts"""
        import tkinter.messagebox as msgbox

        help_text = f"""{APP_NAME} v{VERSION}

Keyboard Shortcuts:
• Ctrl+Enter or F5 - Complete Setup
• Ctrl+T - Test Connection
• Ctrl+R - Reset UNESWA Settings Only
• F1 - Show this help
• Ctrl+Q - Quit application
• Tab - Navigate between fields

Usage:
1. Enter your Student ID
2. Enter birthday in ddmmyy format
3. Click Complete Setup or press F5

ICT Society - University of Eswatini"""

        msgbox.showinfo("Help & Shortcuts", help_text)

    def _set_app_icon(self):
        """Try to set application icon"""
        try:
            icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass  # Icon not critical


    def _build_header(self):
        """Build application header"""
        header = ctk.CTkFrame(self.root)
        header.pack(fill="x", padx=15, pady=(15, 10))

        # App title
        title = ctk.CTkLabel(
            header,
            text="UNESWA WiFi AutoConnect",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=15)

        # Language toggle on the right
        self.language_btn = ctk.CTkButton(
            header, text=self._t("language"), width=120, command=self._toggle_language
        )
        self.language_btn.pack(side="right", padx=(0, 5), pady=(5, 0))

        # System info
        system_text = f"{system_info.get_system_summary()}"
        if not self.can_configure:
            system_text += " (Limited privileges)"
        elif self.has_admin:
            system_text += " (Administrator)"

        ctk.CTkLabel(
            header,
            text=system_text,
            text_color="gray70",
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 10))

    def _build_main_content(self):
        """Build main content area with scrollable frame"""
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.root,
            corner_radius=SCROLLABLE_FRAME_CORNER_RADIUS,
            scrollbar_button_color=SCROLLBAR_BUTTON_COLOR,
            scrollbar_button_hover_color=SCROLLBAR_BUTTON_HOVER_COLOR,
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.status_bar = StatusBar(self.scrollable_frame)
        self.status_bar.pack(fill="x", padx=10, pady=(10, 10))

        # Credentials frame
        self.credentials_frame = CredentialsFrame(self.scrollable_frame, translator=self._t)
        self.credentials_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Action buttons
        callbacks = {
            "complete_setup": self._do_complete_setup,
            "wifi_only": self._do_wifi_only,
            "proxy_only": self._do_proxy_only,
            "register_device": self._do_register_device,
            "test_connection": self._do_test_connection,
            "reset_all": self._do_reset_all,
        }
        self.buttons_frame = ActionButtonsFrame(self.scrollable_frame, callbacks, translator=self._t)
        self.buttons_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.log_frame = LogFrame(self.scrollable_frame)
        self.log_frame.pack(fill="x", padx=10, pady=(0, 10))

        padding_frame = ctk.CTkFrame(
            self.scrollable_frame, height=20, corner_radius=0, fg_color="transparent"
        )
        padding_frame.pack(fill="x", pady=(0, 10))

    def _build_footer(self):
        """Build application footer"""
        footer = ctk.CTkFrame(self.root)
        footer.pack(fill="x", padx=15, pady=(0, 15))

        footer_text = "ICT Society - University of Eswatini"
        ctk.CTkLabel(
            footer, text=footer_text, text_color="gray60", font=ctk.CTkFont(size=10)
        ).pack(pady=8)

    def _log(self, message: str):
        """Add message to log"""
        self.log_frame.add_log(message)

    def _run_operation(self, operation: Callable, operation_name: str):
        """Run operation in background thread with UI updates
        
        Network operations can take several seconds. If we run them on the main thread,
        the UI freezes and looks broken. So we run them in a background thread and
        update the UI when done.
        
        Threading basics: Python can run multiple things at once using threads.
        - Main thread: Handles UI (button clicks, window updates)
        - Worker thread: Does slow network stuff (WiFi connection, proxy setup)
        This keeps the UI responsive while work happens in the background.
        """
        if self.is_running_operation:
            self._log(f"{operation_name} already in progress")
            return

        # Define a worker function that will run in the background thread
        def worker():
            self.is_running_operation = True
            self.buttons_frame.set_buttons_enabled(False)  # Prevent double-clicks

            try:
                self._log(f"Starting {operation_name}...")
                operation()  # This is the actual work (connect WiFi, etc.)
            except Exception as e:
                self._log(f"{operation_name} failed: {e}")
            finally:
                self.is_running_operation = False
                self.buttons_frame.set_buttons_enabled(True)
                self._update_connection_status()

        # Create and start the background thread
        # daemon=True means the thread dies when the main program exits
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _do_complete_setup(self):
        """Complete network setup
        
        This is the main "do everything" button - connects WiFi, sets up proxy,
        and registers the device. Most users will just use this.
        """

        def setup():
            # Validate first - no point trying to connect with bad credentials
            valid, message = self.credentials_frame.validate_credentials()
            if not valid:
                self._log(f"{message}")
                return

            student_id, birthday = self.credentials_frame.get_credentials()

            # Save credentials so users don't have to retype them every time
            # This is just convenience - we store them in plaintext in the user's home dir
            try:
                if save_credentials(student_id, birthday):
                    self._log("Credentials saved for next time")
            except Exception:
                pass  # Not critical if this fails

            self._log("Starting complete network setup...")
            results = network_manager.complete_setup(student_id, birthday)

            if results["wifi"]["success"]:
                self._log(f"WiFi: {results['wifi']['message']}")
            else:
                self._log(f"WiFi: {results['wifi']['message']}")

            if results["proxy"]["success"]:
                self._log(f"Proxy: {results['proxy']['message']}")
            else:
                self._log(f"Proxy: {results['proxy']['message']}")

            if results["registration"]["success"]:
                self._log(f"Registration: {results['registration']['message']}")
            else:
                self._log(f"Registration: {results['registration']['message']}")

            self._log(f"{results['overall']['message']}")

        self._run_operation(setup, "Complete Setup")

    def _do_wifi_only(self):
        """WiFi connection only"""

        def wifi_connect():
            valid, message = self.credentials_frame.validate_credentials()
            if not valid:
                self._log(f"{message}")
                return

            student_id, birthday = self.credentials_frame.get_credentials()
            try:
                save_credentials(student_id, birthday)
            except Exception:
                pass
            
            success, message = network_manager.wifi.connect(student_id, birthday)

            if success:
                self._log(f"{message}")
                ok, test_msg = run_quick_test()
                if ok:
                    self._log(f"Connection test: {test_msg}")
                else:
                    self._log(f"Connection test: {test_msg}")
            else:
                self._log(f"{message}")

        self._run_operation(wifi_connect, "WiFi Connection")

    def _do_proxy_only(self):
        """Proxy configuration only"""

        def proxy_config():
            success, message = network_manager.proxy.enable_proxy()

            if success:
                self._log(f"Proxy configured: {message}")
            else:
                self._log(f"Proxy failed: {message}")

        self._run_operation(proxy_config, "Proxy Configuration")

    def _do_register_device(self):
        """Device registration only"""

        def device_reg():
            valid, message = self.credentials_frame.validate_credentials()
            if not valid:
                self._log(f"{message}")
                return

            student_id, birthday = self.credentials_frame.get_credentials()
            try:
                save_credentials(student_id, birthday)
            except Exception:
                pass
            result = network_manager.registry.register_device(student_id, birthday)

            if result.success:
                self._log(f"Device registered: {result.message}")
            else:
                self._log(f"Registration failed: {result.message}")

        self._run_operation(device_reg, "Device Registration")

    def _do_test_connection(self):
        """Test connection"""

        def test_conn():
            self._log("Testing connection...")
            success, message = run_quick_test()

            if success:
                self._log(f"Connection test: {message}")
            else:
                self._log(f"Connection test: {message}")

        self._run_operation(test_conn, "Connection Test")

    def _do_reset_all(self):
        """Reset all network settings"""

        def reset():
            if msgbox.askyesno(
                "Reset UNESWA Network Settings",
                "Reset UNESWA network settings?\n\nThis will:\n- Disconnect from UNESWA WiFi\n- Remove UNESWA WiFi profiles ONLY\n- Disable proxy settings\n\n(Other WiFi networks will be preserved)",
            ):
                self._log("Resetting UNESWA network settings...")
                self._log("Note: Only UNESWA WiFi profiles will be removed")
                results = network_manager.reset_all_settings()

                for operation, result in results.items():
                    if operation != "overall":
                        if result["success"]:
                            self._log(f"{operation}: {result['message']}")
                        else:
                            self._log(f"{operation}: {result['message']}")

                self._log(f"{results['overall']['message']}")

        self._run_operation(reset, "Reset UNESWA Settings")

    def _update_connection_status(self):
        """Update connection status indicators"""
        try:
            wifi_connected = network_manager.wifi.is_connected()
            proxy_configured = network_manager.proxy.is_proxy_configured()

            self.status_bar.update_status(wifi_connected, proxy_configured)

        except Exception as e:
            self._log(f"Status update error: {e}")

    def _start_monitoring(self):
        """Start background connection monitoring
        
        We check WiFi/proxy status every 30 seconds and update the status bar.
        This runs in a background thread so it doesn't freeze the UI.
        """

        def monitor():
            self.monitor_running = True
            while self.monitor_running:
                try:
                    self._update_connection_status()
                    time.sleep(MONITOR_INTERVAL)  # Wait 30 seconds between checks
                except Exception:
                    time.sleep(MONITOR_INTERVAL)  # Keep going even if check fails

        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()

    def run(self):
        """Start the application"""
        self._log(f"{APP_NAME} v{VERSION} started")
        self._log(f"System: {system_info.get_system_summary()}")

        if not self.can_configure:
            self._log("Limited privileges - some features may not work")

        self.root.mainloop()

        # Cleanup
        self.monitor_running = False


def main():
    """Application entry point"""
    try:
        app = UNESWAWiFiApp()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication closed by user")
    except Exception as e:
        msgbox.showerror("Application Error", f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
