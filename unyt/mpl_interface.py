"""Matplotlib ConversionInterface"""
try:
    from matplotlib.units import (
        ConversionInterface,
        ConversionError,
        AxisInfo,
        registry,
    )
except ModuleNotFoundError:
    pass
else:
    import re
    from unyt import unyt_array, Unit

    class unyt_arrayConverter(ConversionInterface):
        """Matplotlib interface for unyt_array"""

        @staticmethod
        def axisinfo(unit, axis):
            """return default axis label"""
            if isinstance(unit, tuple):
                unit = unit[0]
            label = f"$\\left({Unit(unit).latex_representation()}\\right)$"
            return AxisInfo(label=label)

        @staticmethod
        def default_units(x, axis):
            """Return the default unit for x or None"""
            return x.units

        @staticmethod
        def convert(value, unit, axis):
            """Convert"""
            if isinstance(unit, str) or isinstance(unit, Unit):
                unit = (unit,)
            return value.to(*unit)

    registry[unyt_array] = unyt_arrayConverter()
