#!/usr/bin/env python3
"""
UNESWA WiFi AutoConnect - Translation System
ICT Society Initiative - University of Eswatini

Bilingual support for English and siSwati.

Change history:
 - 2025-10-14: Cleaned comments for clarity and removed informal notes
"""

# Language codes
LANG_ENGLISH = "en"
LANG_SISWATI = "ss"

# Default language
DEFAULT_LANGUAGE = LANG_ENGLISH

# Translation dictionary
TRANSLATIONS = {
    # Application strings
    "app_name": {
        "en": "UNESWA WiFi AutoConnect",
        "ss": "UNESWA WiFi AutoConnect",
    },
    "developer": {
        "en": "ICT Society - University of Eswatini",
        "ss": "ICT Society - Inyuvesi yaseSwatini",
    },
    
    # Connection messages
    "connection_success": {
        "en": "Successfully connected to UNESWA WiFi",
        "ss": "Ukhonile kuxhumeka ku-UNESWA WiFi",
    },
    "connection_failed": {
        "en": "Connection failed",
        "ss": "Kuxhumeka kuhlulekile",
    },
    "connection_pending": {
        "en": "Connection pending - credentials required",
        "ss": "Kuxhumeka kusalindele - kudzingeka tincukacha",
    },
    "credentials_required": {
        "en": "Credentials Required",
        "ss": "Kudzingeka Tincukacha",
    },
    "windows_prompt_message": {
        "en": "Windows will prompt for credentials.\n\nPlease enter:\nUsername: {username}\nPassword: Uneswa[your birthday]\n\nThe credential dialog should appear shortly.",
        "ss": "Windows itawucela tincukacha.\n\nSicela ufake:\nLigama lemsebenti: {username}\nLiphasiwedi: Uneswa[lusuku lwakho lekutalwa]\n\nSiboniso setincukacha sitawuvela maduze.",
    },
    "action_needed_title": {
        "en": "Action Needed",
        "ss": "Kudzingeka Kwenteka",
    },
    "action_needed_message": {
        "en": "Windows did not accept stored EAP credentials; interactive prompt is required.\n\nNext steps:\n1. Click Wi‑Fi icon and select {ssid}.\n2. Enter your Student ID as username and UneswaDDMMYYYY as password.\n3. Check 'Remember my credentials' if shown.",
        "ss": "Windows ayakamukelanga tincukacha te-EAP; kudzingeka ufake ngesandla.\n\nTinyatselo letilandelako:\n1. Chofoza sitfombe se-Wi‑Fi bese ukhetsa {ssid}.\n2. Faka inombolo yakho yesifundziswa njengemagama lemsebenti kanye ne-UneswaDDMMYYYY njengeliphasiwedi.\n3. Chofoza 'Khumbula tincukacha tami' uma kuboniswa.",
    },
    
    # Profile management
    "profile_added": {
        "en": "WiFi profile '{ssid}' added successfully",
        "ss": "Iphrofayela ye-WiFi '{ssid}' yengetiwe ngemphumelelo",
    },
    "profile_removed": {
        "en": "UNESWA WiFi profile '{ssid}' removed successfully",
        "ss": "Iphrofayela ye-UNESWA WiFi '{ssid}' yesusiwe ngemphumelelo",
    },
    "profile_not_found": {
        "en": "UNESWA WiFi profile '{ssid}' not found (already removed)",
        "ss": "Iphrofayela ye-UNESWA WiFi '{ssid}' ayitfolakali (isivele yesusiwe)",
    },
    
    # Credential validation
    "credentials_valid": {
        "en": "Credentials format is valid",
        "ss": "Tincukacha tilungile",
    },
    "credentials_invalid": {
        "en": "Invalid credentials format - expected UneswaDDMMYYYY",
        "ss": "Tincukacha tingalungile - kulindelwe UneswaDDMMYYYY",
    },
    "student_id_empty": {
        "en": "Student ID cannot be empty",
        "ss": "Inombolo yesifundziswa ayikwati kuba ngelutshe",
    },
    "birthday_invalid": {
        "en": "Birthday must be in one of: 'UneswaDDMMYYYY', 'DDMMYYYY' or 'DDMMYY'",
        "ss": "Lusuku lekutalwa kumele lube ngelinye laleti: 'UneswaDDMMYYYY', 'DDMMYYYY' nobe 'DDMMYY'",
    },
    
    # Network status
    "network_available": {
        "en": "Network '{ssid}' is available",
        "ss": "Inethiwekhi '{ssid}' iyatfolakala",
    },
    "network_not_found": {
        "en": "Network '{ssid}' not found - are you in range?",
        "ss": "Inethiwekhi '{ssid}' ayitfolakali - ingabe use-range?",
    },
    "disconnected": {
        "en": "Disconnected from WiFi",
        "ss": "Uphume ku-WiFi",
    },
    "wifi_disabled": {
        "en": "WiFi is disabled",
        "ss": "WiFi ayisebenzi",
    },
    
    # Proxy messages
    "proxy_enabled": {
        "en": "Proxy enabled successfully",
        "ss": "I-proxy inikwe emandla ngemphumelelo",
    },
    "proxy_disabled": {
        "en": "Proxy disabled successfully",
        "ss": "I-proxy ivalwe ngemphumelelo",
    },
    "proxy_configured": {
        "en": "Proxy already configured",
        "ss": "I-proxy isivele ilungiselwe",
    },
    
    # Error messages
    "error": {
        "en": "Error",
        "ss": "Liphutsa",
    },
    "connection_error": {
        "en": "WiFi connection error: {error}",
        "ss": "Liphutsa lekuxhumeka ku-WiFi: {error}",
    },
    "credential_error": {
        "en": "Credential error: {error}",
        "ss": "Liphutsa letincukacha: {error}",
    },
    "profile_setup_failed": {
        "en": "Profile setup failed: {message}",
        "ss": "Kulungiselela iphrofayela kuhlulekile: {message}",
    },
    
    # UI labels
    "student_id": {
        "en": "Student ID",
        "ss": "Inombolo Yesifundziswa",
    },
    "birthday": {
        "en": "Birthday (DDMMYYYY)",
        "ss": "Lusuku Lekutalwa (DDMMYYYY)",
    },
    "password": {
        "en": "Password",
        "ss": "Liphasiwedi",
    },
    "username": {
        "en": "Username",
        "ss": "Ligama Lemsebenti",
    },
    "connect": {
        "en": "Connect",
        "ss": "Xhumeka",
    },
    "disconnect": {
        "en": "Disconnect",
        "ss": "Phuma",
    },
    "status": {
        "en": "Status",
        "ss": "Simo",
    },
    "connected": {
        "en": "Connected",
        "ss": "Kuxhunyiwe",
    },
    "not_connected": {
        "en": "Not Connected",
        "ss": "Akuxhunyiwe",
    },
    "language": {
        "en": "Language",
        "ss": "Lulwimi",
    },
    "english": {
        "en": "English",
        "ss": "SiNgisi",
    },
    "siswati": {
        "en": "siSwati",
        "ss": "siSwati",
    },
}


class TranslationManager:
    """Manages translations for the application"""
    
    def __init__(self, language: str = DEFAULT_LANGUAGE):
        self.language = language
    
    def set_language(self, language: str):
        """Set the current language"""
        if language in [LANG_ENGLISH, LANG_SISWATI]:
            self.language = language
        else:
            self.language = DEFAULT_LANGUAGE
    
    def get(self, key: str, **kwargs) -> str:
        """Get translated string for the current language"""
        if key not in TRANSLATIONS:
            return key
        
        translation = TRANSLATIONS[key].get(self.language, TRANSLATIONS[key].get(LANG_ENGLISH, key))
        
        # Format with provided kwargs if any
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return translation
    
    def get_language(self) -> str:
        """Get current language code"""
        return self.language
    
    def is_siswati(self) -> bool:
        """Check if current language is siSwati"""
        return self.language == LANG_SISWATI


# Global translation manager instance
translator = TranslationManager()


# Convenience function
def t(key: str, **kwargs) -> str:
    """Shorthand for translator.get()"""
    return translator.get(key, **kwargs)
