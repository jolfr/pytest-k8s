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
from .config import (
    KindLoggingConfig,
    ClusterConfig,
    PluginConfig,
    get_plugin_config,
    set_plugin_config,
)

# Import kind utilities for external use
from .kind.loggers import KindLogger, KindLoggerFactory, get_kind_logger
from .kind.streaming import StreamingSubprocess, create_streaming_subprocess
from .kind.command_runner import KindCommandRunner, KubectlCommandRunner

# Import fixtures for external use
from .fixtures import (
    k8s_cluster,
    ClusterFixtureManager,
    KubernetesClient,
    k8s_client,
)

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
    "ClusterConfig",
    "PluginConfig",
    "get_plugin_config",
    "set_plugin_config",
    # Loggers
    "KindLogger",
    "KindLoggerFactory",
    "get_kind_logger",
    # Streaming
    "StreamingSubprocess",
    "create_streaming_subprocess",
    # Command runners
    "KindCommandRunner",
    "KubectlCommandRunner",
    # Fixtures
    "k8s_cluster",
    "ClusterFixtureManager",
    "KubernetesClient",
    "k8s_client",
]
