"""Software-only simulator for the rgbmatrix Python bindings.

The implementation focuses on feature parity that this project relies on:

dash fonts loaded from BDF files

dash text and line primitives

dash double-buffer style frame canvas objects

dash periodic frame dumps to ``web/static/simulator/latest.png`` so the
   developer can view the LED matrix output inside the dev container.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(value: int, lower: int = 0, upper: int = 255) -> int:
    return max(lower, min(upper, int(value)))


# ---------------------------------------------------------------------------
# Graphics primitives
# ---------------------------------------------------------------------------


class Color:
    """Represents an RGB color."""

    __slots__ = ("red", "green", "blue")

    def __init__(self, red: int = 0, green: int = 0, blue: int = 0) -> None:
        self.red = _clamp(red)
        self.green = _clamp(green)
        self.blue = _clamp(blue)


@dataclass
class _Glyph:
    encoding: int
    width: int
    height: int
    x_offset: int
    y_offset: int
    dwidth: int
    bitmap: List[List[int]]  # rows of 0/1 ints, top to bottom


class Font:
    """Loads and exposes bitmap fonts stored as BDF files."""

    def __init__(self) -> None:
        self._glyphs: Dict[int, _Glyph] = {}
        self._path: Optional[str] = None
        self._ascent: int = 0
        self._descent: int = 0
        self._default_char: int = ord("?")
        self._bounding_box_width: int = 6
        self._bounding_box_height: int = 8

    def LoadFont(self, path: str) -> None:
        self._path = path
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            lines = [line.rstrip("\n") for line in handle]
        self._parse(lines)

    def _parse(self, lines: List[str]) -> None:
        self._glyphs.clear()
        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                idx += 1
                continue

            if line.startswith("FONT_ASCENT"):
                self._ascent = int(line.split()[1])
            elif line.startswith("FONT_DESCENT"):
                self._descent = int(line.split()[1])
            elif line.startswith("DEFAULT_CHAR"):
                self._default_char = int(line.split()[1])
            elif line.startswith("FONTBOUNDINGBOX"):
                parts = line.split()
                self._bounding_box_width = int(parts[1])
                self._bounding_box_height = int(parts[2])
            elif line.startswith("STARTCHAR"):
                glyph, idx = self._parse_glyph(lines, idx)
                if glyph.encoding is not None:
                    self._glyphs[glyph.encoding] = glyph
                continue

            idx += 1

    def _parse_glyph(self, lines: List[str], start: int) -> Tuple[_Glyph, int]:
        encoding = -1
        width = self._bounding_box_width
        height = self._bounding_box_height
        x_offset = 0
        y_offset = 0
        dwidth = width
        bitmap: List[List[int]] = []

        idx = start + 1
        while idx < len(lines):
            line = lines[idx].strip()
            if line == "ENDCHAR":
                break
            if line.startswith("ENCODING"):
                encoding = int(line.split()[1])
            elif line.startswith("DWIDTH"):
                parts = line.split()
                dwidth = int(parts[1])
            elif line.startswith("BBX"):
                parts = line.split()
                width = int(parts[1])
                height = int(parts[2])
                x_offset = int(parts[3])
                y_offset = int(parts[4])
            elif line == "BITMAP":
                idx += 1
                bitmap = []
                for _ in range(height):
                    if idx >= len(lines):
                        break
                    row_hex = lines[idx].strip()
                    bitmap.append(self._hex_row_to_bits(row_hex, width))
                    idx += 1
                continue
            idx += 1

        # Ensure bitmap height matches expected size
        if len(bitmap) != height:
            missing = height - len(bitmap)
            bitmap.extend([[0] * width for _ in range(max(0, missing))])

        glyph = _Glyph(
            encoding=encoding,
            width=width,
            height=height,
            x_offset=x_offset,
            y_offset=y_offset,
            dwidth=dwidth or width,
            bitmap=bitmap,
        )
        return glyph, idx + 1

    @staticmethod
    def _hex_row_to_bits(hex_row: str, width: int) -> List[int]:
        if not hex_row:
            return [0] * width
        total_bits = len(hex_row) * 4
        bits = bin(int(hex_row, 16))[2:].zfill(total_bits)
        if total_bits < width:
            bits = bits.zfill(width)
        return [1 if ch == "1" else 0 for ch in bits[:width]]

    def _get_glyph(self, char_code: int) -> Optional[_Glyph]:
        return self._glyphs.get(char_code) or self._glyphs.get(self._default_char)

    @property
    def CharacterWidth(self) -> int:
        return self._bounding_box_width

    @property
    def height(self) -> int:
        return self._bounding_box_height

    @property
    def ascent(self) -> int:
        return self._ascent or self._bounding_box_height


class FrameCanvas:
    """Simple pixel buffer used by the simulator."""

    def __init__(self, width: int = 64, height: int = 32) -> None:
        self.width = width
        self.height = height
        self._pixels = [
            [(0, 0, 0) for _ in range(self.width)] for _ in range(self.height)
        ]

    def Clear(self) -> None:
        for y in range(self.height):
            for x in range(self.width):
                self._pixels[y][x] = (0, 0, 0)

    def Fill(self, red: int, green: int, blue: int) -> None:
        color = (_clamp(red), _clamp(green), _clamp(blue))
        for y in range(self.height):
            for x in range(self.width):
                self._pixels[y][x] = color

    def SetPixel(self, x: int, y: int, red: int, green: int, blue: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self._pixels[y][x] = (_clamp(red), _clamp(green), _clamp(blue))

    def GetPixel(self, x: int, y: int) -> Tuple[int, int, int]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._pixels[y][x]
        return (0, 0, 0)

    def copy(self) -> "FrameCanvas":
        clone = FrameCanvas(self.width, self.height)
        clone._pixels = [row[:] for row in self._pixels]
        return clone


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def DrawLine(canvas: FrameCanvas, x0: int, y0: int, x1: int, y1: int, color: Color) -> int:
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        canvas.SetPixel(x0, y0, color.red, color.green, color.blue)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return 0


def DrawText(
    canvas: FrameCanvas,
    font: Font,
    x: int,
    y: int,
    color: Color,
    text: str,
) -> int:
    cursor = x
    for char in text:
        glyph = font._get_glyph(ord(char))
        if not glyph:
            continue
        top = y - (glyph.y_offset + glyph.height)
        left = cursor + glyph.x_offset
        for row_index, row in enumerate(glyph.bitmap):
            for col_index, bit in enumerate(row):
                if bit:
                    canvas.SetPixel(
                        left + col_index,
                        top + row_index,
                        color.red,
                        color.green,
                        color.blue,
                    )
        cursor += glyph.dwidth
    return cursor - x


def DrawCircle(canvas: FrameCanvas, x: int, y: int, radius: int, color: Color) -> int:
    f = 1 - radius
    ddF_x = 1
    ddF_y = -2 * radius
    x0 = 0
    y0 = radius

    def _plot(px: int, py: int) -> None:
        canvas.SetPixel(px, py, color.red, color.green, color.blue)

    _plot(x, y + radius)
    _plot(x, y - radius)
    _plot(x + radius, y)
    _plot(x - radius, y)

    while x0 < y0:
        if f >= 0:
            y0 -= 1
            ddF_y += 2
            f += ddF_y
        x0 += 1
        ddF_x += 2
        f += ddF_x
        _plot(x + x0, y + y0)
        _plot(x - x0, y + y0)
        _plot(x + x0, y - y0)
        _plot(x - x0, y - y0)
        _plot(x + y0, y + x0)
        _plot(x - y0, y + x0)
        _plot(x + y0, y - x0)
        _plot(x - y0, y - x0)
    return 0


class _GraphicsModule:
    Color = Color
    Font = Font
    DrawText = staticmethod(DrawText)
    DrawLine = staticmethod(DrawLine)
    DrawCircle = staticmethod(DrawCircle)


graphics = _GraphicsModule()


# ---------------------------------------------------------------------------
# Matrix + options
# ---------------------------------------------------------------------------


class RGBMatrixOptions:
    def __init__(self) -> None:
        self.hardware_mapping = "adafruit-hat"
        self.rows = 32
        self.cols = 64
        self.chain_length = 1
        self.parallel = 1
        self.row_address_type = 0
        self.multiplexing = 0
        self.pwm_bits = 11
        self.brightness = 100
        self.pwm_lsb_nanoseconds = 130
        self.led_rgb_sequence = "RGB"
        self.pixel_mapper_config = ""
        self.show_refresh_rate = 0
        self.gpio_slowdown = 1
        self.disable_hardware_pulsing = True
        self.drop_privileges = True


class RGBMatrix:
    """Simulated matrix that writes frames to disk as PNG files."""

    def __init__(self, options: Optional[RGBMatrixOptions] = None) -> None:
        self._options = options or RGBMatrixOptions()
        self._brightness = self._options.brightness
        self._width = self._options.cols * self._options.chain_length
        self._height = self._options.rows * self._options.parallel
        self._active_canvas: Optional[FrameCanvas] = None
        base_dir = Path(__file__).resolve().parent.parent
        default_dir = base_dir / "web" / "static" / "simulator"
        out_dir = os.environ.get("RGBMATRIX_SIM_OUTPUT", str(default_dir))
        self._output_dir = Path(out_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._latest_path = self._output_dir / "latest.png"
        self._scale = max(1, int(os.environ.get("RGBMATRIX_SIM_SCALE", "10")))

    @property
    def brightness(self) -> int:
        return self._brightness

    @brightness.setter
    def brightness(self, value: int) -> None:
        self._brightness = _clamp(value, 0, 100)

    def CreateFrameCanvas(self) -> FrameCanvas:
        canvas = FrameCanvas(self._width, self._height)
        self._active_canvas = canvas
        return canvas

    def SwapOnVSync(self, canvas: FrameCanvas) -> FrameCanvas:
        self._write_image(canvas)
        return canvas

    def SetImage(self, image, offset_x: int = 0, offset_y: int = 0, unsafe: bool = False) -> None:
        """Blit a PIL image into the currently active canvas."""

        if self._active_canvas is None:
            return

        if not isinstance(image, Image.Image):
            pil_image = Image.open(image).convert("RGB")
        else:
            pil_image = image.convert("RGB")

        width, height = pil_image.size
        for y in range(height):
            for x in range(width):
                target_x = offset_x + x
                target_y = offset_y + y
                if 0 <= target_x < self._active_canvas.width and 0 <= target_y < self._active_canvas.height:
                    r, g, b = pil_image.getpixel((x, y))
                    self._active_canvas.SetPixel(target_x, target_y, r, g, b)

    def _write_image(self, canvas: FrameCanvas) -> None:
        factor = self._brightness / 100.0 if self._brightness else 0
        img = Image.new("RGB", (canvas.width, canvas.height))
        for y in range(canvas.height):
            for x in range(canvas.width):
                r, g, b = canvas.GetPixel(x, y)
                img.putpixel((x, y), (
                    int(r * factor),
                    int(g * factor),
                    int(b * factor),
                ))
        if self._scale > 1:
            img = img.resize((canvas.width * self._scale, canvas.height * self._scale), Image.NEAREST)
        img.save(self._latest_path)


__all__ = [
    "RGBMatrix",
    "RGBMatrixOptions",
    "graphics",
    "Color",
    "Font",
    "FrameCanvas",
]
