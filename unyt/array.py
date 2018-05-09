"""
unyt_array class.



"""

# -----------------------------------------------------------------------------
# Copyright (c) 2018, yt Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the LICENSE file, distributed with this software.
# -----------------------------------------------------------------------------

import copy
from functools import wraps
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache
from numbers import Number as numeric_type
import numpy as np
from numpy import (
    add,
    subtract,
    multiply,
    divide,
    logaddexp,
    logaddexp2,
    true_divide,
    floor_divide,
    negative,
    power,
    remainder,
    mod,
    absolute,
    rint,
    sign,
    conj,
    exp,
    exp2,
    log,
    log2,
    log10,
    expm1,
    log1p,
    sqrt,
    square,
    reciprocal,
    sin,
    cos,
    tan,
    arcsin,
    arccos,
    arctan,
    arctan2,
    hypot,
    sinh,
    cosh,
    tanh,
    arcsinh,
    arccosh,
    arctanh,
    deg2rad,
    rad2deg,
    bitwise_and,
    bitwise_or,
    bitwise_xor,
    invert,
    left_shift,
    right_shift,
    greater,
    greater_equal,
    less,
    less_equal,
    not_equal,
    equal,
    logical_and,
    logical_or,
    logical_xor,
    logical_not,
    maximum,
    minimum,
    fmax,
    fmin,
    isreal,
    iscomplex,
    isfinite,
    isinf,
    isnan,
    signbit,
    copysign,
    nextafter,
    modf,
    ldexp,
    frexp,
    fmod,
    floor,
    ceil,
    trunc,
    fabs,
    spacing,
    positive,
    divmod as divmod_,
    isnat,
    heaviside,
)
from numpy.core.umath import _ones_like
from sympy import Rational

from unyt.dimensions import (
    angle,
    temperature
)
from unyt.exceptions import (
    IterableUnitCoercionError,
    InvalidUnitEquivalence,
    InvalidUnitOperation,
    MKSCGSConversionError,
    UnitConversionError,
    UnitOperationError,
)
from unyt.equivalencies import equivalence_registry
from unyt._on_demand_imports import _astropy
from unyt._unit_lookup_table import default_unit_symbol_lut
from unyt._pint_conversions import convert_pint_units
from unyt.unit_object import (
    _check_em_conversion,
    _em_conversion,
    Unit,
    UnitParseError,
)
from unyt.unit_registry import UnitRegistry

NULL_UNIT = Unit()
POWER_SIGN_MAPPING = {multiply: 1, divide: -1}


def _iterable(obj):
    try:
        len(obj)
    except Exception:
        return False
    return True


