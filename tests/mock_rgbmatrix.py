"""
Mock rgbmatrix module for testing without Raspberry Pi hardware.

This module provides mock implementations of the rgbmatrix library classes
so that tests can run on development machines without actual LED matrix
hardware connected.

Usage:
    Set the MOCK_RGBMATRIX environment variable or import this module
    before importing any code that uses rgbmatrix.
"""

from typing import Optional, Tuple, List, Any
from dataclasses import dataclass, field


@dataclass
class Color:
    """Mock Color class representing an RGB color."""
    red: int = 0
    green: int = 0
    blue: int = 0
    
    def __init__(self, red: int = 0, green: int = 0, blue: int = 0):
        self.red = max(0, min(255, red))
        self.green = max(0, min(255, green))
        self.blue = max(0, min(255, blue))


class Font:
    """Mock Font class for loading and using bitmap fonts."""
    
    def __init__(self):
        self._font_path: Optional[str] = None
        self._char_width: int = 6
        self._char_height: int = 8
    
    def LoadFont(self, path: str) -> None:
        """Load a font from a file path."""
        self._font_path = path
        # Extract approximate character size from common font names
        if "4x6" in path:
            self._char_width, self._char_height = 4, 6
        elif "5x7" in path or "5x8" in path:
            self._char_width, self._char_height = 5, 8
        elif "6x10" in path or "6x12" in path or "6x13" in path:
            self._char_width, self._char_height = 6, 13
        elif "7x13" in path or "7x14" in path:
            self._char_width, self._char_height = 7, 13
        elif "8x13" in path:
            self._char_width, self._char_height = 8, 13
    
    @property
    def CharacterWidth(self) -> int:
        return self._char_width
    
    @property
    def height(self) -> int:
        return self._char_height


def DrawText(canvas: 'FrameCanvas', font: Font, x: int, y: int, color: Color, text: str) -> int:
    """Mock DrawText that returns approximate text width."""
    return len(text) * font.CharacterWidth


def DrawLine(canvas: 'FrameCanvas', x0: int, y0: int, x1: int, y1: int, color: Color) -> int:
    """Mock DrawLine that tracks drawn lines."""
    if hasattr(canvas, '_lines'):
        canvas._lines.append((x0, y0, x1, y1, color))
    return 0


def DrawCircle(canvas: 'FrameCanvas', x: int, y: int, radius: int, color: Color) -> int:
    """Mock DrawCircle."""
    return 0


class FrameCanvas:
    """Mock FrameCanvas for double-buffered rendering."""
    
    def __init__(self, width: int = 64, height: int = 32):
        self.width = width
        self.height = height
        self._pixels: List[List[Tuple[int, int, int]]] = [
            [(0, 0, 0) for _ in range(width)] for _ in range(height)
        ]
        self._lines: List[Tuple[int, int, int, int, Color]] = []
    
    def Clear(self) -> None:
        """Clear the canvas to black."""
        self._pixels = [
            [(0, 0, 0) for _ in range(self.width)] for _ in range(self.height)
        ]
        self._lines = []
    
    def Fill(self, red: int, green: int, blue: int) -> None:
        """Fill the entire canvas with a color."""
        self._pixels = [
            [(red, green, blue) for _ in range(self.width)] for _ in range(self.height)
        ]
    
    def SetPixel(self, x: int, y: int, red: int, green: int, blue: int) -> None:
        """Set a single pixel's color."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._pixels[y][x] = (int(red), int(green), int(blue))
    
    def GetPixel(self, x: int, y: int) -> Tuple[int, int, int]:
        """Get a single pixel's color."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._pixels[y][x]
        return (0, 0, 0)


class RGBMatrixOptions:
    """Mock RGBMatrixOptions for configuring the matrix."""
    
    def __init__(self):
        self.hardware_mapping: str = "adafruit-hat"
        self.rows: int = 32
        self.cols: int = 64
        self.chain_length: int = 1
        self.parallel: int = 1
        self.row_address_type: int = 0
        self.multiplexing: int = 0
        self.pwm_bits: int = 11
        self.brightness: int = 100
        self.pwm_lsb_nanoseconds: int = 130
        self.led_rgb_sequence: str = "RGB"
        self.pixel_mapper_config: str = ""
        self.show_refresh_rate: int = 0
        self.gpio_slowdown: int = 1
        self.disable_hardware_pulsing: bool = True
        self.drop_privileges: bool = True


class RGBMatrix:
    """Mock RGBMatrix for LED matrix display."""
    
    def __init__(self, options: Optional[RGBMatrixOptions] = None):
        self._options = options or RGBMatrixOptions()
        self._brightness = self._options.brightness
        self._canvas = FrameCanvas(self._options.cols, self._options.rows)
        self._frame_canvas = FrameCanvas(self._options.cols, self._options.rows)
    
    @property
    def brightness(self) -> int:
        return self._brightness
    
    @brightness.setter
    def brightness(self, value: int) -> None:
        self._brightness = max(0, min(100, value))
    
    def CreateFrameCanvas(self) -> FrameCanvas:
        """Create a new frame canvas for double-buffered rendering."""
        return FrameCanvas(self._options.cols, self._options.rows)
    
    def SwapOnVSync(self, canvas: FrameCanvas) -> FrameCanvas:
        """Swap the canvas with vertical sync (mock just returns canvas)."""
        return canvas
    
    def SetImage(self, image: Any, offset_x: int = 0, offset_y: int = 0) -> None:
        """Set an image on the matrix."""
        pass


# Module-level graphics namespace for compatibility
class graphics:
    """Namespace for graphics functions and classes."""
    Color = Color
    Font = Font
    DrawText = staticmethod(DrawText)
    DrawLine = staticmethod(DrawLine)
    DrawCircle = staticmethod(DrawCircle)
