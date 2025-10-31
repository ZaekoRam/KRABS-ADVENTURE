# main.py
import os

import pygame
from pathlib import Path
import time, math, json
import constantes
from personaje import Personaje
import musica
from pytmx.util_pygame import load_pygame
import imageio
from enemigos import Enemigo
from enemigos import Enemigo_walk
from items import Manzana, bolsa
from fuentes import get_font
from parallax import create_parallax_nivel1
import sys


# -------------------- Secuencia de Victoria (animación tipo Mario) --------------------
class SecuenciaVictoria:
    def __init__(self, jugador, bandera_rect, nivel, on_finish):
        self.jugador = jugador
        self.bandera_rect = bandera_rect
        self.nivel = nivel
        self.on_finish = on_finish
        self._prev_music_vol = None  # para restaurar al final

        self.activa = False
        self.etapa = 0
        self.timer = 0.0
        self.trash_y_inicial = None
        self.trash_y_final = None

        self._finish_lanzado = False  # ← evita llamar on_finish más de una vez

    def iniciar(self):
        self.activa = True
        self.etapa = 0
        self.timer = 0.0
        self.trash_y_inicial = None
        self.trash_y_final = None
        self._finish_lanzado = False
        # <<< NUEVO: música de victoria >>>
        musica.switch("victoria")  # jingle no-loop (o como lo manejes en musica.py)
        musica.set_master_volume(settings["volume"])
        self.jugador.set_dx(0)
        self.jugador.en_piso = True
        self.jugador.facing_right = True
        self.jugador.state = "idle"

    def actualizar(self, dt):
        if not self.activa:
            return

        if self.etapa == 0:
            # caminar hacia la derecha hasta quedar frente a la bandera
            self.jugador.forma.x += int(90 * dt)
            if self.jugador.forma.centerx >= self.bandera_rect.centerx - 30:
                self.etapa = 1
                self.jugador.state = "idle"

        elif self.etapa == 1:
            # voltear a la izquierda un instante
            self.jugador.facing_right = False
            self.timer += dt
            if self.timer > 0.5:
                self.etapa = 2
                self.timer = 0.0

        elif self.etapa == 2:
            # SUBIR LA BANDERA HASTA ARRIBA DEL NIVEL (y=0), más lento
            if self.trash_y_inicial is None:
                self.trash_y_inicial = self.bandera_rect.bottom
            RAISE_SPEED = 190  # ⇦ baja este número si la quieres aún más lenta
            # sigue subiendo hasta que la bandera salga por arriba (bottom <= 0)
            if self.bandera_rect.bottom > 0:
                self.bandera_rect.bottom -= int(RAISE_SPEED * dt)
            else:
                # bandera ya salió por arriba; ahora sí, pasamos a mover al jugador
                self.etapa = 3
                self.timer = 0.0

        elif self.etapa == 3:
            # pequeña pausa antes de caminar (opcional)
            self.timer += dt
            if self.timer >= 0.20:
                self.jugador.facing_right = True
                self.etapa = 4

        elif self.etapa == 4:
            # ahora el jugador camina hacia la derecha hasta salir del mapa
            self.jugador.forma.x += int(140 * dt)
            if self.jugador.forma.left > self.nivel.width_px + 64:
                self.etapa = 5

        elif self.etapa == 5:
            # terminar nivel
            self.activa = False
            if callable(self.on_finish):
                self.on_finish()


# === SPAWN FIX ===
# Pequeña ventana de invencibilidad y 2 frames sin física al entrar al nivel.
SPAWN_GRACE = 0.2 # segundos invencible al cargar/cerrar tutorial
SPAWN_SKIP_FRAMES = 2  # frames sin física para estabilizar


# -------------------- Intro video --------------------
# === CONFIGURACIÓN GLOBAL ===
settings = {
    "volume": 0.8,      # volumen inicial (0.0 - 1.0)
    "language": None,   # idioma elegido (None al inicio, luego "es" o "en")
}

# === TEXTOS (I18N) ===
I18N = {
    "es": {
        "select_lang": "Selecciona tu idioma",
        "spanish": "Español",
        "english": "Inglés",
        "skip": "Pulsa cualquier tecla para saltar",
    },
    "en": {
        "select_lang": "Select your language",
        "spanish": "Spanish",
        "english": "English",
        "skip": "Press any key to skip",
    }
}

try:
    from ffpyplayer.player import MediaPlayer
    _HAS_FFPY = True
except Exception:
    _HAS_FFPY = False
    MediaPlayer = None

class FFVideo:
    def __init__(self, path: str, out_size: tuple[int,int]):
        if not _HAS_FFPY:
            raise RuntimeError("ffpyplayer no está disponible")
        self.player = MediaPlayer(path, ff_opts={'sync': 'video'})  # audio lo maneja ffpyplayer
        self.surf = None
        self.size = out_size
        self.done = False

    def update(self):
        if self.done:
            return
        frame, val = self.player.get_frame()
        if val == 'eof':
            self.done = True
            return
        if frame is not None:
            img, pts = frame
            w, h = img.get_size()
            # buffer RGB -> Surface
            data = img.to_bytearray()[0]
            frame_surf = pygame.image.frombuffer(data, (w, h), 'RGB')
            # escalar a ventana (mantén aspect si quieres)
            self.surf = pygame.transform.smoothscale(frame_surf, self.size)

    def draw(self, screen):
        if self.surf:
            screen.blit(self.surf, (0, 0))

    def close(self):
        try:
            self.player.close_player()
        except Exception:
            pass


# -------------------- Paths/prefs --------------------
BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "assets" / "images"
MAP_DIR = BASE_DIR / "assets" / "maps"
VIDEO_DIR_ES = "assets/video/intro_es.mp4"
VIDEO_DIR_EN = "assets/video/intro_en.mp4"
PREFS_PATH = BASE_DIR / "settings.json"


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


# -------------------- Helpers/HUD --------------------}

# ===== Helpers UI para Game Over =====
def draw_text_center(surface, text, font, color, x_center, y, shadow=True):
    """Dibuja texto centrado; si shadow=True añade sombra suave."""
    if shadow:
        shadow_surf = font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect(midtop=(x_center+2, y+2))
        surface.blit(shadow_surf, shadow_rect)

    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(midtop=(x_center, y))
    surface.blit(text_surf, text_rect)
    return text_rect  # por si quieres saber el alto

def draw_button_auto(surface, text, font, center, bg=(30,60,140), fg=(255,255,255),
                     pad_x=24, pad_y=14, border=3, radius=12, hover=False):
    """Botón cuyo tamaño se adapta al texto."""
    text_surf = font.render(text, True, fg)
    tw, th = text_surf.get_size()
    w = tw + pad_x*2
    h = th + pad_y*2
    rect = pygame.Rect(0, 0, w, h)
    rect.center = center

    # hover color
    bg_draw = bg
    if hover:
        bg_draw = (min(bg[0]+20,255), min(bg[1]+20,255), min(bg[2]+30,255))

    pygame.draw.rect(surface, bg_draw, rect, border_radius=radius)
    pygame.draw.rect(surface, (220, 230, 255), rect, width=border, border_radius=radius)

    surface.blit(text_surf, text_surf.get_rect(center=rect.center))
    return rect

# === Settings ===
settings = {
    "volume": 0.8,    # 0.0 - 1.0
    "language": "es", # "es" | "en"
}

# === I18N ===
I18N = {
    "es": {
        "options_title": "OPCIONES (ESC para volver)",
        "volume": "Volumen",
        "language": "Idioma",
        "lang_value": {"es": "Español", "en": "Inglés"},
        "hint": "Arrastra la barra o usa ← →",
        "toggle": "Cambiar idioma"
    },
    "en": {
        "options_title": "OPTIONS (ESC to go back)",
        "volume": "Volume",
        "language": "Language",
        "lang_value": {"es": "Spanish", "en": "English"},
        "hint": "Drag the bar or use ← →",
        "toggle": "Toggle language"
    }
}

# === Slider ===
SLIDER_W = 360
SLIDER_H = 8
HANDLE_R = 10
slider_bar_rect = pygame.Rect(0, 0, SLIDER_W, SLIDER_H)
slider_bar_rect.center = (constantes.ANCHO_VENTANA // 2, 220)

def slider_handle_pos_x():
    return int(slider_bar_rect.left + settings["volume"] * slider_bar_rect.width)

slider_dragging = False

# === Botón de idioma ===
btn_lang_rect = pygame.Rect(0, 0, 260, 50)
btn_lang_rect.center = (constantes.ANCHO_VENTANA // 2, 320)



def esta_en_suelo(j, col_rects) -> bool:
    """Chequeo inmediato de suelo: mira 1px por debajo del jugador."""
    probe = j.forma.copy()
    probe.y += 1
    for r in col_rects:
        if probe.colliderect(r):
            return True
    return False


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
    return pygame.transform.smoothscale(surf, (constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))


def draw_timer(surface, font, seconds, pos=(20, 20)):
    s = max(0, int(seconds))
    color = (255, 80, 80) if s <= 10 else (255, 255, 255)
    sombra = (0, 0, 0)
    txt = f"Tiempo: {s:02d}"
    surf = font.render(txt, True, color)
    shad = font.render(txt, True, sombra)
    x, y = pos
    surface.blit(shad, (x + 2, y + 2))
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

    # === SPAWN FIX: pegar al piso justo tras colocar midbottom ===
    px = jugador.forma.centerx
    mejor_top = None
    for r in nivel.collision_rects:
        if r.left - 2 <= px <= r.right + 2:  # bajo la misma X
            if r.top >= jugador.forma.bottom - 120:  # plataforma bajo nosotros (tolerancia)
                if (mejor_top is None) or (r.top < mejor_top):
                    mejor_top = r.top
    if mejor_top is not None:
        jugador.forma.bottom = int(mejor_top)
        jugador.vel_y = 0
        jugador.en_piso = True
    else:
        # si no hay piso detectado cerca, al menos no caigas disparado
        jugador.vel_y = 0
        jugador.en_piso = False

    print(f"[DEBUG] reiniciar_nivel -> spawn=({x},{y_spawn}), jugador.rect={jugador.forma}")


def iniciar_muerte(jugador):
    death_jump = getattr(constantes, "DEATH_JUMP_VEL",
                         max(-700, int(getattr(constantes, "SALTO_VEL", -750) * 1.1)))
    jugador.vel_y = death_jump
    jugador.en_piso = False
    jugador.state = "fall"


def _reset_player_combat_state(p):
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
    for name, value in [
        ("knockback_speed_x", 0.0),
        ("knockback_speed_y", 0.0),
        ("vel_y", 0.0),
    ]:
        if hasattr(p, name):
            setattr(p, name, value)
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
            self.rect = self.image.get_rect(center=center);
            self._anchor = ("center", self.rect.center)
        elif midleft:
            self.rect = self.image.get_rect(midleft=midleft);
            self._anchor = ("midleft", self.rect.midleft)
        else:
            self.rect = self.image.get_rect();
            self._anchor = ("topleft", self.rect.topleft)
        self._last_size = self.image.get_size()

    def _scaled(self, surf, factor):
        w = int(surf.get_width() * factor);
        h = int(surf.get_height() * factor)
        return pygame.transform.scale(surf, (w, h))

    def update(self, mouse_pos, mouse_down):
        hovering = self.rect.collidepoint(mouse_pos)
        target = self.hover_scale if (hovering and not mouse_down) else self.scale
        size = (int(self.base.get_width() * target), int(self.base.get_height() * target))
        if size != self._last_size:
            self.image = self._scaled(self.base, target)
            self.rect = self.image.get_rect()
            setattr(self.rect, self._anchor[0], self._anchor[1])
            self._last_size = size

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))


