# main.py
import pygame
from pathlib import Path
import constantes
from personaje import Personaje

# -------------------- Helpers de rutas e imágenes --------------------
BASE_DIR = Path(__file__).resolve().parent
IMG_DIR  = BASE_DIR / "assets" / "images"

def scale_to_width(surf: pygame.Surface, target_w: int) -> pygame.Surface:
    ratio = target_w / surf.get_width()
    target_h = int(surf.get_height() * ratio)
    # Para pixel art usa "scale" (nearest). Cambia a smoothscale si prefieres suavizado.
    return pygame.transform.scale(surf, (target_w, target_h))

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
    # Para pixel art más nítido, cambia smoothscale -> scale
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
        return pygame.transform.scale(surf, (w, h))  # nearest para pixel art

    def update(self, mouse_pos, mouse_down):
        hovering = self.rect.collidepoint(mouse_pos)
        target = self.hover_scale if (hovering and not mouse_down) else self.scale
        size = (int(self.base.get_width()*target), int(self.base.get_height()*target))
        if size != self._last_size:
            self.image = self._scaled(self.base, target)
            self.rect = self.image.get_rect()
            # reanclar en el mismo punto
            setattr(self.rect, self._anchor[0], self._anchor[1])
            self._last_size = size

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))

# -------------------- Estados --------------------
ESTADO_MENU   = "MENU"
ESTADO_JUEGO  = "JUEGO"
ESTADO_OPC    = "OPCIONES"

def main():
    pygame.init()
    ventana = pygame.display.set_mode((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
    pygame.display.set_caption("Krab's adventure")
    reloj = pygame.time.Clock()
    font_title = pygame.font.Font(None, 72)

    # Fondos
    fondo_menu  = escalar_a_ventana(cargar_primera_imagen("menufondo",  usa_alpha=False))
    fondo_nivel = escalar_a_ventana(cargar_primera_imagen("nivelfondo", usa_alpha=False))

    # Botones (usa tus imágenes)
    img_play = cargar_primera_imagen("botonplay", usa_alpha=True)
    img_opciones = cargar_primera_imagen("botonopciones", usa_alpha=True)
    img_salir = cargar_primera_imagen("botonsalir", usa_alpha=True)

    # Escalar a un ancho común (ajusta 320/360/400 según te guste)
    TARGET_W = 340
    target_play = 360
    target_salir = 345
    img_play = scale_to_width(img_play, target_play)
    img_opciones = scale_to_width(img_opciones, TARGET_W)
    img_salir = scale_to_width(img_salir, target_salir)

    # Columna alineada a la izquierda del centro (ajusta COL_X si quieres)
    COL_X = int(constantes.ANCHO_VENTANA * 0.32)
    COL_play = int(constantes.ANCHO_VENTANA * 0.31)
    Y0 = int(constantes.ALTO_VENTANA * 0.30)  # posición del primer botón
    GAP1 = 70
    GAP = 74 # separación entre botones

    # Crear botones y apilarlos usando el bottom del anterior
    btn_play = ImageButton(img_play, midleft=(COL_play, Y0))
    btn_opc = ImageButton(img_opciones, midleft=(COL_X, btn_play.rect.bottom + GAP1))
    btn_salir = ImageButton(img_salir, midleft=(COL_X, btn_opc.rect.bottom + GAP))
    pygame.draw.rect(ventana, (255, 0, 0), btn_play.rect, 2)
    pygame.draw.rect(ventana, (0, 255, 0), btn_opc.rect, 2)
    pygame.draw.rect(ventana, (0, 0, 255), btn_salir.rect, 2)

    # Juego: usa tu clase actual
    jugador = Personaje(250, 350)
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
                run = False

            if estado == ESTADO_MENU:
                mouse_pos = pygame.mouse.get_pos()
                mouse_down = pygame.mouse.get_pressed()[0]
                btn_play.update(mouse_pos, mouse_down)
                btn_opc.update(mouse_pos, mouse_down)
                btn_salir.update(mouse_pos, mouse_down)
                if btn_play.clicked(event):
                    estado = ESTADO_JUEGO
                elif btn_opc.clicked(event):
                    estado = ESTADO_OPC
                elif btn_salir.clicked(event):
                    run = False


            elif estado == ESTADO_OPC:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    estado = ESTADO_MENU

            elif estado == ESTADO_JUEGO:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        estado = ESTADO_MENU
                    if event.key == pygame.K_a: mover_izquierda = True
                    if event.key == pygame.K_d: mover_derecha   = True
                    if event.key == pygame.K_w: mover_arriba    = True
                    if event.key == pygame.K_s: mover_abajo     = True
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a: mover_izquierda = False
                    if event.key == pygame.K_d: mover_derecha   = False
                    if event.key == pygame.K_w: mover_arriba    = False
                    if event.key == pygame.K_s: mover_abajo     = False

        # -------------------- Actualizar --------------------
        if estado == ESTADO_MENU:
            btn_play.update(mouse_pos, mouse_down)
            btn_opc.update(mouse_pos, mouse_down)
            btn_salir.update(mouse_pos, mouse_down)

        elif estado == ESTADO_JUEGO:
            dx = (constantes.VELOCIDAD if mover_derecha else 0) - (constantes.VELOCIDAD if mover_izquierda else 0)
            dy = (constantes.VELOCIDAD if mover_abajo   else 0) - (constantes.VELOCIDAD if mover_arriba    else 0)
            jugador.movimiento(dx, dy)

        # -------------------- Dibujar --------------------
        if estado == ESTADO_MENU:
            ventana.blit(fondo_menu, (0, 0))
            # título estilo mock (si tienes logo, ponlo en lugar de texto)

            btn_play.draw(ventana)
            btn_opc.draw(ventana)
            btn_salir.draw(ventana)

        elif estado == ESTADO_OPC:
            ventana.blit(fondo_menu, (0, 0))
            sub = pygame.font.Font(None, 48).render("OPCIONES (ESC para volver)", True, (255, 255, 255))
            ventana.blit(sub, (constantes.ANCHO_VENTANA//2 - sub.get_width()//2, 60))

        elif estado == ESTADO_JUEGO:
            ventana.blit(fondo_nivel, (0, 0))
            jugador.dibujar(ventana)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
