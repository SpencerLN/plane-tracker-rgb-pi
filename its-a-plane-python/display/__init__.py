"""Display module for the plane tracker RGB LED matrix.

This module contains the Display class which serves as the main controller
for rendering flight information on an RGB LED matrix display. It combines
multiple scene classes (Clock, Temperature, FlightDetails, etc.) with an
Animator base class to create an animated display that shows real-time
overhead flight data.

The Display class uses a KeyFrame-based animation system where different
methods are registered to execute at specific frame intervals, allowing
for smooth animations and periodic data updates.
"""

import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Set
from setup import frames
from utilities.animator import Animator
from utilities.overhead import Overhead

from scenes.temperature import TemperatureScene
from scenes.flightdetails import FlightDetailsScene
from scenes.flightlogo import FlightLogoScene
from scenes.journey import JourneyScene
from scenes.loadingpulse import LoadingPulseScene
from scenes.clock import ClockScene
from scenes.planedetails import PlaneDetailsScene
from scenes.daysforecast import DaysForecastScene
from scenes.date import DateScene

from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions


def flight_updated(flights_a: List[Dict[str, Any]], flights_b: List[Dict[str, Any]]) -> bool:
    """Check if two flight lists contain the same flights.
    
    Compares two lists of flight dictionaries by their callsigns and directions.
    Order does not matter - only the presence of the same (callsign, direction)
    pairs in both lists.
    
    Args:
        flights_a: First list of flight dictionaries.
        flights_b: Second list of flight dictionaries.
        
    Returns:
        True if both lists contain the same set of (callsign, direction) pairs,
        False otherwise.
    """
    get_callsigns = lambda flights: [(f["callsign"], f["direction"]) for f in flights]
    updatable_a: Set[Tuple[str, str]] = set(get_callsigns(flights_a))
    updatable_b: Set[Tuple[str, str]] = set(get_callsigns(flights_b))

    return updatable_a == updatable_b


try:
    # Attempt to load config data
    from config import (
        BRIGHTNESS,
        GPIO_SLOWDOWN,
        HAT_PWM_ENABLED,
        BRIGHTNESS_NIGHT,
        NIGHT_START,
        NIGHT_END,
        NIGHT_BRIGHTNESS,
    )
    # Parse NIGHT_START and NIGHT_END from strings to datetime objects
    NIGHT_START = datetime.strptime(NIGHT_START, "%H:%M")
    NIGHT_END = datetime.strptime(NIGHT_END, "%H:%M")

except (ModuleNotFoundError, NameError):
    # If there's no config data
    BRIGHTNESS = 100
    GPIO_SLOWDOWN = 1
    HAT_PWM_ENABLED = True
    NIGHT_BRIGHTNESS = False

def adjust_brightness(matrix: RGBMatrix) -> None:
    """Adjust matrix brightness based on time of day.
    
    Automatically dims the display during night hours to reduce light
    pollution and power consumption. The night period is defined by
    NIGHT_START and NIGHT_END configuration values.
    
    Args:
        matrix: The RGBMatrix instance to adjust brightness for.
    """
    if NIGHT_BRIGHTNESS is False:
        return  # Do nothing if NIGHT_BRIGHTNESS is False
        
    # Get current time (hours and minutes only for comparison)
    now = datetime.now().time().replace(second=0, microsecond=0)
    night_start_time = NIGHT_START.time().replace(second=0, microsecond=0)
    night_end_time = NIGHT_END.time().replace(second=0, microsecond=0)

    # Check if current time is after NIGHT_END and before NIGHT_START (daytime)
    if night_end_time <= now < night_start_time:
        new_brightness = BRIGHTNESS
    else:
        new_brightness = BRIGHTNESS_NIGHT
        
    # Only update brightness if it has changed (avoids unnecessary writes)
    if matrix.brightness != new_brightness:
        matrix.brightness = new_brightness
        
