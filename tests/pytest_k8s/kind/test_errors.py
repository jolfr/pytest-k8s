"""
Tests for the kind cluster error classes.

This module contains tests for all exception classes used by the kind cluster
management functionality.
"""

import pytest

from pytest_k8s.kind.errors import (
    DockerNotRunningError,
    KindClusterConfigError,
    KindClusterCreationError,
    KindClusterDeletionError,
    KindClusterError,
    KindClusterNotFoundError,
    KindClusterTimeoutError,
    KindClusterValidationError,
    KindNotInstalledError,
)


class TestKindClusterExceptions:
    """Test cases for exception classes."""

    def test_kind_cluster_error_inheritance(self):
        """Test KindClusterError inheritance."""
        error = KindClusterError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_kind_cluster_creation_error_inheritance(self):
        """Test KindClusterCreationError inheritance."""
        error = KindClusterCreationError("Creation failed")
        assert isinstance(error, KindClusterError)
        assert isinstance(error, Exception)
        assert str(error) == "Creation failed"

    def test_kind_cluster_deletion_error_inheritance(self):
        """Test KindClusterDeletionError inheritance."""
        error = KindClusterDeletionError("Deletion failed")
        assert isinstance(error, KindClusterError)
        assert isinstance(error, Exception)
        assert str(error) == "Deletion failed"

    def test_kind_cluster_not_found_error_inheritance(self):
        """Test KindClusterNotFoundError inheritance."""
        error = KindClusterNotFoundError("Cluster not found")
        assert isinstance(error, KindClusterError)
        assert isinstance(error, Exception)
        assert str(error) == "Cluster not found"

    def test_error_messages(self):
        """Test error messages are properly stored."""
        test_message = "This is a test error message"

        errors = [
            KindClusterError(test_message),
            KindClusterCreationError(test_message),
            KindClusterDeletionError(test_message),
            KindClusterNotFoundError(test_message),
        ]

        for error in errors:
            assert str(error) == test_message

    def test_error_creation_without_message(self):
        """Test error creation with no message."""
        errors = [
            KindClusterError(),
            KindClusterCreationError(),
            KindClusterDeletionError(),
            KindClusterNotFoundError(),
        ]

        for error in errors:
            assert str(error) == ""

    def test_error_with_exception_args(self):
        """Test errors with message and recovery suggestion."""
        message = "Test error message"
        recovery = "Try this recovery step"

        error = KindClusterError(message, recovery)
        assert error.message == message
        assert error.recovery_suggestion == recovery
        assert recovery in str(error)

        creation_error = KindClusterCreationError(message, recovery)
        assert creation_error.message == message
        assert creation_error.recovery_suggestion == recovery

        deletion_error = KindClusterDeletionError(message, recovery)
        assert deletion_error.message == message
        assert deletion_error.recovery_suggestion == recovery

        not_found_error = KindClusterNotFoundError(message, recovery)
        assert not_found_error.message == message
        assert not_found_error.recovery_suggestion == recovery

    def test_raise_and_catch_errors(self):
        """Test raising and catching errors."""
        # Test base error
        with pytest.raises(KindClusterError):
            raise KindClusterError("Base error")

        # Test creation error
        with pytest.raises(KindClusterCreationError):
            raise KindClusterCreationError("Creation error")

        with pytest.raises(KindClusterError):  # Should also catch base class
            raise KindClusterCreationError("Creation error")

        # Test deletion error
        with pytest.raises(KindClusterDeletionError):
            raise KindClusterDeletionError("Deletion error")

        with pytest.raises(KindClusterError):  # Should also catch base class
            raise KindClusterDeletionError("Deletion error")

        # Test not found error
        with pytest.raises(KindClusterNotFoundError):
            raise KindClusterNotFoundError("Not found error")

        with pytest.raises(KindClusterError):  # Should also catch base class
            raise KindClusterNotFoundError("Not found error")

    def test_error_hierarchy(self):
        """Test the error class hierarchy."""
        # All specific errors should be instances of KindClusterError
        creation_error = KindClusterCreationError("test")
        deletion_error = KindClusterDeletionError("test")
        not_found_error = KindClusterNotFoundError("test")

        assert isinstance(creation_error, KindClusterError)
        assert isinstance(deletion_error, KindClusterError)
        assert isinstance(not_found_error, KindClusterError)

        # All errors should be instances of Exception
        base_error = KindClusterError("test")
        assert isinstance(base_error, Exception)
        assert isinstance(creation_error, Exception)
        assert isinstance(deletion_error, Exception)
        assert isinstance(not_found_error, Exception)

        # Specific errors should not be instances of each other
        assert not isinstance(creation_error, KindClusterDeletionError)
        assert not isinstance(creation_error, KindClusterNotFoundError)
        assert not isinstance(deletion_error, KindClusterCreationError)
        assert not isinstance(deletion_error, KindClusterNotFoundError)
        assert not isinstance(not_found_error, KindClusterCreationError)
        assert not isinstance(not_found_error, KindClusterDeletionError)


