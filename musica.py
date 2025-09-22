# musica.py
from pathlib import Path
import pygame

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "assets" / "audio"

LIB = {
    "menu": AUDIO_DIR / "menu.ogg",
    "nivel1": AUDIO_DIR / "nivel1.ogg",
}

_inited = False
_current = None

def _ensure_init():
    global _inited
    if not _inited:
        # mixer se inicializa aquí; pre_init lo harás en main.py antes de pygame.init()
        pygame.mixer.init()
        _inited = True

def play(name: str, loop=True, volumen=0.7, fade_ms=0):
    _ensure_init()
    path = LIB.get(name)
    if not path or not path.exists():
        raise FileNotFoundError(f"No encuentro la pista '{name}' en {AUDIO_DIR}")
    if fade_ms and pygame.mixer.music.get_busy():
        pygame.mixer.music.fadeout(fade_ms)
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.set_volume(max(0.0, min(1.0, volumen)))
    pygame.mixer.music.play(-1 if loop else 0)
    global _current
    _current = name

def switch(name: str, volumen=0.7, crossfade_ms=800):
    global _current
    if name == _current:
        return
    play(name, loop=True, volumen=volumen, fade_ms=crossfade_ms)
    _current = name

def stop(fade_ms=0):
    _ensure_init()
    if fade_ms:
        pygame.mixer.music.fadeout(fade_ms)
    else:
        pygame.mixer.music.stop()
