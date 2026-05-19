"""Clock scene module for displaying time on the RGB matrix."""

from datetime import datetime, date
from typing import Optional, Tuple

from matrix_backend import graphics

from config import CLOCK_FORMAT
from utilities.temperature import grab_forecast
from utilities.animator import Animator
from setup import colours, fonts, frames

# Setup
CLOCK_FONT = fonts.large_bold
CLOCK_POSITION = (0, 11)
DAY_COLOUR = colours.LIGHT_ORANGE
NIGHT_COLOUR = colours.LIGHT_BLUE


class ClockScene(object):
    """Scene that displays the current time with day/night color coding.
    
    The clock color changes based on sunrise and sunset times fetched from
    the weather forecast API.
    """

    def __init__(self) -> None:
        """Initialize the ClockScene with default values."""
        super().__init__()
        self._last_time: Optional[str] = None
        self.today_sunrise: Optional[datetime] = None
        self.today_sunset: Optional[datetime] = None
        self.last_fetch_date: Optional[date] = None

    def calculate_sunrise_sunset(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Calculate and cache today's sunrise and sunset times.
        
        Fetches forecast data from the weather API and extracts sunrise/sunset
        times for the current day. Results are cached and only refreshed when
        the date changes.
        
        Returns:
            Tuple containing (sunrise_time, sunset_time) as datetime objects,
            or (None, None) if data is not available.
        """
        now = datetime.now()
        
        # Check if it's a new day or if there is no cached data
        if self.last_fetch_date != now.date():
            forecast = grab_forecast()
            if forecast is None:
                return self.today_sunrise, self.today_sunset
            for day in forecast:
                forecast_date = day['startTime'][:10]
                if forecast_date == now.strftime('%Y-%m-%d'):
                    # Parse UTC sunrise and sunset times
                    utc_sunrise = datetime.strptime(day['values']['sunriseTime'], '%Y-%m-%dT%H:%M:%SZ')
                    utc_sunset = datetime.strptime(day['values']['sunsetTime'], '%Y-%m-%dT%H:%M:%SZ')

                    # Cache the sunrise and sunset times
                    self.today_sunrise = utc_sunrise
                    self.today_sunset = utc_sunset
                    self.last_fetch_date = now.date()

        return self.today_sunrise, self.today_sunset

    @Animator.KeyFrame.add(frames.PER_SECOND * 1)
    def clock(self, count: int) -> None:
        """Update and display the clock on the matrix.
        
        This method is called once per second to update the time display.
        The clock color changes based on whether it's day or night.
        
        Args:
            count: Frame counter from the animator.
        """
        if len(self._data):
            # Ensure redraw when there's new data
            self._last_time = None
        else:
            # If there's no data to display, then draw a clock
            now = datetime.now()
            if CLOCK_FORMAT == "12hr":
              clock_format = "%l:%M"
            elif CLOCK_FORMAT == "24hr":
              clock_format = "%H:%M"
            current_time = now.strftime(clock_format)

            utc_sunrise, utc_sunset = self.calculate_sunrise_sunset()

            time_until_sunrise = (utc_sunrise - datetime.utcnow()).total_seconds()
            time_until_sunset = (utc_sunset - datetime.utcnow()).total_seconds()
            
            if time_until_sunset <= 0:
                clock_color = NIGHT_COLOUR
            elif time_until_sunrise <= 0:
                clock_color = DAY_COLOUR
            else:
                clock_color = NIGHT_COLOUR

            if self._last_time:
                _ = graphics.DrawText(
                    self.canvas,
                    CLOCK_FONT,
                    CLOCK_POSITION[0],
                    CLOCK_POSITION[1],
                    colours.BLACK,
                    self._last_time,
                )
            self._last_time = current_time

            _ = graphics.DrawText(
                self.canvas,
                CLOCK_FONT,
                CLOCK_POSITION[0],
                CLOCK_POSITION[1],
                clock_color,
                current_time,
            )
