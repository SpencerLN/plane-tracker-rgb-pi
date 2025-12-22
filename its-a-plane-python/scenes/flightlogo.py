import os
from pathlib import Path

from PIL import Image
from PIL.Image import Resampling

from utilities.animator import Animator
from setup import colours

LOGO_SIZE = 16
DEFAULT_IMAGE = "default"
LOGO_DIR = Path(__file__).parent.parent.parent / "logo"

class FlightLogoScene:
    @Animator.KeyFrame.add(0)
    def logo_details(self):

        # Guard against no data
        if len(self._data) == 0:
            return

        # Clear the whole area
        self.draw_square(
            0,
            0,
            LOGO_SIZE,
            LOGO_SIZE,
            colours.BLACK,
        )

        icao = self._data[self._data_index]["owner_icao"]
        if icao in ("", "N/A"):
            icao = DEFAULT_IMAGE

        # Open the file
        try:
            image = Image.open(LOGO_DIR / f"{icao}.png")
        except FileNotFoundError:
            try:
                image = Image.open(LOGO_DIR / f"{DEFAULT_IMAGE}.png")
            except FileNotFoundError:
                # If even the default image is missing, skip displaying the logo
                return


        # Make image fit our screen.
        image.thumbnail((LOGO_SIZE, LOGO_SIZE), Resampling.LANCZOS)
        self.matrix.SetImage(image.convert('RGB'))