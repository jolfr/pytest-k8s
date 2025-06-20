"""
Tests for the kind cluster error classes.

This module contains tests for all exception classes used by the kind cluster
management functionality.
"""

import pytest

from pytest_kubernetes.kind.errors import (
    KindClusterError,
    KindClusterCreationError,
    KindClusterDeletionError,
    KindClusterNotFoundError,
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
        """Test error creation with empty message."""
        errors = [
            KindClusterError(""),
            KindClusterCreationError(""),
            KindClusterDeletionError(""),
            KindClusterNotFoundError(""),
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
