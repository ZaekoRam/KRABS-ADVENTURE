# main.py
import pygame
from pathlib import Path
import constantes
from personaje import Personaje
import musica  # manejo de música

# --- IMPORTS para mapa Tiled y cámara ---
from pytmx.util_pygame import load_pygame

# -------------------- Helpers de rutas e imágenes --------------------
BASE_DIR = Path(__file__).resolve().parent
IMG_DIR  = BASE_DIR / "assets" / "images"
MAP_DIR  = BASE_DIR / "assets" / "maps"

def scale_to_width(surf: pygame.Surface, target_w: int) -> pygame.Surface:
    ratio = target_w / surf.get_width()
    target_h = int(surf.get_height() * ratio)
    return pygame.transform.scale(surf, (target_w, target_h))  # nearest

def cargar_primera_imagen(carpeta_rel: str, usa_alpha: bool) -> pygame.Surface:
    """Carga la primera imagen encontrada dentro de assets/images/<carpeta_rel>."""
    carpeta = IMG_DIR / carpeta_rel
    patrones = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.webp")
    for patron in patrones:
        files = list(carpeta.glob(patron))
        if files:
            surf = pygame.image.load(str(files[0]))
            return surf.convert_alpha() if usa_alpha else surf.convert()
    raise FileNotFoundError(f"No encontré imágenes en {carpeta}")

def escalar_a_ventana(surf: pygame.Surface) -> pygame.Surface:
    return pygame.transform.smoothscale(
        surf, (constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA)
    )

class ImageButton:
    def __init__(self, surf: pygame.Surface, center=None, midleft=None, scale=1.0, hover_scale=1.02):
        self.base = surf
        self.scale = scale
        self.hover_scale = hover_scale
        self.image = self._scaled(self.base, self.scale)
        if center:
            self.rect = self.image.get_rect(center=center)
            self._anchor = ("center", self.rect.center)
        elif midleft:
            self.rect = self.image.get_rect(midleft=midleft)
            self._anchor = ("midleft", self.rect.midleft)
        else:
            self.rect = self.image.get_rect()
            self._anchor = ("topleft", self.rect.topleft)
        self._last_size = self.image.get_size()

    def _scaled(self, surf, factor):
        w = int(surf.get_width() * factor)
        h = int(surf.get_height() * factor)
        return pygame.transform.scale(surf, (w, h))

    def update(self, mouse_pos, mouse_down):
        hovering = self.rect.collidepoint(mouse_pos)
        target = self.hover_scale if (hovering and not mouse_down) else self.scale
        size = (int(self.base.get_width()*target), int(self.base.get_height()*target))
        if size != self._last_size:
            self.image = self._scaled(self.base, target)
            self.rect = self.image.get_rect()
            setattr(self.rect, self._anchor[0], self._anchor[1])  # reanclar
            self._last_size = size

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))

