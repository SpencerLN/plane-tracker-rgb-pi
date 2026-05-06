"""Days forecast scene module for displaying weather forecast on the RGB matrix."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from PIL import Image
from matrix_backend import graphics

from config import NIGHT_START, NIGHT_END
from utilities.animator import Animator
from setup import colours, fonts, frames, screen
from utilities.temperature import grab_forecast

# Setup
DAY_COLOUR = colours.LIGHT_PINK
MIN_T_COLOUR = colours.LIGHT_MID_BLUE
MAX_T_COLOUR = colours.LIGHT_DARK_ORANGE
TEXT_FONT = fonts.extrasmall
FONT_HEIGHT = 5
DISTANCE_FROM_TOP = 32
ICON_SIZE = 10
FORECAST_SIZE = FONT_HEIGHT * 2 + ICON_SIZE
DAY_POSITION = DISTANCE_FROM_TOP - FONT_HEIGHT - ICON_SIZE
ICON_POSITION = DISTANCE_FROM_TOP - FONT_HEIGHT - ICON_SIZE
TEMP_POSITION = DISTANCE_FROM_TOP
NIGHT_START_TIME = datetime.strptime(NIGHT_START, "%H:%M")
NIGHT_END_TIME = datetime.strptime(NIGHT_END, "%H:%M")

# Icon directory path (relative to repo root)
ICONS_DIR = Path(__file__).parent.parent.parent / "icons"


class DaysForecastScene(object):
    """Scene that displays a multi-day weather forecast.
    
    Shows weather icons and temperature ranges for upcoming days,
    with automatic hourly updates and night mode support.
    """

    def __init__(self) -> None:
        """Initialize the DaysForecastScene with default values."""
        super().__init__()
        self._redraw_forecast: bool = True
        self._last_hour: Optional[int] = None
        self._cached_forecast: Optional[List[Dict[str, Any]]] = None

    @Animator.KeyFrame.add(frames.PER_SECOND * 1)
    def day(self, count: int) -> None:
        """Update and display the weather forecast on the matrix.
        
        This method is called once per second but only redraws when the hour
        changes or when triggered by night mode transitions. Displays weather
        icons and temperature ranges for upcoming days.
        
        Args:
            count: Frame counter from the animator.
        """
        # Redraws the screen at night start and end so it'll adjust the brightness
        now = datetime.now().replace(microsecond=0).time()
        if now == NIGHT_START_TIME.time() or now == NIGHT_END_TIME.time():
            self._redraw_forecast = True
            return

        # Ensure redraw when there's new data
        if len(self._data):
            self._redraw_forecast = True
            return

        # If there's no data to display, then draw the forecast
        current_hour = datetime.now().hour

        # Only draw if time needs updated
        if self._last_hour != current_hour or self._redraw_forecast:
            # Clear space if last day is different from current
            if self._last_hour is not None:
                self.draw_square(
                    0,
                    12,  # Start from the bottom of the screen (32 - 20)
                    64,  # Width of the area
                    32,  # Height of the area
                    colours.BLACK,
                )
            self._last_hour = current_hour

            if self._cached_forecast is not None and self._redraw_forecast:
                forecast = self._cached_forecast
            else:
                forecast = grab_forecast()
                self._cached_forecast = forecast

            if forecast is not None:
                self._redraw_forecast = False
                offset = 1
                space_width = screen.WIDTH // 3  # Calculate the width of each third of the screen

                for day in forecast:
                    # Extract day_name and icon
                    day_name = datetime.fromisoformat(day["startTime"].rstrip("Z")).strftime("%a")
                    icon = day["values"]["weatherCodeFullDay"]

                    # Calculate the maximum width between min and max temperature text
                    min_temp = f"{day['values']['temperatureMin']:.0f}"
                    max_temp = f"{day['values']['temperatureMax']:.0f}"
                    
                    # Calculate temperature width for min and max temperatures
                    min_temp_width = len(min_temp) * 4
                    max_temp_width = len(max_temp) * 4

                    # Calculate temp_x for centering temperature text
                    temp_x = offset + (space_width - min_temp_width - max_temp_width - 1) // 2 + 1

                    # Calculate min_temp_x for centering min temperature text
                    min_temp_x = temp_x + max_temp_width

                    # Calculate max_temp_x for centering max temperature text
                    max_temp_x = temp_x

                    # Calculate icon_x for centering the icon
                    icon_x = offset + (space_width - ICON_SIZE) // 2

                    # Calculate day_x for centering the day name
                    day_x = offset + (space_width - 12) // 2 + 1

                    # Draw day
                    _ = graphics.DrawText(
                        self.canvas,
                        TEXT_FONT,
                        day_x,
                        DAY_POSITION,
                        DAY_COLOUR,
                        day_name
                    )

                    # Draw the icon
                    try:
                        image = Image.open(ICONS_DIR / f"{icon}.png")
                    except FileNotFoundError:
                        # Fallback to a default icon if the specific weather code is not available
                        image = Image.open(ICONS_DIR / "1000.png")  # Clear sky as default
                    image.thumbnail((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)
                    self.matrix.SetImage(image.convert('RGB'), icon_x, ICON_POSITION)
                    
                    # Clear previous temperature values
                    self.draw_square(
                        min_temp_x,  # Left x coordinate
                        TEMP_POSITION - FONT_HEIGHT,  # Top y coordinate
                        max_temp_x + max_temp_width,  # Right x coordinate
                        TEMP_POSITION + FONT_HEIGHT,  # Bottom y coordinate
                        colours.BLUE
                    )
                    
                    # Draw min temperature
                    _ = graphics.DrawText(
                        self.canvas,
                        TEXT_FONT,
                        min_temp_x,
                        TEMP_POSITION,
                        MIN_T_COLOUR,
                        min_temp
                    )
        
                    # Draw max temperature
                    _ = graphics.DrawText(
                        self.canvas,
                        TEXT_FONT,
                        max_temp_x,
                        TEMP_POSITION,
                        MAX_T_COLOUR,
                        max_temp
                    )

                    offset += space_width
