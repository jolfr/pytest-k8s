"""
Tests for configuration management.

This module tests the configuration classes and utilities for the pytest-k8s plugin.
"""

import logging
import pytest
from unittest.mock import Mock

from pytest_k8s.config import (
    KindLoggingConfig,
    ClusterConfig,
    PluginConfig,
    get_plugin_config,
    set_plugin_config,
)


class TestKindLoggingConfig:
    """Test the KindLoggingConfig class."""

    def test_init_defaults(self):
        """Test default initialization."""
        config = KindLoggingConfig()

        assert config.stream_logs is True
        assert config.log_level == logging.INFO
        assert config.log_format == "[KIND] {message}"
        assert config.include_stream_info is False

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        config = KindLoggingConfig(
            stream_logs=False,
            log_level="DEBUG",
            log_format="[CUSTOM] {message}",
            include_stream_info=True,
        )

        assert config.stream_logs is False
        assert config.log_level == logging.DEBUG
        assert config.log_format == "[CUSTOM] {message}"
        assert config.include_stream_info is True

    def test_parse_log_level_valid(self):
        """Test parsing valid log levels."""
        assert KindLoggingConfig._parse_log_level("DEBUG") == logging.DEBUG
        assert KindLoggingConfig._parse_log_level("INFO") == logging.INFO
        assert KindLoggingConfig._parse_log_level("WARNING") == logging.WARNING
        assert KindLoggingConfig._parse_log_level("ERROR") == logging.ERROR

        # Test case insensitivity
        assert KindLoggingConfig._parse_log_level("debug") == logging.DEBUG
        assert KindLoggingConfig._parse_log_level("info") == logging.INFO
        assert KindLoggingConfig._parse_log_level("warning") == logging.WARNING
        assert KindLoggingConfig._parse_log_level("error") == logging.ERROR

    def test_parse_log_level_invalid(self):
        """Test parsing invalid log levels."""
        with pytest.raises(ValueError, match="Invalid log level"):
            KindLoggingConfig._parse_log_level("INVALID")

        with pytest.raises(ValueError, match="Invalid log level"):
            KindLoggingConfig._parse_log_level("CRITICAL")

        with pytest.raises(ValueError, match="Invalid log level"):
            KindLoggingConfig._parse_log_level("")

    def test_from_pytest_config(self):
        """Test creating config from pytest config object."""
        # Mock pytest config
        mock_config = Mock()
        mock_config.getoption.side_effect = lambda key, default: {
            "k8s_kind_stream_logs": False,
            "k8s_kind_log_level": "DEBUG",
            "k8s_kind_log_format": "[TEST] {message}",
            "k8s_kind_include_stream_info": True,
        }.get(key, default)

        config = KindLoggingConfig.from_pytest_config(mock_config)

        assert config.stream_logs is False
        assert config.log_level == logging.DEBUG
        assert config.log_format == "[TEST] {message}"
        assert config.include_stream_info is True

        # Verify getoption was called with correct keys
        mock_config.getoption.assert_any_call("k8s_kind_stream_logs", True)
        mock_config.getoption.assert_any_call("k8s_kind_log_level", "INFO")
        mock_config.getoption.assert_any_call("k8s_kind_log_format", "[KIND] {message}")
        mock_config.getoption.assert_any_call("k8s_kind_include_stream_info", False)

    def test_from_pytest_config_defaults(self):
        """Test creating config from pytest config with defaults."""
        # Mock pytest config that returns defaults
        mock_config = Mock()
        mock_config.getoption.side_effect = lambda key, default: default

        config = KindLoggingConfig.from_pytest_config(mock_config)

        assert config.stream_logs is True
        assert config.log_level == logging.INFO
        assert config.log_format == "[KIND] {message}"
        assert config.include_stream_info is False

    def test_get_default(self):
        """Test getting default configuration."""
        config = KindLoggingConfig.get_default()

        assert config.stream_logs is True
        assert config.log_level == logging.INFO
        assert config.log_format == "[KIND] {message}"
        assert config.include_stream_info is False

    def test_repr(self):
        """Test string representation."""
        config = KindLoggingConfig(
            stream_logs=False, log_level="DEBUG", include_stream_info=True
        )

        repr_str = repr(config)

        assert "KindLoggingConfig" in repr_str
        assert "stream_logs=False" in repr_str
        assert "log_level=DEBUG" in repr_str
        assert "include_stream_info=True" in repr_str
        assert "log_format=" in repr_str


