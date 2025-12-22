#!/usr/bin/env python3

import sys
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from rgbmatrix import graphics

# Matrix options (same as main script)
options = RGBMatrixOptions()
options.hardware_mapping = "adafruit-hat"
options.rows = 32
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.row_address_type = 0
options.multiplexing = 0
options.pwm_bits = 11
options.brightness = 100
options.pwm_lsb_nanoseconds = 130
options.led_rgb_sequence = "RGB"
options.pixel_mapper_config = ""
options.show_refresh_rate = 0
options.gpio_slowdown = 4
options.disable_hardware_pulsing = True
options.drop_privileges = True

matrix = RGBMatrix(options=options)
canvas = matrix.CreateFrameCanvas()

# Test 1: Fill the entire screen with red except top right 8x6 with blue
print("Test 1: Filling screen with red, top right 8x6 with blue")
canvas.Fill(255, 0, 0)  # Red
for y in range(0, 6):
    graphics.DrawLine(canvas, 56, y, 63, y, graphics.Color(0, 0, 255))  # Blue
matrix.SwapOnVSync(canvas)
time.sleep(2)

# Test 2: Rapid color changes in top right to test performance
print("Test 2: Rapid color changes in top right 8x6")
colors = [graphics.Color(255, 0, 0), graphics.Color(0, 255, 0), graphics.Color(0, 0, 255), graphics.Color(255, 255, 0)]
for i in range(20):  # 20 rapid changes
    for y in range(0, 6):
        graphics.DrawLine(canvas, 56, y, 63, y, colors[i % 4])
    matrix.SwapOnVSync(canvas)
    time.sleep(0.1)  # Short delay
canvas.Fill(0, 0, 0)  # Clear after test
matrix.SwapOnVSync(canvas)
time.sleep(1)

# Test 3: Draw text in top right with different colors
print("Test 3: Drawing text in top right with gradient colors")
font = graphics.Font()
font.LoadFont("its-a-plane-python/fonts/4x6.bdf")
canvas.Fill(0, 0, 0)
# Simulate temperature text with color gradient
text = "75°"
for i, char in enumerate(text):
    ratio = i / len(text)
    r = int(255 * (1 - ratio))
    g = int(255 * ratio)
    b = 0
    color = graphics.Color(r, g, b)
    graphics.DrawText(canvas, font, 56 + i*5, 6, color, char)
matrix.SwapOnVSync(canvas)
time.sleep(2)

print("Debug test complete. Press Ctrl+C to exit.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    canvas.Clear()
    matrix.SwapOnVSync(canvas)
    sys.exit(0)