class Display(
    TemperatureScene,
    FlightDetailsScene,
    FlightLogoScene,
    JourneyScene,
    LoadingPulseScene,
    PlaneDetailsScene,
    ClockScene,
    DaysForecastScene,
    DateScene,
    Animator,
):
    """Main display controller for the plane tracker RGB LED matrix.
    
    This class combines multiple scene classes through multiple inheritance to
    create a unified display system. Each scene class provides specific rendering
    capabilities (clock, temperature, flight details, etc.), while the Animator
    base class provides the animation framework.
    
    The display uses a KeyFrame decorator pattern from Animator to schedule
    different rendering and data-fetching operations at specific frame intervals.
    Methods decorated with @Animator.KeyFrame.add(n) will be called every n frames.
    
    Attributes:
        matrix: The RGBMatrix hardware interface.
        canvas: The frame canvas for double-buffered rendering.
        overhead: The Overhead utility for fetching flight data.
        delay: Frame delay period in seconds.
        
    Note:
        This class inherits from multiple scene classes and Animator. The order
        of inheritance matters for method resolution order (MRO).
    """
    
    def __init__(self) -> None:
        """Initialize the Display with RGB matrix hardware and data sources.
        
        Sets up the RGB LED matrix with hardware-specific options, creates
        a double-buffered canvas for smooth rendering, initializes the
        Overhead flight data fetcher, and configures all inherited scene
        classes through the parent Animator class.
        """
        # Setup logging for flight data debugging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
        
        # Configure RGB matrix hardware options
        options = RGBMatrixOptions()
        options.hardware_mapping = "adafruit-hat-pwm" if HAT_PWM_ENABLED else "adafruit-hat"
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.row_address_type = 0
        options.multiplexing = 0
        options.pwm_bits = 11
        options.brightness = BRIGHTNESS
        options.pwm_lsb_nanoseconds = 130
        options.led_rgb_sequence = "RGB"
        options.pixel_mapper_config = ""
        options.show_refresh_rate = 0
        options.gpio_slowdown = GPIO_SLOWDOWN
        options.disable_hardware_pulsing = True
        options.drop_privileges = True
        self.matrix = RGBMatrix(options=options)

        # Setup canvas
        self.canvas = self.matrix.CreateFrameCanvas()
        self.canvas.Clear()

        # Data to render
        self._data_index = 0
        self._data = []

        # Start Looking for planes
        self.overhead = Overhead()
        self.overhead.grab_data()

        # Initalise animator and scenes
        super().__init__()

        # Overwrite any default settings from
        # Animator or Scenes
        self.delay = frames.PERIOD

    def draw_square(self, x0: int, y0: int, x1: int, y1: int, colour: graphics.Color) -> None:
        """Draw a filled rectangle on the canvas.
        
        Args:
            x0: Left edge x-coordinate.
            y0: Top edge y-coordinate.
            x1: Right edge x-coordinate (exclusive).
            y1: Bottom edge y-coordinate.
            colour: RGB color to fill the rectangle with.
        """
        for x in range(x0, x1):
            _ = graphics.DrawLine(self.canvas, x, y0, x, y1, colour)

    # =========================================================================
    # KeyFrame-decorated methods
    # =========================================================================
    # The @Animator.KeyFrame.add(n) decorator registers methods to be called
    # at specific frame intervals. The argument 'n' specifies after how many
    # frames the method should be invoked:
    #   - n=0: Called once at the start of each animation cycle (reset)
    #   - n=1: Called every single frame
    #   - n=frames.PER_SECOND * X: Called every X seconds
    # 
    # Methods receive a 'count' parameter (except for frame 0) indicating
    # the current frame number in the animation cycle.
    # =========================================================================

    @Animator.KeyFrame.add(0)
    def clear_screen(self) -> None:
        """Clear the canvas at the start of each animation cycle.
        
        This is the first operation after a screen reset (frame 0).
        It ensures a clean slate before rendering new content.
        """
        self.canvas.Clear()

    @Animator.KeyFrame.add(frames.PER_SECOND * 5)
    def check_for_loaded_data(self, count: int) -> None:
        """Check for new flight data and update display if needed.
        
        Called every 5 seconds to check if the Overhead utility has fetched
        new flight data. If new data is available and different from what's
        currently displayed, triggers a scene reset to render the new data.
        
        Args:
            count: Current frame count in the animation cycle.
        """
        if self.overhead.new_data:
            # Check if there's data
            there_is_data = len(self._data) > 0 or not self.overhead.data_is_empty

            # this marks self.overhead.data as no longer new
            new_data = self.overhead.data
            logging.info(f"New flight data detected. Data length: {len(new_data)}")

            # See if this matches the data already on the screen
            # This test only checks if it's 2 lists with the same
            # callsigns, regardless or order
            data_is_different = not flight_updated(self._data, new_data)

            if data_is_different:
                logging.info("Flight data has changed. Updating internal data store.")
                self._data_index = 0
                self._data_all_looped = False
                self._data = new_data

            # Only reset if there's flight data already
            # on the screen, of if there's some new
            # data available to draw which is different
            # from the current data
            reset_required = there_is_data and data_is_different

            if reset_required:
                logging.info("Reset required: new flight data will be rendered.")
                self.reset_scene()

    @Animator.KeyFrame.add(1)
    def sync(self, count: int) -> None:
        """Synchronize canvas with display and adjust brightness.
        
        Called every frame to swap the double-buffered canvas to the display
        synchronized with vertical refresh, and to check/adjust brightness
        based on time of day.
        
        Args:
            count: Current frame count in the animation cycle.
        """
        # Swap double-buffered canvas on vertical sync for smooth display
        _ = self.matrix.SwapOnVSync(self.canvas)
        
    
        # Adjust brightness
        adjust_brightness(self.matrix)

    @Animator.KeyFrame.add(frames.PER_SECOND * 30)
    def grab_new_data(self, count: int) -> None:
        """Trigger fetching of new flight data from the overhead scanner.
        
        Called every 30 seconds to request fresh flight data. To avoid
        redundant API calls and ensure smooth display transitions, data
        is only fetched when:
        - Not already processing a request
        - No unprocessed new data is waiting
        - All current flight data has been displayed at least once
        - OR the internal data store has 1 or fewer flights
        
        Args:
            count: Current frame count in the animation cycle.
        """
        # Only grab data if we're not already searching
        # for planes, or if there's new data available
        # which hasn't been displayed.
        #
        # We also need wait until all previously grabbed
        # data has been looped through the display.
        #
        # Last, if our internal store of the data
        # is empty, try and grab data
        if not (self.overhead.processing and self.overhead.new_data) and (
            self._data_all_looped or len(self._data) <= 1
        ):
            logging.info("Grabbing new flight data from overhead.")
            self.overhead.grab_data()

    def run(self) -> None:
        """Start the main display loop.
        
        Begins the animation playback which continuously renders frames
        to the LED matrix. The loop runs until interrupted by the user
        with CTRL-C.
        """
        try:
            # Start loop
            print("Press CTRL-C to stop")
            self.play()

        except KeyboardInterrupt:
            print("Exiting\n")
            sys.exit(0)
