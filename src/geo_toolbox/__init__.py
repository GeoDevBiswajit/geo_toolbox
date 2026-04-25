"""
geo_toolbox: Geospatial data extraction and analysis toolkit powered by Google Earth Engine.
"""

from .core.eedata import GEETimeSeriesExtractor, Reducer
from .processing.processors import TimeSeriesProcessor
from .visualization.visualizer import TimeSeriesPlotter

__version__ = "0.1.0"
__author__ = "Your Name"
__all__ = [
    "GEETimeSeriesExtractor",
    "Reducer",
    "TimeSeriesProcessor",
    "TimeSeriesPlotter",
]
