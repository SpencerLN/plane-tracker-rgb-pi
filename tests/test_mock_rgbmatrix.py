"""Tests for the mock rgbmatrix module."""

import pytest
import sys
from pathlib import Path

# Ensure conftest.py is loaded first
sys.path.insert(0, str(Path(__file__).parent))


class TestMockColor:
    """Test the mock Color class."""
    
    def test_color_creation(self):
        """Test creating a color with RGB values."""
        from mock_rgbmatrix import Color
        
        color = Color(255, 128, 64)
        
        assert color.red == 255
        assert color.green == 128
        assert color.blue == 64
    
    def test_color_clamping(self):
        """Test that color values are clamped to 0-255."""
        from mock_rgbmatrix import Color
        
        color = Color(300, -50, 128)
        
        assert color.red == 255
        assert color.green == 0
        assert color.blue == 128
    
    def test_color_defaults(self):
        """Test default color values."""
        from mock_rgbmatrix import Color
        
        color = Color()
        
        assert color.red == 0
        assert color.green == 0
        assert color.blue == 0


class TestMockFrameCanvas:
    """Test the mock FrameCanvas class."""
    
    def test_canvas_creation(self):
        """Test creating a canvas with dimensions."""
        from mock_rgbmatrix import FrameCanvas
        
        canvas = FrameCanvas(64, 32)
        
        assert canvas.width == 64
        assert canvas.height == 32
    
    def test_canvas_clear(self):
        """Test clearing the canvas."""
        from mock_rgbmatrix import FrameCanvas
        
        canvas = FrameCanvas(64, 32)
        canvas.SetPixel(10, 10, 255, 0, 0)
        canvas.Clear()
        
        assert canvas.GetPixel(10, 10) == (0, 0, 0)
    
    def test_canvas_fill(self):
        """Test filling the canvas."""
        from mock_rgbmatrix import FrameCanvas
        
        canvas = FrameCanvas(64, 32)
        canvas.Fill(128, 64, 32)
        
        assert canvas.GetPixel(0, 0) == (128, 64, 32)
        assert canvas.GetPixel(63, 31) == (128, 64, 32)
    
    def test_canvas_set_get_pixel(self):
        """Test setting and getting pixels."""
        from mock_rgbmatrix import FrameCanvas
        
        canvas = FrameCanvas(64, 32)
        canvas.SetPixel(10, 20, 100, 150, 200)
        
        assert canvas.GetPixel(10, 20) == (100, 150, 200)
    
    def test_canvas_bounds_checking(self):
        """Test that out of bounds pixels return black."""
        from mock_rgbmatrix import FrameCanvas
        
        canvas = FrameCanvas(64, 32)
        
        # Out of bounds should return black
        assert canvas.GetPixel(100, 100) == (0, 0, 0)
        
        # Setting out of bounds should not crash
        canvas.SetPixel(100, 100, 255, 255, 255)  # Should not raise


class TestMockRGBMatrix:
    """Test the mock RGBMatrix class."""
    
    def test_matrix_creation(self):
        """Test creating a matrix with options."""
        from mock_rgbmatrix import RGBMatrix, RGBMatrixOptions
        
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.brightness = 75
        
        matrix = RGBMatrix(options=options)
        
        assert matrix.brightness == 75
    
    def test_matrix_brightness_property(self):
        """Test brightness getter and setter."""
        from mock_rgbmatrix import RGBMatrix
        
        matrix = RGBMatrix()
        matrix.brightness = 50
        
        assert matrix.brightness == 50
    
    def test_matrix_brightness_clamping(self):
        """Test that brightness is clamped to valid range."""
        from mock_rgbmatrix import RGBMatrix
        
        matrix = RGBMatrix()
        matrix.brightness = 150
        
        assert matrix.brightness == 100
    
    def test_matrix_create_frame_canvas(self):
        """Test creating a frame canvas."""
        from mock_rgbmatrix import RGBMatrix, RGBMatrixOptions, FrameCanvas
        
        options = RGBMatrixOptions()
        options.cols = 64
        options.rows = 32
        
        matrix = RGBMatrix(options=options)
        canvas = matrix.CreateFrameCanvas()
        
        assert isinstance(canvas, FrameCanvas)
        assert canvas.width == 64
        assert canvas.height == 32
    
    def test_matrix_swap_on_vsync(self):
        """Test SwapOnVSync returns a canvas."""
        from mock_rgbmatrix import RGBMatrix, FrameCanvas
        
        matrix = RGBMatrix()
        canvas = matrix.CreateFrameCanvas()
        
        result = matrix.SwapOnVSync(canvas)
        
        assert isinstance(result, FrameCanvas)


class TestMockGraphics:
    """Test the mock graphics functions."""
    
    def test_draw_text(self):
        """Test DrawText returns text width."""
        from mock_rgbmatrix import DrawText, Font, FrameCanvas, Color
        
        canvas = FrameCanvas()
        font = Font()
        font.LoadFont("fonts/6x13.bdf")
        color = Color(255, 255, 255)
        
        width = DrawText(canvas, font, 0, 10, color, "Hello")
        
        assert width > 0
        assert width == 5 * font.CharacterWidth  # 5 characters
    
    def test_draw_line(self):
        """Test DrawLine tracks drawn lines."""
        from mock_rgbmatrix import DrawLine, FrameCanvas, Color
        
        canvas = FrameCanvas()
        canvas._lines = []  # Reset
        color = Color(255, 0, 0)
        
        DrawLine(canvas, 0, 0, 10, 10, color)
        
        assert len(canvas._lines) == 1
        assert canvas._lines[0][:4] == (0, 0, 10, 10)


class TestMockFont:
    """Test the mock Font class."""
    
    def test_font_load(self):
        """Test loading a font."""
        from mock_rgbmatrix import Font
        
        font = Font()
        font.LoadFont("fonts/6x13.bdf")
        
        assert font.CharacterWidth == 6
        assert font.height == 13
    
    def test_font_size_detection(self):
        """Test that font sizes are detected from filename."""
        from mock_rgbmatrix import Font
        
        font = Font()
        
        font.LoadFont("fonts/4x6.bdf")
        assert font.CharacterWidth == 4
        assert font.height == 6
        
        font.LoadFont("fonts/8x13.bdf")
        assert font.CharacterWidth == 8
        assert font.height == 13
