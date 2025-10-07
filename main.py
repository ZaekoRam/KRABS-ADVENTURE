# main.py
import pygame
from pathlib import Path
import time, math, json  # <-- json para persistir 'tutorial_seen'
import constantes
from personaje import Personaje
import musica
from pytmx.util_pygame import (load_pygame)
import imageio
from enemigos import Enemigo
from items import Manzana
from items import bolsa
from fuentes import get_font  # usar tu fuente pixel
from parallax import create_parallax_nivel1  # PARALLAX


# --- Reproductor de intro usando imageio con sync estable, fps robusto y delay de audio por evento ---
def play_intro(
    screen,
    video_path: Path,
    audio_path: Path,
    size=(constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA),
    skip_keys=(pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE),
    FPS_MIN=5.0,
    FPS_MAX=60.0,
    FPS_OVERRIDE=30,   # fuerza FPS si lo conoces (ej: 30.0)
    AV_OFFSET=0.0,       # offset (+/- seg) para ajustar video vs audio
    audio_delay=0.0,      # segundos que esperará la música antes de empezar
):
    """
    Sincroniza el video al tiempo real y permite retrasar el arranque del audio sin pausar el video.
    - FPS robusto: usa nframes/duration cuando sea posible; si no, meta['fps'] con límites [FPS_MIN..FPS_MAX].
    - Índice de frame = int(elapsed * fps) (no incrementa i a mano).
    - 'audio_delay' se implementa con un evento programado (se nota sí o sí).
    - SPACE/ENTER/ESC para saltar.
    """
    if not video_path.exists():
        return

    clock = pygame.time.Clock()
    reader = None

    # ---- Audio: pre-cargar y programar arranque por evento (ms) ----
    AUDIO_START_EVENT = pygame.USEREVENT + 24
    audio_started = False
    music_loaded = False

    try:
        if audio_path.exists():
            pygame.mixer.music.stop()  # garantiza silencio previo
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.set_volume(1.0)
            music_loaded = True
            pygame.time.set_timer(AUDIO_START_EVENT, int(max(0.0, float(audio_delay)) * 1000), loops=1)
        else:
            pygame.mixer.music.stop()
    except Exception as e:
        print("Aviso audio intro:", e)

    try:
        reader = imageio.get_reader(str(video_path))
        meta = reader.get_meta_data()

        meta_fps = meta.get("fps", 24.0)
        nframes = meta.get("nframes", None)
        duration = meta.get("duration", None)

        # Saneos
        if not (isinstance(nframes, (int, float)) and math.isfinite(nframes) and nframes > 0):
            nframes = None
        if not (isinstance(duration, (int, float)) and math.isfinite(duration) and duration > 0):
            duration = None

        # FPS robusto
        if FPS_OVERRIDE is not None and FPS_OVERRIDE > 0:
            fps = float(FPS_OVERRIDE)
        elif nframes is not None and duration is not None:
            fps = float(nframes) / float(duration)
        else:
            try:
                fps = float(meta_fps)
            except Exception:
                fps = 24.0

        # Limitar a un rango razonable
        fps = max(FPS_MIN, min(FPS_MAX, fps))

        # Reloj base para el video
        t0 = time.perf_counter() + AV_OFFSET

        last_drawn = -1  # último índice dibujado

        while True:
            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.mixer.music.stop()
                    if reader: reader.close()
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key in skip_keys:
                    pygame.mixer.music.stop()
                    if reader: reader.close()
                    return
                # Arranque diferido del audio por evento: respeta exactamente 'audio_delay'
                if event.type == AUDIO_START_EVENT and music_loaded and not audio_started:
                    try:
                        pygame.mixer.music.play(loops=0)
                    except Exception as e:
                        print("Aviso al reproducir audio intro:", e)
                    audio_started = True

            now = time.perf_counter()
            elapsed = now - t0

            # Cortar por duración finita (con pequeño margen)
            if duration is not None and elapsed > (duration + 0.05):
                break

            expected_i = int(max(0.0, elapsed) * fps)

            # Cortar por nframes válido
            if nframes is not None and expected_i >= int(nframes):
                break

            # Si no hay nuevo frame “teórico”, respira y sigue
            if expected_i == last_drawn:
                clock.tick(120)
                continue

            # Obtener frame; si no existe, salimos
            try:
                frame = reader.get_data(expected_i)
            except IndexError:
                break

            h, w = frame.shape[0], frame.shape[1]
            surf = pygame.image.frombuffer(frame.tobytes(), (w, h), "RGB").convert()
            if (w, h) != size:
                surf = pygame.transform.smoothscale(surf, size)

            screen.blit(surf, (0, 0))
            pygame.display.flip()
            last_drawn = expected_i

            # Suavizado: esperar hasta el siguiente instante teórico de frame
            next_time = (last_drawn + 1) / fps
            spare = next_time - (time.perf_counter() - t0)
            if spare > 0:
                time.sleep(min(spare, 0.02))
            clock.tick(240)

    finally:
        try:
            if reader: reader.close()
        except Exception:
            pass
        pygame.mixer.music.stop()


# -------------------- Paths --------------------
BASE_DIR = Path(__file__).resolve().parent
IMG_DIR  = BASE_DIR / "assets" / "images"
MAP_DIR  = BASE_DIR / "assets" / "maps"
VID_DIR  = BASE_DIR / "assets" / "video"    # carpeta de video
PREFS_PATH = BASE_DIR / "settings.json"     # <-- persistencia tutorial

