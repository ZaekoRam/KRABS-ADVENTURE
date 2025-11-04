# i18n.py
# No guarda nada. Lee el idioma desde la variable global "settings" inyectada por main.py.

STRINGS = {
    "es": {
        "lang_select_title": "Selecciona tu idioma",
        "spanish": "Español",
        "english": "Inglés",
        "skip": "Pulsa cualquier tecla para saltar",
        "menu_title": "Menú Principal",
        "play": "Jugar",
        "options": "Opciones",
        "quit": "Salir",
        "options_title": "OPCIONES",
        "language": "Idioma",
        "volume": "Volumen",
        "back": "Volver",
        "game_over": "PARTIDA TERMINADA",
        "keep_trying": "¡Sigue intentándolo, tú puedes!",
        "victory": "¡MISIÓN CUMPLIDA!",
    },
    "en": {
        "lang_select_title": "Select your language",
        "spanish": "Spanish",
        "english": "English",
        "skip": "Press any key to skip",
        "menu_title": "Main Menu",
        "play": "Play",
        "options": "Options",
        "quit": "Quit",
        "options_title": "OPTIONS",
        "language": "Language",
        "volume": "Volume",
        "back": "Back",
        "game_over": "GAME OVER",
        "keep_trying": "Keep trying, you can do it!",
        "victory": "MISSION ACCOMPLISHED!",
    },
}

# Estas variables las "inyectará" main.py antes de usar t()
_settings_ref = {"language": "es"}  # valor por defecto de respaldo

def _inject_settings_ref(settings_dict):
    global _settings_ref
    _settings_ref = settings_dict

def t(key):
    lang = _settings_ref.get("language") or "es"
    table = STRINGS.get(lang, STRINGS["es"])
    return table.get(key, key)
