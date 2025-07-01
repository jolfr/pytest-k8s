"""
pytest-k8s: Kubernetes-based testing for pytest

This module serves as the entry point for the pytest-k8s plugin.
When installed, pytest will automatically discover and load this plugin
through the pytest11 entry point defined in pyproject.toml.

The plugin provides fixtures for testing Python applications with
Kubernetes dependencies using kind-based test clusters.
"""

# Import plugin hooks to make them available to pytest
from .plugin import (
    pytest_addoption,
    pytest_configure,
    pytest_unconfigure,
    pytest_sessionstart,
    pytest_sessionfinish,
    pytest_report_header,
)

# Import configuration classes for external use
from .config import KindLoggingConfig, PluginConfig, get_plugin_config, set_plugin_config

# Import kind utilities for external use
from .kind.loggers import KindStreamLogger, KindStdoutLogger, KindStderrLogger, KindLoggerFactory
from .kind.streaming import StreamingSubprocess, create_streaming_subprocess
from .kind.command_runner import KindCommandRunner, KubectlCommandRunner

__all__ = [
    # Plugin hooks
    "pytest_addoption",
    "pytest_configure", 
    "pytest_unconfigure",
    "pytest_sessionstart",
    "pytest_sessionfinish",
    "pytest_report_header",
    
    # Configuration
    "KindLoggingConfig",
    "PluginConfig", 
    "get_plugin_config",
    "set_plugin_config",
    
    # Loggers
    "KindStreamLogger",
    "KindStdoutLogger", 
    "KindStderrLogger",
    "KindLoggerFactory",
    
    # Streaming
    "StreamingSubprocess",
    "create_streaming_subprocess",
    
    # Command runners
    "KindCommandRunner",
    "KubectlCommandRunner",
]

# Plugin fixtures and hooks will be implemented here
# TODO: Implement k8s_cluster fixture
# TODO: Implement k8s_client fixture  
# TODO: Implement k8s_namespace fixture
# TODO: Implement k8s_resource fixture
