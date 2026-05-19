"""Loading pulse scene module for displaying a processing indicator."""

from typing import Tuple

from utilities.animator import Animator
from setup import colours

# Setup
BLINKER_POSITION: Tuple[int, int] = (63, 0)
BLINKER_STEPS: int = 10
BLINKER_COLOUR = colours.GREY


class LoadingPulseScene(object):
    """Scene that displays a pulsing indicator when processing is active.
    
    Shows a small blinking pixel in the corner of the display that pulses
    to indicate background processing is occurring.
    """

    def __init__(self) -> None:
        """Initialize the LoadingPulseScene."""
        super().__init__()

    @Animator.KeyFrame.add(2)
    def loading_pulse(self, count: int) -> bool:
        """Update the loading pulse indicator.
        
        Displays a pulsing pixel when background processing is active.
        The brightness fades in a cycle based on the frame count.
        
        Args:
            count: Frame counter from the animator.
            
        Returns:
            True if the counter should reset, False otherwise.
        """
        reset_count = True
        if self.overhead.processing:
            # Calculate the brightness scaler and
            # ensure it's within a sensible range
            brightness = (1 - (count / BLINKER_STEPS)) / 2
            brightness = 0 if (brightness < 0 or brightness > 1) else brightness

            self.canvas.SetPixel(
                BLINKER_POSITION[0],
                BLINKER_POSITION[1],
                brightness * BLINKER_COLOUR.red,
                brightness * BLINKER_COLOUR.green,
                brightness * BLINKER_COLOUR.blue,
            )

            # Only count 0 -> (BLINKER_STEPS - 1)
            reset_count = count == (BLINKER_STEPS - 1)
        else:
            # Not processing, blank the square
            self.canvas.SetPixel(BLINKER_POSITION[0], BLINKER_POSITION[1], 0, 0, 0)

        return reset_count
