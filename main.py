# main.py
import pygame
from pathlib import Path
import constantes
from personaje import Personaje
import musica
from pytmx.util_pygame import load_pygame

# -------------------- Paths --------------------
BASE_DIR = Path(__file__).resolve().parent
IMG_DIR  = BASE_DIR / "assets" / "images"
MAP_DIR  = BASE_DIR / "assets" / "maps"

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
    if getattr(nivel, "spawn", None):
        x, y = int(nivel.spawn[0]), int(nivel.spawn[1])
    else:
        x, y = 250, 250
    jugador.forma.midbottom = (x, y)
    jugador.vel_y = 0
    jugador.en_piso = False

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

        self.collision_rects = []
        if "Collisions" in self.tmx.objectgroups:
            for obj in self.tmx.objectgroups["Collisions"]:
                self.collision_rects.append(pygame.Rect(int(obj.x), int(obj.y), int(obj.width), int(obj.height)))

        self.spawn = None
        if "Spawns" in self.tmx.objectgroups:
            for obj in self.tmx.objectgroups["Spawns"]:
                if getattr(obj, "name", "") == "player":
                    self.spawn = (int(obj.x), int(obj.y)); break

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
        self.font_title = pygame.font.Font(None, 64)
        self.font_item  = pygame.font.Font(None, 42)
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
        self.font_title = pygame.font.Font(None, 64)
        self.font_item  = pygame.font.Font(None, 42)
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
        self.p.en_piso = True
        self.p.vel_y = 0
        self.state = "idle"
        self.vx = 0.0
        self.scale = float(scale)

    def jump_and_leave(self):
        if self.state != "idle": return
        try: musica.sfx("jump", volume=0.9)
        except Exception: pass
        self.state = "leaving"
        self.p.saltar(forzado=True)
        self.vx = float(getattr(constantes, "VELOCIDAD", 300)) * 0.9

    def update(self, dt):
        if self.state == "idle":
            self.p.set_dx(0)
            self.p.state = "idle"
            self.p.animar(dt)
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
ESTADO_MUERTE   = "MUERTE"
ESTADO_CONTINUE = "CONTINUE"
ESTADO_GAMEOVER = "GAMEOVER"

def main():
    pygame.mixer.pre_init(44100, -16, 2, 512); pygame.init()
    ventana = pygame.display.set_mode((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    pygame.display.set_caption("Krab's adventure")
    reloj = pygame.time.Clock()

    font_hud = pygame.font.Font(None, 36)

    tiempo_total = float(getattr(constantes, "TIEMPO_NIVEL1", 60))
    timer = tiempo_total

    # --- Recursos menú
    fondo_menu = escalar_a_ventana(cargar_primera_imagen("menufondo", False))
    img_play     = scale_to_width(cargar_primera_imagen("botonplay",     True), 360)
    img_opciones = scale_to_width(cargar_primera_imagen("botonopciones", True), 340)
    img_salir    = scale_to_width(cargar_primera_imagen("botonsalir",    True), 345)

    COL_X = int(constantes.ANCHO_VENTANA * 0.28)
    COL_play = int(constantes.ANCHO_VENTANA * 0.27)
    Y0, GAP1, GAP = int(constantes.ALTO_VENTANA * 0.30), 70, 74
    btn_play  = ImageButton(img_play,     midleft=(COL_play, Y0))
    btn_opc   = ImageButton(img_opciones, midleft=(COL_X, btn_play.rect.bottom + GAP1))
    btn_salir = ImageButton(img_salir,    midleft=(COL_X, btn_opc.rect.bottom + GAP))

    # ---- Krabby en el menú (más grande y movido a la derecha)
    KRAB_MENU_POS  = (int(constantes.ANCHO_VENTANA*0.85), int(constantes.ALTO_VENTANA*0.83))
    KRAB_MENU_SCALE = 2.0  # <-- ajusta a tu gusto: 1.5, 2.0, 2.5...
    menu_krab = MenuKrab(midbottom=KRAB_MENU_POS, scale=KRAB_MENU_SCALE)
    menu_leaving = False

    # --- Nivel y jugador
    nivel = NivelTiled(MAP_DIR / "nivel1.tmx")
    spawn_x, spawn_y = nivel.spawn if nivel.spawn else (250, 250)
    jugador = Personaje(spawn_x, spawn_y)

    # Alinear al piso al iniciar
    suelo_top = constantes.ALTO_VENTANA - constantes.ALTURA_SUELO
    jugador.forma.bottom = suelo_top
    jugador.en_piso = True
    jugador.vel_y = 0

    cam = Camara((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA), nivel.world_size())

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
                    jugador.forma.bottom = constantes.ALTO_VENTANA - constantes.ALTURA_SUELO
                    jugador.vel_y = 0; jugador.en_piso = True
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

        # -------------------- Update --------------------
        if estado == ESTADO_MENU:
            menu_krab.update(dt)
            if menu_leaving and menu_krab.offscreen(constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA):
                musica.switch("nivel1")
                pygame.mixer.music.set_volume(VOL_NORMAL)
                timer = tiempo_total
                estado = ESTADO_JUEGO

        elif estado == ESTADO_JUEGO:
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
            dx = vx * dt

            jugador.aplicar_gravedad(dt)
            dy = int(jugador.vel_y * dt)
            jugador.movimiento(dx, 0.0)
            jugador.forma.y += dy

            suelo_top = constantes.ALTO_VENTANA - constantes.ALTURA_SUELO
            if jugador.forma.bottom >= suelo_top:
                jugador.forma.bottom = suelo_top
                jugador.vel_y = 0; jugador.en_piso = True
            else:
                jugador.en_piso = False

            if jugador.en_piso:
                jugador.state = "run" if vx != 0 else "idle"

            jugador.set_dx(vx)
            jugador.animar(dt)
            cam.follow(jugador.forma, lerp=1.0)

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
            btn_play.draw(ventana); btn_opc.draw(ventana); btn_salir.draw(ventana)
            menu_krab.draw(ventana)

        elif estado == ESTADO_OPC:
            ventana.blit(fondo_menu, (0, 0))
            sub = pygame.font.Font(None, 48).render("OPCIONES (ESC para volver)", True, (255, 255, 255))
            ventana.blit(sub, (constantes.ANCHO_VENTANA//2 - sub.get_width()//2, 60))

        elif estado in ("JUEGO", "PAUSA"):
            nivel.draw(ventana, cam.offset())
            ox, oy = cam.offset()
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

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()

