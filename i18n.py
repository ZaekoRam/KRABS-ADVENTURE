# i18n.py
# No guarda nada. Lee el idioma desde la variable global "settings" inyectada por main.py.

# i18n.py  (añade/actualiza dentro de STRINGS)
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
        "options_title": "OPCIONES (ESC para volver)",
        "language": "Idioma",
        "volume": "Volumen",
        "toggle_language": "Cambiar idioma",
        "back": "Volver",
        "game_over": "PARTIDA TERMINADA",
        "keep_trying": "¡Sigue intentando, tú puedes!",
        "victory": "¡MISIÓN CUMPLIDA!",
        "menu": "Menú",
        "continue": "Continuar",
        "enter_menu": "ENTER/ESPACIO: Menú",
        "select_character": "SELECCIÓN DE PERSONAJE",
        "select_level": "SELECCIÓN DE NIVEL",
        "level": "NIVEL",
        "difficulty": "DIFICULTAD",
        "easy": "PRINCIPIANTE",
        "hard": "DESAFIANTE",
        "level_hint": "Dale clic o 1/2/3 • ESC para volver",
        "diff_hint": "Clic o ←/→ para jugar • ESC para volver",
        "time": "Tiempo",
        "points": "Puntos",
        "press_enter_to_menu": "Pulsa ENTER para volver al menú",
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
        "options_title": "OPTIONS (ESC to go back)",
        "language": "Language",
        "volume": "Volume",
        "toggle_language": "Toggle language",
        "back": "Back",
        "game_over": "GAME OVER",
        "keep_trying": "Keep trying, you can do it!",
        "victory": "MISSION ACCOMPLISHED!",
        "menu": "Menu",
        "continue": "Continue",
        "enter_menu": "ENTER/SPACE: Menu",
        "select_character": "CHARACTER SELECT",
        "select_level": "LEVEL SELECT",
        "level": "LEVEL",
        "difficulty": "DIFFICULTY",
        "easy": "BEGINNER",
        "hard": "CHALLENGING",
        "level_hint": "Click or 1/2/3 • ESC to go back",
        "diff_hint": "Click or ←/→ to play • ESC to go back",
        "time": "Time",
        "points": "Points",
        "press_enter_to_menu": "Press ENTER to return to menu",
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
