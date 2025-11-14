"""Immutable representation of a CCD image with associated metadata.

The CCDImage class encapsulates a 2D numeric data array along with optional
header metadata, mask, variance, and unit information. The class ensures that
the data array is immutable, C-contiguous, and uses a native-endian dtype.
It also provides methods to create modified copies of the image with updated
fields while preserving immutability.

Note:
    This module requires numpy to be installed.
    Masks use the convention where True indicates bad pixels.

"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
import numpy.typing as npt

# pylint: disable=too-many-arguments,magic-value-comparison,too-few-public-methods


class _CopySentinel:
    __slots__ = ()


_COPY = _CopySentinel()

# Type alias for a numeric ndarray; 2D shape is enforced at runtime, not by the type system.
Array2D = npt.NDArray[np.number]


@dataclass(frozen=True, slots=True)
class CCDImage:
    """Immutable representation of a CCD image with associated metadata."""

    data: Array2D  # np.ndarray, shape (ny, nx)
    header: Mapping[str, object] = field(default_factory=dict)
    mask: npt.NDArray[np.bool_] | None = None  # True for bad pixels
    variance: Array2D | None = None
    unit: str | None = None

    def __post_init__(self):
        """Validate the CCDImage fields after initialization."""

        self._validate_data()
        self._validate_mask()
        self._validate_variance()

        # ensure header is an immutable mapping
        # copy to decouple from any external dict / astropy.Header
        hdr = dict(self.header)
        object.__setattr__(self, "header", MappingProxyType(hdr))

    def copy_with(
        self,
        *,
        data: Array2D | _CopySentinel = _COPY,
        header: Mapping[str, object] | _CopySentinel = _COPY,
        mask: npt.NDArray[np.bool_] | None | _CopySentinel = _COPY,
        variance: Array2D | None | _CopySentinel = _COPY,
        unit: str | None | _CopySentinel = _COPY,
    ) -> CCDImage:
        """Create a copy of this CCDImage with optional modifications.

        Values not provided will be copied from the existing instance.

        Example:
            # Create a new CCDImage with updated data and unit, everything else copied
            new_image = old_image.copy_with(data=new_data_array, unit="adu")
            # Create a new CCDImage with the mask cleared (set to None)
            new_image = old_image.copy_with(mask=None)
        """

        def _resolve(field_value, current_value):
            return current_value if field_value is _COPY else field_value

        return CCDImage(
            data=_resolve(data, self.data),
            header=_resolve(header, self.header),
            mask=_resolve(mask, self.mask),
            variance=_resolve(variance, self.variance),
            unit=_resolve(unit, self.unit),
        )

    def with_updated_header(self, updates: Mapping[str, object]) -> CCDImage:
        """Return a new CCDImage with updated header entries.

        Args:
            updates (Mapping[str, object]): Header entries to add or update.

        Returns:
            CCDImage: A new CCDImage instance with the updated header.
        """

        new_header = dict(self.header)
        new_header.update(updates)
        return self.copy_with(header=new_header)

    # --- Internals ---

    def _validate_data(self) -> None:
        """Validate the data array.

        Validate the data array to ensure it is a 2D numeric array with native-endian
        dtype, C-contiguous memory layout, and immutability.
        """

        if self.data.ndim != 2:
            raise ValueError("CCDImage.data must be a 2D array.")
        if not np.issubdtype(self.data.dtype, np.number):
            raise ValueError("CCDImage.data must have a numeric dtype.")
        if not self.data.dtype.isnative:
            raise ValueError("CCDImage.data must use native-endian dtype.")
        if not self.data.flags["C_CONTIGUOUS"]:
            raise ValueError("CCDImage.data must be C-contiguous.")
        if self.data.flags.writeable:
            raise ValueError("CCDImage.data must be immutable.")

    def _validate_mask(self) -> None:
        """Validate the mask array if it exists.

        Validate the mask array if it exists. The mask array must have the same shape
        as the data array, must have a boolean dtype, and must be immutable.
        """

        if self.mask is not None:
            if self.mask.shape != self.data.shape:
                raise ValueError("Mask shape must match data shape.")
            if self.mask.dtype != np.bool_:
                raise ValueError("Mask dtype must be bool.")
            if self.mask.flags.writeable:
                raise ValueError("CCDImage.mask must be immutable.")

    def _validate_variance(self) -> None:
        """Validate the variance array if it exists.

        Validate the variance array if it exists. The variance array must have the same shape
        as the data array, must have a floating-point dtype, and must be immutable.

        Raises:
            ValueError: If the variance array does not meet the required conditions.
        """

        if self.variance is not None:
            if self.variance.shape != self.data.shape:
                raise ValueError("Variance shape must match data shape.")
            if not np.issubdtype(self.variance.dtype, np.floating):
                raise ValueError("Variance array must have a floating-point dtype.")
            if self.variance.flags.writeable:
                raise ValueError("CCDImage.variance must be immutable.")