class TestKindNotInstalledError:
    """Test cases for KindNotInstalledError."""

    def test_default_initialization(self):
        """Test KindNotInstalledError with default message."""
        error = KindNotInstalledError()

        assert isinstance(error, KindClusterError)
        assert error.message == "kind command not available"
        assert (
            error.recovery_suggestion
            == "Install kind from https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
        )
        assert "kind command not available" in str(error)
        assert "Install kind from" in str(error)

    def test_custom_message(self):
        """Test KindNotInstalledError with custom message."""
        custom_message = "Custom kind error message"
        error = KindNotInstalledError(custom_message)

        assert error.message == custom_message
        assert (
            error.recovery_suggestion
            == "Install kind from https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
        )
        assert custom_message in str(error)
        assert "Install kind from" in str(error)

    def test_inheritance(self):
        """Test KindNotInstalledError inheritance."""
        error = KindNotInstalledError()

        assert isinstance(error, KindClusterError)
        assert isinstance(error, Exception)

    def test_raise_and_catch(self):
        """Test raising and catching KindNotInstalledError."""
        with pytest.raises(KindNotInstalledError):
            raise KindNotInstalledError("kind not found")

        with pytest.raises(KindClusterError):  # Should also catch base class
            raise KindNotInstalledError("kind not found")


class TestDockerNotRunningError:
    """Test cases for DockerNotRunningError."""

    def test_default_initialization(self):
        """Test DockerNotRunningError with default message."""
        error = DockerNotRunningError()

        assert isinstance(error, KindClusterError)
        assert error.message == "Docker not available or not running"
        assert (
            error.recovery_suggestion
            == "Start Docker Desktop or Docker daemon, or install Docker from https://docs.docker.com/get-docker/"
        )
        assert "Docker not available" in str(error)
        assert "Start Docker Desktop" in str(error)

    def test_custom_message(self):
        """Test DockerNotRunningError with custom message."""
        custom_message = "Custom Docker error message"
        error = DockerNotRunningError(custom_message)

        assert error.message == custom_message
        assert (
            error.recovery_suggestion
            == "Start Docker Desktop or Docker daemon, or install Docker from https://docs.docker.com/get-docker/"
        )
        assert custom_message in str(error)
        assert "Start Docker Desktop" in str(error)

    def test_inheritance(self):
        """Test DockerNotRunningError inheritance."""
        error = DockerNotRunningError()

        assert isinstance(error, KindClusterError)
        assert isinstance(error, Exception)

    def test_raise_and_catch(self):
        """Test raising and catching DockerNotRunningError."""
        with pytest.raises(DockerNotRunningError):
            raise DockerNotRunningError("Docker not running")

        with pytest.raises(KindClusterError):  # Should also catch base class
            raise DockerNotRunningError("Docker not running")


