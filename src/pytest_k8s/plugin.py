"""
Pytest plugin hooks and configuration for pytest-k8s.

This module provides the pytest plugin integration, including
command-line options, configuration management, and plugin hooks.
"""

import pytest
from typing import Any

from .config import PluginConfig, set_plugin_config


def pytest_addoption(parser: pytest.Parser) -> None:
    """
    Add command-line options for the pytest-k8s plugin.
    
    Args:
        parser: Pytest argument parser
    """
    group = parser.getgroup("k8s", "Kubernetes testing options")
    
    # Kind logging options
    group.addoption(
        "--k8s-kind-stream-logs",
        action="store_true",
        default=True,
        help="Enable streaming of kind command logs (default: True)"
    )
    
    group.addoption(
        "--k8s-no-kind-stream-logs",
        action="store_true",
        default=False,
        help="Disable streaming of kind command logs"
    )
    
    group.addoption(
        "--k8s-kind-stdout-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level for kind stdout (default: INFO)"
    )
    
    group.addoption(
        "--k8s-kind-stderr-level",
        default="WARNING", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level for kind stderr (default: WARNING)"
    )
    
    group.addoption(
        "--k8s-kind-log-format",
        default="[KIND {stream}] {message}",
        help="Format template for kind log messages (default: '[KIND {stream}] {message}')"
    )


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure the pytest-k8s plugin.
    
    This hook is called after command line options have been parsed
    and all plugins and initial conftest files been loaded.
    
    Args:
        config: Pytest configuration object
    """
    # Handle conflicting stream log options
    if config.getoption("k8s_no_kind_stream_logs"):
        config.option.k8s_kind_stream_logs = False
    
    # Create and set global plugin configuration
    plugin_config = PluginConfig(config)
    set_plugin_config(plugin_config)


def pytest_unconfigure(config: pytest.Config) -> None:
    """
    Clean up plugin resources.
    
    This hook is called before test process is exited.
    
    Args:
        config: Pytest configuration object
    """
    # Any cleanup needed when pytest exits
    pass


def pytest_sessionstart(session: pytest.Session) -> None:
    """
    Called after the Session object has been created.
    
    Args:
        session: Pytest session object
    """
    # Log configuration information if debug logging is enabled
    import logging
    from .config import get_plugin_config
    
    logger = logging.getLogger(__name__)
    config = get_plugin_config()
    
    logger.debug(f"pytest-k8s plugin configured: {config.kind_logging}")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Called after whole test run finished.
    
    Args:
        session: Pytest session object
        exitstatus: Exit status of the test run
    """
    # Any session cleanup needed
    pass


# Plugin metadata
def pytest_report_header(config: pytest.Config) -> str:
    """
    Return a string to be displayed as header info for terminal reporting.
    
    Args:
        config: Pytest configuration object
        
    Returns:
        Header string for pytest output
    """
    from .config import get_plugin_config
    
    plugin_config = get_plugin_config()
    
    if plugin_config.kind_logging.stream_logs:
        return (
            f"pytest-k8s: kind log streaming enabled "
            f"(stdout: {plugin_config.kind_logging.stdout_level}, "
            f"stderr: {plugin_config.kind_logging.stderr_level})"
        )
    else:
        return "pytest-k8s: kind log streaming disabled"
