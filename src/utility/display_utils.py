from PIL import Image, ImageDraw, ImageFont
from typing import Optional
import logging
import cv2
import numpy as np

# Edge case for bad boot involving fonts missing
try:
    from fonts.ttf import RobotoMedium as UserFont
    DEFAULT_FONT = ImageFont.truetype(UserFont, 18)
except Exception:
    logging.warning("Roboto font not found, using default PIL font.")
    DEFAULT_FONT = ImageFont.load_default()

def render_centered_text(lcd, message: str,
                         bg=(0, 170, 170),
                         fg=(255, 255, 255),
                         font=DEFAULT_FONT):
    """
    Renders a string (supports multi-line) centred on the LCD and displays it.

    lcd:   uavlcd.display.LCD instance
    message: str, can contain '\n' for multiple lines
    bg:    background colour (R,G,B)
    fg:    foreground/text colour (R,G,B)
    font:  PIL ImageFont object
    """
    img = Image.new("RGB", (lcd.width, lcd.height), color=bg)
    draw = ImageDraw.Draw(img)

    lines = message.split("\n")
    line_heights = []
    max_width = 0

    for line in lines:
        x1, y1, x2, y2 = font.getbbox(line if line else " ")
        w, h = x2 - x1, y2 - y1
        max_width = max(max_width, w)
        line_heights.append(h)

    total_h = sum(line_heights)
    y = (lcd.height - total_h) / 2

    for i, line in enumerate(lines):
        x1, y1, x2, y2 = font.getbbox(line if line else " ")
        w = x2 - x1
        x = (lcd.width - w) / 2
        draw.text((x, y), line, font=font, fill=fg)
        y += line_heights[i]

    lcd.show(img)

def _letterbox_to_lcd(lcd, img_pil):
    W = int(getattr(lcd, "width", img_pil.width) or img_pil.width)
    H = int(getattr(lcd, "height", img_pil.height) or img_pil.height)
    
    scale = min(W / img_pil.width, H / img_pil.height)
    new_w = max(1, int(img_pil.width * scale))
    new_h = max(1, int(img_pil.height * scale))

    resized = img_pil.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas.paste(resized, ((W - new_w) // 2, (H - new_h) // 2))
    return canvas

def lcd_show_image(lcd, img_pil, rotate_deg: int | None = None) -> bool:
    # Build the *panel-sized* image and ensure RGB
    img = _letterbox_to_lcd(lcd, img_pil).convert("RGB")
    if rotate_deg:
        img = img.rotate(rotate_deg, expand=False)

    try:
        getattr(lcd, "show")(img) # Ideal method.
        return True
    except Exception as e:
        logging.debug("lcd.show failed: %s", e)

    # Fallback for drivers expecting a NumPy array
    try:
        import numpy as np
        frame = np.array(img)
        for method in ("write_frame", "blit", "render"):
            if hasattr(lcd, method):
                try:
                    getattr(lcd, method)(frame)
                    return True
                except Exception as e:
                    logging.debug("lcd.%s failed: %s", method, e)
    except Exception:
        pass

    return False

def lcd_show_image_frame(lcd, frame_bgr: np.ndarray, rotate_deg: Optional[int] = None) -> bool:
    """
    Functionally optimal display technique for a given frame.

    Fast path for st7735:
    - resize/letterbox with OpenCV into LCD native resolution
    - convert BGR->RGB once
    - hand off a panel-sized PIL.Image to lcd.show()

    Returns True on success, False on failure.
    """
    try:
        H, W = int(lcd.height), int(lcd.width)
        if frame_bgr is None or frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            logging.debug("blit_numpy_bgr_to_st7735: bad frame shape %s", getattr(frame_bgr, "shape", None))
            return False

        h, w = frame_bgr.shape[:2]
        scale = min(W / w, H / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        # Resize with good downsampler
        resized = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Letterbox into final panel-sized canvas
        canvas = np.zeros((H, W, 3), dtype=np.uint8)
        x = (W - new_w) // 2
        y = (H - new_h) // 2
        canvas[y:y + new_h, x:x + new_w] = resized

        # BGR->RGB, optional rotate, convert to PIL and display
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb, mode="RGB")
        if rotate_deg:
            img = img.rotate(rotate_deg, expand=False)

        lcd.show(img)
        return True

    except Exception as e:
        logging.exception("blit_numpy_bgr_to_st7735 failed: %s", e)
        return False