class TestClusterConfig:
    """Test the ClusterConfig class."""

    def test_init_defaults(self):
        """Test default initialization."""
        config = ClusterConfig()

        assert config.default_scope == "session"
        assert config.default_timeout == 300
        assert config.default_keep_cluster is False

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        config = ClusterConfig(
            default_scope="function",
            default_timeout=600,
            default_keep_cluster=True,
        )

        assert config.default_scope == "function"
        assert config.default_timeout == 600
        assert config.default_keep_cluster is True

    def test_from_pytest_config(self):
        """Test creating config from pytest config object."""
        # Mock pytest config
        mock_config = Mock()
        mock_config.getoption.side_effect = lambda key, default: {
            "k8s_cluster_scope": "module",
            "k8s_cluster_timeout": 600,
            "k8s_cluster_keep": True,
            "k8s_no_cluster_keep": False,
        }.get(key, default)

        config = ClusterConfig.from_pytest_config(mock_config)

        assert config.default_scope == "module"
        assert config.default_timeout == 600
        assert config.default_keep_cluster is True

        # Verify getoption was called with correct keys
        mock_config.getoption.assert_any_call("k8s_cluster_scope", "session")
        mock_config.getoption.assert_any_call("k8s_cluster_timeout", 300)
        mock_config.getoption.assert_any_call("k8s_cluster_keep", False)
        mock_config.getoption.assert_any_call("k8s_no_cluster_keep", False)

    def test_from_pytest_config_no_cluster_keep_override(self):
        """Test that --k8s-no-cluster-keep overrides --k8s-cluster-keep."""
        # Mock pytest config
        mock_config = Mock()
        mock_config.getoption.side_effect = lambda key, default: {
            "k8s_cluster_scope": "session",
            "k8s_cluster_timeout": 300,
            "k8s_cluster_keep": True,  # This should be overridden
            "k8s_no_cluster_keep": True,  # This overrides the above
        }.get(key, default)

        config = ClusterConfig.from_pytest_config(mock_config)

        assert config.default_keep_cluster is False

    def test_from_pytest_config_defaults(self):
        """Test creating config from pytest config with defaults."""
        # Mock pytest config that returns defaults
        mock_config = Mock()
        mock_config.getoption.side_effect = lambda key, default: default

        config = ClusterConfig.from_pytest_config(mock_config)

        assert config.default_scope == "session"
        assert config.default_timeout == 300
        assert config.default_keep_cluster is False

    def test_get_default(self):
        """Test getting default configuration."""
        config = ClusterConfig.get_default()

        assert config.default_scope == "session"
        assert config.default_timeout == 300
        assert config.default_keep_cluster is False

    def test_repr(self):
        """Test string representation."""
        config = ClusterConfig(
            default_scope="function",
            default_timeout=600,
            default_keep_cluster=True,
        )

        repr_str = repr(config)

        assert "ClusterConfig" in repr_str
        assert "default_scope='function'" in repr_str
        assert "default_timeout=600" in repr_str
        assert "default_keep_cluster=True" in repr_str


