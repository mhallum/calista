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

# pylint: disable=too-many-arguments,magic-value-comparison

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
        data: Array2D | None = None,
        header: Mapping[str, object] | None = None,
        mask: npt.NDArray[np.bool_] | None = None,
        variance: Array2D | None = None,
        unit: str | None = None,
    ) -> CCDImage:
        """Create a copy of this CCDImage with optional modifications.

        Args:
            data (Array2D | None): New data array, or None to keep existing.
            header (Mapping[str, object] | None): New header mapping, or None to keep existing.
            mask (npt.NDArray[np.bool_] | None): New mask array, or None to keep existing.
            variance (Array2D | None): New variance array, or None to keep existing.
            unit (str | None): New unit string, or None to keep existing.
        """

        return CCDImage(
            data=data if data is not None else self.data,
            header=header if header is not None else self.header,
            mask=mask if mask is not None else self.mask,
            variance=variance if variance is not None else self.variance,
            unit=unit if unit is not None else self.unit,
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
