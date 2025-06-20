"""
Exception classes for kind cluster operations.

This module contains all the exception classes used by the kind cluster
management functionality.
"""


class KindClusterError(Exception):
    """Base exception for kind cluster operations."""
    pass


class KindClusterCreationError(KindClusterError):
    """Raised when cluster creation fails."""
    pass


class KindClusterDeletionError(KindClusterError):
    """Raised when cluster deletion fails."""
    pass


class KindClusterNotFoundError(KindClusterError):
    """Raised when cluster is not found."""
    pass