class TestPluginConfig:
    """Test the PluginConfig class."""

    def test_init_without_pytest_config(self):
        """Test initialization without pytest config."""
        config = PluginConfig()

        assert config.pytest_config is None
        assert isinstance(config.kind_logging, KindLoggingConfig)
        assert config.kind_logging.stream_logs is True
        assert isinstance(config.cluster, ClusterConfig)
        assert config.cluster.default_scope == "session"
        assert config.cluster.default_timeout == 300
        assert config.cluster.default_keep_cluster is False

    def test_init_with_pytest_config(self):
        """Test initialization with pytest config."""
        # Mock pytest config
        mock_pytest_config = Mock()
        mock_pytest_config.getoption.side_effect = lambda key, default: {
            "k8s_kind_stream_logs": False,
            "k8s_kind_log_level": "DEBUG",
            "k8s_kind_log_format": "[TEST] {message}",
            "k8s_kind_include_stream_info": True,
        }.get(key, default)

        config = PluginConfig(mock_pytest_config)

        assert config.pytest_config is mock_pytest_config
        assert isinstance(config.kind_logging, KindLoggingConfig)
        assert config.kind_logging.stream_logs is False
        assert config.kind_logging.log_level == logging.DEBUG

    def test_get_default(self):
        """Test getting default plugin configuration."""
        config = PluginConfig.get_default()

        assert config.pytest_config is None
        assert isinstance(config.kind_logging, KindLoggingConfig)
        assert config.kind_logging.stream_logs is True


class TestGlobalConfig:
    """Test global configuration management."""

    def test_get_plugin_config_default(self):
        """Test getting default plugin config."""
        # Reset global config
        set_plugin_config(None)

        config = get_plugin_config()

        assert isinstance(config, PluginConfig)
        assert config.pytest_config is None
        assert config.kind_logging.stream_logs is True

    def test_set_and_get_plugin_config(self):
        """Test setting and getting plugin config."""
        # Create custom config
        custom_config = PluginConfig()
        custom_config.kind_logging.stream_logs = False

        # Set the config
        set_plugin_config(custom_config)

        # Get the config
        retrieved_config = get_plugin_config()

        assert retrieved_config is custom_config
        assert retrieved_config.kind_logging.stream_logs is False

    def test_global_config_persistence(self):
        """Test that global config persists across calls."""
        # Create and set custom config
        custom_config = PluginConfig()
        custom_config.kind_logging.log_level = logging.DEBUG
        set_plugin_config(custom_config)

        # Get config multiple times
        config1 = get_plugin_config()
        config2 = get_plugin_config()

        assert config1 is config2
        assert config1.kind_logging.log_level == logging.DEBUG

    def teardown_method(self):
        """Reset global config after each test."""
        set_plugin_config(None)


