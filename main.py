# main.py
import pygame
from pathlib import Path
import time, math  # necesarios para sincronización y saneo de metadatos
import constantes
from personaje import Personaje
import musica
from pytmx.util_pygame import (load_pygame)
import imageio
from enemigos import Enemigo
from fuentes import get_font  # <-- NUEVO: usar tu fuente pixel


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
VID_DIR  = BASE_DIR / "assets" / "video"    # <--- carpeta de video

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


def reiniciar_nivel(nivel, jugador):
    # Fallback si no hay spawn
    x, y_spawn = 100, 670

    if nivel.spawn:
        x, y_spawn = int(nivel.spawn[0]), int(nivel.spawn[1])

    # Si tu clase Personaje tiene un método para colocar (como usar en MenuKrab), úsalo:
    if hasattr(jugador, "colocar_en_midbottom"):
        try:
            jugador.colocar_en_midbottom(x, y_spawn)
        except Exception:
            # Caer de vuelta a la manipulación directa del rect
            jugador.forma.midbottom = (x, y_spawn)
    else:
        jugador.forma.midbottom = (x, y_spawn)

    jugador.vel_y = 0
    jugador.en_piso = True
    jugador.state = "idle"

    # DEBUG opcional: imprime valores para verificar que el spawn es correcto
    print(f"[DEBUG] reiniciar_nivel -> spawn=({x},{y_spawn}), jugador.rect={jugador.forma}")