# -------------------- Mapa Tiled + Cámara --------------------
class NivelTiled:
    def __init__(self, ruta_tmx: Path):
        # Carga TMX con imágenes listas para blit
        self.tmx = load_pygame(str(ruta_tmx))
        self.tile_w = self.tmx.tilewidth
        self.tile_h = self.tmx.tileheight
        self.width_px  = self.tmx.width  * self.tile_w
        self.height_px = self.tmx.height * self.tile_h

        # (Opcional) grupos de objetos "Collisions" y "Spawns"
        self.collision_rects = []
        if "Collisions" in self.tmx.objectgroups:
            for obj in self.tmx.objectgroups["Collisions"]:
                r = pygame.Rect(int(obj.x), int(obj.y), int(obj.width), int(obj.height))
                self.collision_rects.append(r)

        self.spawn = None
        if "Spawns" in self.tmx.objectgroups:
            for obj in self.tmx.objectgroups["Spawns"]:
                if getattr(obj, "name", "") == "player":
                    self.spawn = (int(obj.x), int(obj.y))
                    break

    def draw(self, surface: pygame.Surface, camera_offset):
        """Dibuja solo lo visible según el offset de cámara."""
        ox, oy = camera_offset
        sw, sh = surface.get_size()

        x0 = max(0, ox // self.tile_w)
        y0 = max(0, oy // self.tile_h)
        x1 = min(self.tmx.width,  (ox + sw) // self.tile_w + 2)
        y1 = min(self.tmx.height, (oy + sh) // self.tile_h + 2)

        for layer in self.tmx.visible_layers:
            if hasattr(layer, "tiles"):  # solo tile layers
                for x, y, image in layer.tiles():
                    if x0 <= x < x1 and y0 <= y < y1:
                        surface.blit(image, (x * self.tile_w - ox, y * self.tile_h - oy))

    def world_size(self):
        return self.width_px, self.height_px

class Camara:
    def __init__(self, viewport_size, world_size):
        self.vw, self.vh = viewport_size
        self.ww, self.wh = world_size
        self.ox = 0
        self.oy = 0

    def follow(self, target_rect: pygame.Rect, lerp=1.0):
        cx = target_rect.centerx - self.vw // 2
        cy = target_rect.centery - self.vh // 2
        cx = max(0, min(cx, self.ww - self.vw))
        cy = max(0, min(cy, self.wh - self.vh))
        # seguimiento (lerp=1 -> directo)
        self.ox += (cx - self.ox) * lerp
        self.oy += (cy - self.oy) * lerp

    def offset(self):
        return int(self.ox), int(self.oy)

# -------------------- Estados --------------------
ESTADO_MENU   = "MENU"
ESTADO_JUEGO  = "JUEGO"
ESTADO_OPC    = "OPCIONES"

def main():
    # ¡Muy importante! Configurar mixer ANTES de pygame.init()
    pygame.mixer.pre_init(44100, -16, 2, 512)

    pygame.init()
    ventana = pygame.display.set_mode((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    pygame.display.set_caption("Krab's adventure")
    reloj = pygame.time.Clock()

    # Fondos (solo menú)
    fondo_menu  = escalar_a_ventana(cargar_primera_imagen("menufondo",  usa_alpha=False))

    # Botones
    img_play     = cargar_primera_imagen("botonplay",     usa_alpha=True)
    img_opciones = cargar_primera_imagen("botonopciones", usa_alpha=True)
    img_salir    = cargar_primera_imagen("botonsalir",    usa_alpha=True)

    # Escalados
    TARGET_W = 340
    target_play  = 360
    target_salir = 345
    img_play     = scale_to_width(img_play, target_play)
    img_opciones = scale_to_width(img_opciones, TARGET_W)
    img_salir    = scale_to_width(img_salir, target_salir)

    # Colocación
    COL_X     = int(constantes.ANCHO_VENTANA * 0.28)
    COL_play  = int(constantes.ANCHO_VENTANA * 0.27)
    Y0        = int(constantes.ALTO_VENTANA * 0.30)
    GAP1      = 70
    GAP       = 74

    btn_play  = ImageButton(img_play,     midleft=(COL_play, Y0))
    btn_opc   = ImageButton(img_opciones, midleft=(COL_X, btn_play.rect.bottom + GAP1))
    btn_salir = ImageButton(img_salir,    midleft=(COL_X, btn_opc.rect.bottom + GAP))

    # --------- Cargar mapa Tiled y preparar jugador + cámara ----------
    # Cambia el nombre si tu archivo se llama distinto
    tmx_path = MAP_DIR / "nivel1.tmx"
    try:
        nivel = NivelTiled(tmx_path)
    except Exception as e:
        raise SystemExit(f"Error cargando TMX {tmx_path}: {e}")

    # Spawn del jugador (si no hay punto en TMX, usa uno por defecto)
    spawn_x, spawn_y = nivel.spawn if nivel.spawn else (250, 250)
    jugador = Personaje(spawn_x, spawn_y)

    cam = Camara(
        (constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA),
        nivel.world_size()
    )

    # Música inicial: menú
    try:
        musica.play("menu", volumen=0.8)
    except Exception as e:
        print("Aviso música:", e)

    # Flags de input
    jump_held = False
    mover_arriba = mover_abajo = mover_izquierda = mover_derecha = False

    estado = ESTADO_MENU
    run = True
    while run:
        dt = reloj.tick(constantes.FPS) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        mouse_down = pygame.mouse.get_pressed()[0]

        # -------------------- Eventos --------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                musica.stop(300)
                run = False

            if estado == ESTADO_MENU:
                btn_play.update(mouse_pos, mouse_down)
                btn_opc.update(mouse_pos, mouse_down)
                btn_salir.update(mouse_pos, mouse_down)
                if btn_play.clicked(event):
                    estado = ESTADO_JUEGO
                    musica.switch("nivel1")
                elif btn_opc.clicked(event):
                    estado = ESTADO_OPC
                elif btn_salir.clicked(event):
                    musica.stop(300)
                    run = False

            elif estado == ESTADO_OPC:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    estado = ESTADO_MENU
                    musica.switch("menu")

            elif estado == ESTADO_JUEGO:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        estado = ESTADO_MENU
                        musica.switch("menu")
                    if event.key in (pygame.K_a, pygame.K_LEFT) : mover_izquierda = True
                    if event.key in (pygame.K_d, pygame.K_RIGHT): mover_derecha   = True
                    if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                        jump_held = True
                        jugador.saltar(forzado=False)
                    if event.key in (pygame.K_s, pygame.K_DOWN): mover_abajo = True
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_a, pygame.K_LEFT): mover_izquierda = False
                    if event.key in (pygame.K_d, pygame.K_RIGHT): mover_derecha  = False
                    if event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                        jump_held = False
                    if event.key in (pygame.K_s, pygame.K_DOWN): mover_abajo    = False

        # -------------------- Actualizar --------------------
        if estado == ESTADO_JUEGO:
            dx = (constantes.VELOCIDAD if mover_derecha else 0) - (constantes.VELOCIDAD if mover_izquierda else 0)
            dy = (constantes.VELOCIDAD if mover_abajo   else 0) - (constantes.VELOCIDAD if mover_arriba    else 0)

            # Actualiza física/anim del jugador
            jugador.actualizar(dt)
            jugador.movimiento(dx, dy)

            # Cámara siguiendo al jugador
            cam.follow(jugador.forma, lerp=1.0)

        # -------------------- Dibujar --------------------
        if estado == ESTADO_MENU:
            ventana.blit(fondo_menu, (0, 0))
            btn_play.draw(ventana)
            btn_opc.draw(ventana)
            btn_salir.draw(ventana)

        elif estado == ESTADO_OPC:
            ventana.blit(fondo_menu, (0, 0))
            sub = pygame.font.Font(None, 48).render("OPCIONES (ESC para volver)", True, (255, 255, 255))
            ventana.blit(sub, (constantes.ANCHO_VENTANA//2 - sub.get_width()//2, 60))

        elif estado == ESTADO_JUEGO:
            # Dibuja TMX y luego al jugador con offset
            nivel.draw(ventana, cam.offset())
            ox, oy = cam.offset()
            ventana.blit(jugador.image, (jugador.forma.x - ox, jugador.forma.y - oy))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
