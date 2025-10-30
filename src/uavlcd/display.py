import st7735

class LCD:
    def __init__(self):
        self._lcd = st7735.ST7735(
            port=0, cs=1, dc="GPIO9", backlight="GPIO12", rotation=270, spi_speed_hz=10_000_000
        )
        self._lcd.begin()
    @property
    def width(self): return self._lcd.width
    @property
    def height(self): return self._lcd.height
    def show(self, img): self._lcd.display(img)
    def set_backlight(self, on: bool = True):
        # some drivers expose set_backlight; if not, this is harmless
        try:
            self._lcd.set_backlight(1 if on else 0)
        except AttributeError:
            pass
