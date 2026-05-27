"""Unified access to either the physical rgbmatrix backend or the local simulator.

This module attempts to import the real ``rgbmatrix`` module that ships with
``hzeller/rpi-rgb-led-matrix``. If it cannot be imported (e.g., when developing
on a laptop or inside a dev container), it automatically falls back to the
software simulator found in ``its-a-plane-python/simulator``.

Set the ``RGBMATRIX_FORCE_SIMULATOR`` environment variable to ``1`` to force the
simulator even when the native module is available. Set
``RGBMATRIX_FORCE_HARDWARE`` to ``1`` to prefer the hardware module and raise an
error when it is missing.
"""

from __future__ import annotations

import importlib
import os
import logging

logger = logging.getLogger(__name__)

_FORCE_SIM = os.environ.get("RGBMATRIX_FORCE_SIMULATOR", "0") == "1"
_FORCE_HW = os.environ.get("RGBMATRIX_FORCE_HARDWARE", "0") == "1"

_BACKEND_NAME: str

if not _FORCE_SIM:
    try:
        _real_rgbmatrix = importlib.import_module("rgbmatrix")
    except ModuleNotFoundError:
        if _FORCE_HW:
            raise
        _real_rgbmatrix = None
    else:
        _BACKEND_NAME = "hardware"
        RGBMatrix = _real_rgbmatrix.RGBMatrix  # type: ignore[attr-defined]
        RGBMatrixOptions = _real_rgbmatrix.RGBMatrixOptions  # type: ignore[attr-defined]
        graphics = importlib.import_module("rgbmatrix.graphics")
        logger.info("Using hardware rgbmatrix backend")

if '_BACKEND_NAME' not in globals():
    from simulator.rgbmatrix_simulator import (  # type: ignore[assignment]
        RGBMatrix,
        RGBMatrixOptions,
        graphics,
    )

    _BACKEND_NAME = "simulator"
    logger.info("Using simulator rgbmatrix backend")


def using_simulator() -> bool:
    """Return True if the simulator backend is active."""

    return _BACKEND_NAME == "simulator"


__all__ = [
    "RGBMatrix",
    "RGBMatrixOptions",
    "graphics",
    "using_simulator",
]