# -------------------- Simple Button --------------------
class BotonSimple:
    def __init__(self, texto, center, width=200, height=50):
        self.font = get_font(constantes.FONT_UI_ITEM)
        self.texto = texto
        self.center = center
        self.width = width
        self.height = height

        # Colores estilo marino/azul para coincidir con tu tema
        self.color_normal = (30, 60, 120)  # Azul oscuro
        self.color_hover = (50, 100, 180)  # Azul medio
        self.color_texto = (255, 255, 255)  # Blanco

        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = center
        self.hover = False

    def update(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        # Color del botón
        color = self.color_hover if self.hover else self.color_normal

        # Dibujar botón con bordes redondeados
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, width=2, border_radius=6)

        # Texto
        texto_surf = self.font.render(self.texto, True, self.color_texto)
        texto_rect = texto_surf.get_rect(center=self.rect.center)
        surface.blit(texto_surf, texto_rect)


# -------------------- TMX Level --------------------
class NivelTiled:
    def __init__(self, ruta_tmx: Path):
        self.tmx = load_pygame(str(ruta_tmx))
        self.tile_w = self.tmx.tilewidth
        self.tile_h = self.tmx.tileheight
        self.width_px = self.tmx.width * self.tile_w
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
        ox, oy = camera_offset;
        sw, sh = surface.get_size()
        x0 = max(0, ox // self.tile_w);
        y0 = max(0, oy // self.tile_h)
        x1 = min(self.tmx.width, (ox + sw) // self.tile_w + 2)
        y1 = min(self.tmx.height, (oy + sh) // self.tile_h + 2)
        for layer in self.tmx.visible_layers:
            if hasattr(layer, "tiles"):
                for x, y, image in layer.tiles():
                    if x0 <= x < x1 and y0 <= y < y1:
                        surface.blit(image, (x * self.tile_w - ox, y * self.tile_h - oy))

    def world_size(self):
        return self.width_px, self.height_px


# -------------------- Camera --------------------
class Camara:
    def __init__(self, viewport_size, world_size):
        self.vw, self.vh = viewport_size;
        self.ww, self.wh = world_size
        self.ox = 0.0;
        self.oy = 0.0

    def follow(self, r: pygame.Rect, lerp=1.0):
        cx = r.centerx - self.vw // 2;
        cy = r.centery - self.vh // 2
        cx = max(0, min(cx, self.ww - self.vw));
        cy = max(0, min(cy, self.wh - self.vh))
        self.ox += (cx - self.ox) * lerp;
        self.oy += (cy - self.oy) * lerp

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
        self.panel = pygame.Surface((int(self.w * 0.6), int(self.h * 0.5)), pygame.SRCALPHA)
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
            x = (self.w - self.panel.get_width()) // 2
            y = (self.h - self.panel.get_height()) // 2
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
            r = pygame.Rect(0, 0, 300, 48)
            r.centerx = px + self.panel.get_width() // 2
            r.y = start_y + i * 60
            rects.append(r)
        return rects

    def draw(self, surface):
        dim = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 100));
        surface.blit(dim, (0, 0))
        px = (self.w - self.panel.get_width()) // 2
        py = (self.h - self.panel.get_height()) // 2
        surface.blit(self.panel, (px, py))
        title = self.font_title.render("PAUSA", True, (255, 255, 255))
        surface.blit(title, (self.w // 2 - title.get_width() // 2, py + 40))
        for i, text in enumerate(self.options):
            color = (255, 230, 120) if i == self.selected else (230, 230, 230)
            surf = self.font_item.render(text, True, color)
            r = surf.get_rect(center=(self.w // 2, py + 120 + i * 60))
            surface.blit(surf, r)


# -------------------- Game Over Screen --------------------
class GameOverScreen:
    def __init__(self, size):
        self.w, self.h = size
        self.font_title = get_font(constantes.FONT_UI_TITLE)
        self.font_sub = get_font(constantes.FONT_UI_ITEM)
        self.font_item = get_font(constantes.FONT_UI_ITEM)

        # Imagen opcional (puedes dejar fondo del juego)
        try:
            self.bg = pygame.image.load(IMG_DIR / "ui" / "game_over.png").convert()
            self.bg = pygame.transform.scale(self.bg, (self.w, self.h))
        except:
            self.bg = None

        # --- PANEL Y BOTONES ---
        BTN_W, BTN_H = 280, 70
        spacing = 90  # distancia entre botones

        center_y = self.h // 2 + 35

        self.btn_retry = BotonSimple("Continuar", (self.w // 2, center_y), BTN_W, BTN_H)
        self.btn_menu = BotonSimple("Menú", (self.w // 2, center_y + spacing), BTN_W, BTN_H)

    def reset(self):
        pass

    def update(self, mouse_pos):
        self.btn_retry.update(mouse_pos)
        self.btn_menu.update(mouse_pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_retry.rect.collidepoint(event.pos):
                return "continuar"
            elif self.btn_menu.rect.collidepoint(event.pos):
                return "menu"

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_c):
                return "continuar"
            if event.key in (pygame.K_ESCAPE, pygame.K_m, pygame.K_BACKSPACE):
                return "menu"
        return None

    def draw(self, surface):
        # Fondo
        if self.bg:
            surface.blit(self.bg, (0, 0))
        else:
            surface.fill((20, 0, 0))

        # Capa oscura
        dim = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        surface.blit(dim, (0, 0))

        # --- TÍTULO PRINCIPAL ---
        title = self.font_title.render("PARTIDA TERMINADA", True, (255, 180, 50))
        title_rect = title.get_rect(center=(self.w // 2, self.h // 2 - 140))
        surface.blit(title, title_rect)

        # --- SUBTEXTO ---
        subt = self.font_sub.render("Sigue intentando, aún podemos lograrlo!", True, (255, 255, 255))
        subt_rect = subt.get_rect(center=(self.w // 2, self.h // 2 - 80))
        surface.blit(subt, subt_rect)

        # --- BOTONES ---
        self.btn_retry.draw(surface)
        self.btn_menu.draw(surface)

        # --- INSTRUCCIONES ABAJO ---
        hint = self.font_item.render("ENTER: Reintentar | ESC: Menú", True, (255, 255, 255))
        hint_rect = hint.get_rect(center=(self.w // 2, self.h - 60))
        surface.blit(hint, hint_rect)

class VictoryScreen:
    def __init__(self, size, image_name="victory_screen.png"):
        self.w, self.h = size

        # Fuentes (reusa tu get_font si lo tienes)
        try:
            from fuentes import get_font
            import constantes
            self.font_item = get_font(constantes.FONT_UI_ITEM)
        except:
            pygame.font.init()
            self.font_item = pygame.font.SysFont("Arial", 26)

        # Fondo: imagen de victoria a pantalla completa (manteniendo proporción)
        self.bg = None
        try:
            img = pygame.image.load(IMG_DIR / "ui" / image_name).convert_alpha()
        except:
            img = None

        if img:
            # Escala manteniendo proporción y centrado
            iw, ih = img.get_width(), img.get_height()
            scale = min(self.w / iw, self.h / ih)
            nw, nh = int(iw * scale), int(ih * scale)
            self.bg = pygame.transform.smoothscale(img, (nw, nh))
            self.bg_rect = self.bg.get_rect(center=(self.w // 2, self.h // 2))

        # Dim capa oscura suave para contraste del botón
        self.dim = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.dim.fill((0, 0, 0, 80))

        # Botón MENÚ (usa tu BotonSimple para que quede igual al resto del juego)
        BTN_W, BTN_H = 260, 64
        self.btn_menu = BotonSimple("Menú", (self.w // 2, self.h // 2 + 180), BTN_W, BTN_H)

    def update(self, mouse_pos):
        self.btn_menu.update(mouse_pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_menu.rect.collidepoint(event.pos):
                return "menu"
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_m, pygame.K_RETURN, pygame.K_SPACE):
                return "menu"
        return None

    def draw(self, surface):
        surface.fill((0, 0, 0))
        if self.bg:
            surface.blit(self.bg, self.bg_rect)
        surface.blit(self.dim, (0, 0))

        self.btn_menu.draw(surface)

        hint = self.font_item.render("ENTER/ESPACIO: Menú", True, (255, 255, 255))
        surface.blit(hint, hint.get_rect(center=(self.w // 2, self.h - 60)))


# -------------------- Character Select UI --------------------
class CharacterSelectUI:
    def __init__(self, size, img_m, img_f):
        self.w, self.h = size
        self.font_title = get_font(constantes.FONT_UI_TITLE)
        self.font_item = get_font(constantes.FONT_UI_ITEM)
        self.card_w, self.card_h = 260, 300
        gap = 80
        cx = self.w // 2
        cy = self.h // 2 + 20
        self.rect_m = pygame.Rect(0, 0, self.card_w, self.card_h);
        self.rect_m.center = (cx - (self.card_w // 2 + gap), cy)
        self.rect_f = pygame.Rect(0, 0, self.card_w, self.card_h);
        self.rect_f.center = (cx + (self.card_w // 2 + gap), cy)
        self.pic_m = img_m
        self.pic_f = img_f
        self.txt_m = self.font_item.render("KRABBY", True, (20, 30, 60))
        self.txt_f = self.font_item.render("KAROL", True, (20, 30, 60))
        self.hover = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = 'm' if self.rect_m.collidepoint(event.pos) else (
                'f' if self.rect_f.collidepoint(event.pos) else None)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_m.collidepoint(event.pos): return "male"
            if self.rect_f.collidepoint(event.pos): return "female"
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):   return "male"
            if event.key in (pygame.K_RIGHT, pygame.K_d):  return "female"
            if event.key in (pygame.K_SPACE, pygame.K_BACKSPACE): return "male"
        return None

    def _draw_card(self, surface, rect, portrait, name_surf, enabled=True, hover=False):
        pygame.draw.rect(surface, (15, 70, 130), rect, border_radius=8, width=6)
        inner = rect.inflate(-12, -12)
        pygame.draw.rect(surface, (200, 230, 255) if enabled else (200, 200, 200), inner, border_radius=6)
        if hover and enabled:
            pygame.draw.rect(surface, (80, 180, 255), inner, width=4, border_radius=6)
        pic_rect = portrait.get_rect(center=(inner.centerx, inner.top + 160 // 2 + 26))
        surface.blit(portrait, pic_rect)
        name_bar = pygame.Rect(inner.left + 8, inner.bottom - 56, inner.width - 16, 40)
        pygame.draw.rect(surface, (170, 210, 255) if enabled else (180, 180, 180), name_bar, border_radius=6)
        nr = name_surf.get_rect(center=name_bar.center);
        surface.blit(name_surf, nr)

    def draw(self, surface):
        title = self.font_title.render("SELECCIÓN DE PERSONAJE", True, (15, 40, 80))
        band = pygame.Surface((title.get_width() + 40, title.get_height() + 18), pygame.SRCALPHA)
        pygame.draw.rect(band, (180, 210, 255, 230), band.get_rect(), border_radius=8)
        band.blit(title, (20, 9))
        band_rect = band.get_rect(center=(self.w // 2, 90))
        surface.blit(band, band_rect)
        self._draw_card(surface, self.rect_m, self.pic_m, self.txt_m, enabled=True, hover=(self.hover == 'm'))
        self._draw_card(surface, self.rect_f, self.pic_f, self.txt_f, enabled=True, hover=(self.hover == 'f'))


# -------------------- Level Select UI --------------------
class LevelSelectUI:
    """Selector visual de nivel 1, 2, 3 (front)."""

    def __init__(self, size, thumbs=None):
        self.w, self.h = size
        self.font_title = get_font(constantes.FONT_UI_TITLE)
        self.font_item = get_font(constantes.FONT_UI_ITEM)
        self.card_w, self.card_h = 220, 240
        gap = 60
        cx = self.w // 2
        cy = self.h // 2 + 10
        self.rects = []
        x0 = cx - self.card_w - gap
        x1 = cx
        x2 = cx + self.card_w + gap
        for x in (x0, x1, x2):
            r = pygame.Rect(0, 0, self.card_w, self.card_h)
            r.center = (x, cy)
            self.rects.append(r)
        self.thumbs = thumbs or {}
        self.labels = [
            self.font_item.render("NIVEL 1", True, (20, 30, 60)),
            self.font_item.render("NIVEL 2", True, (20, 30, 60)),
            self.font_item.render("NIVEL 3", True, (20, 30, 60)),
        ]
        self.hover = None
        self.selected = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = None
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.hover = i
                    break
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.selected = i + 1
                    return self.selected
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_1, pygame.K_KP1): self.selected = 1; return 1
            if event.key in (pygame.K_2, pygame.K_KP2): self.selected = 2; return 2
            if event.key in (pygame.K_3, pygame.K_KP3): self.selected = 3; return 3
            if event.key in (pygame.K_RETURN, pygame.K_SPACE): self.selected = 2; return 2
        return None

    def _draw_card(self, surface, rect, n_level, label, hover=False, selected=False):
        pygame.draw.rect(surface, (15, 70, 130), rect, border_radius=8, width=5)
        inner = rect.inflate(-12, -12)
        base_color = (200, 230, 255)
        if selected: base_color = (180, 220, 255)
        pygame.draw.rect(surface, base_color, inner, border_radius=6)
        if hover: pygame.draw.rect(surface, (80, 180, 255), inner, width=4, border_radius=6)
        thumb = self.thumbs.get(n_level)
        if thumb:
            tr = thumb.get_rect(center=(inner.centerx, inner.top + 80))
            surface.blit(thumb, tr)
        else:
            ph = pygame.Surface((120, 80));
            ph.fill((170, 210, 255))
            pr = ph.get_rect(center=(inner.centerx, inner.top + 80))
            surface.blit(ph, pr)
        bar = pygame.Rect(inner.left + 8, inner.bottom - 56, inner.width - 16, 40)
        pygame.draw.rect(surface, (170, 210, 255), bar, border_radius=6)
        lr = label.get_rect(center=bar.center)
        surface.blit(label, lr)
        if selected:
            tic = self.font_item.render("✓", True, (15, 40, 80))
            trect = tic.get_rect(center=(inner.right - 28, inner.top + 26))
            surface.blit(tic, trect)

    def draw(self, surface):
        title = self.font_title.render("SELECCIÓN DE NIVEL", True, (15, 40, 80))
        band = pygame.Surface((title.get_width() + 40, title.get_height() + 18), pygame.SRCALPHA)
        pygame.draw.rect(band, (180, 210, 255, 230), band.get_rect(), border_radius=8)
        band.blit(title, (20, 9))
        band_rect = band.get_rect(center=(self.w // 2, 90))
        surface.blit(band, band_rect)
        for i, r in enumerate(self.rects):
            self._draw_card(surface, r, i + 1, self.labels[i], hover=(self.hover == i),
                            selected=(self.selected == i + 1))
        hint_txt = "Dale clic o 1/2/3 • ESC para volver"
        hint = self.font_item.render(hint_txt, True, (20, 20, 20))  # negro para legibilidad
        surface.blit(hint, hint.get_rect(center=(self.w // 2, self.h - 40)))


# -------------------- Difficulty Select UI --------------------
class DifficultySelectUI:
    """Pantalla con dos tarjetas: FÁCIL (default) y DIFÍCIL, con hover e íconos opcionales."""

    def __init__(self, size, icon_easy: pygame.Surface | None = None, icon_hard: pygame.Surface | None = None):
        self.w, self.h = size
        self.font_title = get_font(constantes.FONT_UI_TITLE)
        self.font_item = get_font(constantes.FONT_UI_ITEM)

        # geometría de tarjetas
        self.card_w, self.card_h = 260, 220
        self.gap = self.card_w // 2 + 50  # separación

        cy = self.h // 2 + 10
        cx = self.w // 2

        self.rect_easy = pygame.Rect(0, 0, self.card_w, self.card_h);
        self.rect_easy.center = (cx - self.gap, cy)
        self.rect_hard = pygame.Rect(0, 0, self.card_w, self.card_h);
        self.rect_hard.center = (cx + self.gap, cy)

        self.lbl_easy = self.font_item.render("PRINCIPIANTE", True, (20, 30, 60))
        self.lbl_hard = self.font_item.render("DESAFIANTE", True, (20, 30, 60))

        # íconos (opcional)
        def _fit_icon(surf: pygame.Surface | None) -> pygame.Surface | None:
            if not surf:
                return None
            # Tamaño máximo deseado del ícono
            max_w, max_h = 200, 160
            iw, ih = surf.get_size()

            # ✅ Quitamos el límite que impedía escalar hacia arriba
            scale = min(max_w / iw, max_h / ih)

            # Puedes usar smoothscale si quieres íconos suaves, o scale si quieres pixel art
            surf = pygame.transform.scale(surf, (int(iw * scale), int(ih * scale)))
            return surf.convert_alpha()

        self.icon_easy = _fit_icon(icon_easy)
        self.icon_hard = _fit_icon(icon_hard)

        self.hover = None  # 'easy' | 'hard' | None
        self.selected = "FACIL"  # por defecto FÁCIL

    def handle_event(self, event):
        """Devuelve 'FACIL', 'DIFICIL', 'BACK' o None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_easy.collidepoint(event.pos):
                self.selected = "FACIL";
                return "FACIL"
            if self.rect_hard.collidepoint(event.pos):
                self.selected = "DIFICIL";
                return "DIFICIL"

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_1, pygame.K_KP1):
                self.selected = "FACIL";
                return "FACIL"
            if event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_2, pygame.K_KP2):
                self.selected = "DIFICIL";
                return "DIFICIL"
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self.selected
            if event.key == pygame.K_ESCAPE:
                return "BACK"
        return None

    def _draw_card(self, surface, rect, label_surf, icon=None, selected=False, hover=False):
        # marco externo
        pygame.draw.rect(surface, (15, 70, 130), rect, border_radius=8, width=5)
        inner = rect.inflate(-12, -12)

        # fondo
        base = (200, 230, 255)
        pygame.draw.rect(surface, base, inner, border_radius=6)

        # borde de selección / hover
        if selected:
            pygame.draw.rect(surface, (120, 170, 230), inner.inflate(-6, -6), width=3, border_radius=6)
        if hover:
            pygame.draw.rect(surface, (80, 180, 255), inner, width=4, border_radius=6)

        # icono
        if icon:
            ir = icon.get_rect(center=(inner.centerx, inner.top + 75))
            surface.blit(icon, ir)
        else:
            # placeholder
            ph = pygame.Surface((100, 70));
            ph.fill((170, 210, 255))
            pr = ph.get_rect(center=(inner.centerx, inner.top + 70))
            surface.blit(ph, pr)

        # barra inferior con texto
        bar = pygame.Rect(inner.left + 8, inner.bottom - 56, inner.width - 16, 40)
        pygame.draw.rect(surface, (170, 210, 255), bar, border_radius=6)
        lr = label_surf.get_rect(center=bar.center)
        surface.blit(label_surf, lr)

    def draw(self, surface):
        # título
        title = self.font_title.render("DIFICULTAD", True, (15, 40, 80))
        band = pygame.Surface((title.get_width() + 40, title.get_height() + 18), pygame.SRCALPHA)
        pygame.draw.rect(band, (180, 210, 255, 230), band.get_rect(), border_radius=8)
        band.blit(title, (20, 9))
        surface.blit(band, band.get_rect(center=(self.w // 2, 90)))

        # hover
        mx, my = pygame.mouse.get_pos()
        if self.rect_easy.collidepoint((mx, my)):
            self.hover = 'easy'
        elif self.rect_hard.collidepoint((mx, my)):
            self.hover = 'hard'
        else:
            self.hover = None

        # tarjetas
        self._draw_card(surface, self.rect_easy, self.lbl_easy, icon=self.icon_easy,
                        selected=(self.selected == "FACIL"), hover=(self.hover == 'easy'))
        self._draw_card(surface, self.rect_hard, self.lbl_hard, icon=self.icon_hard,
                        selected=(self.selected == "DIFICIL"), hover=(self.hover == 'hard'))

        # hint
        hint_txt = "Clic o ←/→ para jugar • ESC para volver"
        hint = self.font_item.render(hint_txt, True, (20, 20, 20))
        surface.blit(hint, hint.get_rect(center=(self.w // 2, self.h - 40)))


# -------------------- Tutorial Overlay --------------------
class TutorialOverlay:
    def __init__(self, size, image_surf: pygame.Surface, margin=32):
        self.w, self.h = size
        self.img = image_surf.convert_alpha()
        self.margin = margin
        max_w = self.w - margin * 2
        max_h = self.h - margin * 2
        iw, ih = self.img.get_size()
        scale = min(max_w / iw, max_h / ih, 1.0)
        if scale != 1.0:
            self.img = pygame.transform.smoothscale(self.img, (int(iw * scale), int(ih * scale)))

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
        r = self.img.get_rect(center=(self.w // 2, self.h // 2))
        surface.blit(self.img, r)
        hint_font = get_font(constantes.FONT_UI_ITEM)
        hint = hint_font.render("Enter para continuar • F1 para volver a ver", True, (230, 230, 230))
        surface.blit(hint,
                     (self.w // 2 - hint.get_width() // 2, r.bottom + 12 if r.bottom + 28 < self.h else self.h - 28))


# -------------------- Menu Krab --------------------
class MenuKrab:
    def __init__(self, midbottom, scale=2.0):
        self.p = Personaje(midbottom[0], midbottom[1])
        self.p.colocar_en_midbottom(*midbottom)
        self.initial_midbottom = midbottom
        self.p.en_piso = True
        self.p.vel_y = 0
        self.state = "idle"
        self.vx = 0.0
        self.scale = float(scale)

    def jump_and_leave(self):
        if self.state != "idle": return
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
            self.p.forma.midbottom = self.initial_midbottom
            self.p.vel_y = 0
            self.p.en_piso = True
        elif self.state == "leaving":
            self.p.aplicar_gravedad(dt)
            self.p.movimiento(self.vx * dt, 0.0)
            self.p.forma.y += int(self.p.vel_y * dt)
            self.p.animar(dt)

    def offscreen(self, w, h):
        return (self.p.forma.bottom < -40) or (self.p.forma.left > w + 40) or (self.p.forma.top > h + 40)

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
ESTADO_MUERTE = "MUERTE"
ESTADO_CONTINUE = "CONTINUE"
ESTADO_DIFICULTAD = "DIFICULTAD"
ESTADO_NIVELES = "NIVELES"
ESTADO_GAMEOVER = "GAMEOVER"
ESTADO_TUTORIAL = "TUTORIAL"
ESTADO_VICTORIA = "VICTORIA"
ESTADO_SELECT_PERSONAJE = "SELECT_PERSONAJE"
ESTADO_SELECT_NIVEL = "SELECT_NIVEL"
ESTADO_LANG_SELECT = "LANG_SELECT"
ESTADO_INTRO_VIDEO = "INTRO_VIDEO"
ESTADO_VICTORY_SCREEN = "VICTORY_SCREEN"



def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init(44100, -16, 2, 512)

    ventana = pygame.display.set_mode((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    pygame.display.set_caption("Krab's adventure")
    reloj = pygame.time.Clock()
    prefs = _load_prefs()

    # === ESTADO INICIAL ===
    estado = ESTADO_LANG_SELECT

    # === BOTONES DE IDIOMA ===
    BTN_W, BTN_H = 260, 60
    btn_es = pygame.Rect(0, 0, BTN_W, BTN_H)
    btn_en = pygame.Rect(0, 0, BTN_W, BTN_H)
    btn_es.center = (constantes.ANCHO_VENTANA // 2, 300)
    btn_en.center = (constantes.ANCHO_VENTANA // 2, 380)

    # === VIDEO INTRO (variable temporal) ===
    video_intro = None

    # Tutorial (si existe)
    try:
        tutorial_img = pygame.image.load(IMG_DIR / "ui" / "tutorial.png").convert_alpha()
    except Exception:
        tutorial_img = None
    tutorial_overlay = TutorialOverlay(
        (constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA),
        tutorial_img if tutorial_img else pygame.Surface((800, 450), pygame.SRCALPHA)
    ) if tutorial_img else None

    # HUD imágenes
    try:
        vida_lleno_img = pygame.image.load(IMG_DIR / "vidas/vida_llena.png").convert_alpha()
        vida_vacio_img = pygame.image.load(IMG_DIR / "vidas/vida_vacia.png").convert_alpha()
        vida_lleno_img = pygame.transform.scale(vida_lleno_img, (32, 32))
        vida_vacio_img = pygame.transform.scale(vida_vacio_img, (32, 32))
    except pygame.error as e:
        print(f"ERROR AL CARGAR IMÁGENES DEL HUD: {e}")
        vida_lleno_img = vida_vacio_img = None
    # --- Bandera (sprite) ---
    try:
        # Tamaño original: NO la escales
        flag_img = pygame.image.load(IMG_DIR / "props" / "bandera.png").convert_alpha()
    except Exception as e:
        print("[WARN] No se pudo cargar bandera:", e)
        flag_img = None

    # Posición por nivel (mundo, en píxeles) de la base de la bandera (bottom-left)
    # Ajusta estos valores a tu mapa:
    FLAG_POS_BY_LEVEL = {
        1: (5491, 683),  # NIVEL 1
        2: (6485, 845),  # NIVEL 2 (ejemplo)
        3: (8673, 871),  # si algún día agregas nivel 3
    }

    # variable que usaremos al dibujar (se actualiza al cargar cada nivel)
    flag_pos_world = FLAG_POS_BY_LEVEL.get(1, (0, 0))

    # Intro
    font_hud = get_font(constantes.FONT_HUD)
    tiempo_total = float(getattr(constantes, "TIEMPO_NIVEL1", 60))
    timer = tiempo_total

    # Recursos menú
    fondo_menu = escalar_a_ventana(cargar_primera_imagen("menufondo", False))
    titulo_img = scale_to_width(cargar_primera_imagen("menu_titulo", True), 360)
    img_play = scale_to_width(cargar_primera_imagen("botonplay", True), 360)
    img_opciones = scale_to_width(cargar_primera_imagen("botonopciones", True), 340)
    img_salir = scale_to_width(cargar_primera_imagen("botonsalir", True), 345)
    # -------------- Miniaturas de los niveles --------------
    thumbs = {}
    try:
        t1 = pygame.image.load(IMG_DIR / "ui" / "niveles" / "nivel1_thumb.png").convert_alpha()
        t2 = pygame.image.load(IMG_DIR / "ui" / "niveles" / "nivel2_thumb.png").convert_alpha()
        t3 = pygame.image.load(IMG_DIR / "ui" / "niveles" / "nivel3_thumb.png").convert_alpha()

        t1 = pygame.transform.scale(t1, (190, 185))
        t2 = pygame.transform.scale(t2, (190, 185))
        t3 = pygame.transform.scale(t3, (190, 185))

        thumbs = {1: t1, 2: t2, 3: t3}
    except Exception as e:
        print(f"[WARN] No se pudieron cargar miniaturas de nivel: {e}")

    # Retratos selección (32x32 → 160x160)
    try:
        portrait_krabby = pygame.image.load(IMG_DIR / "ui" / "select_krabby.png").convert_alpha()
        portrait_karol = pygame.image.load(IMG_DIR / "ui" / "select_karol.png").convert_alpha()
        portrait_krabby = pygame.transform.scale(portrait_krabby, (160, 160))
        portrait_karol = pygame.transform.scale(portrait_karol, (160, 160))
    except Exception as e:
        print("Aviso portraits:", e)
        portrait_krabby = pygame.Surface((160, 160), pygame.SRCALPHA);
        portrait_krabby.fill((30, 140, 220))
        portrait_karol = pygame.Surface((160, 160), pygame.SRCALPHA);
        portrait_karol.fill((220, 60, 140))
    # ---------- Iconos de dificultad ----------
    # Rutas sugeridas: assets/images/ui/dificultad/facil.png y dificil.png
    try:
        icon_easy = pygame.image.load(IMG_DIR / "ui" / "dificultad" / "facil.png").convert_alpha()
        icon_hard = pygame.image.load(IMG_DIR / "ui" / "dificultad" / "dificil.png").convert_alpha()
        # tamaño agradable para la tarjeta
        icon_easy = pygame.transform.smoothscale(icon_easy, (96, 96))
        icon_hard = pygame.transform.smoothscale(icon_hard, (96, 96))
    except Exception as e:
        print("[WARN] No se pudieron cargar iconos de dificultad:", e)
        icon_easy = icon_hard = None

    # Botones del menú
    COL_X = int(constantes.ANCHO_VENTANA * 0.28)
    Y1 = int(constantes.ALTO_VENTANA * 0.15)
    COL_TITLE = int(constantes.ANCHO_VENTANA * 0.28)
    COL_play = int(constantes.ANCHO_VENTANA * 0.27)
    Y0, GAP1, GAP = int(constantes.ALTO_VENTANA * 0.35), 60, 64
    titulo = ImageButton(titulo_img, midleft=(COL_TITLE, Y1))
    btn_play = ImageButton(img_play, midleft=(COL_play, Y0))
    btn_opc = ImageButton(img_opciones, midleft=(COL_X, btn_play.rect.bottom + GAP1))
    btn_salir = ImageButton(img_salir, midleft=(COL_X, btn_opc.rect.bottom + GAP))

    # Krabby en el menú
    KRAB_MENU_POS = (int(constantes.ANCHO_VENTANA * 0.85), int(constantes.ALTO_VENTANA * 0.83))
    KRAB_MENU_SCALE = 2.0
    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)
    menu_leaving = False

    # Select personaje / nivel / dificultad
    select_ui = None
    selected_gender = None
    select_lock = False
    last_select_time = 0
    SELECT_COOLDOWN_MS = 250

    level_select_ui = None
    diff_ui = None
    selected_difficulty = "FACIL"
    nivel_actual = 1  # ← cambia al elegir

    # Juego
    dificultad_seleccionada = "NORMAL"  # (no usada, pero la conservo por compatibilidad)
    jugador = Personaje(1000000, 100000)
    jugador.knockback_activo = False
    jugador.knockback_timer = 0.0
    jugador.stun_sound_played = False

    parallax = None
    prev_cam_offset_x = 0
    enemigos = pygame.sprite.Group()
    items = pygame.sprite.Group()
    puntuacion = 0
    tutorial_shown_level1 = False
    tutorial_context = None

    # === SPAWN FIX: contadores de gracia/frames ===
    spawn_grace = 0.0
    spawn_skip_frames = 0

    # Música menú
    try:
        musica.play("menu", volumen=0.8)
    except Exception as e:
        print("Aviso música:", e)

    mover_izquierda = mover_derecha = False
    estado, run = ESTADO_MENU, True
    VOL_NORMAL, VOL_PAUSA = 0.8, 0.3
    pause_menu = PauseMenu((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    # CAMBIO AQUÍ: ContinueOverlay → GameOverScreen
    continue_ui = GameOverScreen((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    victory_ui = VictoryScreen((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    freeze_cam_offset = None

    # --------- Game Loop ---------
    while run:
        dt = reloj.tick(constantes.FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos();
        mouse_down = pygame.mouse.get_pressed()[0]

        # -------------------- EVENTOS --------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                musica.stop(300);
                run = False

            elif estado == ESTADO_LANG_SELECT:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if btn_es.collidepoint(mx, my):
                        settings["language"] = "es"
                        # lanzar video ES
                        if _HAS_FFPY and os.path.exists(VIDEO_DIR_ES):
                            video_intro = FFVideo(VIDEO_DIR_ES, ventana.get_size())
                            estado = ESTADO_INTRO_VIDEO
                        else:
                            # Si no hay video, pasar directo al menú
                            estado = ESTADO_MENU
                    elif btn_en.collidepoint(mx, my):
                        settings["language"] = "en"
                        # lanzar video EN
                        if _HAS_FFPY and os.path.exists(VIDEO_DIR_EN):
                            video_intro = FFVideo(VIDEO_DIR_EN, ventana.get_size())
                            estado = ESTADO_INTRO_VIDEO
                        else:
                            estado = ESTADO_MENU

                elif event.type == pygame.KEYDOWN:
                    # Atajos: E para español, I para inglés
                    if event.key == pygame.K_e:
                        settings["language"] = "es"
                        if _HAS_FFPY and os.path.exists(VIDEO_DIR_ES):
                            video_intro = FFVideo(VIDEO_DIR_ES, ventana.get_size())
                            estado = ESTADO_INTRO_VIDEO
                        else:
                            estado = ESTADO_MENU
                    elif event.key == pygame.K_i:
                        settings["language"] = "en"
                        if _HAS_FFPY and os.path.exists(VIDEO_DIR_EN):
                            video_intro = FFVideo(VIDEO_DIR_EN, ventana.get_size())
                            estado = ESTADO_INTRO_VIDEO
                        else:
                            estado = ESTADO_MENU

                # --- REPRODUCCIÓN DE VIDEO INTRO ---
            elif estado == ESTADO_INTRO_VIDEO:
                # permitir saltar con cualquier tecla/click
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    if video_intro:
                        video_intro.close()
                        video_intro = None
                    estado = ESTADO_MENU
                    # aquí puedes arrancar la música del menú en el idioma ya elegido
                    # musica.switch("menu")

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
                        musica.stop(300);
                        run = False

            elif estado == ESTADO_SELECT_PERSONAJE:
                now_ms = pygame.time.get_ticks()
                if now_ms - last_select_time >= SELECT_COOLDOWN_MS and not select_lock:
                    choice = select_ui.handle_event(event)
                    if choice in ("male", "female"):
                        select_lock = True
                        last_select_time = now_ms
                        selected_gender = "M" if choice == "male" else "F"
                        # Crear al jugador según el personaje seleccionado
                        if selected_gender == "M":
                            jugador = Personaje(100, 670, gender="M")  # Krabby
                        else:
                            jugador = Personaje(100, 670, gender="F")  # Karol
                        level_select_ui = LevelSelectUI((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), thumbs)
                        estado = ESTADO_SELECT_NIVEL
                        # Permitir volver al menú con ESC
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        estado = ESTADO_MENU
                        menu_leaving = False
                        menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)
                        try:
                            _clear_input_state()
                        except Exception:
                            pass
                        musica.set_master_volume(settings["volume"])
                        musica.switch("menu")

            elif estado == ESTADO_SELECT_NIVEL:
                choice = level_select_ui.handle_event(event)
                if choice == 1:
                    nivel_actual = 1
                    # Ir a dificultad
                    diff_ui = DifficultySelectUI((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), icon_easy,
                                                 icon_hard)
                    selected_difficulty = "FACIL"
                    estado = ESTADO_DIFICULTAD
                elif choice == 2:
                    nivel_actual = 2
                    # Ir a dificultad
                    diff_ui = DifficultySelectUI((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), icon_easy,
                                                 icon_hard)
                    selected_difficulty = "FACIL"
                    estado = ESTADO_DIFICULTAD
                elif choice == 3:
                    nivel_actual = 3
                    # Ir a dificultad
                    diff_ui = DifficultySelectUI((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), icon_easy,
                                                 icon_hard)
                    selected_difficulty = "FACIL"
                    estado = ESTADO_DIFICULTAD
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    estado = ESTADO_SELECT_PERSONAJE
                    select_lock = False
                    last_select_time = pygame.time.get_ticks()

            elif estado == ESTADO_DIFICULTAD:
                result = diff_ui.handle_event(event)
                if result == "BACK":
                    estado = ESTADO_SELECT_NIVEL
                elif result in ("FACIL", "DIFICIL"):
                    selected_difficulty = result
                    estado = ESTADO_CARGANDO


            elif estado == ESTADO_OPC:
                if event.type == pygame.KEYDOWN:
                    # Volver al menú
                    if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        estado = ESTADO_MENU

                    # Ajustar volumen con flechas
                    elif event.key == pygame.K_LEFT:
                        settings["volume"] = max(0.0, settings["volume"] - 0.05)
                        musica.set_master_volume(settings["volume"])
                    elif event.key == pygame.K_RIGHT:
                        settings["volume"] = min(1.0, settings["volume"] + 0.05)
                        musica.set_master_volume(settings["volume"])

                    # Toggle de idioma con Enter/Espacio si el cursor está sobre el botón (opcional)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        mx, my = pygame.mouse.get_pos()
                        if btn_lang_rect.collidepoint(mx, my):
                            settings["language"] = "en" if settings["language"] == "es" else "es"

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos

                    # Slider: iniciar drag si clickea sobre la barra/handle
                    handle_x = slider_handle_pos_x()
                    handle_hit = pygame.Rect(handle_x - HANDLE_R, slider_bar_rect.centery - HANDLE_R, HANDLE_R * 2,
                                             HANDLE_R * 2)
                    if handle_hit.collidepoint(mx, my) or slider_bar_rect.collidepoint(mx, my):
                        slider_dragging = True
                        rel = (mx - slider_bar_rect.left) / slider_bar_rect.width
                        settings["volume"] = min(1.0, max(0.0, rel))
                        musica.set_master_volume(settings["volume"])

                    # Botón de idioma
                    if btn_lang_rect.collidepoint(mx, my):
                        settings["language"] = "en" if settings["language"] == "es" else "es"

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    slider_dragging = False

                elif event.type == pygame.MOUSEMOTION and slider_dragging:
                    mx, my = event.pos
                    rel = (mx - slider_bar_rect.left) / slider_bar_rect.width
                    settings["volume"] = min(1.0, max(0.0, rel))
                    musica.set_master_volume(settings["volume"])


            elif estado == ESTADO_JUEGO:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        jugador.start_attack()
                    if event.key == pygame.K_ESCAPE:
                        estado = ESTADO_PAUSA
                        musica.set_master_volume(settings["volume"] * 0.5)  # volumen reducido
                    if event.key in (pygame.K_a, pygame.K_LEFT):  mover_izquierda = True
                    if event.key in (pygame.K_d, pygame.K_RIGHT): mover_derecha = True
                    if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                        # Solo permite saltar si REALMENTE hay suelo ahora mismo
                        if esta_en_suelo(jugador, nivel.collision_rects):
                            try:
                                if getattr(jugador, "en_piso", False):
                                    musica.sfx("jump", volume=0.9)
                            except Exception:
                                pass
                            jugador.saltar()
                    if event.key == pygame.K_F1 and tutorial_overlay:
                        estado = ESTADO_TUTORIAL
                        musica.set_master_volume(settings["volume"] * 0.5)  # volumen reducido
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_a, pygame.K_LEFT):  mover_izquierda = False
                    if event.key in (pygame.K_d, pygame.K_RIGHT): mover_derecha = False
                    if event.key == pygame.K_F9:
                        print("Jugador midbottom:", jugador.forma.midbottom)

            # === BLOQUE NUEVO: MANEJO DE PAUSA ===
            elif estado == ESTADO_PAUSA:
                action = pause_menu.handle_event(event)
                if action == "resume":
                    estado = ESTADO_JUEGO
                    musica.set_master_volume(settings["volume"])
                    # limpiar entradas pegadas
                    mover_izquierda = False
                    mover_derecha = False
                    try:
                        _clear_input_state()
                    except Exception:
                        pass
                elif action == "menu":
                    estado = ESTADO_MENU
                    musica.set_master_volume(settings["volume"])
                    musica.switch("menu")
                    menu_leaving = False
                    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)
                    try:
                        _clear_input_state()
                    except Exception:
                        pass
            # === FIN BLOQUE NUEVO ===

            elif estado == ESTADO_CONTINUE:
                # CAMBIO AQUÍ: Actualizar botones del Game Over
                continue_ui.update(mouse_pos)
                action = continue_ui.handle_event(event)
                if action == "continuar":
                    estado = ESTADO_CARGANDO
                    freeze_cam_offset = None
                elif action == "menu":
                    musica.set_master_volume(settings["volume"])
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

                        tutorial_shown_level1 = True  # ✅ marcar como visto
                        prefs["tutorial_seen"] = True
                        _save_prefs(prefs)

                        # === SPAWN FIX: al cerrar tutorial, dar protección de spawn ===
                        spawn_grace = SPAWN_GRACE
                        spawn_skip_frames = SPAWN_SKIP_FRAMES
                        jugador.invencible = True
                        jugador.invencible_timer = SPAWN_GRACE
                        jugador.knockback_activo = False
                        jugador.knockback_timer = 0.0
                        jugador.vel_y = 0
                        jugador.en_piso = True

                        estado = ESTADO_JUEGO
                        musica.set_master_volume(settings["volume"])

            elif estado == ESTADO_VICTORIA:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE,
                                                                  pygame.K_ESCAPE):
                    musica.switch("menu")
                    estado = ESTADO_MENU
                    menu_leaving = False
                    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)

            elif estado == ESTADO_VICTORY_SCREEN:
                victory_ui.update(mouse_pos)
                action = victory_ui.handle_event(event)
                if action == "menu":
                    musica.switch("menu")
                    estado = ESTADO_MENU
                    menu_leaving = False
                    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)

        # -------------------- UPDATE --------------------
        if estado == ESTADO_MENU:
            menu_krab.update(dt)
            if menu_leaving and menu_krab.offscreen(constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA):
                musica.set_master_volume(settings["volume"])
                select_ui = CharacterSelectUI((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), portrait_krabby,
                                              portrait_karol)
                estado = ESTADO_SELECT_PERSONAJE
                select_lock = False
                last_select_time = pygame.time.get_ticks()

        elif estado == ESTADO_CARGANDO:
            # Carga el TMX según nivel_actual
            nivel = NivelTiled(MAP_DIR / f"nivel{nivel_actual}.tmx")
            cam = Camara((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), nivel.world_size())
            flag_pos_world = FLAG_POS_BY_LEVEL.get(nivel_actual, FLAG_POS_BY_LEVEL.get(1, (0, 0)))
            cx = jugador.forma.centerx - cam.vw // 2
            cy = jugador.forma.centery - cam.vh // 2
            cx = max(0, min(cx, cam.ww - cam.vw))
            cy = max(0, min(cy, cam.wh - cam.vh))
            cam.set_offset(cx, cy)
            cam.follow(jugador.forma, lerp=1.0)

            print("[DEBUG] Estado de carga: Iniciando nivel", nivel_actual)
            try:
                musica.switch(f"nivel{nivel_actual}")  # ← reproduce nivel1, nivel2, nivel3 según corresponda
                musica.set_master_volume(settings["volume"])
            except Exception as e:
                print("Aviso música de nivel:", e)
            puntuacion = 0
            timer = tiempo_total
            parallax = create_parallax_nivel1()
            prev_cam_offset_x = cam.offset()[0]

            reiniciar_nivel(nivel, jugador)
            cam = Camara((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), nivel.world_size())
            cam.follow(jugador.forma, lerp=1.0)
            parallax = create_parallax_nivel1()
            prev_cam_offset_x = cam.offset()[0]
            mover_derecha = False
            mover_izquierda = False

            enemigos = pygame.sprite.Group()

            def _ir_a_victoria():
                nonlocal estado
                if nivel_actual == 3:
                    musica.switch("victoria_lvl3")
                    estado = "VICTORY_SCREEN"
                else:
                    estado = ESTADO_VICTORIA

            secuencia_victoria = SecuenciaVictoria(
                jugador,
                pygame.Rect(flag_pos_world[0], flag_pos_world[1] - 200, 32, 200),
                nivel,
                on_finish=_ir_a_victoria
            )

            if nivel_actual == 1:
                enemigos.add(
                    Enemigo(x=450, y=675, velocidad=34, escala=2.5),
                    Enemigo(x=800, y=675, velocidad=35, escala=2.5),
                    Enemigo(x=760, y=450, velocidad=35, escala=2.5),
                    Enemigo(x=2176, y=640, velocidad=35, escala=2.5),
                    Enemigo(x=2750, y=381, velocidad=35, escala=2.5),
                    Enemigo(x=4000, y=640, velocidad=35, escala=2.5),
                    Enemigo(x=5100, y=420, velocidad=35, escala=2.5),
                    Enemigo(x=2830, y=643, velocidad=35, escala=2.5),
                    Enemigo(x=3725, y=320, escala=2.5)
                )
            elif nivel_actual == 2:
                enemigos.add(
                    Enemigo_walk(x=299, y=833, velocidad = 40),
                    Enemigo(x=450, y=675, velocidad=35, escala=2.5),
                    Enemigo_walk(x=1578, y=831, velocidad=40),
                    Enemigo(x=2331, y=830, velocidad=35, escala=2.5),
                    Enemigo(x=2903, y=607, velocidad=35, escala=2.5),
                    Enemigo_walk(x=2922, y=832, velocidad=40),
                    Enemigo_walk(x=3543, y=830, velocidad=40),
                    Enemigo_walk(x=3885, y=830, velocidad=40),
                    Enemigo(x=3878, y=576, velocidad=35, escala=2.5),
                    Enemigo(x=4572, y=606, velocidad=35, escala=2.5),
                    Enemigo_walk(x=5445, y=832, velocidad=40),
                    Enemigo(x=5442, y=574, velocidad=35, escala=2.5),
                    Enemigo_walk(x=6084, y=448, velocidad=40),

                )
            elif nivel_actual == 3:
                enemigos.add(
                    Enemigo_walk(x=611, y=864, velocidad = 40),
                    Enemigo(x=869, y=671, velocidad=35, escala=2.5),
                    Enemigo_walk(x=1469, y=864, velocidad=40),
                    Enemigo_walk(x=2414, y=864, velocidad=40),
                    Enemigo_walk(x=2046, y=864, velocidad=40),
                    Enemigo_walk(x=1744, y=864, velocidad=40),
                    Enemigo(x=2132, y=702, velocidad=35, escala=2.5),
                    Enemigo(x=2121, y=545, velocidad=35, escala=2.5),
                    Enemigo_walk(x=2862, y=864, velocidad=40),
                    Enemigo_walk(x=4801, y=864, velocidad=40),
                    Enemigo(x=4445, y=864, velocidad=35, escala=2.5),
                    Enemigo_walk(x=4083, y=864, velocidad=40),
                    Enemigo_walk(x=5946, y=864, velocidad=40),
                    Enemigo(x=5933, y=735, velocidad=35, escala=2.5),
                    Enemigo_walk(x=7548, y=864, velocidad=40),
                    Enemigo(x=7552, y=672, velocidad=35, escala=2.5),
                    Enemigo(x=7550, y=543, velocidad=35, escala=2.5),
                    Enemigo(x=7552, y=672, velocidad=35, escala=2.5),
                    Enemigo(x=8319, y=448, velocidad=35, escala=2.5),

                )
            items = pygame.sprite.Group()
            if nivel_actual == 1:
                items.add(
                    Manzana(x=338, y=479),
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
                    bolsa(x=3715, y=260)
                )

            # === Ajustes por dificultad ===
            if selected_difficulty == "DIFICIL":
                timer = tiempo_total * 0.7  # menos tiempo
                for e in enemigos:
                    # + VIDA (duplica vida y, si existe, vida máxima)
                    if hasattr(e, "vida_maxima"):
                        e.vida_maxima = int(e.vida_maxima * 1.5)
                        if hasattr(e, "vida"):
                            # Aumenta la vida actual en proporción sin exceder el nuevo máximo
                            e.vida = min(int(e.vida * 1.5), e.vida_maxima)
                    elif hasattr(e, "vida"):
                        e.vida = int(e.vida * 1.5)

                    # x2 DAÑO (intenta cubrir distintos nombres de atributo)
                    if hasattr(e, "attack_damage"):
                        e.attack_damage = int(e.attack_damage * 2)
                    elif hasattr(e, "dano"):
                        e.dano = int(e.dano * 2)
                    elif hasattr(e, "daño"):
                        setattr(e, "daño", int(getattr(e, "daño") * 2))
                    elif hasattr(e, "damage"):
                        e.damage = int(e.damage * 2)

                jugador.vida_actual = jugador.vida_maxima
            else:
                timer = tiempo_total
                jugador.vida_actual = jugador.vida_maxima

            # Mostrar tutorial solo en nivel 1, fácil y primera vez
            if (
                    nivel_actual == 1
                    and selected_difficulty == "FACIL"
                    and not tutorial_shown_level1
                    and tutorial_overlay
            ):
                tutorial_context = "game"
                estado = ESTADO_TUTORIAL
                musica.set_master_volume(settings["volume"] * 0.5)  # volumen reducido
            else:
                # === SPAWN FIX: al entrar directo al juego, activar gracia/frames ===
                spawn_grace = SPAWN_GRACE
                spawn_skip_frames = SPAWN_SKIP_FRAMES
                jugador.invencible = True
                jugador.invencible_timer = SPAWN_GRACE
                jugador.knockback_activo = False
                jugador.knockback_timer = 0.0
                jugador.vel_y = 0
                jugador.en_piso = True
                estado = ESTADO_JUEGO

        elif estado == ESTADO_TUTORIAL:
            pass  # la interacción se maneja en eventos

        elif estado == ESTADO_JUEGO:
            # === SPAWN FIX: protección de los primeros frames y gracia ===
            if spawn_skip_frames > 0:
                spawn_skip_frames -= 1

            if spawn_grace > 0.0:
                spawn_grace = max(0.0, spawn_grace - dt)
                jugador.invencible = True
                jugador.invencible_timer = max(getattr(jugador, "invencible_timer", 0.0), spawn_grace)
                jugador.knockback_activo = False
                jugador.knockback_timer = 0.0

                # Repegar al piso durante la gracia (por si la física movió algo)
                px = jugador.forma.centerx
                best_top = None
                for r in nivel.collision_rects:
                    if r.left - 2 <= px <= r.right + 2:
                        if r.top >= jugador.forma.bottom - 120:
                            if (best_top is None) or (r.top < best_top):
                                best_top = r.top
                if best_top is not None:
                    jugador.forma.bottom = int(best_top)
                jugador.vel_y = 0
                jugador.en_piso = True

                # En los frames de spawn evitamos el resto de la lógica/peligros
                # Mantén HUD, cámara y animación suaves:
                jugador.actualizar(dt)
                jugador.animar(dt)
                cam.follow(jugador.forma, lerp=1.0)
                if parallax is not None:
                    new_ox = cam.offset()[0]
                    camera_dx = new_ox - prev_cam_offset_x
                    prev_cam_offset_x = new_ox
                    parallax.update_by_camera(camera_dx)

                # saltamos el resto del update de juego este frame
                continue

            # Tiempo
            timer -= dt
            if timer <= 0:
                timer = 0
                try:
                    musica.sfx("death", volume=0.9)
                except Exception:
                    pass

                # Música de derrota (sin loop)
                try:
                    musica.switch("derrota", crossfade_ms=200)
                    musica.set_master_volume(settings["volume"])
                except Exception as e:
                    print("Aviso música derrota (timeout):", e)

                freeze_cam_offset = cam.offset()
                iniciar_muerte(jugador)

                estado = ESTADO_MUERTE

            jugador.actualizar(dt)
            jugador.update(dt, nivel.collision_rects)
            colisiones_para_enemigos = nivel.collision_rects + getattr(nivel, "enemy_barrier_rects", [])
            enemigos.update(dt, colisiones_para_enemigos)

            # Caída del nivel
            if jugador.forma.bottom > nivel.tmx.height * nivel.tmx.tileheight:
                try:
                    musica.sfx("death", volume=0.9)
                except Exception:
                    pass

                try:
                    musica.switch("derrota", crossfade_ms=200)
                    musica.set_master_volume(settings["volume"])
                except Exception as e:
                    print("Aviso música derrota (caída):", e)

                freeze_cam_offset = cam.offset()
                iniciar_muerte(jugador)
                # pygame.mixer.music.set_volume(0.35)
                estado = ESTADO_MUERTE

            # Items
            for item in list(items.sprites()):
                if item.tocar_jugador(jugador):
                    puntuacion += item.puntos
                    musica.sfx("coin", volume=0.8)
                    item.kill()

            # I-frames
            if getattr(jugador, "invencible", False):
                jugador.invencible_timer -= dt
                if jugador.invencible_timer <= 0:
                    jugador.invencible = False
                    jugador.stun_sound_played = False

            # Knockback
            if getattr(jugador, "knockback_activo", False):
                jugador.knockback_timer -= dt
                if jugador.knockback_timer <= 0:
                    jugador.knockback_activo = False

            # Movimiento
            if getattr(jugador, "knockback_activo", False):
                direccion_knockback = -1 if jugador.facing_right else 1
                dx = jugador.knockback_speed_x * direccion_knockback * dt
                vx = 0
            else:
                vx = (constantes.VELOCIDAD if mover_derecha else 0) - (constantes.VELOCIDAD if mover_izquierda else 0)
                dx = vx * dt

            jugador.aplicar_gravedad(dt)
            dy = int(jugador.vel_y * dt)

            jugador.forma.x += int(dx)
            for rect in nivel.collision_rects:
                if jugador.forma.colliderect(rect):
                    if dx > 0:
                        jugador.forma.right = rect.left
                    elif dx < 0:
                        jugador.forma.left = rect.right

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

            if not getattr(jugador, "invencible", False):
                jugador.set_dx(vx)

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

            # Cámara + parallax
            cam.follow(jugador.forma, lerp=1.0)
            if parallax is not None:
                new_ox = cam.offset()[0]
                camera_dx = new_ox - prev_cam_offset_x
                prev_cam_offset_x = new_ox
                parallax.update_by_camera(camera_dx)

            # Meta
            for goal in nivel.goal_rects:
                if jugador.forma.colliderect(goal):
                    if not getattr(secuencia_victoria, "activa", False):
                        secuencia_victoria.iniciar()
                    break

            # Ataque
            if jugador.attacking and jugador.attack_timer > 0:
                atk = jugador.get_attack_rect()
                for e in list(enemigos):
                    if atk.colliderect(e.rect):
                        if hasattr(e, "hurt"):
                            e.hurt(jugador.attack_damage)
                            if not jugador.hit_sound_played:
                                musica.sfx("golpe", volume=0.9)
                                jugador.hit_sound_played = True
                        if e.vida <= 0:
                            puntuacion += e.puntos

            if jugador.attack_timer <= 0:
                jugador.hit_sound_played = False

            # Daño del enemigo
            for e in enemigos:
                if e.tocar_jugador(jugador) and not getattr(jugador, "invencible", False):
                    if selected_difficulty == "DIFICIL":
                        jugador.recibir_dano(2)
                        try:
                            musica.sfx("stun", volume=0.9)
                        except Exception:
                            pass
                        jugador.invencible = True
                        jugador.invencible_timer = 0.45
                        jugador.knockback_activo = True
                        jugador.knockback_timer = 0.22
                        if not hasattr(jugador, "knockback_speed_x") or jugador.knockback_speed_x == 0:
                            jugador.knockback_speed_x = 650
                    else:
                        jugador.recibir_dano(1)
                        try:
                            musica.sfx("stun", volume=0.9)
                        except Exception:
                            pass
                        jugador.invencible = True
                        jugador.invencible_timer = 0.45
                        jugador.knockback_activo = True
                        jugador.knockback_timer = 0.22
                        if not hasattr(jugador, "knockback_speed_x") or jugador.knockback_speed_x == 0:
                            jugador.knockback_speed_x = 650

            # Muerte por vida
            if jugador.vida_actual <= 0 and estado == ESTADO_JUEGO:
                vx = 0
                jugador.knockback_activo = False
                jugador.knockback_timer = 0.0
                musica.sfx("death", volume=0.9)

                try:
                    musica.switch("derrota", crossfade_ms=200)
                    musica.set_master_volume(settings["volume"])
                except Exception as e:
                    print("Aviso música derrota (hp=0):", e)

                freeze_cam_offset = cam.offset()
                iniciar_muerte(jugador)
                estado = ESTADO_MUERTE

                # ⛳ Si la secuencia de victoria está activa, congelar jugabilidad normal
            if "secuencia_victoria" in locals() and secuencia_victoria.activa:
                mover_izquierda = False
                mover_derecha = False
                reproducido = False

                # congela al jugador
                jugador.state = "idle"
                jugador.set_dx(0)
                jugador.vx = 0  # ← asegura velocidad horizontal 0
                # avanzar la cinemática (caminar → girar → subir bandera → esperar → salir)
                secuencia_victoria.actualizar(dt)
                # animación del sprite aquí (NUNCA en EVENTOS)
                jugador.animar(dt)
                # cámara/parallax pueden seguir al jugador durante la escena
                cam.follow(jugador.forma, lerp=1.0)
                if parallax is not None:
                    new_ox = cam.offset()[0]
                    camera_dx = new_ox - prev_cam_offset_x
                    prev_cam_offset_x = new_ox
                    parallax.update_by_camera(camera_dx)

                # saltar TODO lo demás de la lógica de juego este frame

        elif estado == ESTADO_VICTORIA:
            # Mantén al jugador animando en idle (sin freeze)
            jugador.set_dx(0)
            jugador.state = "idle"
            jugador.animar(dt)
            # Mantén cámara/parallax vivos (aunque no se muevan ya)
            cam.follow(jugador.forma, lerp=1.0)
            if parallax is not None:
                new_ox = cam.offset()[0]
                camera_dx = new_ox - prev_cam_offset_x
                prev_cam_offset_x = new_ox
                parallax.update_by_camera(camera_dx)

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
            # CAMBIO AQUÍ: Ya no hay temporizador automático, solo actualizamos botones
            continue_ui.update(mouse_pos)
            # El cambio de estado ahora se maneja completamente con los botones/teclado

        # -------------------- DRAW --------------------

        # --- UPDATE ---
        if estado == ESTADO_INTRO_VIDEO and video_intro:
            video_intro.update()
            if video_intro.done:
                video_intro.close()
                video_intro = None
                estado = ESTADO_MENU
                # musica.switch("menu")

        # --- DRAW ---
        if estado == ESTADO_LANG_SELECT:
            ventana.fill((10, 10, 14))
            # Título (usa un fallback si language aún es None)
            lang_ui = "es"
            t = I18N[lang_ui]
            title = get_font(constantes.FONT_SUBTITLE).render(t["select_lang"], True, (255, 255, 255))
            ventana.blit(title, (constantes.ANCHO_VENTANA // 2 - title.get_width() // 2, 120))

            # Botón ES
            pygame.draw.rect(ventana, (40, 40, 60), btn_es, border_radius=12)
            pygame.draw.rect(ventana, (120, 120, 160), btn_es, 2, border_radius=12)
            txt_es = get_font(constantes.FONT_TEXT).render(t["spanish"], True, (230, 230, 230))
            ventana.blit(txt_es, (btn_es.centerx - txt_es.get_width() // 2, btn_es.centery - txt_es.get_height() // 2))

            # Botón EN
            pygame.draw.rect(ventana, (40, 40, 60), btn_en, border_radius=12)
            pygame.draw.rect(ventana, (120, 120, 160), btn_en, 2, border_radius=12)
            txt_en = get_font(constantes.FONT_TEXT).render(t["english"], True, (230, 230, 230))
            ventana.blit(txt_en, (btn_en.centerx - txt_en.get_width() // 2, btn_en.centery - txt_en.get_height() // 2))

        elif estado == ESTADO_INTRO_VIDEO:
            ventana.fill((0, 0, 0))
            if video_intro:
                video_intro.draw(ventana)
                # hint para saltar
                lang = settings["language"] or "es"
                t = I18N[lang]
                hint = get_font(constantes.FONT_SMALL).render(t["skip"], True, (200, 200, 200))
                ventana.blit(hint,
                             (constantes.ANCHO_VENTANA // 2 - hint.get_width() // 2, constantes.ALTO_VENTANA - 40))

        if estado == ESTADO_MENU:
            ventana.blit(fondo_menu, (0, 0))
            titulo.draw(ventana);
            btn_play.draw(ventana);
            btn_opc.draw(ventana);
            btn_salir.draw(ventana)
            menu_krab.draw(ventana)

        elif estado == ESTADO_OPC:
            ventana.blit(fondo_menu, (0, 0))

            lang = settings["language"]
            t = I18N[lang]

            # Título
            sub = get_font(constantes.FONT_SUBTITLE).render(t["options_title"], True, (255, 255, 255))
            ventana.blit(sub, (constantes.ANCHO_VENTANA // 2 - sub.get_width() // 2, 60))

            # Etiqueta Volumen
            vol_label = get_font(constantes.FONT_HUD).render(t["volume"], True, (220, 220, 220))
            ventana.blit(vol_label, (slider_bar_rect.centerx - vol_label.get_width() // 2, slider_bar_rect.top - 40))

            # Slider (bar + progress + handle)
            pygame.draw.rect(ventana, (80, 80, 90), slider_bar_rect, border_radius=SLIDER_H // 2)
            progress_rect = slider_bar_rect.copy()
            progress_rect.width = int(settings["volume"] * slider_bar_rect.width)
            pygame.draw.rect(ventana, (120, 180, 255), progress_rect, border_radius=SLIDER_H // 2)

            hx = slider_handle_pos_x()
            hy = slider_bar_rect.centery
            pygame.draw.circle(ventana, (240, 240, 255), (hx, hy), HANDLE_R)

            hint = get_font(constantes.FONT_HUD).render(t["hint"], True, (180, 180, 180))
            ventana.blit(hint, (slider_bar_rect.centerx - hint.get_width() // 2, slider_bar_rect.bottom + 12))

            # Botón de idioma
            pygame.draw.rect(ventana, (40, 40, 50), btn_lang_rect, border_radius=12)
            pygame.draw.rect(ventana, (120, 120, 140), btn_lang_rect, width=2, border_radius=12)

            lang_label = get_font(constantes.FONT_HUD).render(t["language"], True, (230, 230, 230))
            ventana.blit(lang_label, (btn_lang_rect.centerx - lang_label.get_width() // 2, btn_lang_rect.top + 6))

            lang_value_str = t["lang_value"][settings["language"]]
            lang_value = get_font(constantes.FONT_HUD).render(lang_value_str, True, (180, 210, 255))
            ventana.blit(lang_value, (btn_lang_rect.centerx - lang_value.get_width() // 2, btn_lang_rect.top + 28))


        elif estado == ESTADO_SELECT_PERSONAJE:
            ventana.blit(fondo_menu, (0, 0))
            select_ui.draw(ventana)

        elif estado == ESTADO_SELECT_NIVEL:
            ventana.blit(fondo_menu, (0, 0))
            level_select_ui.draw(ventana)

        elif estado == ESTADO_DIFICULTAD:
            ventana.blit(fondo_menu, (0, 0))
            diff_ui.draw(ventana)

        elif estado in ("JUEGO", "PAUSA"):
            # Fondo/parallax y mapa
            if parallax is not None:
                parallax.draw(ventana)
            nivel.draw(ventana, cam.offset())

            # Offset de cámara (úsalo para TODO lo que dibujas)
            ox, oy = cam.offset()

            # --- DIBUJAR BANDERA / BASURA ---
            if flag_img:
                if "secuencia_victoria" in locals() and secuencia_victoria.activa:
                    bx = secuencia_victoria.bandera_rect.x - ox
                    by = secuencia_victoria.bandera_rect.bottom - oy
                    fr = flag_img.get_rect(bottomleft=(bx, by))
                else:
                    # fallback por si no existe la variable (usa la posición fija del mapa)
                    fr = flag_img.get_rect(bottomleft=(flag_pos_world[0] - ox, flag_pos_world[1] - oy))
                ventana.blit(flag_img, fr)

            # Enemigos e ítems
            # --- DIBUJAR ENEMIGOS CON OFFSET VISUAL ---
            for e in enemigos:
                ventana.blit(e.image, (e.rect.x - ox, e.rect.y - oy + e.render_offset_y))
            for item in items:
                ventana.blit(item.image, (item.rect.x - ox, item.rect.y - oy))

            # Jugador
            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))
            if estado == "PAUSA":
                pause_menu.draw(ventana)
            # HUD solo si NO hay cutscene de victoria (para que no parezca congelado)
            if not ("secuencia_victoria" in locals() and secuencia_victoria.activa):
                draw_timer(ventana, font_hud, timer, pos=(20, 20))
                draw_hud(ventana, jugador, vida_lleno_img, vida_vacio_img)
                draw_puntuacion(ventana, font_hud, puntuacion)

        elif estado == "MUERTE":
            if parallax is not None:
                parallax.draw(ventana)
            if freeze_cam_offset is None:
                freeze_cam_offset = cam.offset()
            nivel.draw(ventana, freeze_cam_offset)
            ox, oy = freeze_cam_offset
            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))
            draw_timer(ventana, font_hud, max(0, timer), pos=(20, 20))

        elif estado == "CONTINUE":
            # SOLO el nuevo Game Over - sin fondo del juego
            continue_ui.draw(ventana)

        elif estado == ESTADO_VICTORY_SCREEN:
            victory_ui.draw(ventana)


        elif estado == ESTADO_TUTORIAL:
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

            # Dibuja la bandera en su posición final (usa bandera_rect si existe, si no, fallback)
            if flag_img:
                if "secuencia_victoria" in locals():
                    bx = secuencia_victoria.bandera_rect.x - ox
                    by = secuencia_victoria.bandera_rect.bottom - oy
                    fr = flag_img.get_rect(bottomleft=(bx, by))
                else:
                    fr = flag_img.get_rect(bottomleft=(flag_pos_world[0] - ox, flag_pos_world[1] - oy))
                ventana.blit(flag_img, fr)

            # Jugador
            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))

            # Mensaje
            msg = get_font(constantes.FONT_UI_TITLE).render("¡VICTORIA!", True, (255, 255, 0))
            ventana.blit(
                msg,
                (constantes.ANCHO_VENTANA // 2 - msg.get_width() // 2,
                 constantes.ALTO_VENTANA // 2 - msg.get_height() // 2)
            )
            hint = get_font(constantes.FONT_UI_ITEM).render("Pulsa ENTER para volver al menú", True, (255, 255, 255))
            ventana.blit(
                hint,
                (constantes.ANCHO_VENTANA // 2 - hint.get_width() // 2,
                 constantes.ALTO_VENTANA // 2 + 60)
            )
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()