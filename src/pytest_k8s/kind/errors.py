"""
Exception classes for kind cluster operations.

This module contains all the exception classes used by the kind cluster
management functionality.
"""

from typing import Optional


class KindClusterError(Exception):
    """
    Base exception for kind cluster operations.

    Attributes:
        message: The error message
        recovery_suggestion: Optional suggestion for recovery
    """

    def __init__(self, message: str = "", recovery_suggestion: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.recovery_suggestion = recovery_suggestion

    def __str__(self) -> str:
        """Return formatted error message with recovery suggestion if available."""
        if self.recovery_suggestion:
            return f"{self.message}\nRecovery suggestion: {self.recovery_suggestion}"
        return self.message


class KindClusterCreationError(KindClusterError):
    """Raised when cluster creation fails."""

    pass


class KindClusterDeletionError(KindClusterError):
    """Raised when cluster deletion fails."""

    pass


class KindClusterNotFoundError(KindClusterError):
    """Raised when cluster is not found."""

    pass


class KindNotInstalledError(KindClusterError):
    """Raised when kind is not installed or not available."""

    def __init__(self, message: str = "kind command not available"):
        super().__init__(
            message,
            "Install kind from https://kind.sigs.k8s.io/docs/user/quick-start/#installation",
        )


class DockerNotRunningError(KindClusterError):
    """Raised when Docker is not running or not available."""

    def __init__(self, message: str = "Docker not available or not running"):
        super().__init__(
            message,
            "Start Docker Desktop or Docker daemon, or install Docker from https://docs.docker.com/get-docker/",
        )


class KindClusterTimeoutError(KindClusterError):
    """Raised when cluster operations timeout."""

    def __init__(self, message: str, timeout: int):
        super().__init__(
            message,
            f"Try increasing the timeout value (currently {timeout} seconds) or check system resources",
        )
        self.timeout = timeout


class KindClusterConfigError(KindClusterError):
    """Raised when cluster configuration is invalid."""

    pass


class KindClusterValidationError(KindClusterError):
    """Raised when cluster validation fails."""

    pass