class TestKindClusterTimeoutError:
    """Test cases for KindClusterTimeoutError."""

    def test_initialization_with_timeout(self):
        """Test KindClusterTimeoutError initialization."""
        message = "Operation timed out"
        timeout = 300
        error = KindClusterTimeoutError(message, timeout)

        assert isinstance(error, KindClusterError)
        assert error.message == message
        assert error.timeout == timeout
        assert (
            error.recovery_suggestion
            == f"Try increasing the timeout value (currently {timeout} seconds) or check system resources"
        )
        assert message in str(error)
        assert str(timeout) in str(error)
        assert "Try increasing the timeout" in str(error)

    def test_different_timeout_values(self):
        """Test KindClusterTimeoutError with different timeout values."""
        test_cases = [
            (30, "currently 30 seconds"),
            (600, "currently 600 seconds"),
            (0, "currently 0 seconds"),
            (3600, "currently 3600 seconds"),
        ]

        for timeout, expected_text in test_cases:
            error = KindClusterTimeoutError("Test timeout", timeout)
            assert error.timeout == timeout
            assert expected_text in str(error)

    def test_inheritance(self):
        """Test KindClusterTimeoutError inheritance."""
        error = KindClusterTimeoutError("timeout", 60)

        assert isinstance(error, KindClusterError)
        assert isinstance(error, Exception)

    def test_raise_and_catch(self):
        """Test raising and catching KindClusterTimeoutError."""
        with pytest.raises(KindClusterTimeoutError):
            raise KindClusterTimeoutError("timeout error", 120)

        with pytest.raises(KindClusterError):  # Should also catch base class
            raise KindClusterTimeoutError("timeout error", 120)

    def test_timeout_attribute_access(self):
        """Test direct access to timeout attribute."""
        timeout_value = 180
        error = KindClusterTimeoutError("test", timeout_value)

        # Test direct attribute access
        assert hasattr(error, "timeout")
        assert error.timeout == timeout_value

        # Test that timeout is part of the error state
        assert error.timeout != 200  # Different value
        assert error.timeout == 180  # Original value


class TestKindClusterConfigError:
    """Test cases for KindClusterConfigError."""

    def test_initialization(self):
        """Test KindClusterConfigError initialization."""
        message = "Invalid configuration"
        error = KindClusterConfigError(message)

        assert isinstance(error, KindClusterError)
        assert error.message == message
        assert str(error) == message

    def test_inheritance(self):
        """Test KindClusterConfigError inheritance."""
        error = KindClusterConfigError("config error")

        assert isinstance(error, KindClusterError)
        assert isinstance(error, Exception)

    def test_with_recovery_suggestion(self):
        """Test KindClusterConfigError with recovery suggestion."""
        message = "Invalid port mapping"
        recovery = "Check port ranges and conflicts"
        error = KindClusterConfigError(message, recovery)

        assert error.message == message
        assert error.recovery_suggestion == recovery
        assert message in str(error)
        assert recovery in str(error)

    def test_raise_and_catch(self):
        """Test raising and catching KindClusterConfigError."""
        with pytest.raises(KindClusterConfigError):
            raise KindClusterConfigError("config error")

        with pytest.raises(KindClusterError):  # Should also catch base class
            raise KindClusterConfigError("config error")