class TestPluginIntegration:
    """Test plugin integration using pytester."""

    def test_plugin_loads_successfully(self, pytester):
        """Test that the plugin loads without errors."""
        pytester.makepyfile("""
            def test_dummy():
                pass
        """)

        result = pytester.runpytest("--help")
        assert result.ret == 0
        assert "k8s" in result.stdout.str()

    def test_default_configuration(self, pytester):
        """Test default plugin configuration."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_default_config():
                config = pytest_k8s.get_plugin_config()
                assert config.kind_logging.stream_logs is True
                assert config.kind_logging.log_level == 20  # INFO
        """)

        result = pytester.runpytest("-v")
        assert result.ret == 0
        assert "pytest-k8s: kind log streaming enabled" in result.stdout.str()

    def test_command_line_options(self, pytester):
        """Test command line option parsing."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_custom_config():
                config = pytest_k8s.get_plugin_config()
                assert config.kind_logging.stream_logs is False
                assert config.kind_logging.log_level == 10  # DEBUG
        """)

        result = pytester.runpytest(
            "--k8s-no-kind-stream-logs", "--k8s-kind-log-level=DEBUG", "-v"
        )
        assert result.ret == 0
        assert "pytest-k8s: kind log streaming disabled" in result.stdout.str()

    def test_conflicting_stream_options(self, pytester):
        """Test that --k8s-no-kind-stream-logs overrides --k8s-kind-stream-logs."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_stream_disabled():
                config = pytest_k8s.get_plugin_config()
                assert config.kind_logging.stream_logs is False
        """)

        result = pytester.runpytest(
            "--k8s-kind-stream-logs", "--k8s-no-kind-stream-logs", "-v"
        )
        assert result.ret == 0
        assert "pytest-k8s: kind log streaming disabled" in result.stdout.str()

    def test_custom_log_format(self, pytester):
        """Test custom log format configuration."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_custom_format():
                config = pytest_k8s.get_plugin_config()
                assert config.kind_logging.log_format == "[CUSTOM] {message}"
        """)

        result = pytester.runpytest("--k8s-kind-log-format=[CUSTOM] {message}", "-v")
        assert result.ret == 0

    def test_include_stream_info_option(self, pytester):
        """Test include stream info option."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_stream_info_enabled():
                config = pytest_k8s.get_plugin_config()
                assert config.kind_logging.include_stream_info is True
        """)

        result = pytester.runpytest("--k8s-kind-include-stream-info", "-v")
        assert result.ret == 0

    def test_conftest_override(self, pytester):
        """Test that conftest.py can override configuration."""
        pytester.makeconftest("""
            def pytest_configure(config):
                # Override configuration in conftest.py
                config.option.k8s_kind_stream_logs = False
                config.option.k8s_kind_log_level = "ERROR"
        """)

        pytester.makepyfile("""
            import pytest_k8s
            
            def test_conftest_override():
                config = pytest_k8s.get_plugin_config()
                assert config.kind_logging.stream_logs is False
                assert config.kind_logging.log_level == 40  # ERROR
        """)

        result = pytester.runpytest("-v")
        assert result.ret == 0
        assert "pytest-k8s: kind log streaming disabled" in result.stdout.str()

    def test_invalid_log_level(self, pytester):
        """Test that invalid log levels are handled gracefully."""
        pytester.makepyfile("""
            def test_dummy():
                pass
        """)

        result = pytester.runpytest("--k8s-kind-log-level=INVALID")
        assert result.ret != 0
        assert "invalid choice" in result.stderr.str().lower()

    def test_plugin_header_display(self, pytester):
        """Test that plugin header is displayed correctly."""
        pytester.makepyfile("""
            def test_dummy():
                pass
        """)

        # Test with streaming enabled
        result = pytester.runpytest("-v")
        assert "pytest-k8s: kind log streaming enabled" in result.stdout.str()

        # Test with streaming disabled
        result = pytester.runpytest("--k8s-no-kind-stream-logs", "-v")
        assert "pytest-k8s: kind log streaming disabled" in result.stdout.str()

    def test_cluster_timeout_option(self, pytester):
        """Test cluster timeout command line option."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_cluster_timeout():
                config = pytest_k8s.get_plugin_config()
                assert config.cluster.default_timeout == 600
        """)

        result = pytester.runpytest("--k8s-cluster-timeout=600", "-v")
        assert result.ret == 0

    def test_cluster_keep_option(self, pytester):
        """Test cluster keep command line option."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_cluster_keep():
                config = pytest_k8s.get_plugin_config()
                assert config.cluster.default_keep_cluster is True
        """)

        result = pytester.runpytest("--k8s-cluster-keep", "-v")
        assert result.ret == 0

    def test_conflicting_cluster_keep_options(self, pytester):
        """Test that --k8s-no-cluster-keep overrides --k8s-cluster-keep."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_cluster_keep_disabled():
                config = pytest_k8s.get_plugin_config()
                assert config.cluster.default_keep_cluster is False
        """)

        result = pytester.runpytest("--k8s-cluster-keep", "--k8s-no-cluster-keep", "-v")
        assert result.ret == 0

    def test_cluster_scope_option(self, pytester):
        """Test cluster scope command line option."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_cluster_scope():
                config = pytest_k8s.get_plugin_config()
                assert config.cluster.default_scope == "function"
        """)

        result = pytester.runpytest("--k8s-cluster-scope=function", "-v")
        assert result.ret == 0

    def test_all_cluster_options_together(self, pytester):
        """Test all cluster options together."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_all_cluster_options():
                config = pytest_k8s.get_plugin_config()
                assert config.cluster.default_scope == "module"
                assert config.cluster.default_timeout == 900
                assert config.cluster.default_keep_cluster is True
        """)

        result = pytester.runpytest(
            "--k8s-cluster-scope=module",
            "--k8s-cluster-timeout=900",
            "--k8s-cluster-keep",
            "-v",
        )
        assert result.ret == 0