def _return_arr(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        ret, units = func(*args, **kwargs)
        if ret.shape == ():
            return unyt_quantity(ret, units)
        else:
            # This could be a subclass, so don't call unyt_array directly.
            return type(args[0])(ret, units)
    return wrapped


@lru_cache(maxsize=128, typed=False)
def _sqrt_unit(unit):
    return unit**0.5


@lru_cache(maxsize=128, typed=False)
def _multiply_units(unit1, unit2):
    return unit1 * unit2


def _preserve_units(unit1, unit2=None):
    return unit1


@lru_cache(maxsize=128, typed=False)
def _power_unit(unit, power):
    return unit**power


@lru_cache(maxsize=128, typed=False)
def _square_unit(unit):
    return unit*unit


@lru_cache(maxsize=128, typed=False)
def _divide_units(unit1, unit2):
    return unit1/unit2


@lru_cache(maxsize=128, typed=False)
def _reciprocal_unit(unit):
    return unit**-1


def _passthrough_unit(unit, unit2=None):
    return unit


def _return_without_unit(unit, unit2=None):
    return None


def _arctan2_unit(unit1, unit2):
    return NULL_UNIT


def _comparison_unit(unit1, unit2=None):
    return None


def _invert_units(unit):
    raise TypeError(
        "Bit-twiddling operators are not defined for unyt_array instances")


def _bitop_units(unit1, unit2):
    raise TypeError(
        "Bit-twiddling operators are not defined for unyt_array instances")


def _coerce_iterable_units(input_object):
    if isinstance(input_object, np.ndarray):
        return input_object
    if _iterable(input_object):
        if any([isinstance(o, unyt_array) for o in input_object]):
            ff = getattr(input_object[0], 'units', NULL_UNIT, )
            if any([ff != getattr(_, 'units', NULL_UNIT)
                    for _ in input_object]):
                raise IterableUnitCoercionError(input_object)
            # This will create a copy of the data in the iterable.
            return unyt_array(input_object)
    return np.asarray(input_object)


@lru_cache(maxsize=128, typed=False)
def _unit_repr_check_same(my_units, other_units):
    """
    Takes a Unit object, or string of known unit symbol, and check that it
    is compatible with this quantity. Returns Unit object.

    """
    if not my_units.same_dimensions_as(other_units):
        raise UnitConversionError(
            my_units, my_units.dimensions, other_units, other_units.dimensions)

    return other_units


def _sanitize_units_convert(possible_units, registry):
    if isinstance(possible_units, Unit):
        return possible_units

    # let Unit() try to parse this if it's not already a Unit
    unit = Unit(possible_units, registry=registry)

    return unit


unary_operators = (
    negative,
    absolute,
    rint,
    sign,
    conj,
    exp,
    exp2,
    log,
    log2,
    log10,
    expm1,
    log1p,
    sqrt,
    square,
    reciprocal,
    sin,
    cos,
    tan,
    arcsin,
    arccos,
    arctan,
    sinh,
    cosh,
    tanh,
    arcsinh,
    arccosh,
    arctanh,
    deg2rad,
    rad2deg,
    invert,
    logical_not,
    isreal,
    iscomplex,
    isfinite,
    isinf,
    isnan,
    signbit,
    floor,
    ceil,
    trunc,
    modf,
    frexp,
    fabs,
    spacing,
    positive,
    isnat,
)

binary_operators = (
    add,
    subtract,
    multiply,
    divide,
    logaddexp,
    logaddexp2,
    true_divide,
    power,
    remainder,
    mod,
    arctan2,
    hypot,
    bitwise_and,
    bitwise_or,
    bitwise_xor,
    left_shift,
    right_shift,
    greater,
    greater_equal,
    less,
    less_equal,
    not_equal,
    equal,
    logical_and,
    logical_or,
    logical_xor,
    maximum,
    minimum,
    fmax,
    fmin,
    copysign,
    nextafter,
    ldexp,
    fmod,
    divmod_,
    heaviside
)

trigonometric_operators = (
    sin,
    cos,
    tan,
)


class unyt_array(np.ndarray):
    """
    An ndarray subclass that attaches a symbolic unit object to the array data.

    Parameters
    ----------

    input_array : iterable
        A tuple, list, or array to attach units to
    input_units : String unit name, unit symbol object, or astropy unit
        The units of the array. Powers must be specified using python
        syntax (cm**3, not cm^3).
    registry : ~unyt.unit_registry.UnitRegistry
        The registry to create units from. If input_units is already associated
        with a unit registry and this is specified, this will be used instead
        of the registry associated with the unit object.
    dtype : numpy dtype or dtype name
        The dtype of the array data. Defaults to the dtype of the input data,
        or, if none is found, uses np.float64
    bypass_validation : boolean
        If True, all input validation is skipped. Using this option may produce
        corrupted, invalid units or array data, but can lead to significant
        speedups in the input validation logic adds significant overhead. If
        set, input_units *must* be a valid unit object. Defaults to False.

    Examples
    --------

    >>> from unyt import unyt_array
    >>> a = unyt_array([1, 2, 3], 'cm')
    >>> b = unyt_array([4, 5, 6], 'm')
    >>> a + b
    unyt_array([401., 502., 603.], 'cm')
    >>> b + a
    unyt_array([4.01, 5.02, 6.03], 'm')

    NumPy ufuncs will pass through units where appropriate.

    >>> from unyt import g, cm
    >>> import numpy as np
    >>> a = (np.arange(8) - 4)*g/cm**3
    >>> np.abs(a)
    unyt_array([4., 3., 2., 1., 0., 1., 2., 3.], 'g/cm**3')

    and strip them when it would be annoying to deal with them.

    >>> np.log10(np.arange(8)+1)
    array([0.        , 0.30103   , 0.47712125, 0.60205999, 0.69897   ,
           0.77815125, 0.84509804, 0.90308999])

    """
    _ufunc_registry = {
        add: _preserve_units,
        subtract: _preserve_units,
        multiply: _multiply_units,
        divide: _divide_units,
        logaddexp: _return_without_unit,
        logaddexp2: _return_without_unit,
        true_divide: _divide_units,
        floor_divide: _divide_units,
        negative: _passthrough_unit,
        power: _power_unit,
        remainder: _preserve_units,
        mod: _preserve_units,
        fmod: _preserve_units,
        absolute: _passthrough_unit,
        fabs: _passthrough_unit,
        rint: _return_without_unit,
        sign: _return_without_unit,
        conj: _passthrough_unit,
        exp: _return_without_unit,
        exp2: _return_without_unit,
        log: _return_without_unit,
        log2: _return_without_unit,
        log10: _return_without_unit,
        expm1: _return_without_unit,
        log1p: _return_without_unit,
        sqrt: _sqrt_unit,
        square: _square_unit,
        reciprocal: _reciprocal_unit,
        sin: _return_without_unit,
        cos: _return_without_unit,
        tan: _return_without_unit,
        sinh: _return_without_unit,
        cosh: _return_without_unit,
        tanh: _return_without_unit,
        arcsin: _return_without_unit,
        arccos: _return_without_unit,
        arctan: _return_without_unit,
        arctan2: _arctan2_unit,
        arcsinh: _return_without_unit,
        arccosh: _return_without_unit,
        arctanh: _return_without_unit,
        hypot: _preserve_units,
        deg2rad: _return_without_unit,
        rad2deg: _return_without_unit,
        bitwise_and: _bitop_units,
        bitwise_or: _bitop_units,
        bitwise_xor: _bitop_units,
        invert: _invert_units,
        left_shift: _bitop_units,
        right_shift: _bitop_units,
        greater: _comparison_unit,
        greater_equal: _comparison_unit,
        less: _comparison_unit,
        less_equal: _comparison_unit,
        not_equal: _comparison_unit,
        equal: _comparison_unit,
        logical_and: _comparison_unit,
        logical_or: _comparison_unit,
        logical_xor: _comparison_unit,
        logical_not: _return_without_unit,
        maximum: _preserve_units,
        minimum: _preserve_units,
        fmax: _preserve_units,
        fmin: _preserve_units,
        isreal: _return_without_unit,
        iscomplex: _return_without_unit,
        isfinite: _return_without_unit,
        isinf: _return_without_unit,
        isnan: _return_without_unit,
        signbit: _return_without_unit,
        copysign: _passthrough_unit,
        nextafter: _preserve_units,
        modf: _passthrough_unit,
        ldexp: _bitop_units,
        frexp: _return_without_unit,
        floor: _passthrough_unit,
        ceil: _passthrough_unit,
        trunc: _passthrough_unit,
        spacing: _passthrough_unit,
        positive: _passthrough_unit,
        divmod_: _passthrough_unit,
        isnat: _return_without_unit,
        heaviside: _preserve_units,
        _ones_like: _preserve_units,
    }

    __array_priority__ = 2.0

    def __new__(cls, input_array, input_units=None, registry=None, dtype=None,
                bypass_validation=False):
        if dtype is None:
            dtype = np.float64
        if bypass_validation is True:
            obj = input_array.view(type=cls, dtype=dtype)
            obj.units = input_units
            if registry is not None:
                obj.units.registry = registry
            return obj
        if input_array is NotImplemented:
            return input_array.view(cls)
        if registry is None and isinstance(input_units, (str, bytes)):
            if input_units.startswith('code_'):
                raise UnitParseError(
                    "Code units used without referring to a dataset. \n"
                    "Perhaps you meant to do something like this instead: \n"
                    "ds.arr(%s, \"%s\")" % (input_array, input_units)
                    )
        if isinstance(input_array, unyt_array):
            ret = input_array.view(cls)
            if input_units is None:
                if registry is None:
                    ret.units = input_array.units
                else:
                    units = Unit(str(input_array.units), registry=registry)
                    ret.units = units
            elif isinstance(input_units, Unit):
                ret.units = input_units
            else:
                ret.units = Unit(input_units, registry=registry)
            return ret
        elif isinstance(input_array, np.ndarray):
            pass
        elif _iterable(input_array) and input_array:
            if isinstance(input_array[0], unyt_array):
                return unyt_array(np.array(input_array, dtype=dtype),
                                  input_array[0].units, registry=registry)

        # Input array is an already formed ndarray instance
        # We first cast to be our class type

        obj = np.asarray(input_array, dtype=dtype).view(cls)

        # Check units type
        if input_units is None:
            # Nothing provided. Make dimensionless...
            units = Unit()
        elif isinstance(input_units, Unit):
            if registry and registry is not input_units.registry:
                units = Unit(str(input_units), registry=registry)
            else:
                units = input_units
        else:
            # units kwarg set, but it's not a Unit object.
            # don't handle all the cases here, let the Unit class handle if
            # it's a str.
            units = Unit(input_units, registry=registry)

        # Attach the units
        obj.units = units

        return obj

    def __repr__(self):
        rep = super(unyt_array, self).__repr__()
        units_repr = self.units.__repr__()
        return rep[:-1] + ', \'' + units_repr + '\')'

    def __str__(self):
        return str(self.view(np.ndarray)) + ' ' + str(self.units)

    def __format__(self, format_spec):
        ret = super(unyt_array, self).__format__(format_spec)
        return ret + ' {}'.format(self.units)

    #
    # Start unit conversion methods
    #

    def convert_to_units(self, units, equivalence=None, **kwargs):
        """
        Convert the array to the given units in-place.

        Optionally, an equivalence can be specified to convert to an
        equivalent quantity which is not in the same dimensions.

        Parameters
        ----------
        units : Unit object or string
            The units you want to convert to.
        equivalence : string, optional
            The equivalence you wish to use. To see which equivalencies
            are supported for this object, try the ``list_equivalencies``
            method. Default: None
        kwargs: optional
            Any additional keyword arguments are supplied to the equivalence

        Raises
        ------
        If the provided unit does not have the same dimensions as the array
        this will raise a UnitConversionError

        Examples
        --------

        >>> from unyt import cm, km
        >>> length = [3000, 2000, 1000]*cm
        >>> length.convert_to_units('m')
        >>> print(length)
        [30. 20. 10.] m
        """
        units = _sanitize_units_convert(units, self.units.registry)
        if equivalence is None:
            try:
                conv_data = _check_em_conversion(self.units, units)
            except MKSCGSConversionError:
                raise UnitConversionError(self.units, self.units.dimensions,
                                          units, units.dimensions)
            if any(conv_data):
                new_units, (conversion_factor, offset) = _em_conversion(
                    self.units, conv_data, units)
            else:
                new_units = _unit_repr_check_same(self.units, units)
                (conversion_factor, offset) = self.units.get_conversion_factor(
                    new_units)

            self.units = new_units
            values = self.d
            values *= conversion_factor

            if offset:
                np.subtract(values, offset, values)
        else:
            self.convert_to_equivalent(units, equivalence, **kwargs)

    def convert_to_base(self, unit_system="mks", equivalence=None, **kwargs):
        """
        Convert the array in-place to the equivalent base units in
        the specified unit system.

        Optionally, an equivalence can be specified to convert to an
        equivalent quantity which is not in the same dimensions.

        Parameters
        ----------
        unit_system : string, optional
            The unit system to be used in the conversion. If not specified,
            the default base units of mks are used.
        equivalence : string, optional
            The equivalence you wish to use. To see which equivalencies
            are supported for this object, try the ``list_equivalencies``
            method. Default: None
        kwargs: optional
            Any additional keyword arguments are supplied to the equivalence

        Raises
        ------
        If the provided unit does not have the same dimensions as the array
        this will raise a UnitConversionError

        Examples
        --------
        >>> from unyt import erg, s
        >>> E = 2.5*erg/s
        >>> E.convert_to_base("mks")
        >>> E
        unyt_quantity(2.5e-07, 'W')
        """
        self.convert_to_units(self.units.get_base_equivalent(unit_system),
                              equivalence=equivalence, **kwargs)

    def convert_to_cgs(self, equivalence=None, **kwargs):
        """
        Convert the array and in-place to the equivalent cgs units.

        Optionally, an equivalence can be specified to convert to an
        equivalent quantity which is not in the same dimensions.

        Parameters
        ----------
        equivalence : string, optional
            The equivalence you wish to use. To see which equivalencies
            are supported for this object, try the ``list_equivalencies``
            method. Default: None
        kwargs: optional
            Any additional keyword arguments are supplied to the equivalence

        Raises
        ------
        If the provided unit does not have the same dimensions as the array
        this will raise a UnitConversionError

        Examples
        --------
        >>> from unyt import Newton
        >>> data = [1, 2, 3]*Newton
        >>> data.convert_to_cgs()
        >>> data
        unyt_array([100000., 200000., 300000.], 'dyne')

        """
        self.convert_to_units(
            self.units.get_cgs_equivalent(), equivalence=equivalence, **kwargs)

    def convert_to_mks(self, equivalence=None, **kwargs):
        """
        Convert the array and units to the equivalent mks units.

        Optionally, an equivalence can be specified to convert to an
        equivalent quantity which is not in the same dimensions.

        Parameters
        ----------
        equivalence : string, optional
            The equivalence you wish to use. To see which equivalencies
            are supported for this object, try the ``list_equivalencies``
            method. Default: None
        kwargs: optional
            Any additional keyword arguments are supplied to the equivalence

        Raises
        ------
        If the provided unit does not have the same dimensions as the array
        this will raise a UnitConversionError

        Examples
        --------
        >>> from unyt import dyne, erg
        >>> data = [1, 2, 3]*erg
        >>> data
        unyt_array([1., 2., 3.], 'erg')
        >>> data.convert_to_mks()
        >>> data
        unyt_array([1.e-07, 2.e-07, 3.e-07], 'J')
        """
        self.convert_to_units(
            self.units.get_mks_equivalent(), equivalence, **kwargs)

    def in_units(self, units, equivalence=None, **kwargs):
        """
        Creates a copy of this array with the data converted to the
        supplied units, and returns it.

        Optionally, an equivalence can be specified to convert to an
        equivalent quantity which is not in the same dimensions.

        Parameters
        ----------
        units : Unit object or string
            The units you want to get a new quantity in.
        equivalence : string, optional
            The equivalence you wish to use. To see which equivalencies
            are supported for this object, try the ``list_equivalencies``
            method. Default: None
        kwargs: optional
            Any additional keyword arguments are supplied to the
            equivalence

        Raises
        ------
        If the provided unit does not have the same dimensions as the array
        this will raise a UnitConversionError

        Examples
        --------
        >>> from unyt import c, gram
        >>> m = 10*gram
        >>> E = m*c**2
        >>> print(E.in_units('erg'))
        8.987551787368176e+21 erg
        >>> print(E.in_units('J'))
        898755178736817.6 J
        """
        units = _sanitize_units_convert(units, self.units.registry)
        if equivalence is None:
            try:
                conv_data = _check_em_conversion(self.units, units)
            except MKSCGSConversionError:
                raise UnitConversionError(self.units, self.units.dimensions,
                                          units, units.dimensions)
            if any(conv_data):
                new_units, (conversion_factor, offset) = _em_conversion(
                    self.units, conv_data, units)
                offset = 0
            else:
                new_units = _unit_repr_check_same(self.units, units)
                (conversion_factor, offset) = self.units.get_conversion_factor(
                    new_units)

            ret = np.asarray(self.ndview * conversion_factor)
            if offset:
                np.subtract(ret, offset, ret)

            new_array = type(self)(ret, new_units, bypass_validation=True)

            return new_array
        else:
            return self.to_equivalent(units, equivalence, **kwargs)

    def to(self, units, equivalence=None, **kwargs):
        """
        Creates a copy of this array with the data converted to the
        supplied units, and returns it.

        Optionally, an equivalence can be specified to convert to an
        equivalent quantity which is not in the same dimensions.

        .. note::

            All additional keyword arguments are passed to the
            equivalency, which should be used if that particular
            equivalency requires them.

        Parameters
        ----------
        units : Unit object or string
            The units you want to get a new quantity in.
        equivalence : string, optional
            The equivalence you wish to use. To see which
            equivalencies are supported for this unitful
            quantity, try the :meth:`list_equivalencies`
            method. Default: None
        kwargs: optional
            Any additional keywoard arguments are supplied to the
            equivalence

        Raises
        ------
        If the provided unit does not have the same dimensions as the array
        this will raise a UnitConversionError

        Examples
        --------
        >>> from unyt import c, gram
        >>> m = 10*gram
        >>> E = m*c**2
        >>> print(E.to('erg'))
        8.987551787368176e+21 erg
        >>> print(E.to('J'))
        898755178736817.6 J
        """
        return self.in_units(units, equivalence=equivalence, **kwargs)

    def to_value(self, units=None, equivalence=None, **kwargs):
        """
        Creates a copy of this array with the data in the supplied
        units, and returns it without units. Output is therefore a
        bare NumPy array.

        Optionally, an equivalence can be specified to convert to an
        equivalent quantity which is not in the same dimensions.

        .. note::

            All additional keyword arguments are passed to the
            equivalency, which should be used if that particular
            equivalency requires them.

        Parameters
        ----------
        units : Unit object or string, optional
            The units you want to get the bare quantity in. If not
            specified, the value will be returned in the current units.

        equivalence : string, optional
            The equivalence you wish to use. To see which
            equivalencies are supported for this unitful
            quantity, try the :meth:`list_equivalencies`
            method. Default: None

        Examples
        --------
        >>> from unyt import km
        >>> a = [3, 4, 5]*km
        >>> print(a.to_value('cm'))
        [300000. 400000. 500000.]
        """
        if units is None:
            v = self.value
        else:
            v = self.in_units(units, equivalence=equivalence, **kwargs).value
        if isinstance(self, unyt_quantity):
            return float(v)
        else:
            return v

    def in_base(self, unit_system="mks"):
        """
        Creates a copy of this array with the data in the specified unit
        system, and returns it in that system's base units.

        Parameters
        ----------
        unit_system : string, optional
            The unit system to be used in the conversion. If not specified,
            the default base units of mks are used.

        Examples
        --------
        >>> from unyt import erg, s
        >>> E = 2.5*erg/s
        >>> print(E.in_base("mks"))
        2.5e-07 W
        """
        conv_data = _check_em_conversion(self.units)
        if any(conv_data):
            to_units, (conv, offset) = _em_conversion(
                self.units, conv_data, unit_system=unit_system)
        else:
            to_units = self.units.get_base_equivalent(unit_system)
            conv, offset = self.units.get_conversion_factor(to_units)
        ret = self.v*conv
        if offset:
            ret = ret - offset
        return type(self)(ret, to_units)

    def in_cgs(self):
        """
        Creates a copy of this array with the data in the equivalent cgs units,
        and returns it.

        Returns
        -------
        unyt_array object with data in this array converted to cgs units.

        Example
        -------
        >>> from unyt import Newton, km
        >>> print((10*Newton/km).in_cgs())
        10.0 g/s**2
        """
        return self.in_base("cgs")

    def in_mks(self):
        """
        Creates a copy of this array with the data in the equivalent mks units,
        and returns it.

        Returns
        -------
        unyt_array object with data in this array converted to mks units.

        Example
        -------
        >>> from unyt import mile
        >>> print((1*mile).in_mks())
        1609.344 m
        """
        return self.in_base("mks")

    def convert_to_equivalent(self, unit, equivalence, **kwargs):
        """
        Return a copy of the unyt_array in the units specified units, assuming
        the given equivalency. The dimensions of the specified units and the
        dimensions of the original array need not match so long as there is an
        appropriate conversion in the specified equivalency.

        Parameters
        ----------
        unit : string
            The unit that you wish to convert to.
        equivalence : string
            The equivalence you wish to use. To see which equivalencies are
            supported for this unitful quantity, try the
            :meth:`list_equivalencies` method.

        Examples
        --------
        >>> from unyt import K
        >>> a = [10, 20, 30]*(1e7*K)
        >>> a.convert_to_equivalent("keV", "thermal")
        >>> a
        unyt_array([ 8.6173324, 17.2346648, 25.8519972], 'keV')
        """
        conv_unit = Unit(unit, registry=self.units.registry)
        if self.units.same_dimensions_as(conv_unit):
            self.convert_to_units(conv_unit)
        this_equiv = equivalence_registry[equivalence](in_place=True)
        oneway_or_equivalent = (conv_unit.has_equivalent(equivalence)
                                or this_equiv.one_way)
        if self.has_equivalent(equivalence) and oneway_or_equivalent:
            ret = this_equiv._convert(self, conv_unit.dimensions, **kwargs)
            if isinstance(ret, tuple):
                # need to subtract off the current value because index
                # into an array scalar isn't allowed
                view = self.d
                view += (ret[0] - view)
                self.units = Unit(ret[1], registry=self.units.registry)
            try:
                self.convert_to_units(conv_unit)
            except UnitConversionError:
                InvalidUnitEquivalence(equivalence, self.units, unit)
        else:
            raise InvalidUnitEquivalence(equivalence, self.units, unit)

    def to_equivalent(self, unit, equivalence, **kwargs):
        """
        Return a copy of the unyt_array in the units specified units, assuming
        the given equivalency. The dimensions of the specified units and the
        dimensions of the original array need not match so long as there is an
        appropriate conversion in the specified equivalency.

        Parameters
        ----------
        unit : string
            The unit that you wish to convert to.
        equivalence : string
            The equivalence you wish to use. To see which equivalencies are
            supported for this unitful quantity, try the
            :meth:`list_equivalencies` method.

        Examples
        --------
        >>> from unyt import K
        >>> a = 1.0e7*K
        >>> print(a.to_equivalent("keV", "thermal"))
        0.8617332401096504 keV
        """
        conv_unit = Unit(unit, registry=self.units.registry)
        if self.units.same_dimensions_as(conv_unit):
            return self.in_units(conv_unit)
        this_equiv = equivalence_registry[equivalence]()
        oneway_or_equivalent = (
            conv_unit.has_equivalent(equivalence) or this_equiv.one_way)
        if self.has_equivalent(equivalence) and oneway_or_equivalent:
            new_arr = this_equiv._convert(
                self, conv_unit.dimensions, **kwargs)
            if isinstance(new_arr, tuple):
                try:
                    return type(self)(new_arr[0], new_arr[1]).in_units(
                        conv_unit)
                except UnitConversionError:
                    raise InvalidUnitEquivalence(equivalence, self.units, unit)
            else:
                return new_arr.in_units(conv_unit)
        else:
            raise InvalidUnitEquivalence(equivalence, self.units, unit)

    def list_equivalencies(self):
        """
        Lists the possible equivalencies associated with this unyt_array or
        unyt_quantity.

        Example
        -------
        >>> from unyt import km
        >>> (1.0*km).list_equivalencies()
        spectral: length <-> frequency <-> energy
        schwarzschild: mass <-> length
        compton: mass <-> length
        """
        self.units.list_equivalencies()

    def has_equivalent(self, equivalence):
        """
        Check to see if this unyt_array or unyt_quantity has an equivalent
        unit in *equiv*.

        Example
        -------
        >>> from unyt import km, keV
        >>> (1.0*km).has_equivalent('spectral')
        True
        >>> print((1*km).to_equivalent('MHz', equivalence='spectral'))
        0.29979245800000004 MHz
        >>> print((1*keV).to_equivalent('angstrom', equivalence='spectral'))
        12.398419315219659 angstrom
        """
        return self.units.has_equivalent(equivalence)

    def ndarray_view(self):
        """
        Returns a view into the array as a numpy array

        Returns
        -------
        View of this array's data.

        Example
        -------

        >>> from unyt import km
        >>> a = [3, 4, 5]*km
        >>> a
        unyt_array([3., 4., 5.], 'km')
        >>> a.ndarray_view()
        array([3., 4., 5.])

        This function returns a view that shares the same underlying memory
        as the original array.

        >>> b = a.ndarray_view()
        >>> b.base is a.base
        True
        >>> b[2] = 4
        >>> b
        array([3., 4., 4.])
        >>> a
        unyt_array([3., 4., 4.], 'km')
        """
        return self.view(np.ndarray)

    def to_ndarray(self):
        """
        Creates a copy of this array with the unit information stripped

        Example
        -------
        >>> from unyt import km
        >>> a = [3, 4, 5]*km
        >>> a
        unyt_array([3., 4., 5.], 'km')
        >>> b = a.to_ndarray()
        >>> b
        array([3., 4., 5.])

        The returned array will contain a copy of the data contained in
        the original array.

        >>> a.base is not b.base
        True

        """
        return np.array(self)

    @classmethod
    def from_astropy(cls, arr, unit_registry=None):
        """
        Convert an AstroPy "Quantity" to a unyt_array or unyt_quantity.

        Parameters
        ----------
        arr : AstroPy Quantity
            The Quantity to convert from.
        unit_registry : yt UnitRegistry, optional
            A yt unit registry to use in the conversion. If one is not
            supplied, the default one will be used.

        Example
        -------
        >>> from astropy.units import km
        >>> unyt_quantity.from_astropy(km)
        unyt_quantity(1., 'km')
        >>> a = [1, 2, 3]*km
        >>> a
        <Quantity [1., 2., 3.] km>
        >>> unyt_array.from_astropy(a)
        unyt_array([1., 2., 3.], 'km')
        """
        # Converting from AstroPy Quantity
        try:
            u = arr.unit
            _arr = arr
        except AttributeError:
            u = arr
            _arr = 1.0*u
        ap_units = []
        for base, exponent in zip(u.bases, u.powers):
            unit_str = base.to_string()
            # we have to do this because AstroPy is silly and defines
            # hour as "h"
            if unit_str == "h":
                unit_str = "hr"
            ap_units.append("%s**(%s)" % (unit_str, Rational(exponent)))
        ap_units = "*".join(ap_units)
        if isinstance(_arr.value, np.ndarray) and _arr.shape != ():
            return unyt_array(_arr.value, ap_units, registry=unit_registry)
        else:
            return unyt_quantity(_arr.value, ap_units, registry=unit_registry)

    def to_astropy(self, **kwargs):
        """
        Creates a new AstroPy quantity with the same unit information.

        Example
        -------
        >>> from unyt import g, cm
        >>> data = [3, 4, 5]*g/cm**3
        >>> data.to_astropy()
        <Quantity [3., 4., 5.] g / cm3>
        """
        if _astropy.units is None:
            raise ImportError(
                "You don't have AstroPy installed, so you can't convert to " +
                "an AstroPy quantity.")
        return self.value*_astropy.units.Unit(str(self.units), **kwargs)

    @classmethod
    def from_pint(cls, arr, unit_registry=None):
        """
        Convert a Pint "Quantity" to a unyt_array or unyt_quantity.

        Parameters
        ----------
        arr : Pint Quantity
            The Quantity to convert from.
        unit_registry : yt UnitRegistry, optional
            A yt unit registry to use in the conversion. If one is not
            supplied, the default one will be used.

        Examples
        --------
        >>> from pint import UnitRegistry
        >>> import numpy as np
        >>> ureg = UnitRegistry()
        >>> a = np.arange(4)
        >>> b = ureg.Quantity(a, "erg/cm**3")
        >>> b
        <Quantity([0 1 2 3], 'erg / centimeter ** 3')>
        >>> c = unyt_array.from_pint(b)
        >>> c
        unyt_array([0., 1., 2., 3.], 'erg/cm**3')
        """
        p_units = []
        for base, exponent in arr._units.items():
            bs = convert_pint_units(base)
            p_units.append("%s**(%s)" % (bs, Rational(exponent)))
        p_units = "*".join(p_units)
        if isinstance(arr.magnitude, np.ndarray):
            return unyt_array(arr.magnitude, p_units, registry=unit_registry,
                              dtype='float64')
        else:
            return unyt_quantity(arr.magnitude, p_units,
                                 registry=unit_registry, dtype='float64')

    def to_pint(self, unit_registry=None):
        """
        Convert a unyt_array or unyt_quantity to a Pint Quantity.

        Parameters
        ----------
        arr : unyt_array or unyt_quantity
            The unitful quantity to convert from.
        unit_registry : Pint UnitRegistry, optional
            The Pint UnitRegistry to use in the conversion. If one is not
            supplied, the default one will be used. NOTE: This is not
            the same as a yt UnitRegistry object.

        Examples
        --------
        >>> from unyt import cm, s
        >>> a = 4*cm**2/s
        >>> print(a)
        4.0 cm**2/s
        >>> a.to_pint()
        <Quantity(4.0, 'centimeter ** 2 / second')>
        """
        from pint import UnitRegistry
        if unit_registry is None:
            unit_registry = UnitRegistry()
        powers_dict = self.units.expr.as_powers_dict()
        units = []
        for unit, pow in powers_dict.items():
            # we have to do this because Pint doesn't recognize
            # "yr" as "year"
            if str(unit).endswith("yr") and len(str(unit)) in [2, 3]:
                unit = str(unit).replace("yr", "year")
            units.append("%s**(%s)" % (unit, Rational(pow)))
        units = "*".join(units)
        return unit_registry.Quantity(self.value, units)

    #
    # End unit conversion methods
    #

    def write_hdf5(self, filename, dataset_name=None, info=None,
                   group_name=None):
        r"""Writes a unyt_array to hdf5 file.

        Parameters
        ----------
        filename: string
            The filename to create and write a dataset to

        dataset_name: string
            The name of the dataset to create in the file.

        info: dictionary
            A dictionary of supplementary info to write to append as attributes
            to the dataset.

        group_name: string
            An optional group to write the arrays to. If not specified, the
            arrays are datasets at the top level by default.

        Examples
        --------
        >>> from unyt import cm
        >>> a = [1,2,3]*cm
        >>> myinfo = {'field':'dinosaurs', 'type':'field_data'}
        >>> a.write_hdf5('test_array_data.h5', dataset_name='dinosaurs',
        ...              info=myinfo)  # doctest: +SKIP
        """
        from unyt._on_demand_imports import _h5py as h5py
        from six.moves import cPickle as pickle
        if info is None:
            info = {}

        info['units'] = str(self.units)
        info['unit_registry'] = np.void(pickle.dumps(self.units.registry.lut))

        if dataset_name is None:
            dataset_name = 'array_data'

        f = h5py.File(filename)
        if group_name is not None:
            if group_name in f:
                g = f[group_name]
            else:
                g = f.create_group(group_name)
        else:
            g = f
        if dataset_name in g.keys():
            d = g[dataset_name]
            # Overwrite without deleting if we can get away with it.
            if d.shape == self.shape and d.dtype == self.dtype:
                d[...] = self
                for k in d.attrs.keys():
                    del d.attrs[k]
            else:
                del f[dataset_name]
                d = g.create_dataset(dataset_name, data=self)
        else:
            d = g.create_dataset(dataset_name, data=self)

        for k, v in info.items():
            d.attrs[k] = v
        f.close()

    @classmethod
    def from_hdf5(cls, filename, dataset_name=None, group_name=None):
        r"""Attempts read in and convert a dataset in an hdf5 file into a
        unyt_array.

        Parameters
        ----------
        filename: string
        The filename to of the hdf5 file.

        dataset_name: string
            The name of the dataset to read from.  If the dataset has a units
            attribute, attempt to infer units as well.

        group_name: string
            An optional group to read the arrays from. If not specified, the
            arrays are datasets at the top level by default.

        """
        from unyt._on_demand_imports import _h5py as h5py
        from six.moves import cPickle as pickle

        if dataset_name is None:
            dataset_name = 'array_data'

        f = h5py.File(filename)
        if group_name is not None:
            g = f[group_name]
        else:
            g = f
        dataset = g[dataset_name]
        data = dataset[:]
        units = dataset.attrs.get('units', '')
        if 'unit_registry' in dataset.attrs.keys():
            unit_lut = pickle.loads(dataset.attrs['unit_registry'].tostring())
        else:
            unit_lut = None
        f.close()
        registry = UnitRegistry(lut=unit_lut, add_default_symbols=False)
        return cls(data, units, registry=registry)

    #
    # Start convenience methods
    #

    @property
    def value(self):
        """
        Creates a copy of this array with the unit information stripped

        Example
        -------
        >>> from unyt import km
        >>> a = [3, 4, 5]*km
        >>> a
        unyt_array([3., 4., 5.], 'km')
        >>> b = a.value
        >>> b
        array([3., 4., 5.])

        The returned array will contain a copy of the data contained in
        the original array.

        >>> a.base is not b.base
        True

        """
        return np.array(self)

    @property
    def v(self):
        """
        Creates a copy of this array with the unit information stripped

        Example
        -------
        >>> from unyt import km
        >>> a = [3, 4, 5]*km
        >>> a
        unyt_array([3., 4., 5.], 'km')
        >>> b = a.v
        >>> b
        array([3., 4., 5.])

        The returned array will contain a copy of the data contained in
        the original array.

        >>> a.base is not b.base
        True

        """
        return np.array(self)

    @property
    def ndview(self):
        """
        Returns a view into the array as a numpy array

        Returns
        -------
        View of this array's data.

        Example
        -------

        >>> from unyt import km
        >>> a = [3, 4, 5]*km
        >>> a
        unyt_array([3., 4., 5.], 'km')
        >>> a.ndview
        array([3., 4., 5.])

        This function returns a view that shares the same underlying memory
        as the original array.

        >>> b = a.ndview
        >>> b.base is a.base
        True
        >>> b[2] = 4
        >>> b
        array([3., 4., 4.])
        >>> a
        unyt_array([3., 4., 4.], 'km')

        """
        return self.view(np.ndarray)

    @property
    def d(self):
        """
        Returns a view into the array as a numpy array

        Returns
        -------
        View of this array's data.

        Example
        -------

        >>> from unyt import km
        >>> a = [3, 4, 5]*km
        >>> a
        unyt_array([3., 4., 5.], 'km')
        >>> a.d
        array([3., 4., 5.])

        This function returns a view that shares the same underlying memory
        as the original array.

        >>> b = a.d
        >>> b.base is a.base
        True
        >>> b[2] = 4
        >>> b
        array([3., 4., 4.])
        >>> a
        unyt_array([3., 4., 4.], 'km')
        """
        return self.view(np.ndarray)

    @property
    def unit_quantity(self):
        """
        Return a quantity with a value of 1 and the same units as this array

        Example
        -------
        >>> from unyt import km
        >>> a = [4, 5, 6]*km
        >>> a.unit_quantity
        unyt_quantity(1., 'km')
        >>> print(a + 7*a.unit_quantity)
        [11. 12. 13.] km
        """
        return unyt_quantity(1.0, self.units)

    @property
    def uq(self):
        """
        Return a quantity with a value of 1 and the same units as this array

        Example
        -------
        >>> from unyt import km
        >>> a = [4, 5, 6]*km
        >>> a.uq
        unyt_quantity(1., 'km')
        >>> print(a + 7*a.uq)
        [11. 12. 13.] km
        """
        return unyt_quantity(1.0, self.units)

    @property
    def unit_array(self):
        """
        Return an array filled with ones with the same units as this array

        Example
        -------
        >>> from unyt import km
        >>> a = [4, 5, 6]*km
        >>> a.unit_array
        unyt_array([1., 1., 1.], 'km')
        >>> print(a + 7*a.unit_array)
        [11. 12. 13.] km
        """
        return np.ones_like(self)

    @property
    def ua(self):
        """
        Return an array filled with ones with the same units as this array

        Example
        -------
        >>> from unyt import km
        >>> a = [4, 5, 6]*km
        >>> a.unit_array
        unyt_array([1., 1., 1.], 'km')
        >>> print(a + 7*a.unit_array)
        [11. 12. 13.] km
        """
        return np.ones_like(self)

    def __getitem__(self, item):
        ret = super(unyt_array, self).__getitem__(item)
        if ret.shape == ():
            return unyt_quantity(ret, self.units, bypass_validation=True)
        else:
            if hasattr(self, 'units'):
                ret.units = self.units
            return ret

    #
    # Start operation methods
    #

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        func = getattr(ufunc, method)
        if 'out' not in kwargs:
            out = None
            out_func = None
        else:
            # we need to get both the actual "out" object and a view onto it
            # in case we need to do in-place operations
            out = kwargs.pop('out')[0]
            out_func = out.view(np.ndarray)
        if len(inputs) == 1:
            # Unary ufuncs
            inp = inputs[0]
            u = getattr(inp, 'units', None)
            if u is None:
                u = NULL_UNIT
            if u.dimensions is angle and ufunc in trigonometric_operators:
                # ensure np.sin(90*degrees) works as expected
                inp = inp.in_units('radian').v
            # evaluate the ufunc
            out_arr = func(np.asarray(inp), out=out_func, **kwargs)
            if ufunc in (multiply, divide) and method == 'reduce':
                # a reduction of a multiply or divide corresponds to
                # a repeated product which we implement as an exponent
                power_sign = POWER_SIGN_MAPPING[ufunc]
                if 'axis' in kwargs and kwargs['axis'] is not None:
                    unit = u**(power_sign*inp.shape[kwargs['axis']])
                else:
                    unit = u**(power_sign*inp.size)
            else:
                # get unit of result
                unit = self._ufunc_registry[ufunc](u)
            # use type(self) here so we can support user-defined
            # subclasses of unyt_array
            ret_class = type(self)
        elif len(inputs) == 2:
            # binary ufuncs
            i0 = inputs[0]
            i1 = inputs[1]
            # coerce inputs to be ndarrays if they aren't already
            inp0 = _coerce_iterable_units(i0)
            inp1 = _coerce_iterable_units(i1)
            u0 = getattr(i0, 'units', None) or getattr(inp0, 'units', None)
            u1 = getattr(i1, 'units', None) or getattr(inp1, 'units', None)
            ret_class = _get_binary_op_return_class(type(i0), type(i1))
            if u0 is None:
                u0 = Unit(registry=getattr(u1, 'registry', None))
            if u1 is None and ufunc is not power:
                u1 = Unit(registry=getattr(u0, 'registry', None))
            elif ufunc is power:
                u1 = inp1
                if isinstance(u1, np.ndarray):
                    if isinstance(u1, unyt_array):
                        if u1.units.is_dimensionless:
                            pass
                        else:
                            raise UnitOperationError(ufunc, u0, u1)
                    try:
                        u1 = float(u1)
                    except TypeError:
                        raise UnitOperationError(ufunc, u0, u1)
            unit_operator = self._ufunc_registry[ufunc]
            if unit_operator in (_preserve_units, _comparison_unit,
                                 _arctan2_unit):
                # check "is" equality first for speed
                if u0 is not u1 and u0 != u1:
                    # we allow adding, multiplying, comparisons with
                    # zero-filled arrays, lists, etc or scalar zero. We
                    # do not allow zero-filled unyt_array instances for
                    # performance reasons. If we did allow it, every
                    # binary operation would need to scan over all the
                    # elements of both arrays to check for arrays filled
                    # with zeros
                    if ((not isinstance(i0, unyt_array) or
                         not isinstance(i1, unyt_array))):
                        any_nonzero = [np.count_nonzero(i0),
                                       np.count_nonzero(i1)]
                        if any_nonzero[0] == 0:
                            u0 = u1
                        elif any_nonzero[1] == 0:
                            u1 = u0
                    if not u0.same_dimensions_as(u1):
                        if unit_operator is _comparison_unit:
                            # we allow comparisons between data with
                            # units and dimensionless data
                            if u0.is_dimensionless:
                                u0 = u1
                            elif u1.is_dimensionless:
                                u1 = u0
                            else:
                                raise UnitOperationError(ufunc, u0, u1)
                        else:
                            raise UnitOperationError(ufunc, u0, u1)
                    conv, offset = u1.get_conversion_factor(u0)
                    if offset is not None:
                        raise InvalidUnitOperation(
                            "Quantities with units of Fahrenheit or Celsius "
                            "cannot by multiplied, divided, subtracted or "
                            "added.")
                    inp1 = np.asarray(inp1)*conv
                else:
                    if ((u0.base_offset and u0.dimensions is temperature or
                         u1.base_offset and u1.dimensions is temperature)):
                        raise InvalidUnitOperation(
                            "Quantities with units of Fahrenheit or Celsius "
                            "cannot by multiplied, divide, subtracted or "
                            "added.")
            # get the unit of the result
            unit = unit_operator(u0, u1)
            # actually evaluate the ufunc
            out_arr = func(inp0.view(np.ndarray), inp1.view(np.ndarray),
                           out=out_func, **kwargs)
            if unit_operator in (_multiply_units, _divide_units):
                if unit.is_dimensionless and unit.base_value != 1.0:
                    if not u0.is_dimensionless:
                        if u0.dimensions == u1.dimensions:
                            if out_func is not None:
                                out_arr = np.multiply(
                                    out_arr.view(np.ndarray),
                                    unit.base_value, out=out_func)
                            else:
                                out_arr = np.multiply(out_arr.view(np.ndarray),
                                                      unit.base_value, out=out)
                            unit = Unit(registry=unit.registry)
                if ((u0.base_offset and u0.dimensions is temperature or
                     u1.base_offset and u1.dimensions is temperature)):
                    raise InvalidUnitOperation(
                        "Quantities with units of Fahrenheit or Celsius "
                        "cannot by multiplied, divide, subtracted or added.")
        else:
            raise RuntimeError(
                "Support for the %s ufunc with %i inputs has not been"
                "added to unyt_array." % (str(ufunc), len(inputs)))
        if unit is None:
            out_arr = np.array(out_arr, copy=False)
        elif ufunc in (modf, divmod_):
            out_arr = tuple((ret_class(o, unit) for o in out_arr))
        elif out_arr.size == 1:
            out_arr = unyt_quantity(np.asarray(out_arr), unit)
        else:
            if ret_class is unyt_quantity:
                # This happens if you do ndarray * unyt_quantity.
                # Explicitly casting to unyt_array avoids creating a
                # unyt_quantity with size > 1
                out_arr = unyt_array(out_arr, unit)
            else:
                out_arr = ret_class(out_arr, unit, bypass_validation=True)
        if out is not None:
            if isinstance(out, unyt_array):
                try:
                    out.units = out_arr.units
                except AttributeError:
                    # out_arr is an ndarray
                    out.units = Unit('', registry=self.units.registry)
        return out_arr

    def copy(self, order='C'):
        """
        Return a copy of the array.

        Parameters
        ----------
        order : {'C', 'F', 'A', 'K'}, optional
            Controls the memory layout of the copy. 'C' means C-order,
            'F' means F-order, 'A' means 'F' if `a` is Fortran contiguous,
            'C' otherwise. 'K' means match the layout of `a` as closely
            as possible. (Note that this function and :func:`numpy.copy`
            are very similar, but have different default values for their
            order= arguments.)

        See also
        --------
        numpy.copy
        numpy.copyto

        Examples
        --------
        >>> from unyt import km
        >>> x = [[1,2,3],[4,5,6]] * km
        >>> y = x.copy()
        >>> x.fill(0)
        >>> print(x)
        [[0. 0. 0.]
         [0. 0. 0.]] km

        >>> print(y)
        [[1. 2. 3.]
         [4. 5. 6.]] km

        """
        return type(self)(np.copy(np.asarray(self)), self.units)

    def __array_finalize__(self, obj):
        if obj is None and hasattr(self, 'units'):
            return
        self.units = getattr(obj, 'units', NULL_UNIT)

    def __pos__(self):
        """ Posify the data. """
        # this needs to be defined for all numpy versions, see
        # numpy issue #9081
        return type(self)(super(unyt_array, self).__pos__(), self.units)

    @_return_arr
    def dot(self, b, out=None):
        """dot product of two arrays.

        Refer to `numpy.dot` for full documentation.

        See Also
        --------
        numpy.dot : equivalent function

        Examples
        --------
        >>> from unyt import km, s
        >>> a = np.eye(2)*km
        >>> b = (np.ones((2, 2)) * 2)*s
        >>> print(a.dot(b))
        [[2. 2.]
         [2. 2.]] km*s

        This array method can be conveniently chained:

        >>> print(a.dot(b).dot(b))
        [[8. 8.]
         [8. 8.]] km*s**2
        """
        return super(unyt_array, self).dot(b), self.units*b.units

    def __reduce__(self):
        """Pickle reduction method

        See the documentation for the standard library pickle module:
        http://docs.python.org/2/library/pickle.html

        Unit metadata is encoded in the zeroth element of third element of the
        returned tuple, itself a tuple used to restore the state of the
        ndarray. This is always defined for numpy arrays.
        """
        np_ret = super(unyt_array, self).__reduce__()
        obj_state = np_ret[2]
        unit_state = ((((str(self.units), self.units.registry.lut),) +
                       obj_state[:],))
        new_ret = np_ret[:2] + unit_state + np_ret[3:]
        return new_ret

    def __setstate__(self, state):
        """Pickle setstate method

        This is called inside pickle.read() and restores the unit data from the
        metadata extracted in __reduce__ and then serialized by pickle.
        """
        super(unyt_array, self).__setstate__(state[1:])
        try:
            unit, lut = state[0]
        except TypeError:
            # this case happens when we try to load an old pickle file
            # created before we serialized the unit symbol lookup table
            # into the pickle file
            unit, lut = str(state[0]), default_unit_symbol_lut.copy()
        # need to fix up the lut if the pickle was saved prior to PR #1728
        # when the pickle format changed
        if len(lut['m']) == 2:
            lut.update(default_unit_symbol_lut)
            for k, v in [(k, v) for k, v in lut.items() if len(v) == 2]:
                lut[k] = v + (0.0, r'\rm{' + k.replace('_', '\ ') + '}')
        registry = UnitRegistry(lut=lut, add_default_symbols=False)
        self.units = Unit(unit, registry=registry)

    def __deepcopy__(self, memodict=None):
        """copy.deepcopy implementation

        This is necessary for stdlib deepcopy of arrays and quantities.
        """
        if memodict is None:
            memodict = {}
        ret = super(unyt_array, self).__deepcopy__(memodict)
        return type(self)(ret, copy.deepcopy(self.units))


class unyt_quantity(unyt_array):
    """
    A scalar associated with a unit.

    Parameters
    ----------

    input_scalar : an integer or floating point scalar
        The scalar to attach units to
    input_units : String unit specification, unit symbol object, or astropy
                  units
        The units of the quantity. Powers must be specified using python syntax
        (cm**3, not cm^3).
    registry : A UnitRegistry object
        The registry to create units from. If input_units is already associated
        with a unit registry and this is specified, this will be used instead
        of the registry associated with the unit object.
    dtype : data-type
        The dtype of the array data.

    Examples
    --------

    >>> a = unyt_quantity(3, 'cm')
    >>> b = unyt_quantity(2, 'm')
    >>> print(a + b)
    203.0 cm
    >>> print(b + a)
    2.03 m

    NumPy ufuncs will pass through units where appropriate.

    >>> import numpy as np
    >>> from unyt import g, cm
    >>> a = 12*g/cm**3
    >>> print(np.abs(a))
    12.0 g/cm**3

    and strip them when it would be annoying to deal with them.

    >>> print(np.log10(a))
    1.0791812460476249

    """
    def __new__(cls, input_scalar, input_units=None, registry=None,
                dtype=np.float64, bypass_validation=False):
        if not isinstance(input_scalar, (numeric_type, np.number, np.ndarray)):
            raise RuntimeError("unyt_quantity values must be numeric")
        if input_units is None:
            units = getattr(input_scalar, 'units', None)
        else:
            units = input_units
        ret = unyt_array.__new__(
            cls, np.asarray(input_scalar), units, registry, dtype=dtype,
            bypass_validation=bypass_validation)
        if ret.size > 1:
            raise RuntimeError("unyt_quantity instances must be scalars")
        return ret


def _validate_numpy_wrapper_units(v, arrs):
    if not any(isinstance(a, unyt_array) for a in arrs):
        return v
    if not all(isinstance(a, unyt_array) for a in arrs):
        raise RuntimeError("Not all of your arrays are unyt_arrays.")
    a1 = arrs[0]
    if not all(a.units == a1.units for a in arrs[1:]):
        raise RuntimeError("Your arrays must have identical units.")
    v.units = a1.units
    return v


def uconcatenate(arrs, axis=0):
    """Concatenate a sequence of arrays.

    This wrapper around numpy.concatenate preserves units. All input arrays
    must have the same units.  See the documentation of numpy.concatenate for
    full details.

    Examples
    --------
    >>> from unyt import cm
    >>> A = [1, 2, 3]*cm
    >>> B = [2, 3, 4]*cm
    >>> uconcatenate((A, B))
    unyt_array([1., 2., 3., 2., 3., 4.], 'cm')

    """
    v = np.concatenate(arrs, axis=axis)
    v = _validate_numpy_wrapper_units(v, arrs)
    return v


def ucross(arr1, arr2, registry=None, axisa=-1, axisb=-1, axisc=-1, axis=None):
    """Applies the cross product to two YT arrays.

    This wrapper around numpy.cross preserves units.
    See the documentation of numpy.cross for full
    details.
    """
    v = np.cross(arr1, arr2, axisa=axisa, axisb=axisb, axisc=axisc, axis=axis)
    units = arr1.units * arr2.units
    arr = unyt_array(v, units, registry=registry)
    return arr


def uintersect1d(arr1, arr2, assume_unique=False):
    """Find the sorted unique elements of the two input arrays.

    A wrapper around numpy.intersect1d that preserves units.  All input arrays
    must have the same units.  See the documentation of numpy.intersect1d for
    full details.

    Examples
    --------
    >>> from unyt import cm
    >>> A = [1, 2, 3]*cm
    >>> B = [2, 3, 4]*cm
    >>> uintersect1d(A, B)
    unyt_array([2., 3.], 'cm')

    """
    v = np.intersect1d(arr1, arr2, assume_unique=assume_unique)
    v = _validate_numpy_wrapper_units(v, [arr1, arr2])
    return v


def uunion1d(arr1, arr2):
    """Find the union of two arrays.

    A wrapper around numpy.intersect1d that preserves units.  All input arrays
    must have the same units.  See the documentation of numpy.intersect1d for
    full details.

    Examples
    --------
    >>> from unyt import cm
    >>> A = [1, 2, 3]*cm
    >>> B = [2, 3, 4]*cm
    >>> uunion1d(A, B)
    unyt_array([1., 2., 3., 4.], 'cm')

    """
    v = np.union1d(arr1, arr2)
    v = _validate_numpy_wrapper_units(v, [arr1, arr2])
    return v


def unorm(data, ord=None, axis=None, keepdims=False):
    """Matrix or vector norm that preserves units

    This is a wrapper around np.linalg.norm that preserves units. See
    the documentation for that function for descriptions of the keyword
    arguments.

    Examples
    --------
    >>> from unyt import km
    >>> data = [1, 2, 3]*km
    >>> print(unorm(data))
    3.7416573867739413 km
    """
    norm = np.linalg.norm(data, ord=ord, axis=axis, keepdims=keepdims)
    if norm.shape == ():
        return unyt_quantity(norm, data.units)
    return unyt_array(norm, data.units)


def udot(op1, op2):
    """Matrix or vector dot product that preserves units

    This is a wrapper around np.dot that preserves units.

    Examples
    --------
    >>> from unyt import km, s
    >>> a = np.eye(2)*km
    >>> b = (np.ones((2, 2)) * 2)*s
    >>> print(udot(a, b))
    [[2. 2.]
     [2. 2.]] km*s
    """
    dot = np.dot(op1.d, op2.d)
    units = op1.units*op2.units
    if dot.shape == ():
        return unyt_quantity(dot, units)
    return unyt_array(dot, units)


def uvstack(arrs):
    """Stack arrays in sequence vertically (row wise) while preserving units

    This is a wrapper around np.vstack that preserves units.

    Examples
    --------
    >>> from unyt import km
    >>> a = [1, 2, 3]*km
    >>> b = [2, 3, 4]*km
    >>> print(uvstack([a, b]))
    [[1. 2. 3.]
     [2. 3. 4.]] km
    """
    v = np.vstack(arrs)
    v = _validate_numpy_wrapper_units(v, arrs)
    return v


def uhstack(arrs):
    """Stack arrays in sequence horizontally while preserving units

    This is a wrapper around np.hstack that preserves units.

    Examples
    --------
    >>> from unyt import km
    >>> a = [1, 2, 3]*km
    >>> b = [2, 3, 4]*km
    >>> print(uhstack([a, b]))
    [1. 2. 3. 2. 3. 4.] km
    >>> a = [[1],[2],[3]]*km
    >>> b = [[2],[3],[4]]*km
    >>> print(uhstack([a, b]))
    [[1. 2.]
     [2. 3.]
     [3. 4.]] km
    """
    v = np.hstack(arrs)
    v = _validate_numpy_wrapper_units(v, arrs)
    return v


def ustack(arrs, axis=0):
    """Join a sequence of arrays along a new axis while preserving units

    The axis parameter specifies the index of the new axis in the
    dimensions of the result. For example, if ``axis=0`` it will be the
    first dimension and if ``axis=-1`` it will be the last dimension.

    This is a wrapper around np.stack that preserves units. See the
    documentation for np.stack for full details.

    """
    v = np.stack(arrs)
    v = _validate_numpy_wrapper_units(v, arrs)
    return v


def _get_binary_op_return_class(cls1, cls2):
    if cls1 is cls2:
        return cls1
    if ((cls1 in (Unit, np.ndarray, np.matrix, np.ma.masked_array) or
         issubclass(cls1, (numeric_type, np.number, list, tuple)))):
        return cls2
    if ((cls2 in (Unit, np.ndarray, np.matrix, np.ma.masked_array) or
         issubclass(cls2, (numeric_type, np.number, list, tuple)))):
        return cls1
    if issubclass(cls1, unyt_quantity):
        return cls2
    if issubclass(cls2, unyt_quantity):
        return cls1
    if issubclass(cls1, cls2):
        return cls1
    if issubclass(cls2, cls1):
        return cls2
    else:
        raise RuntimeError(
            "Undefined operation for a unyt_array subclass. "
            "Received operand types (%s) and (%s)" % (cls1, cls2))


def loadtxt(fname, dtype='float', delimiter='\t', usecols=None, comments='#'):
    r"""
    Load unyt_arrays with unit information from a text file. Each row in the
    text file must have the same number of values.

    Parameters
    ----------
    fname : str
        Filename to read.
    dtype : data-type, optional
        Data-type of the resulting array; default: float.
    delimiter : str, optional
        The string used to separate values.  By default, this is any
        whitespace.
    usecols : sequence, optional
        Which columns to read, with 0 being the first.  For example,
        ``usecols = (1,4,5)`` will extract the 2nd, 5th and 6th columns.
        The default, None, results in all columns being read.
    comments : str, optional
        The character used to indicate the start of a comment;
        default: '#'.

    Examples
    --------
    >>> temp, velx = loadtxt(
    ...    "sphere.dat", usecols=(1,2), delimiter="\t")  # doctest: +SKIP
    """
    f = open(fname, 'r')
    next_one = False
    units = []
    num_cols = -1
    for line in f.readlines():
        words = line.strip().split()
        if len(words) == 0:
            continue
        if line[0] == comments:
            if next_one:
                units = words[1:]
            if len(words) == 2 and words[1] == "Units":
                next_one = True
        else:
            # Here we catch the first line of numbers
            try:
                col_words = line.strip().split(delimiter)
                for word in col_words:
                    float(word)
                num_cols = len(col_words)
                break
            except ValueError:
                pass
    f.close()
    if len(units) != num_cols:
        units = ["dimensionless"]*num_cols
    arrays = np.loadtxt(fname, dtype=dtype, comments=comments,
                        delimiter=delimiter, converters=None,
                        unpack=True, usecols=usecols, ndmin=0)
    if usecols is not None:
        units = [units[col] for col in usecols]
    return tuple([unyt_array(arr, unit) for arr, unit in zip(arrays, units)])


def savetxt(fname, arrays, fmt='%.18e', delimiter='\t', header='',
            footer='', comments='#'):
    r"""
    Write unyt_arrays with unit information to a text file.

    Parameters
    ----------
    fname : str
        The file to write the unyt_arrays to.
    arrays : list of unyt_arrays or single unyt_array
        The array(s) to write to the file.
    fmt : str or sequence of strs, optional
        A single format (%10.5f), or a sequence of formats.
    delimiter : str, optional
        String or character separating columns.
    header : str, optional
        String that will be written at the beginning of the file, before the
        unit header.
    footer : str, optional
        String that will be written at the end of the file.
    comments : str, optional
        String that will be prepended to the ``header`` and ``footer`` strings,
        to mark them as comments. Default: '# ', as expected by e.g.
        ``unyt.loadtxt``.

    Examples
    --------
    >>> import unyt as u
    >>> a = [1, 2, 3]*u.cm
    >>> b = [8, 10, 12]*u.cm/u.s
    >>> c = [2, 85, 9]*u.g
    >>> savetxt("sphere.dat", [a,b,c], header='My sphere stuff',
    ...          delimiter="\t")  # doctest: +SKIP
    """
    if not isinstance(arrays, list):
        arrays = [arrays]
    units = []
    for array in arrays:
        if hasattr(array, "units"):
            units.append(str(array.units))
        else:
            units.append("dimensionless")
    if header != '':
        header += '\n'
    header += " Units\n " + '\t'.join(units)
    np.savetxt(fname, np.transpose(arrays), header=header,
               fmt=fmt, delimiter=delimiter, footer=footer,
               newline='\n', comments=comments)
