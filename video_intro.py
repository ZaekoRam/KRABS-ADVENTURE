# video_intro.py
import pygame
from pathlib import Path

def play_intro_or_skip(lang: str, screen, clock):
    """
    Reproduce el video de introducción en 800x600 a 30 FPS.
    - lang: "es" o "en"
    - Se puede saltar con cualquier tecla o clic.
    """
    try:
        from ffpyplayer.player import MediaPlayer
    except Exception:
        return  # ffpyplayer no instalado

    # --- Rutas del video ---
    video_path = Path(__file__).resolve().parent / "assets" / "video" / (
        "intro_es.mp4" if lang == "es" else "intro_en.mp4"
    )
    if not video_path.exists():
        return

    # --- Configuración del reproductor ---
    player = MediaPlayer(
        str(video_path),
        ff_opts={
            "sync": "audio",       # mantiene sincronía entre audio y video
            "out_fmt": "yuv420p",  # formato eficiente para rendimiento
            "paused": False
        }
    )

    # --- Configuración de ventana ---
    target_size = (800, 600)   # tamaño fijo del video
    screen_w, screen_h = screen.get_size()
    clock.tick(30)
    pygame.event.clear()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try:
                    player.close_player()
                except Exception:
                    pass
                pygame.quit()
                raise SystemExit

            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False

        frame, val = player.get_frame()
        if val == 'eof':
            break

        if frame is not None:
            img, t = frame
            w, h = img.get_size()

            # --- convertir frame ---
            surf = pygame.image.frombuffer(img.to_bytearray()[0], (w, h), "RGB")

            # --- escalar a 800x600 y centrar en la pantalla ---
            scaled = pygame.transform.smoothscale(surf, target_size)
            x = (screen_w - target_size[0]) // 2
            y = (screen_h - target_size[1]) // 2
            screen.fill((0, 0, 0))
            screen.blit(scaled, (x, y))
            pygame.display.flip()

        # --- Control de FPS (30) ---
        clock.tick(32)

    # --- Cierre seguro ---
    try:
        player.close_player()
    except Exception:
        pass