class TestKindClusterValidationError:
    """Test cases for KindClusterValidationError."""

    def test_initialization(self):
        """Test KindClusterValidationError initialization."""
        message = "Cluster validation failed"
        error = KindClusterValidationError(message)

        assert isinstance(error, KindClusterError)
        assert error.message == message
        assert str(error) == message

    def test_inheritance(self):
        """Test KindClusterValidationError inheritance."""
        error = KindClusterValidationError("validation error")

        assert isinstance(error, KindClusterError)
        assert isinstance(error, Exception)

    def test_with_recovery_suggestion(self):
        """Test KindClusterValidationError with recovery suggestion."""
        message = "Node not ready"
        recovery = "Wait for cluster to stabilize or check node status"
        error = KindClusterValidationError(message, recovery)

        assert error.message == message
        assert error.recovery_suggestion == recovery
        assert message in str(error)
        assert recovery in str(error)

    def test_raise_and_catch(self):
        """Test raising and catching KindClusterValidationError."""
        with pytest.raises(KindClusterValidationError):
            raise KindClusterValidationError("validation error")

        with pytest.raises(KindClusterError):  # Should also catch base class
            raise KindClusterValidationError("validation error")


class TestCompleteErrorHierarchy:
    """Test complete error hierarchy and relationships."""

    def test_all_errors_inherit_from_base(self):
        """Test that all error types inherit from KindClusterError."""
        errors = [
            KindClusterError("test"),
            KindClusterCreationError("test"),
            KindClusterDeletionError("test"),
            KindClusterNotFoundError("test"),
            KindNotInstalledError("test"),
            DockerNotRunningError("test"),
            KindClusterTimeoutError("test", 60),
            KindClusterConfigError("test"),
            KindClusterValidationError("test"),
        ]

        for error in errors:
            assert isinstance(error, KindClusterError)
            assert isinstance(error, Exception)

    def test_error_type_distinctness(self):
        """Test that different error types are distinct."""
        errors = [
            KindClusterCreationError("test"),
            KindClusterDeletionError("test"),
            KindClusterNotFoundError("test"),
            KindNotInstalledError("test"),
            DockerNotRunningError("test"),
            KindClusterTimeoutError("test", 60),
            KindClusterConfigError("test"),
            KindClusterValidationError("test"),
        ]

        # Each error should not be an instance of any other specific error type
        for i, error1 in enumerate(errors):
            for j, error2 in enumerate(errors):
                if i != j:
                    assert not isinstance(error1, type(error2))

    def test_all_errors_with_recovery_suggestions(self):
        """Test that all errors can have recovery suggestions."""
        recovery = "Test recovery suggestion"

        errors = [
            KindClusterError("test", recovery),
            KindClusterCreationError("test", recovery),
            KindClusterDeletionError("test", recovery),
            KindClusterNotFoundError("test", recovery),
            KindClusterConfigError("test", recovery),
            KindClusterValidationError("test", recovery),
        ]

        for error in errors:
            assert error.recovery_suggestion == recovery
            assert recovery in str(error)

    def test_error_message_formatting(self):
        """Test error message formatting consistency."""
        message = "Test error message"
        recovery = "Test recovery"

        # Test without recovery suggestion
        error_no_recovery = KindClusterError(message)
        assert str(error_no_recovery) == message

        # Test with recovery suggestion
        error_with_recovery = KindClusterError(message, recovery)
        expected_formatted = f"{message}\nRecovery suggestion: {recovery}"
        assert str(error_with_recovery) == expected_formatted

    def test_empty_message_handling(self):
        """Test handling of empty messages."""
        # Test all error types with empty messages
        errors = [
            KindClusterError(""),
            KindClusterCreationError(""),
            KindClusterDeletionError(""),
            KindClusterNotFoundError(""),
            KindClusterConfigError(""),
            KindClusterValidationError(""),
        ]

        for error in errors:
            assert error.message == ""
            # Without recovery suggestion, should just be empty
            if not error.recovery_suggestion:
                assert str(error) == ""

    def test_special_character_handling(self):
        """Test error handling with special characters."""
        special_chars = [
            "Error with 🚀 emoji",
            "Error with \n newline",
            "Error with \t tab",
            "Error with 'quotes'",
            'Error with "double quotes"',
            "Error with unicode: 测试",
        ]

        for message in special_chars:
            error = KindClusterError(message)
            assert error.message == message
            assert message in str(error)
