# musica.py
from pathlib import Path
import pygame

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "assets" / "audio"
SFX_DIR   = AUDIO_DIR / "sfx"

# ------------ Música (igual que antes) ------------
LIB = {
    "menu":   AUDIO_DIR / "menu.ogg",
    "nivel1": AUDIO_DIR / "nivel1.ogg",
}

_inited = False
_current = None

def _ensure_init():
    global _inited
    if not _inited:
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

# ------------ Efectos de sonido (nuevo) ------------
# Mapea nombres → archivos. Cambia los nombres si tus archivos se llaman distinto.
SFX_LIB = {
    "jump":  SFX_DIR / "jump.wav",
    "coin":  SFX_DIR / "coin.wav",
    "click": SFX_DIR / "click.wav",
}

# Caché de pygame.mixer.Sound
_SFX_CACHE = {}

def sfx(name: str, volume=1.0):
    """Reproduce un efecto por nombre. Carga bajo demanda y cachea."""
    _ensure_init()
    path = SFX_LIB.get(name)
    if not path:
        raise KeyError(f"SFX '{name}' no está definido en SFX_LIB")
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de SFX: {path}")

    snd = _SFX_CACHE.get(name)
    if snd is None:
        snd = pygame.mixer.Sound(str(path))
        _SFX_CACHE[name] = snd
    snd.set_volume(max(0.0, min(1.0, volume)))

    # Usa un canal libre para no cortar otros sonidos
    ch = pygame.mixer.find_channel()
    if ch:
        ch.play(snd)
    else:
        snd.play()