def iniciar_muerte(jugador):
    death_jump = getattr(constantes, "DEATH_JUMP_VEL",
                         max(-700, int(getattr(constantes, "SALTO_VEL", -750) * 1.1)))
    jugador.vel_y = death_jump
    jugador.en_piso = False
    jugador.state = "fall"

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
        self.collision_rects = []
        try:
            # 1. Intenta obtener la capa de objetos por su nombre
            collision_layer = self.tmx.get_layer_by_name("collisions")
            # Si el nombre es en minúsculas en Tiled, usa "collisions"

            # 2. Verifica que sea una capa de objetos (clase TiledObjectGroup)
            import pytmx
            if isinstance(collision_layer, pytmx.TiledObjectGroup):
                for obj in collision_layer:
                    # 3. Solo añadimos objetos con tamaño real
                    if obj.width > 0 and obj.height > 0:
                        rect = pygame.Rect(
                            int(obj.x),
                            int(obj.y),
                            int(obj.width),
                            int(obj.height)
                        )
                        self.collision_rects.append(rect)
                print(f"DEBUG: Se cargaron {len(self.collision_rects)} rectángulos de colisión.")  # DEBUGGING
            else:
                print("ADVERTENCIA: La capa 'Collisions' existe pero no es una TiledObjectGroup.")

        except ValueError:
            print("ADVERTENCIA: Capa de colisiones 'Collisions' no encontrada en el archivo TMX.")

        Meta_layer = self.tmx.get_layer_by_name("Meta")
        # Si el nombre es en minúsculas en Tiled, usa "collisions"

        # 2. Verifica que sea una capa de objetos (clase TiledObjectGroup)
        import pytmx
        if isinstance(Meta_layer, pytmx.TiledObjectGroup):
            for obj in Meta_layer:
                # 3. Solo añadimos objetos con tamaño real
                if obj.width > 0 and obj.height > 0:
                    rect = pygame.Rect(
                        int(obj.x),
                        int(obj.y),
                        int(obj.width),
                        int(obj.height)
                    )
                    self.goal_rects.append(rect)

        self.spawn = None
        if "Spawns" in self.tmx.objectgroups:
            for obj in self.tmx.objectgroups["Spawns"]:
                if getattr(obj, "name", "") == "player":
                    # Si el objeto tiene altura (ej. tile), usamos y + height para obtener la "base".
                    oy = int(getattr(obj, "y", 0))
                    oh = int(getattr(obj, "height", 0))
                    ox = int(getattr(obj, "x", 0))
                    if oh > 0:
                        spawn_x = ox + int(
                            getattr(obj, "width", 0) // 2)  # centrar horizontalmente sobre el objeto/tile
                        spawn_y = oy + oh  # base (= bottom) del objeto
                    else:
                        # point object: usar exactamente la coordenada
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

# -------------------- MENU KRAB (con escala) --------------------
class MenuKrab:
    """Krabby en el menú: idle a la derecha; al pulsar Play salta y se va de pantalla."""
    def __init__(self, midbottom, scale=2.0):
        self.p = Personaje(midbottom[0], midbottom[1])
        self.p.colocar_en_midbottom(*midbottom)
        self.initial_midbottom = midbottom # 🔑 Guardamos la posición original
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

            # 🔑 CORRECCIÓN: Forzar la posición vertical al suelo del menú
            # Esto actúa como el suelo virtual
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
ESTADO_MUERTE   = "MUERTE"
ESTADO_CONTINUE = "CONTINUE"
ESTADO_GAMEOVER = "GAMEOVER"
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

    # --- INTRO: solo una vez por sesión ---
    video_path = VID_DIR / "intro.mp4"
    audio_path = VID_DIR / "intro.wav"  # tu audio real (WAV/OGG recomendado)
    pygame.mixer.music.set_volume(1.0)  # volumen de la intro
    # Ajusta a tu gusto:
    play_intro(
        ventana,
        video_path,
        audio_path,
        FPS_OVERRIDE=25.0,     # <-- tu video a 30 fps
        AV_OFFSET=0.0,         # mueve el video vs audio si hay desfase fijo (ej. -0.08)
        audio_delay=1.2,        # <-- retrasa el audio X s sin parar el video (prueba 0.0 / 0.8 / 1.2 / 1.5)
    )

    font_hud = get_font(constantes.FONT_HUD)  # <-- cambiado
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

    # ---- Krabby en el menú (más grande y movido a la derecha)
    KRAB_MENU_POS  = (int(constantes.ANCHO_VENTANA*0.85), int(constantes.ALTO_VENTANA*0.83))
    KRAB_MENU_SCALE = 2.0
    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)
    menu_leaving = False

    # ... dentro de def main():

    # --- Nivel y jugador
    nivel = NivelTiled(MAP_DIR / "nivel1.tmx")

    # 🔑 CREACIÓN INMEDIATA: El jugador existe desde el inicio, pero fuera de la pantalla
    jugador = Personaje(1000000, 100000)
    # La cámara se debe inicializar DESPUÉS de posicionar al jugador
    cam = Camara((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), nivel.world_size())
    enemigos = pygame.sprite.Group()

    # Música del menú (se arranca DESPUÉS de la intro)
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

        for event in pygame.event.get():
            if event.type == pygame.QUIT: musica.stop(300); run = False

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
                    if event.key == pygame.K_ESCAPE:
                        estado = ESTADO_PAUSA
                        pygame.mixer.music.set_volume(VOL_PAUSA)
                    if event.key in (pygame.K_a, pygame.K_LEFT):  mover_izquierda = True
                    if event.key in (pygame.K_d, pygame.K_RIGHT): mover_derecha   = True
                    if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                        if getattr(jugador, "en_piso", False): musica.sfx("jump", volume=0.9)
                        jugador.saltar()
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
                    reiniciar_nivel(nivel, jugador)
                    enemigos = pygame.sprite.Group()
                    enemigos.add(Enemigo(x=400, y=670, velocidad=constantes.VEL_ENEM, escala=2),
                                 Enemigo(x=700, y=670, velocidad=constantes.VEL_ENEM, escala=2))
                    timer = tiempo_total
                    pygame.mixer.music.set_volume(VOL_NORMAL)
                    estado = ESTADO_JUEGO
                    freeze_cam_offset = None




                elif action == "menu":
                    pygame.mixer.music.set_volume(VOL_NORMAL)
                    musica.switch("menu")
                    estado = ESTADO_MENU
                    freeze_cam_offset = None
                    menu_leaving = False
                    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)

            elif estado == ESTADO_VICTORIA:
               if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN,
                                                                   pygame.K_SPACE,
                                                                   pygame.K_ESCAPE):
                     musica.switch("menu")
                     estado = ESTADO_MENU
                     menu_leaving = False
                     menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)


                # -------------------- Update --------------------
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

                # Forzar la cámara inmediatamente al centro del jugador (sin interpolación)
                cx = jugador.forma.centerx - cam.vw // 2
                cy = jugador.forma.centery - cam.vh // 2
                # Clamp para no salir del world bounds
                cx = max(0, min(cx, cam.ww - cam.vw))
                cy = max(0, min(cy, cam.wh - cam.vh))
                cam.set_offset(cx, cy)

                # opcional: asegurar que follow deja el mismo valor
                cam.follow(jugador.forma, lerp=1.0)

                limite_y = nivel.tmx.height * nivel.tmx.tileheight
                enemigos = pygame.sprite.Group()
                eenemigos = pygame.sprite.Group()
                # Pasa el nuevo parámetro de escala al crear los enemigos
                enemigos.add(Enemigo(x= 450, y = 600, velocidad = 30,escala = 2.5),
                             Enemigo(x = 800,y = 600,velocidad = 30,escala = 2.5))


                # Verificación ÚNICA al iniciar
                if jugador.forma.top > limite_y:
                    # Por ejemplo, cambiar a estado de muerte en vez de jugar
                    estado = ESTADO_MUERTE
                    print("El jugador apareció fuera del mapa. Pasando a ESTADO_MUERTE")
                else:
                    estado = ESTADO_JUEGO



        elif estado == ESTADO_JUEGO:
            # --- en tu bucle de juego principal ---
            jugador.update(dt, nivel.collision_rects)
            enemigos.update(dt, nivel.collision_rects)
            enemigos.draw(ventana)
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
            # Si el jugador cae por debajo del mapa

            # --- OBTENER OFFSET DE CÁMARA ---
            ox, oy = cam.offset()


            # --- DEBUGGING VISUAL: DIBUJAR CAJAS DE COLISIÓN ---
            for rect in nivel.collision_rects:
                # Dibuja el rect de colisión, movido por el offset de la cámara
                debug_rect = rect.move(-ox, -oy)
                pygame.draw.rect(ventana, (255, 0, 0), debug_rect, 2)  # Rojo: Colisiones

            # ... (Tu código de movimiento horizontal con colisión) ...

            # Dibuja el jugador (también con offset de cámara)
            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))
            timer -= dt
            if timer <= 0:
                timer = 0
                try: musica.sfx("death", volume=0.9)
                except Exception: pass
                freeze_cam_offset = cam.offset()
                iniciar_muerte(jugador)
                pygame.mixer.music.set_volume(0.35)
                estado = ESTADO_MUERTE
            vx = (constantes.VELOCIDAD if mover_derecha else 0) - (constantes.VELOCIDAD if mover_izquierda else 0)
            dx = vx * dt  # Este es el desplazamiento horizontal

            jugador.aplicar_gravedad(dt)
            dy = int(jugador.vel_y * dt)  # Este es el desplazamiento vertical

            # ----------------------------------------------------
            # --- CORRECCIÓN 1: Movimiento horizontal + colisión ---
            # ----------------------------------------------------
            jugador.forma.x += int(dx)  # 1. Aplicar movimiento horizontal

            for rect in nivel.collision_rects:
                # 2. Chequear y corregir colisión horizontal
                if jugador.forma.colliderect(rect):
                    if dx > 0:  # Movimiento hacia la derecha
                        jugador.forma.right = rect.left  # Lo empuja hacia atrás (a la izquierda)
                    elif dx < 0:  # Movimiento hacia la izquierda
                        jugador.forma.left = rect.right  # Lo empuja hacia adelante (a la derecha)

            # ----------------------------------------------------
            # --- Movimiento vertical + colisión ---
            # ----------------------------------------------------
            jugador.forma.y += dy  # 3. Aplicar movimiento vertical

            for rect in nivel.collision_rects:
                if jugador.forma.colliderect(rect):
                    if dy > 0:  # cayendo
                        jugador.forma.bottom = rect.top
                        jugador.vel_y = 0
                        jugador.en_piso = True
                    elif dy < 0:  # saltando
                        jugador.forma.top = rect.bottom
                        jugador.vel_y = 0

            # --- Lógica de estado final ---
            if jugador.en_piso:
                jugador.state = "run" if vx != 0 else "idle"

            jugador.set_dx(vx)
            jugador.animar(dt)
            cam.follow(jugador.forma, lerp=1.0)

            for goal in nivel.goal_rects:
                if jugador.forma.colliderect(goal):
                    estado = ESTADO_VICTORIA  # o llama a una función ganar()
                    print("¡Has ganado!")
                    break


            for e in enemigos:
                if e.tocar_jugador(jugador):
                    # Aquí puedes añadir efectos de sonido o visuales antes de cambiar de estado
                    try:
                        musica.sfx("death", volume=0.9)
                    except Exception:
                        pass
                    freeze_cam_offset = cam.offset()
                    iniciar_muerte(jugador)
                    pygame.mixer.music.set_volume(0.35)
                    estado = ESTADO_MUERTE
                    break  # Termina el bucle si un enemigo ya te ha golpeado

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




        # -------------------- Draw --------------------
        if estado == ESTADO_MENU:
            ventana.blit(fondo_menu, (0, 0))
            titulo.draw(ventana); btn_play.draw(ventana); btn_opc.draw(ventana); btn_salir.draw(ventana)
            menu_krab.draw(ventana)

        elif estado == ESTADO_OPC:
            ventana.blit(fondo_menu, (0, 0))
            sub = get_font(constantes.FONT_SUBTITLE).render("OPCIONES (ESC para volver)", True, (255, 255, 255))
            ventana.blit(sub, (constantes.ANCHO_VENTANA//2 - sub.get_width()//2, 60))

        elif estado in ("JUEGO", "PAUSA"):
            nivel.draw(ventana, cam.offset())
            ox, oy = cam.offset()

            for enemigo in enemigos:
                ventana.blit(enemigo.image, (enemigo.rect.x - ox, enemigo.rect.y - oy))

            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))
            draw_timer(ventana, font_hud, timer, pos=(20, 20))
            if estado == "PAUSA":
                pause_menu.draw(ventana)

        elif estado in ("MUERTE", "CONTINUE"):
            if freeze_cam_offset is None:
                freeze_cam_offset = cam.offset()
            nivel.draw(ventana, freeze_cam_offset)
            ox, oy = freeze_cam_offset
            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))
            draw_timer(ventana, font_hud, max(0, timer), pos=(20, 20))
            if estado == "CONTINUE":
                continue_ui.draw(ventana)

        elif estado == ESTADO_VICTORIA:
            # Fondo del nivel congelado
            nivel.draw(ventana, cam.offset())
            ox, oy = cam.offset()
            ventana.blit(jugador.image,
                         (jugador.forma.x - ox, jugador.forma.y - oy))

            # Mensaje de victoria
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
