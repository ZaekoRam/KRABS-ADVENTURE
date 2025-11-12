# musica.py
from pathlib import Path
import pygame

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "assets" / "audio"
MUSIC_DIR = AUDIO_DIR / "musica"        # <— aquí viven victoria.ogg y derrota.ogg
SFX_DIR   = AUDIO_DIR / "sfx"


# ------------ Música ------------

# ===== Volúmenes globales =====
MASTER_VOLUME = 0.8  # control general (slider del menú)
MUSIC_VOLUME  = 1.0  # balance música
SFX_VOLUME    = 1.0  # balance efectos/sfx
JINGLE_VOLUME = 1.0  # balance jingles

# Volumen temporal para cuando el juego está en pausa
VOL_PAUSA = 0.5   # porcentaje del volumen maestro
_is_paused_volume = False

def _clamp01(v: float) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except Exception:
        return 0.0

def _apply_volumes():
    """Aplica volúmenes actuales a música y a lo que ya esté cacheado."""
    _ensure_init()
    # música de fondo
    try:
        pygame.mixer.music.set_volume(_clamp01(MASTER_VOLUME * MUSIC_VOLUME))
    except Exception:
        pass
    # SFX ya cacheados
    for snd in _SFX_CACHE.values():
        snd.set_volume(_clamp01(MASTER_VOLUME * SFX_VOLUME))
    # Jingles ya cacheados (volumen base, el específico se setea al reproducir)
    for snd in _JINGLE_CACHE.values():
        snd.set_volume(_clamp01(MASTER_VOLUME * JINGLE_VOLUME))

def set_master_volume(v: float):
    global MASTER_VOLUME
    MASTER_VOLUME = _clamp01(v)
    _apply_volumes()

def set_music_volume(v: float):
    global MUSIC_VOLUME
    MUSIC_VOLUME = _clamp01(v)
    _apply_volumes()

def set_sfx_volume(v: float):
    global SFX_VOLUME
    SFX_VOLUME = _clamp01(v)
    _apply_volumes()

def set_jingle_volume(v: float):
    global JINGLE_VOLUME
    JINGLE_VOLUME = _clamp01(v)
    _apply_volumes()

LIB = {
    "menu":     AUDIO_DIR / "menu.ogg",
    "nivel0":   AUDIO_DIR / "nivel0.ogg",
    "nivel1":   AUDIO_DIR / "nivel1.ogg",
    "nivel2":   AUDIO_DIR / "nivel2.ogg",
    "nivel3":   AUDIO_DIR / "nivel3.ogg",
}

# Jingles (sin loop) -> se cargan como Sound para evitar bloqueos
JINGLES = {
    "victoria_lvl3": MUSIC_DIR / "victoria_lvl3.ogg",
    "victoria": MUSIC_DIR / "victoria.ogg",
    "derrota":  MUSIC_DIR / "derrota.ogg",
}

# caché de jingles como Sound
_JINGLE_CACHE = {}
# canal dedicado (opcional) para jingles
_JINGLE_CHANNEL_IDX = 7   # usa un canal “alto” para no pisar otros


_inited = False
_current = None

def _ensure_init():
    global _inited
    if not _inited:
        # buffer pequeño para menor latencia (ya usas pre_init(…, 512) en main)
        pygame.mixer.init()
        # reserva explícitamente algunos canales (no obligatorio, pero ayuda a ordenar)
        pygame.mixer.set_num_channels(max(16, pygame.mixer.get_num_channels() or 8))
        # precargar jingles como Sound (lectura de disco una sola vez)
        for name, path in JINGLES.items():
            if not path.exists():
                print(f"[musica] WARNING: jingle {name} no existe: {path}")
                continue
            try:
                _JINGLE_CACHE[name] = pygame.mixer.Sound(str(path))
            except Exception as e:
                print(f"[musica] ERROR cargando jingle {name}: {e}")
        _inited = True

def _play_music(name: str, loop=True, volumen=0.7, fade_ms=0):
    """Reproduce música de fondo usando mixer.music (bloquea un poco al cargar)."""
    _ensure_init()
    path = LIB.get(name)
    if not path or not path.exists():
        raise FileNotFoundError(f"No encuentro la pista '{name}'. Busqué en: {path or AUDIO_DIR}")
    if fade_ms and pygame.mixer.music.get_busy():
        pygame.mixer.music.fadeout(fade_ms)
    else:
        pygame.mixer.music.stop()
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.set_volume(_clamp01(MASTER_VOLUME * MUSIC_VOLUME * volumen))
    pygame.mixer.music.play(-1 if loop else 0)
    global _current
    _current = name


def jingle(name: str, volumen=0.9, fade_music_ms=200, stop_music=True):
    """
    Reproduce un jingle precargado como Sound (NO bloquea).
    Opcionalmente hace fadeout de la música de fondo.
    """
    _ensure_init()
    snd = _JINGLE_CACHE.get(name)
    if not snd:
        raise KeyError(f"Jingle '{name}' no está cargado. Revisa JINGLES y el archivo.")

    if stop_music:
        try:
            if fade_music_ms > 0:
                pygame.mixer.music.fadeout(int(fade_music_ms))
            else:
                pygame.mixer.music.stop()
        except Exception:
            pass

    snd.set_volume(_clamp01(MASTER_VOLUME * JINGLE_VOLUME * volumen))
    # usa canal dedicado si está libre; si no, busca uno libre
    ch = pygame.mixer.Channel(_JINGLE_CHANNEL_IDX)
    if ch.get_busy():
        ch = pygame.mixer.find_channel() or ch
    ch.play(snd)

def play(name: str, loop=True, volumen=0.7, fade_ms=0):
    """Compatibilidad si alguien llama play directo (sólo para música de fondo)."""
    if name in JINGLES:
        # si llaman play con un jingle, reencaminar:
        return jingle(name, volumen=volumen, fade_music_ms=fade_ms, stop_music=True)
    return _play_music(name, loop=loop, volumen=volumen, fade_ms=fade_ms)

def switch(name: str, volumen=0.7, crossfade_ms=600):
    """
    Cambia pista:
      - si es música de fondo: crossfade con mixer.music
      - si es jingle: lo toca como Sound (sin bloqueo) y hace fadeout de la música
    """
    global _current
    if name == _current and name in LIB:
        return
    if name in JINGLES:
        _current = None
        return jingle(name, volumen=volumen, fade_music_ms=crossfade_ms, stop_music=True)
    _play_music(name, loop=True, volumen=volumen, fade_ms=crossfade_ms)
    _current = name

def stop(fade_ms=0):
    _ensure_init()
    if fade_ms:
        pygame.mixer.music.fadeout(fade_ms)
    else:
        pygame.mixer.music.stop()
# ------------ Efectos de sonido ------------
SFX_LIB = {
    "jump":  SFX_DIR / "jump.wav",
    "coin":  SFX_DIR / "coin.wav",
    "click": SFX_DIR / "click.wav",
    "death": SFX_DIR / "death.wav",
    "golpe": SFX_DIR / "golpe.wav",
    "stun":  SFX_DIR / "stun.wav",
    "1up":  SFX_DIR / "1up.ogg",
}

_SFX_CACHE = {}

def sfx(name: str, volume=1.0):
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
    snd.set_volume(_clamp01(MASTER_VOLUME * SFX_VOLUME * volume))

    ch = pygame.mixer.find_channel()
    if ch: ch.play(snd)
    else:  snd.play()
