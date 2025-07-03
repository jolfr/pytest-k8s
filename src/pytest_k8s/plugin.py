"""
Pytest plugin hooks and configuration for pytest-k8s.

This module provides the pytest plugin integration, including
command-line options, configuration management, and plugin hooks.
"""

import pytest

from .config import PluginConfig, set_plugin_config
from .cleanup import get_cleanup_manager

# Import fixtures to make them available


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
        help="Enable streaming of kind command logs (default: True)",
    )

    group.addoption(
        "--k8s-no-kind-stream-logs",
        action="store_true",
        default=False,
        help="Disable streaming of kind command logs",
    )

    group.addoption(
        "--k8s-kind-log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level for all kind messages (default: INFO)",
    )

    group.addoption(
        "--k8s-kind-log-format",
        default="[KIND] {message}",
        help="Format template for kind log messages (default: '[KIND] {message}')",
    )

    group.addoption(
        "--k8s-kind-include-stream-info",
        action="store_true",
        default=False,
        help="Include stream info (STDOUT/STDERR) in log messages for debugging",
    )

    # Cluster fixture options
    group.addoption(
        "--k8s-cluster-scope",
        default="session",
        choices=["function", "class", "module", "session"],
        help="Default scope for k8s_cluster fixture (default: session)",
    )

    group.addoption(
        "--k8s-cluster-timeout",
        type=int,
        default=300,
        help="Default timeout in seconds for cluster operations (default: 300)",
    )

    group.addoption(
        "--k8s-cluster-keep",
        action="store_true",
        default=False,
        help="Keep clusters after tests complete by default",
    )

    group.addoption(
        "--k8s-no-cluster-keep",
        action="store_true",
        default=False,
        help="Explicitly disable keeping clusters (overrides --k8s-cluster-keep)",
    )

    # Cleanup options
    group.addoption(
        "--k8s-cleanup-on-interrupt",
        action="store_true",
        default=True,
        help="Clean up clusters on interrupt signals (default: True)",
    )

    group.addoption(
        "--k8s-no-cleanup-on-interrupt",
        action="store_true",
        default=False,
        help="Disable cleanup on interrupt signals",
    )

    group.addoption(
        "--k8s-cleanup-orphaned",
        action="store_true",
        default=True,
        help="Clean up orphaned clusters from previous runs (default: True)",
    )

    group.addoption(
        "--k8s-no-cleanup-orphaned",
        action="store_true",
        default=False,
        help="Disable cleanup of orphaned clusters",
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

    # Handle conflicting keep cluster options
    if config.getoption("k8s_no_cluster_keep"):
        config.option.k8s_cluster_keep = False

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
    # Ensure all clusters are cleaned up at session end
    cleanup_manager = get_cleanup_manager()
    cleanup_manager.force_cleanup_all()


@pytest.hookimpl(tryfirst=True)
def pytest_keyboard_interrupt(excinfo) -> None:
    """
    Handle keyboard interrupt (Ctrl+C) by cleaning up clusters.

    Args:
        excinfo: Exception info for the keyboard interrupt
    """
    import logging

    logger = logging.getLogger(__name__)

    logger.info("Keyboard interrupt received, cleaning up clusters...")
    cleanup_manager = get_cleanup_manager()
    cleanup_manager.force_cleanup_all()


@pytest.hookimpl(tryfirst=True)
def pytest_internalerror(excrepr, excinfo) -> None:
    """
    Handle internal pytest errors by cleaning up clusters.

    Args:
        excrepr: Exception representation
        excinfo: Exception info
    """
    import logging

    logger = logging.getLogger(__name__)

    logger.error("Internal pytest error occurred, cleaning up clusters...")
    cleanup_manager = get_cleanup_manager()
    cleanup_manager.force_cleanup_all()


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
    import logging

    plugin_config = get_plugin_config()

    if plugin_config.kind_logging.stream_logs:
        level_name = logging.getLevelName(plugin_config.kind_logging.log_level)
        return f"pytest-k8s: kind log streaming enabled (level: {level_name})"
    else:
        return "pytest-k8s: kind log streaming disabled"
