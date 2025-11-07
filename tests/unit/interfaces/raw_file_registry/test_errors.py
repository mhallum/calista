from calista.interfaces.raw_file_registry import FileAlreadyRegistered

# pylint: disable=magic-value-comparison, too-few-public-methods


class TestFileAlreadyRegisteredError:
    """Tests for the FileAlreadyRegistered error class."""

    @staticmethod
    def test_attributes_assigned_correctly():
        """Test that the FileAlreadyRegistered error attributes are set correctly."""
        error = FileAlreadyRegistered(
            sha256="abc123",
            existing_session_id="session-123",
            requested_session_id="session-456",
        )
        assert error.sha256 == "abc123"
        assert error.existing_session_id == "session-123"
        assert error.requested_session_id == "session-456"

    @staticmethod
    def test_error_message_format():
        """Test that the FileAlreadyRegistered error message is formatted correctly."""
        error = FileAlreadyRegistered(
            sha256="def456",
            existing_session_id="session-789",
            requested_session_id="session-012",
        )
        expected_message = (
            "raw file hash 'def456' already bound to session "
            "'session-789' (requested 'session-012')"
        )
        assert str(error) == expected_message