# -------------------- Persistencia simple --------------------
def _load_prefs() -> dict:
    try:
        with open(PREFS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {"tutorial_seen": False}

def _save_prefs(data: dict):
    try:
        with open(PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[WARN] No se pudo guardar settings.json:", e)

# -------------------- Helpers --------------------
def scale_to_width(surf: pygame.Surface, target_w: int) -> pygame.Surface:
    ratio = target_w / surf.get_width()
    target_h = int(surf.get_height() * ratio)
    return pygame.transform.scale(surf, (target_w, target_h))

def cargar_primera_imagen(carpeta_rel: str, usa_alpha: bool) -> pygame.Surface:
    carpeta = IMG_DIR / carpeta_rel
    for patron in ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.webp"):
        files = list(carpeta.glob(patron))
        if files:
            surf = pygame.image.load(str(files[0]))
            return surf.convert_alpha() if usa_alpha else surf.convert()
    raise FileNotFoundError(f"No encontré imágenes en {carpeta}")

def escalar_a_ventana(surf: pygame.Surface) -> pygame.Surface:
    return pygame.transform.smoothscale(
        surf, (constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA)
    )

# ---- HUD helpers ----
def draw_timer(surface, font, seconds, pos=(20, 20)):
    s = max(0, int(seconds))
    color = (255, 80, 80) if s <= 10 else (255, 255, 255)
    sombra = (0, 0, 0)
    txt = f"Tiempo: {s:02d}"
    surf = font.render(txt, True, color)
    shad = font.render(txt, True, sombra)
    x, y = pos
    surface.blit(shad, (x+2, y+2))
    surface.blit(surf, (x, y))

def draw_hud(surface, jugador, img_lleno, img_vacio):
    if not img_lleno: return
    for i in range(jugador.vida_maxima):
        pos_x = 20 + i * 40
        pos_y = 50
        if i < jugador.vida_actual:
            surface.blit(img_lleno, (pos_x, pos_y))
        else:
            surface.blit(img_vacio, (pos_x, pos_y))

def draw_puntuacion(surface, font, puntuacion, pos=(20, 80)):
    texto = font.render(f"Puntos: {puntuacion}", True, (255, 255, 255))
    surface.blit(texto, pos)

def reiniciar_nivel(nivel, jugador):
    # Fallback si no hay spawn
    x, y_spawn = 100, 670
    if nivel.spawn:
        x, y_spawn = int(nivel.spawn[0]), int(nivel.spawn[1])

    if hasattr(jugador, "colocar_en_midbottom"):
        try:
            jugador.colocar_en_midbottom(x, y_spawn)
        except Exception:
            jugador.forma.midbottom = (x, y_spawn)
    else:
        jugador.forma.midbottom = (x, y_spawn)



    jugador.vel_y = 0
    jugador.en_piso = True
    jugador.state = "idle"
    jugador.vida_actual = jugador.vida_maxima
    print(f"[DEBUG] reiniciar_nivel -> spawn=({x},{y_spawn}), jugador.rect={jugador.forma}")

def iniciar_muerte(jugador):
    death_jump = getattr(constantes, "DEATH_JUMP_VEL",
                         max(-700, int(getattr(constantes, "SALTO_VEL", -750) * 1.1)))
    jugador.vel_y = death_jump
    jugador.en_piso = False
    jugador.state = "fall"

def _reset_player_combat_state(p):
    # Flags/timers de daño
    for name, value in [
        ("invencible", False),
        ("invencible_timer", 0.0),
        ("stunned", False),
        ("stun_timer", 0.0),
        ("hurt", False),
        ("hurt_dir", 0),
        ("attack_timer", 0.0),
        ("attacking", False),
    ]:
        if hasattr(p, name):
            setattr(p, name, value)

    # Velocidades de knockback/arrastre
    for name, value in [
        ("knockback_speed_x", 0.0),
        ("knockback_speed_y", 0.0),
        ("vel_y", 0.0),
    ]:
        if hasattr(p, name):
            setattr(p, name, value)

    # (si tu Personaje guarda un vx propio, también a 0)
    if hasattr(p, "vx"):
        p.vx = 0.0


def _clear_input_state():
    pygame.key.set_mods(0)
    pygame.event.clear([pygame.KEYDOWN, pygame.KEYUP])
    pygame.event.pump()

# -------------------- UI Button --------------------
class ImageButton:
    def __init__(self, surf: pygame.Surface, center=None, midleft=None, scale=1.0, hover_scale=1.02):
        self.base = surf
        self.scale = scale
        self.hover_scale = hover_scale
        self.image = self._scaled(self.base, self.scale)
        if center:
            self.rect = self.image.get_rect(center=center); self._anchor = ("center", self.rect.center)
        elif midleft:
            self.rect = self.image.get_rect(midleft=midleft); self._anchor = ("midleft", self.rect.midleft)
        else:
            self.rect = self.image.get_rect(); self._anchor = ("topleft", self.rect.topleft)
        self._last_size = self.image.get_size()

    def _scaled(self, surf, factor):
        w = int(surf.get_width() * factor); h = int(surf.get_height() * factor)
        return pygame.transform.scale(surf, (w, h))

    def update(self, mouse_pos, mouse_down):
        hovering = self.rect.collidepoint(mouse_pos)
        target = self.hover_scale if (hovering and not mouse_down) else self.scale
        size = (int(self.base.get_width()*target), int(self.base.get_height()*target))
        if size != self._last_size:
            self.image = self._scaled(self.base, target)
            self.rect = self.image.get_rect()
            setattr(self.rect, self._anchor[0], self._anchor[1])
            self._last_size = size

    def draw(self, screen): screen.blit(self.image, self.rect)
    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))

