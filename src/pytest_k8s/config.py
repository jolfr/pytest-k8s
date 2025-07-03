"""
Configuration management for pytest-k8s plugin.

This module provides configuration classes and utilities for managing
plugin settings, including logging configuration for kind operations.
"""

import logging
from typing import Optional, Any


class KindLoggingConfig:
    """
    Configuration for kind command logging and streaming.

    This class manages the configuration for how kind command output
    is logged and streamed during test execution.
    """

    def __init__(
        self,
        stream_logs: bool = True,
        log_level: str = "INFO",
        log_format: str = "[KIND] {message}",
        include_stream_info: bool = False,
    ):
        """
        Initialize kind logging configuration.

        Args:
            stream_logs: Whether to enable real-time log streaming
            log_level: Log level for all kind messages (DEBUG, INFO, WARNING, ERROR)
            log_format: Format template for log messages
            include_stream_info: Whether to include stream info in log messages
        """
        self.stream_logs = stream_logs
        self.log_level = self._parse_log_level(log_level)
        self.log_format = log_format
        self.include_stream_info = include_stream_info

    @staticmethod
    def _parse_log_level(level: str) -> int:
        """
        Parse string log level to logging constant.

        Args:
            level: Log level as string (DEBUG, INFO, WARNING, ERROR)

        Returns:
            Logging level constant

        Raises:
            ValueError: If log level is invalid
        """
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
        }

        level_upper = level.upper()
        if level_upper not in level_map:
            raise ValueError(
                f"Invalid log level: {level}. "
                f"Must be one of: {', '.join(level_map.keys())}"
            )

        return level_map[level_upper]

    @classmethod
    def from_pytest_config(cls, pytest_config: Any) -> "KindLoggingConfig":
        """
        Create configuration from pytest config object.

        Args:
            pytest_config: Pytest configuration object

        Returns:
            KindLoggingConfig instance
        """
        # Get options using getoption method with defaults
        stream_logs = pytest_config.getoption("k8s_kind_stream_logs", True)
        log_level = pytest_config.getoption("k8s_kind_log_level", "INFO")
        log_format = pytest_config.getoption("k8s_kind_log_format", "[KIND] {message}")
        include_stream_info = pytest_config.getoption(
            "k8s_kind_include_stream_info", False
        )

        return cls(
            stream_logs=stream_logs,
            log_level=log_level,
            log_format=log_format,
            include_stream_info=include_stream_info,
        )

    @classmethod
    def get_default(cls) -> "KindLoggingConfig":
        """
        Get default configuration.

        Returns:
            KindLoggingConfig with default settings
        """
        return cls()

    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"KindLoggingConfig("
            f"stream_logs={self.stream_logs}, "
            f"log_level={logging.getLevelName(self.log_level)}, "
            f"log_format='{self.log_format}', "
            f"include_stream_info={self.include_stream_info}"
            f")"
        )


class ClusterConfig:
    """
    Configuration for cluster fixtures.

    This class manages configuration settings for k8s cluster fixtures.
    """

    def __init__(
        self,
        default_scope: str = "session",
        default_timeout: int = 300,
        default_keep_cluster: bool = False,
    ):
        """
        Initialize cluster configuration.

        Args:
            default_scope: Default scope for k8s_cluster fixture
            default_timeout: Default timeout in seconds for cluster operations
            default_keep_cluster: Default for keeping clusters after tests
        """
        self.default_scope = default_scope
        self.default_timeout = default_timeout
        self.default_keep_cluster = default_keep_cluster

    @classmethod
    def from_pytest_config(cls, pytest_config: Any) -> "ClusterConfig":
        """
        Create configuration from pytest config object.

        Args:
            pytest_config: Pytest configuration object

        Returns:
            ClusterConfig instance
        """
        default_scope = pytest_config.getoption("k8s_cluster_scope", "session")
        default_timeout = pytest_config.getoption("k8s_cluster_timeout", 300)

        # Handle conflicting keep cluster options
        default_keep_cluster = pytest_config.getoption("k8s_cluster_keep", False)
        if pytest_config.getoption("k8s_no_cluster_keep", False):
            default_keep_cluster = False

        return cls(
            default_scope=default_scope,
            default_timeout=default_timeout,
            default_keep_cluster=default_keep_cluster,
        )

    @classmethod
    def get_default(cls) -> "ClusterConfig":
        """
        Get default configuration.

        Returns:
            ClusterConfig with default settings
        """
        return cls()

    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"ClusterConfig("
            f"default_scope='{self.default_scope}', "
            f"default_timeout={self.default_timeout}, "
            f"default_keep_cluster={self.default_keep_cluster}"
            f")"
        )


class PluginConfig:
    """
    Global configuration for the pytest-k8s plugin.

    This class manages all plugin-wide configuration settings
    and provides access to subsystem configurations.
    """

    def __init__(self, pytest_config: Optional[Any] = None):
        """
        Initialize plugin configuration.

        Args:
            pytest_config: Pytest configuration object
        """
        self.pytest_config = pytest_config

        if pytest_config:
            self.kind_logging = KindLoggingConfig.from_pytest_config(pytest_config)
            self.cluster = ClusterConfig.from_pytest_config(pytest_config)
        else:
            self.kind_logging = KindLoggingConfig.get_default()
            self.cluster = ClusterConfig.get_default()

    @classmethod
    def get_default(cls) -> "PluginConfig":
        """
        Get default plugin configuration.

        Returns:
            PluginConfig with default settings
        """
        return cls()


# Global configuration instance
_global_config: Optional[PluginConfig] = None


def get_plugin_config() -> PluginConfig:
    """
    Get the global plugin configuration.

    Returns:
        Current plugin configuration
    """
    global _global_config
    if _global_config is None:
        _global_config = PluginConfig.get_default()
    return _global_config


def set_plugin_config(config: PluginConfig) -> None:
    """
    Set the global plugin configuration.

    Args:
        config: Plugin configuration to set
    """
    global _global_config
    _global_config = config
