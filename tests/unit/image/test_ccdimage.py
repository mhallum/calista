"""Unit tests for CCDImage."""

from collections.abc import Mapping

import numpy as np
import pytest

from calista.image.ccd_image import CCDImage

# pylint: disable=magic-value-comparison


def test_2d_shape_inforced():
    """Test that CCDImage enforces 2D shape for data array."""
    data_1d = np.array([1, 2, 3], dtype=np.float32)
    data_1d.setflags(write=False)  # Make immutable
    with pytest.raises(ValueError, match="CCDImage.data must be a 2D array."):
        CCDImage(data=data_1d)


def test_numeric_dtype_enforced():
    """Test that CCDImage enforces numeric dtype for data array."""
    data_str = np.array([["a", "b"], ["c", "d"]])
    data_str.setflags(write=False)  # Make immutable
    with pytest.raises(ValueError, match="CCDImage.data must have a numeric dtype."):
        CCDImage(data=data_str)


def test_native_endian_enforced():
    """Test that CCDImage enforces native-endian dtype for data array."""
    data_non_native = np.array([[1, 2], [3, 4]], dtype=">i4")  # Big-endian
    data_non_native.setflags(write=False)  # Make immutable
    with pytest.raises(ValueError, match="CCDImage.data must use native-endian dtype."):
        CCDImage(data=data_non_native)


def test_c_contiguous_enforced():
    """Test that CCDImage enforces C-contiguous layout for data array."""
    data_fort = np.asfortranarray(np.array([[1, 2], [3, 4]], dtype=np.float32))
    data_fort.setflags(write=False)  # Make immutable
    with pytest.raises(ValueError, match="CCDImage.data must be C-contiguous."):
        CCDImage(data=data_fort)


def test_mask_shape_enforced():
    """Test that CCDImage enforces mask shape matching data shape."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    mask = np.array([[True, False, True], [False, True, False]])
    data.setflags(write=False)  # Make immutable
    mask.setflags(write=False)  # Make immutable
    with pytest.raises(ValueError, match="Mask shape must match data shape."):
        CCDImage(data=data, mask=mask)


def test_mask_dtype_enforced():
    """Test that CCDImage enforces mask dtype to be bool."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    mask = np.array([[1, 0], [0, 1]], dtype=np.int32)
    data.setflags(write=False)  # Make immutable
    mask.setflags(write=False)  # Make immutable
    with pytest.raises(ValueError, match="Mask dtype must be bool."):
        CCDImage(data=data, mask=mask)  # type: ignore[arg-type]


def test_variance_shape_enforced():
    """Test that CCDImage enforces variance shape matching data shape."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    variance = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]], dtype=np.float32)
    data.setflags(write=False)  # Make immutable
    variance.setflags(write=False)  # Make immutable
    with pytest.raises(ValueError, match="Variance shape must match data shape."):
        CCDImage(data=data, variance=variance)


def test_variance_dtype_enforced():
    """Test that CCDImage enforces variance dtype to be floating-point."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    variance = np.array([[1, 2], [3, 4]], dtype=np.int32)
    data.setflags(write=False)  # Make immutable
    variance.setflags(write=False)  # Make immutable
    with pytest.raises(
        ValueError, match="Variance array must have a floating-point dtype."
    ):
        CCDImage(data=data, variance=variance)


def test_data_immutability_enforced():
    """Test that CCDImage enforces immutability of data, mask, and variance."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)

    with pytest.raises(ValueError, match="CCDImage.data must be immutable."):
        CCDImage(data=data)


def test_mask_immutability_enforced():
    """Test that CCDImage enforces immutability of data, mask, and variance."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    mask = np.array([[True, False], [False, True]], dtype=np.bool_)
    data.setflags(write=False)  # Make immutable

    with pytest.raises(ValueError, match="CCDImage.mask must be immutable."):
        CCDImage(data=data, mask=mask)


def test_variance_immutability_enforced():
    """Test that CCDImage enforces immutability of data, mask, and variance."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    variance = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    data.setflags(write=False)  # Make immutable

    with pytest.raises(ValueError, match="CCDImage.variance must be immutable."):
        CCDImage(data=data, variance=variance)


def test_header_immutable_mapping():
    """Test that CCDImage header is stored as an immutable mapping."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    data.setflags(write=False)  # Make immutable
    header = {"EXPTIME": 30.0, "FILTER": "R"}

    ccd_image = CCDImage(data=data, header=header)

    assert isinstance(ccd_image.header, Mapping)
    with pytest.raises(TypeError):
        # Attempt to modify should fail
        ccd_image.header["NEW_KEY"] = "value"  # type: ignore[index]


def test_happy_path_construction():
    """Test that a valid CCDImage can be constructed successfully."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    mask = np.array([[True, False], [False, True]], dtype=np.bool_)
    variance = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    data.setflags(write=False)  # Make immutable
    mask.setflags(write=False)  # Make immutable
    variance.setflags(write=False)  # Make immutable
    header = {"EXPTIME": 30.0, "FILTER": "R"}

    ccd_image = CCDImage(
        data=data,
        header=header,
        mask=mask,
        variance=variance,
        unit="adu",
    )

    assert np.array_equal(ccd_image.data, data)
    assert ccd_image.header["EXPTIME"] == 30.0
    assert np.array_equal(ccd_image.mask, mask)  # type: ignore[arg-type]
    assert np.array_equal(ccd_image.variance, variance)  # type: ignore[arg-type]
    assert ccd_image.unit == "adu"


def test_copy_with_modifications():
    """Test that copy_with creates a modified copy of the CCDImage."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    data.setflags(write=False)  # Make immutable
    header = {"EXPTIME": 30.0, "FILTER": "R"}

    ccd_image = CCDImage(data=data, header=header)

    new_data = np.array([[5, 6], [7, 8]], dtype=np.float32)
    new_data.setflags(write=False)  # Make immutable
    new_header = {"EXPTIME": 60.0, "FILTER": "G"}

    modified_image = ccd_image.copy_with(data=new_data, header=new_header)

    assert np.array_equal(modified_image.data, new_data)
    assert modified_image.header["EXPTIME"] == 60.0
    # Original remains unchanged
    assert np.array_equal(ccd_image.data, data)
    assert ccd_image.header["EXPTIME"] == 30.0


def test_copy_with_defaults():
    """Test that copy_with without arguments creates an identical copy."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    data.setflags(write=False)  # Make immutable
    header = {"EXPTIME": 30.0, "FILTER": "R"}

    ccd_image = CCDImage(data=data, header=header)

    copied_image = ccd_image.copy_with()

    assert np.array_equal(copied_image.data, ccd_image.data)
    assert copied_image.header == ccd_image.header
    assert copied_image.mask == ccd_image.mask
    assert copied_image.variance == ccd_image.variance
    assert copied_image.unit == ccd_image.unit


def test_with_updated_header():
    """Test that with_updated_header returns a new CCDImage with updated header."""
    data = np.array([[1, 2], [3, 4]], dtype=np.float32)
    data.setflags(write=False)  # Make immutable
    header = {"EXPTIME": 30.0, "FILTER": "R"}

    ccd_image = CCDImage(data=data, header=header)

    updates = {"EXPTIME": 60.0, "OBSERVER": "Alice"}
    updated_image = ccd_image.with_updated_header(updates)

    assert updated_image.header["EXPTIME"] == 60.0
    assert updated_image.header["OBSERVER"] == "Alice"
    assert updated_image.header["FILTER"] == "R"
    # Original remains unchanged
    assert ccd_image.header["EXPTIME"] == 30.0
    assert "OBSERVER" not in ccd_image.header
