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
        stdout_level: str = "INFO",
        stderr_level: str = "WARNING",
        log_format: str = "[KIND {stream}] {message}",
    ):
        """
        Initialize kind logging configuration.
        
        Args:
            stream_logs: Whether to enable real-time log streaming
            stdout_level: Log level for stdout messages (DEBUG, INFO, WARNING, ERROR)
            stderr_level: Log level for stderr messages (DEBUG, INFO, WARNING, ERROR)
            log_format: Format template for log messages
        """
        self.stream_logs = stream_logs
        self.stdout_level = self._parse_log_level(stdout_level)
        self.stderr_level = self._parse_log_level(stderr_level)
        self.log_format = log_format
    
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
        stdout_level = pytest_config.getoption("k8s_kind_stdout_level", "INFO")
        stderr_level = pytest_config.getoption("k8s_kind_stderr_level", "WARNING")
        log_format = pytest_config.getoption("k8s_kind_log_format", "[KIND {stream}] {message}")
        
        return cls(
            stream_logs=stream_logs,
            stdout_level=stdout_level,
            stderr_level=stderr_level,
            log_format=log_format,
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
            f"stdout_level={logging.getLevelName(self.stdout_level)}, "
            f"stderr_level={logging.getLevelName(self.stderr_level)}, "
            f"log_format='{self.log_format}'"
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
        else:
            self.kind_logging = KindLoggingConfig.get_default()
    
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
