"""Date scene module for displaying the date with moon phase effects."""

from datetime import datetime
from typing import Optional, Tuple, Any

from matrix_backend import graphics

from config import NIGHT_START, NIGHT_END
from utilities.temperature import grab_forecast
from utilities.animator import Animator
from setup import colours, fonts, frames

# Setup
DATE_FONT = fonts.extrasmall
DATE_POSITION = (40, 11)

# Convert NIGHT_START and NIGHT_END to datetime objects
NIGHT_START_TIME = datetime.strptime(NIGHT_START, "%H:%M")
NIGHT_END_TIME = datetime.strptime(NIGHT_END, "%H:%M")


class DateScene(object):
    """Scene that displays the current date with moon phase gradient colors.
    
    The date text is rendered with a gradient that changes based on the
    current moon phase, providing a visual indication of the lunar cycle.
    """

    def __init__(self) -> None:
        """Initialize the DateScene with default values."""
        super().__init__()
        self._last_date: Optional[str] = None
        self.today_moonphase: Optional[int] = None
        self.last_fetched_moonphase: Optional[int] = None 


    def moonphase(self) -> Optional[int]:
        """Get the current moon phase, fetching from API if needed.
        
        Moon phase values are cached daily and only refreshed when the
        day changes.
        
        Returns:
            Integer representing moon phase (0-7), or None if not available.
        """
        now = datetime.now()
        
        if self.last_fetched_moonphase != now.day:
            forecast = grab_forecast()
            for day in forecast:
                forecast_date = day['startTime'][:10]
                if forecast_date == now.strftime('%Y-%m-%d'):
                    utc_moonphase = int(day["values"]["moonPhase"])
                    self.today_moonphase = utc_moonphase
                    self.last_fetched_moonphase = now.day
                    break

        return self.today_moonphase

    def map_moon_phase_to_color(self, moonphase: int) -> Tuple[Any, Any]:
        """Map a moon phase value to gradient colors.
        
        Args:
            moonphase: Integer value representing the moon phase (0-7).
        
        Returns:
            Tuple of (start_color, end_color) for the gradient.
        """
        colors = [
            [colours.DARK_PURPLE, colours.DARK_PURPLE],  # Moon phase 0
            [colours.DARK_PURPLE, colours.DARK_MID_PURPLE],  # Moon phase 1
            [colours.DARK_PURPLE, colours.WHITE],  # Moon phase 2
            [colours.DARK_MID_PURPLE, colours.WHITE],  # Moon phase 3
            [colours.GREY, colours.GREY],  # Moon phase 4 (no gradient, same color)
            [colours.WHITE, colours.DARK_MID_PURPLE],  # Moon phase 5
            [colours.WHITE, colours.DARK_PURPLE],  # Moon phase 6
            [colours.DARK_MID_PURPLE, colours.DARK_PURPLE]  # Moon phase 7
        ]

        # Ensure moonphase is within the valid range
        moonphase = min(max(moonphase, 0), 7)

        # Get the corresponding colors for the moon phase
        gradient_start_color, gradient_end_color = colors[moonphase]

        return gradient_start_color, gradient_end_color

    def draw_gradient_text(self, text: str, x: int, y: int, start_color: Any, end_color: Any) -> None:
        """Draw text with a horizontal color gradient.
        
        Args:
            text: The text string to draw.
            x: X coordinate for the start of the text.
            y: Y coordinate for the text baseline.
            start_color: Color at the beginning of the text.
            end_color: Color at the end of the text.
        """
        text_length = len(text)
        char_width = 4  # Width of each character
        for i, char in enumerate(text):
            position = i / (text_length - 1)
            r = int(start_color.red + (end_color.red - start_color.red) * position)
            g = int(start_color.green + (end_color.green - start_color.green) * position)
            b = int(start_color.blue + (end_color.blue - start_color.blue) * position)
            char_color = graphics.Color(r, g, b)
            char_x = x + (i * char_width)
            _ = graphics.DrawText(
                self.canvas,
                DATE_FONT,
                char_x,
                y,
                char_color,
                char,
            )

    @Animator.KeyFrame.add(frames.PER_SECOND * 1)
    def date(self, count: int) -> None:
        """Update and display the date on the matrix.
        
        This method is called once per second to update the date display.
        The date is rendered with a gradient based on the current moon phase.
        Triggers a redraw at night mode transitions for brightness adjustment.
        
        Args:
            count: Frame counter from the animator.
        """
        # Redraws the screen at night start and end so it'll adjust the brightness
        now = datetime.now().replace(microsecond=0).time()
        if now == NIGHT_START_TIME.time() or now == NIGHT_END_TIME.time():
            self._last_date = None
            return

        if len(self._data):
            # Ensure redraw when there's new data
            self._last_date = None
        else:
            # If there's no data to display
            # then draw the date
            now = datetime.now()
            current_date = now.strftime("%b %d")

            # Get the moon phase colors based on the current moon phase
            start_color, end_color = self.map_moon_phase_to_color(self.moonphase())

            # Only draw if the date needs updating
            if self._last_date != current_date:
                # Undraw the last date if different from the current date
                if not self._last_date is None:
                    _ = graphics.DrawText(
                        self.canvas,
                        DATE_FONT,
                        DATE_POSITION[0],
                        DATE_POSITION[1],
                        colours.BLACK,
                        self._last_date,
                    )
                self._last_date = current_date

                # Draw the date with a gradient color
                self.draw_gradient_text(current_date, DATE_POSITION[0], DATE_POSITION[1], start_color, end_color)
