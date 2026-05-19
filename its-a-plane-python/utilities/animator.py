"""
Animator module for managing keyframe-based animations.

Provides a base class for creating animated scenes with configurable
frame timing and keyframe-based method execution.
"""

import logging
from time import sleep
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)

DELAY_DEFAULT: float = 0.01


class Animator:
    """
    Base class for keyframe-based animations.

    This class provides a framework for creating animations where methods
    are executed at specific frame intervals. Methods decorated with
    @Animator.KeyFrame.add() are automatically registered and called
    according to their divisor and offset settings.

    Attributes:
        keyframes: List of registered keyframe methods.
        frame: Current frame number.

    Example usage:
        class MyAnimation(Animator):
            @Animator.KeyFrame.add(divisor=5, offset=1)
            def animate_element(self, count: int) -> bool:
                # Called every 5 frames, starting at frame 1
                logger.info(f"Animating at count {count}")
                return False  # Return True to reset count

            @Animator.KeyFrame.add(divisor=0)
            def setup(self) -> None:
                # Called once at frame 0
                logger.info("Setup complete")

        animation = MyAnimation()
        animation.play()
    """

    class KeyFrame:
        """
        Decorator class for marking methods as keyframes.

        Keyframes are methods that execute at specific frame intervals
        during animation playback.
        """

        @staticmethod
        def add(divisor: int, offset: int = 0) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            """
            Decorator to register a method as a keyframe.

            Args:
                divisor: Frame interval for execution. If 0, the method
                    runs only once at frame 0 (initialization).
                offset: Frame offset before first execution. Default is 0.

            Returns:
                A decorator function that adds keyframe properties to the method.

            Example:
                @Animator.KeyFrame.add(divisor=10, offset=5)
                def my_keyframe(self, count: int) -> bool:
                    # Executes every 10 frames, starting at frame 5
                    return False
            """
            def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
                func.properties = {"divisor": divisor, "offset": offset, "count": 0}
                return func

            return wrapper

    def __init__(self) -> None:
        """Initialize the Animator with default settings."""
        self.keyframes: List[Callable[..., Any]] = []
        self.frame: int = 0
        self._delay: float = DELAY_DEFAULT
        self._reset_scene: bool = True

        self._register_keyframes()

        super().__init__()

    def _register_keyframes(self) -> None:
        """
        Register all keyframe-decorated methods.

        Uses introspection to find all methods with keyframe properties
        and adds them to the keyframes list.
        """
        for methodname in dir(self):
            method = getattr(self, methodname)
            if hasattr(method, "properties"):
                self.keyframes.append(method)

    def reset_scene(self) -> None:
        """
        Reset the scene by executing all initialization keyframes.

        Calls all keyframes with divisor=0, which are typically used
        for scene setup and initialization.
        """
        for keyframe in self.keyframes:
            if keyframe.properties["divisor"] == 0:
                keyframe()

    def play(self) -> None:
        """
        Start the animation loop.

        Continuously iterates through frames, executing keyframes according
        to their divisor and offset settings. This method runs indefinitely
        until interrupted.

        Frame execution logic:
            - Frame 0: Only keyframes with divisor=0 are executed (initialization)
            - Frame > 0: Keyframes execute when (frame - offset) % divisor == 0
        """
        while True:
            for keyframe in self.keyframes:
                # If divisor == 0 then only run once on first loop
                if self.frame == 0:
                    if keyframe.properties["divisor"] == 0:
                        keyframe()

                # Otherwise perform normal operation
                if (
                    self.frame > 0
                    and keyframe.properties["divisor"]
                    and not (
                        (self.frame - keyframe.properties["offset"])
                        % keyframe.properties["divisor"]
                    )
                ):
                    if keyframe(keyframe.properties["count"]):
                        keyframe.properties["count"] = 0
                    else:
                        keyframe.properties["count"] += 1

            self._reset_scene = False
            self.frame += 1
            sleep(self._delay)

    @property
    def delay(self) -> float:
        """
        Get the current frame delay.

        Returns:
            The delay in seconds between frames.
        """
        return self._delay

    @delay.setter
    def delay(self, value: float) -> None:
        """
        Set the frame delay.

        Args:
            value: The delay in seconds between frames.
        """
        self._delay = value