# -------------------- TMX Level --------------------
class NivelTiled:
    def __init__(self, ruta_tmx: Path):
        self.tmx = load_pygame(str(ruta_tmx))
        self.tile_w = self.tmx.tilewidth; self.tile_h = self.tmx.tileheight
        self.width_px  = self.tmx.width  * self.tile_w
        self.height_px = self.tmx.height * self.tile_h

        self.goal_rects = []
        self.enemy_barrier_rects = []
        self.collision_rects = []
        try:
            barrier_layer = self.tmx.get_layer_by_name("barrera_enemigos")
            import pytmx
            if isinstance(barrier_layer, pytmx.TiledObjectGroup):
                for obj in barrier_layer:
                    if obj.width > 0 and obj.height > 0:
                        rect = pygame.Rect(int(obj.x), int(obj.y), int(obj.width), int(obj.height))
                        self.enemy_barrier_rects.append(rect)
        except ValueError:
            print("ADVERTENCIA: Capa 'barrera_enemigos' no encontrada. Los enemigos podrían caerse.")

        try:
            collision_layer = self.tmx.get_layer_by_name("collisions")
            import pytmx
            if isinstance(collision_layer, pytmx.TiledObjectGroup):
                for obj in collision_layer:
                    if obj.width > 0 and obj.height > 0:
                        rect = pygame.Rect(int(obj.x), int(obj.y), int(obj.width), int(obj.height))
                        self.collision_rects.append(rect)
                print(f"DEBUG: Se cargaron {len(self.collision_rects)} rectángulos de colisión.")
            else:
                print("ADVERTENCIA: La capa 'Collisions' existe pero no es una TiledObjectGroup.")
        except ValueError:
            print("ADVERTENCIA: Capa de colisiones 'Collisions' no encontrada en el archivo TMX.")

        try:
            Meta_layer = self.tmx.get_layer_by_name("Meta")
            import pytmx
            if isinstance(Meta_layer, pytmx.TiledObjectGroup):
                for obj in Meta_layer:
                    if obj.width > 0 and obj.height > 0:
                        rect = pygame.Rect(int(obj.x), int(obj.y), int(obj.width), int(obj.height))
                        self.goal_rects.append(rect)
        except ValueError:
            pass

        self.spawn = None
        if "Spawns" in self.tmx.objectgroups:
            for obj in self.tmx.objectgroups["Spawns"]:
                if getattr(obj, "name", "") == "player":
                    oy = int(getattr(obj, "y", 0))
                    oh = int(getattr(obj, "height", 0))
                    ox = int(getattr(obj, "x", 0))
                    if oh > 0:
                        spawn_x = ox + int(getattr(obj, "width", 0) // 2)
                        spawn_y = oy + oh
                    else:
                        spawn_x = ox
                        spawn_y = oy
                    self.spawn = (spawn_x, spawn_y)
                    break

    def draw(self, surface: pygame.Surface, camera_offset):
        ox, oy = camera_offset; sw, sh = surface.get_size()
        x0 = max(0, ox // self.tile_w); y0 = max(0, oy // self.tile_h)
        x1 = min(self.tmx.width,  (ox + sw) // self.tile_w + 2)
        y1 = min(self.tmx.height, (oy + sh) // self.tile_h + 2)
        for layer in self.tmx.visible_layers:
            if hasattr(layer, "tiles"):
                for x, y, image in layer.tiles():
                    if x0 <= x < x1 and y0 <= y < y1:
                        surface.blit(image, (x * self.tile_w - ox, y * self.tile_h - oy))

    def world_size(self): return self.width_px, self.height_px

# -------------------- Camera --------------------
class Camara:
    def __init__(self, viewport_size, world_size):
        self.vw, self.vh = viewport_size; self.ww, self.wh = world_size
        self.ox = 0.0; self.oy = 0.0
    def follow(self, r: pygame.Rect, lerp=1.0):
        cx = r.centerx - self.vw // 2; cy = r.centery - self.vh // 2
        cx = max(0, min(cx, self.ww - self.vw)); cy = max(0, min(cy, self.wh - self.vh))
        self.ox += (cx - self.ox) * lerp; self.oy += (cy - self.oy) * lerp
    def offset(self): return int(self.ox), int(self.oy)
    def set_offset(self, ox, oy): self.ox, self.oy = float(ox), float(oy)

# -------------------- Pause Menu --------------------
class PauseMenu:
    def __init__(self, size):
        self.w, self.h = size
        self.font_title = get_font(constantes.FONT_UI_TITLE)
        self.font_item = get_font(constantes.FONT_UI_ITEM)
        self.options = ["Continuar", "Salir al menú"]
        self.selected = 0
        self.panel = pygame.Surface((int(self.w*0.6), int(self.h*0.5)), pygame.SRCALPHA)
        self.panel.fill((0, 0, 0, 140))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                return "resume" if self.selected == 0 else "menu"
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            x = (self.w - self.panel.get_width())//2
            y = (self.h - self.panel.get_height())//2
            items = self._item_rects(x, y)
            for i, r in enumerate(items):
                if r.collidepoint(mx, my):
                    self.selected = i
                    return "resume" if i == 0 else "menu"
        return None

    def _item_rects(self, px, py):
        rects = []
        start_y = py + 120
        for i, _ in enumerate(self.options):
            r = pygame.Rect(0,0, 300, 48)
            r.centerx = px + self.panel.get_width()//2
            r.y = start_y + i*60
            rects.append(r)
        return rects

    def draw(self, surface):
        dim = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        dim.fill((0,0,0,100)); surface.blit(dim, (0,0))
        px = (self.w - self.panel.get_width())//2
        py = (self.h - self.panel.get_height())//2
        surface.blit(self.panel, (px, py))
        title = self.font_title.render("PAUSA", True, (255,255,255))
        surface.blit(title, (self.w//2 - title.get_width()//2, py + 40))
        for i, text in enumerate(self.options):
            color = (255,230,120) if i == self.selected else (230,230,230)
            surf = self.font_item.render(text, True, color)
            r = surf.get_rect(center=(self.w//2, py + 120 + i*60))
            surface.blit(surf, r)

# -------------------- Continue Overlay --------------------
class ContinueOverlay:
    def __init__(self, size, seconds=8):
        self.w, self.h = size
        self.font_title = get_font(constantes.FONT_UI_TITLE)
        self.font_item = get_font(constantes.FONT_UI_ITEM)
        self.seconds_total = float(seconds)
        self.remaining = float(seconds)
        self.panel = pygame.Surface((int(self.w*0.6), int(self.h*0.5)), pygame.SRCALPHA)
        self.panel.fill((0, 0, 0, 185))

    def reset(self):
        self.remaining = float(self.seconds_total)

    def update(self, dt):
        self.remaining = max(0.0, self.remaining - dt)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return "continue"
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "menu"
        return None

    def draw(self, surface):
        dim = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        dim.fill((0,0,0,140)); surface.blit(dim, (0,0))
        px = (self.w - self.panel.get_width())//2
        py = (self.h - self.panel.get_height())//2
        surface.blit(self.panel, (px, py))

        title = self.font_title.render("¿Continuar?", True, (255, 230, 120))
        surface.blit(title, (self.w//2 - title.get_width()//2, py + 50))

        secs = int(self.remaining)
        color_secs = (255, 100, 100) if secs <= 3 else (255, 255, 255)
        t_secs = self.font_title.render(f"{secs}", True, color_secs)
        surface.blit(t_secs, (self.w//2 - t_secs.get_width()//2, py + 120))

        hint = self.font_item.render("ENTER: Sí   |   ESC: Menú", True, (230,230,230))
        surface.blit(hint, (self.w//2 - hint.get_width()//2, py + 200))


# -------------------- Tutorial Overlay (imagen centrada) --------------------
class TutorialOverlay:
    def __init__(self, size, image_surf: pygame.Surface, margin=32):
        self.w, self.h = size
        self.img = image_surf.convert_alpha()
        self.margin = margin
        # escala para caber en pantalla con margen
        max_w = self.w - margin * 2
        max_h = self.h - margin * 2
        iw, ih = self.img.get_size()
        scale = min(max_w / iw, max_h / ih, 1.0)
        if scale != 1.0:
            self.img = pygame.transform.smoothscale(self.img, (int(iw*scale), int(ih*scale)))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
            return "close"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return "close"
        return None

    def draw(self, surface):
        dim = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surface.blit(dim, (0, 0))
        r = self.img.get_rect(center=(self.w//2, self.h//2))
        surface.blit(self.img, r)
        # hint
        hint_font = get_font(constantes.FONT_UI_ITEM)
        hint = hint_font.render("Enter para continuar • F1 para volver a ver", True, (230,230,230))
        surface.blit(hint, (self.w//2 - hint.get_width()//2, r.bottom + 12 if r.bottom + 28 < self.h else self.h - 28))


# -------------------- MENU KRAB (con escala) --------------------
class MenuKrab:
    """Krabby en el menú: idle a la derecha; al pulsar Play salta y se va de pantalla."""
    def __init__(self, midbottom, scale=2.0):
        self.p = Personaje(midbottom[0], midbottom[1])
        self.p.colocar_en_midbottom(*midbottom)
        self.initial_midbottom = midbottom # Guardamos la posición original
        self.p.en_piso = True
        self.p.vel_y = 0
        self.state = "idle"
        self.vx = 0.0
        self.scale = float(scale)

    def jump_and_leave(self):
        if self.state != "idle":
            return
        try:
            musica.sfx("jump", volume=0.9)
        except Exception:
            pass
        self.state = "leaving"
        self.p.saltar(forzado=True)
        self.vx = float(getattr(constantes, "VELOCIDAD", 300)) * 0.9

    def update(self, dt):
        if self.state == "idle":
            self.p.set_dx(0)
            self.p.state = "idle"
            self.p.animar(dt)
            # Suelo virtual del menú
            self.p.forma.midbottom = self.initial_midbottom
            self.p.vel_y = 0
            self.p.en_piso = True
        elif self.state == "leaving":
            self.p.aplicar_gravedad(dt)
            self.p.movimiento(self.vx * dt, 0.0)
            self.p.forma.y += int(self.p.vel_y * dt)
            self.p.animar(dt)

    def offscreen(self, w, h):
        return (self.p.forma.bottom < -40) or \
               (self.p.forma.left > w + 40) or \
               (self.p.forma.top > h + 40)

    def draw(self, surface):
        if self.scale != 1.0:
            img = pygame.transform.scale(
                self.p.image,
                (int(self.p.image.get_width() * self.scale),
                 int(self.p.image.get_height() * self.scale))
            )
            rect = img.get_rect(center=self.p.forma.center)
            surface.blit(img, rect)
        else:
            surface.blit(self.p.image, self.p.forma)


# -------------------- Estados --------------------
ESTADO_MENU, ESTADO_JUEGO, ESTADO_OPC, ESTADO_PAUSA = "MENU", "JUEGO", "OPCIONES", "PAUSA"
ESTADO_CARGANDO = "CARGANDO"
ESTADO_MUERTE   = "MUERTE"
ESTADO_CONTINUE = "CONTINUE"
ESTADO_DIFICULTAD = "DIFICULTAD"
ESTADO_NIVELES = "NIVELES"
ESTADO_GAMEOVER = "GAMEOVER"
ESTADO_TUTORIAL = "TUTORIAL"
ESTADO_VICTORIA = "VICTORIA"

def main():
    # Audio antes de pygame.init para evitar pops
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init(44100, -16, 2, 512)

    ventana = pygame.display.set_mode((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    pygame.display.set_caption("Krab's adventure")
    reloj = pygame.time.Clock()

    # Prefs (persistencia tutorial)
    prefs = _load_prefs()

    # Imagen de tutorial
    try:
        tutorial_img = pygame.image.load(IMG_DIR / "ui" / "tutorial.png").convert_alpha()
    except Exception:
        tutorial_img = None  # por si aún no la tienes

    tutorial_overlay = TutorialOverlay(
        (constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA),
        tutorial_img if tutorial_img else pygame.Surface((800, 450), pygame.SRCALPHA)
    ) if tutorial_img else None

    try:
        # HUD
        vida_lleno_img = pygame.image.load(IMG_DIR / "vidas/vida_llena.png").convert_alpha()
        vida_vacio_img = pygame.image.load(IMG_DIR / "vidas/vida_vacia.png").convert_alpha()
        vida_lleno_img = pygame.transform.scale(vida_lleno_img, (32, 32))
        vida_vacio_img = pygame.transform.scale(vida_vacio_img, (32, 32))
    except pygame.error as e:
        print(f"ERROR AL CARGAR IMÁGENES DEL HUD: {e}")
        vida_lleno_img = vida_vacio_img = None

    # --- INTRO: solo una vez por sesión ---
    video_path = VID_DIR / "intro.mp4"
    audio_path = VID_DIR / "intro.wav"  # tu audio real (WAV/OGG recomendado)
    pygame.mixer.music.set_volume(1.0)  # volumen de la intro
    play_intro(
        ventana,
        video_path,
        audio_path,
        FPS_OVERRIDE=25,
        AV_OFFSET=0.0,
        audio_delay=0.1,
    )

    font_hud = get_font(constantes.FONT_HUD)
    tiempo_total = float(getattr(constantes, "TIEMPO_NIVEL1", 60))
    timer = tiempo_total

    # --- Recursos menú
    fondo_menu   = escalar_a_ventana(cargar_primera_imagen("menufondo", False))
    titulo_img   = scale_to_width(cargar_primera_imagen("menu_titulo", True), 360)
    img_play     = scale_to_width(cargar_primera_imagen("botonplay",     True), 360)
    img_opciones = scale_to_width(cargar_primera_imagen("botonopciones", True), 340)
    img_salir    = scale_to_width(cargar_primera_imagen("botonsalir",    True), 345)

    COL_X = int(constantes.ANCHO_VENTANA * 0.28)
    Y1 = int(constantes.ALTO_VENTANA * 0.15)
    COL_TITLE = int(constantes.ANCHO_VENTANA * 0.28)
    COL_play = int(constantes.ANCHO_VENTANA * 0.27)
    Y0, GAP1, GAP = int(constantes.ALTO_VENTANA * 0.35), 60, 64

    titulo    = ImageButton(titulo_img, midleft=(COL_TITLE, Y1))
    btn_play  = ImageButton(img_play,     midleft=(COL_play, Y0))
    btn_opc   = ImageButton(img_opciones, midleft=(COL_X, btn_play.rect.bottom + GAP1))
    btn_salir = ImageButton(img_salir,    midleft=(COL_X, btn_opc.rect.bottom + GAP))

    # Krabby en el menú
    KRAB_MENU_POS  = (int(constantes.ANCHO_VENTANA*0.85), int(constantes.ALTO_VENTANA*0.83))
    KRAB_MENU_SCALE = 2.0
    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)
    menu_leaving = False

    # --- Nivel y jugador ---
    dificultad_seleccionada = "NORMAL"
    nivel_a_cargar = 1
    nivel = NivelTiled(MAP_DIR / "nivel1.tmx")

    jugador = Personaje(1000000, 100000)  # creado fuera, recolocado al iniciar
    cam = Camara((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), nivel.world_size())

    # PARALLAX
    parallax = None
    prev_cam_offset_x = 0

    enemigos = pygame.sprite.Group()
    items = pygame.sprite.Group()
    puntuacion = 0

    tutorial_shown_level1 = False

    # Música del menú
    try: musica.play("menu", volumen=0.8)
    except Exception as e: print("Aviso música:", e)

    mover_izquierda = mover_derecha = False
    estado, run = ESTADO_MENU, True
    VOL_NORMAL, VOL_PAUSA = 0.8, 0.3

    pause_menu = PauseMenu((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    continue_ui = ContinueOverlay((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), seconds=8)

    freeze_cam_offset = None

    while run:
        dt = reloj.tick(constantes.FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos(); mouse_down = pygame.mouse.get_pressed()[0]

        # ==================== EVENTOS ====================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                musica.stop(300); run = False

            if estado == ESTADO_MENU:
                if not menu_leaving:
                    btn_play.update(mouse_pos, mouse_down)
                    btn_opc.update(mouse_pos, mouse_down)
                    btn_salir.update(mouse_pos, mouse_down)
                    if btn_play.clicked(event):
                        menu_leaving = True
                        menu_krab.jump_and_leave()
                    elif btn_opc.clicked(event):
                        estado = ESTADO_OPC
                    elif btn_salir.clicked(event):
                        musica.stop(300); run = False

            elif estado == ESTADO_OPC:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    estado = ESTADO_MENU

            elif estado == ESTADO_JUEGO:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        jugador.start_attack()
                    if event.key == pygame.K_ESCAPE:
                        estado = ESTADO_PAUSA
                        pygame.mixer.music.set_volume(VOL_PAUSA)
                    if event.key in (pygame.K_a, pygame.K_LEFT):  mover_izquierda = True
                    if event.key in (pygame.K_d, pygame.K_RIGHT): mover_derecha   = True
                    if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                        if getattr(jugador, "en_piso", False): musica.sfx("jump", volume=0.9)
                        jugador.saltar()
                    # Mostrar tutorial manualmente
                    if event.key == pygame.K_F1 and tutorial_overlay:
                        estado = ESTADO_TUTORIAL
                        pygame.mixer.music.set_volume(VOL_PAUSA)
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_a, pygame.K_LEFT):  mover_izquierda = False
                    if event.key in (pygame.K_d, pygame.K_RIGHT): mover_derecha   = False

            elif estado == ESTADO_PAUSA:
                action = pause_menu.handle_event(event)
                if action == "resume":
                    estado = ESTADO_JUEGO; pygame.mixer.music.set_volume(VOL_NORMAL)
                elif action == "menu":
                    estado = ESTADO_MENU; pygame.mixer.music.set_volume(VOL_NORMAL); musica.switch("menu")
                    menu_leaving = False
                    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)

            elif estado == ESTADO_CONTINUE:
                action = continue_ui.handle_event(event)
                if action == "continue":
                    estado = ESTADO_CARGANDO
                    freeze_cam_offset = None
                elif action == "menu":
                    pygame.mixer.music.set_volume(VOL_NORMAL)
                    musica.switch("menu")
                    estado = ESTADO_MENU
                    freeze_cam_offset = None
                    menu_leaving = False
                    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)

            elif estado == ESTADO_TUTORIAL:
                if tutorial_overlay:
                    action = tutorial_overlay.handle_event(event)
                    if action == "close":
                        try:
                            _clear_input_state()
                        except Exception:
                            pass
                        # Marca como visto SOLO la primera vez que se cierra automáticamente
                        if not prefs.get("tutorial_seen", False):
                            prefs["tutorial_seen"] = True
                            _save_prefs(prefs)
                        estado = ESTADO_JUEGO
                        pygame.mixer.music.set_volume(VOL_NORMAL)

            elif estado == ESTADO_VICTORIA:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN,
                                                                   pygame.K_SPACE,
                                                                   pygame.K_ESCAPE):
                    musica.switch("menu")
                    estado = ESTADO_MENU
                    menu_leaving = False
                    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)

        # ==================== UPDATE ====================
        if estado == ESTADO_MENU:
            menu_krab.update(dt)
            if menu_leaving and menu_krab.offscreen(constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA):
                print("[DEBUG] Transición MENU -> JUEGO")
                print(f" nivel.spawn = {nivel.spawn}")
                print(f" jugador antes reiniciar = {jugador.forma}")
                musica.switch("nivel1")
                pygame.mixer.music.set_volume(VOL_NORMAL)
                timer = tiempo_total

                reiniciar_nivel(nivel, jugador)
                print(f" jugador después reiniciar = {jugador.forma}")
                print(f" cam.offset() = {cam.offset()}")

                # Forzar la cámara inmediatamente al centro del jugador
                cx = jugador.forma.centerx - cam.vw // 2
                cy = jugador.forma.centery - cam.vh // 2
                cx = max(0, min(cx, cam.ww - cam.vw))
                cy = max(0, min(cy, cam.wh - cam.vh))
                cam.set_offset(cx, cy)
                cam.follow(jugador.forma, lerp=1.0)

                # PARALLAX: crear y sincronizar con la cámara actual
                parallax = create_parallax_nivel1()
                prev_cam_offset_x = cam.offset()[0]

                limite_y = nivel.tmx.height * nivel.tmx.tileheight

                if jugador.forma.top > limite_y:
                    estado = ESTADO_MUERTE
                    print("El jugador apareció fuera del mapa. Pasando a ESTADO_MUERTE")
                else:
                    estado = ESTADO_CARGANDO

        elif estado == ESTADO_CARGANDO:
            print("[DEBUG] Estado de carga: Iniciando...")
            musica.switch("nivel1")
            pygame.mixer.music.set_volume(VOL_NORMAL)
            puntuacion = 0
            timer = tiempo_total

            nivel_actual = 1
            nivel = NivelTiled(MAP_DIR / f"nivel{nivel_actual}.tmx")

            reiniciar_nivel(nivel, jugador)
            cam = Camara((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), nivel.world_size())
            cam.follow(jugador.forma, lerp=1.0)

            parallax = create_parallax_nivel1()
            prev_cam_offset_x = cam.offset()[0]

            mover_derecha = False
            mover_izquierda = False

            enemigos = pygame.sprite.Group()
            enemigos.add(Enemigo(x=450, y=675, velocidad=34, escala=2.5),
                         Enemigo(x=800, y=675, velocidad=35, escala=2.5),
                         Enemigo(x=760, y=450, velocidad=35, escala=2.5),
                         Enemigo(x=2176, y=640,velocidad=35, escala=2.5),
                         Enemigo(x= 2750, y=381,velocidad=35, escala=2.5),
                         Enemigo(x= 4000, y=640,velocidad=35, escala=2.5),
                         Enemigo(x= 5100, y=420,velocidad=35, escala=2.5),
                         Enemigo(x=2830, y=643, velocidad=35, escala=2.5),
                         Enemigo(x= 3725, y=320, escala=2.5))


            items = pygame.sprite.Group()
            items.add(Manzana(x=338, y=479),
                      Manzana(x=724, y=374),
                      Manzana(x=981, y=309),
                      Manzana(x=1234, y=383),
                      Manzana(x=2003, y=387),
                      Manzana(x=2245, y=298),
                      Manzana(x=2767, y=348),
                      Manzana(x=2216, y=526),
                      Manzana(x=4481, y=425),
                      Manzana(x=4585, y=425),
                      Manzana(x=4585, y=425),
                      Manzana(x=4681, y=425),
                      Manzana(x=3403, y=379),
                      Manzana(x=3981, y=384),
                      Manzana(x=3981, y=384),
                      bolsa(x=2508, y=150),
                      bolsa(x=5342, y=254),
                      bolsa(x= 3715, y=260))

            # Mostrar tutorial SOLO la primera vez que se abre el juego
            if nivel_actual == 1 and (not tutorial_shown_level1) and tutorial_overlay:
                tutorial_context = "game"
                estado = "TUTORIAL"
                pygame.mixer.music.set_volume(VOL_PAUSA)
            else:
                estado = "JUEGO"

        elif estado == ESTADO_TUTORIAL:
            if tutorial_context == "game":
                # Esperar exclusivamente a la tecla ENTER
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    tutorial_shown_level1 = True  # ya se mostró al inicio de nivel 1
                    pygame.mixer.music.set_volume(VOL_NORMAL)
                    estado = "JUEGO"
                    _clear_input_state()  # limpia el teclado al salir


        elif estado == ESTADO_JUEGO:
            # Actualiza tiempo
            timer -= dt
            if timer <= 0:
                timer = 0
                try: musica.sfx("death", volume=0.9)
                except Exception: pass
                freeze_cam_offset = cam.offset()
                iniciar_muerte(jugador)
                pygame.mixer.music.set_volume(0.35)
                estado = ESTADO_MUERTE

            jugador.actualizar(dt)
            jugador.update(dt, nivel.collision_rects)
            colisiones_para_enemigos = nivel.collision_rects + nivel.enemy_barrier_rects if hasattr(nivel, "enemy_barrier_rects") else nivel.collision_rects
            enemigos.update(dt, colisiones_para_enemigos)

            if jugador.forma.bottom > nivel.tmx.height * nivel.tmx.tileheight:
                print("Jugador cayó del nivel, reiniciando...")
                try:
                    musica.sfx("death", volume=0.9)
                except Exception:
                    pass
                freeze_cam_offset = cam.offset()
                iniciar_muerte(jugador)
                pygame.mixer.music.set_volume(0.35)
                estado = ESTADO_MUERTE

            # OBTENER OFFSET DE CÁMARA
            ox, oy = cam.offset()

            # Items
            for item in list(items.sprites()):
                if item.tocar_jugador(jugador):
                    puntuacion += item.puntos
                    item.kill()
                    print(f"¡Manzana recogida! Puntuación actual: {puntuacion}")

            # Movimiento / física player
            if getattr(jugador, "invencible", False):
                jugador.invencible_timer -= dt
                if jugador.invencible_timer <= 0:
                    jugador.invencible = False

            if getattr(jugador, "invencible", False):
                direccion_knockback = -1 if jugador.facing_right else 1
                dx = jugador.knockback_speed_x * direccion_knockback * dt
                vx = 0
            else:
                vx = (constantes.VELOCIDAD if mover_derecha else 0) - (constantes.VELOCIDAD if mover_izquierda else 0)
                dx = vx * dt

            jugador.aplicar_gravedad(dt)
            dy = int(jugador.vel_y * dt)

            # Movimiento horizontal + colisión
            jugador.forma.x += int(dx)
            for rect in nivel.collision_rects:
                if jugador.forma.colliderect(rect):
                    if dx > 0:
                        jugador.forma.right = rect.left
                    elif dx < 0:
                        jugador.forma.left = rect.right

            # Movimiento vertical + colisión
            jugador.forma.y += dy
            for rect in nivel.collision_rects:
                if jugador.forma.colliderect(rect):
                    if dy > 0:
                        jugador.forma.bottom = rect.top
                        jugador.vel_y = 0
                        jugador.en_piso = True
                    elif dy < 0:
                        jugador.forma.top = rect.bottom
                        jugador.vel_y = 0

            # Estado/animación
            if not getattr(jugador, "invencible", False):
                jugador.set_dx(vx)  # solo cambia orientación

            if jugador.attacking:
                jugador.state = "attack"
            else:
                if not jugador.en_piso:
                    jugador.state = "jump" if jugador.vel_y < 0 else "fall"
                else:
                    jugador.state = "run" if vx != 0 else "idle"

            jugador.animar(dt)
            jugador.set_dx(vx)
            jugador.animar(dt)

            # Cámara sigue al jugador
            cam.follow(jugador.forma, lerp=1.0)

            # PARALLAX: actualizar por delta horizontal de la cámara
            if parallax is not None:
                new_ox = cam.offset()[0]
                camera_dx = new_ox - prev_cam_offset_x
                prev_cam_offset_x = new_ox
                parallax.update_by_camera(camera_dx)

            # Meta / victoria
            for goal in nivel.goal_rects:
                if jugador.forma.colliderect(goal):
                    estado = ESTADO_VICTORIA
                    print("¡Has ganado!")
                    break

            # Ataque colisiones
            if jugador.attacking and jugador.attack_timer > 0:
                atk = jugador.get_attack_rect()
                for e in list(enemigos):
                    if atk.colliderect(e.rect):
                        if hasattr(e, "hurt"):
                            e.hurt(jugador.attack_damage)
                        else:
                            e.kill()

            # Daño del enemigo
            for e in enemigos:
                if e.tocar_jugador(jugador):
                    jugador.recibir_dano(1)

            # Muerte por vida
            if jugador.vida_actual <= 0 and estado == ESTADO_JUEGO:
                freeze_cam_offset = cam.offset()
                iniciar_muerte(jugador)
                estado = ESTADO_MUERTE

        elif estado == ESTADO_MUERTE:
            jugador.aplicar_gravedad(dt)
            dy = int(jugador.vel_y * dt)
            jugador.forma.y += dy
            jugador.state = "fall"
            jugador.animar(dt)
            if jugador.forma.top > constantes.ALTO_VENTANA + 300:
                estado = ESTADO_CONTINUE
                continue_ui.reset()

        elif estado == ESTADO_CONTINUE:
            continue_ui.update(dt)
            if continue_ui.remaining <= 0:
                pygame.mixer.music.set_volume(VOL_NORMAL)
                musica.switch("menu")
                estado = ESTADO_MENU
                freeze_cam_offset = None
                menu_leaving = False
                menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)

        # ==================== DRAW ====================
        if estado == ESTADO_MENU:
            ventana.blit(fondo_menu, (0, 0))
            titulo.draw(ventana); btn_play.draw(ventana); btn_opc.draw(ventana); btn_salir.draw(ventana)
            menu_krab.draw(ventana)

        elif estado == ESTADO_OPC:
            ventana.blit(fondo_menu, (0, 0))
            sub = get_font(constantes.FONT_SUBTITLE).render("OPCIONES (ESC para volver)", True, (255, 255, 255))
            ventana.blit(sub, (constantes.ANCHO_VENTANA//2 - sub.get_width()//2, 60))

        elif estado in ("JUEGO", "PAUSA"):
            # PARALLAX primero
            if parallax is not None:
                parallax.draw(ventana)

            # Luego el nivel con offset
            nivel.draw(ventana, cam.offset())
            ox, oy = cam.offset()

            # HUD + sprites
            draw_timer(ventana, font_hud, timer, pos=(20, 20))
            draw_hud(ventana, jugador, vida_lleno_img, vida_vacio_img)
            draw_puntuacion(ventana, font_hud, puntuacion)

            for enemigo in enemigos:
                ventana.blit(enemigo.image, (enemigo.rect.x - ox, enemigo.rect.y - oy))

            for item in items:
                ventana.blit(item.image, (item.rect.x - ox, item.rect.y - oy))

            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))
            draw_timer(ventana, font_hud, timer, pos=(20, 20))
            if estado == "PAUSA":
                pause_menu.draw(ventana)

        elif estado in ("MUERTE", "CONTINUE"):
            # Fondo congelado: dibuja parallax y nivel sin actualizar
            if parallax is not None:
                parallax.draw(ventana)
            if freeze_cam_offset is None:
                freeze_cam_offset = cam.offset()
            nivel.draw(ventana, freeze_cam_offset)
            ox, oy = freeze_cam_offset
            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))
            draw_timer(ventana, font_hud, max(0, timer), pos=(20, 20))
            if estado == "CONTINUE":
                continue_ui.draw(ventana)

        elif estado == ESTADO_TUTORIAL:
            # Dibuja la escena actual de fondo (congelada)
            if parallax is not None:
                parallax.draw(ventana)
            nivel.draw(ventana, cam.offset())
            ox, oy = cam.offset()
            for enemigo in enemigos:
                ventana.blit(enemigo.image, (enemigo.rect.x - ox, enemigo.rect.y - oy))
            for item in items:
                ventana.blit(item.image, (item.rect.x - ox, item.rect.y - oy))
            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))
            draw_timer(ventana, font_hud, timer, pos=(20, 20))
            draw_hud(ventana, jugador, vida_lleno_img, vida_vacio_img)
            draw_puntuacion(ventana, font_hud, puntuacion)
            if tutorial_overlay:
                tutorial_overlay.draw(ventana)

        elif estado == ESTADO_VICTORIA:
            if parallax is not None:
                parallax.draw(ventana)
            nivel.draw(ventana, cam.offset())
            ox, oy = cam.offset()
            ventana.blit(jugador.image,
                         (jugador.forma.x - ox, jugador.forma.y - oy))

            msg = get_font(constantes.FONT_UI_TITLE).render("¡VICTORIA!", True, (255, 255, 0))
            ventana.blit(msg, (constantes.ANCHO_VENTANA // 2 - msg.get_width() // 2,
                               constantes.ALTO_VENTANA // 2 - msg.get_height() // 2))

            hint = get_font(constantes.FONT_UI_ITEM).render("Pulsa ENTER para volver al menú", True, (255, 255, 255))
            ventana.blit(hint, (constantes.ANCHO_VENTANA // 2 - hint.get_width() // 2,
                                constantes.ALTO_VENTANA // 2 + 60))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
