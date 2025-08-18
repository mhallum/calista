"""Sanity tests for the CALISTA project.
These tests are used to make sure that pytest is working correctly
and that the package can be imported successfully."""

from calista import __version__


def test_version():
    """Test to ensure that the version is correctly set."""
    assert __version__ is not None, "Version should not be None"
    assert isinstance(__version__, str), "Version should be a string"
    assert len(__version__) > 0, "Version string should not be empty"
    print(f"Sanity test passed with version: {__version__}")
