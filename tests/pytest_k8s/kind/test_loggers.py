"""
Tests for kind logging functionality.

This module tests the unified logger for kind command output streaming.
"""

import logging
import pytest
from unittest.mock import Mock

from pytest_k8s.kind.loggers import (
    KindLogger,
    KindLoggerFactory,
    get_kind_logger,
)
from pytest_k8s.config import KindLoggingConfig


class TestKindLogger:
    """Test the KindLogger class."""

    def test_init_defaults(self):
        """Test default initialization."""
        logger = KindLogger()

        assert logger.level == logging.INFO
        assert logger.format_template == "[KIND] {message}"
        assert logger.include_stream_info is False
        assert logger.logger.name == "pytest_k8s.kind"
        assert logger.logger.propagate is True

    def test_init_custom_settings(self):
        """Test initialization with custom settings."""
        logger = KindLogger(
            level=logging.DEBUG,
            format_template="[CUSTOM] {message}",
            logger_name="custom.logger",
            include_stream_info=True,
        )

        assert logger.level == logging.DEBUG
        assert logger.format_template == "[CUSTOM] {message}"
        assert logger.include_stream_info is True
        assert logger.logger.name == "custom.logger"

    def test_log_line_basic(self, caplog):
        """Test logging a single line without stream info."""
        with caplog.at_level(logging.INFO):
            logger = KindLogger()
            logger.log_line("Test message")

            assert len(caplog.records) == 1
            assert "[KIND] Test message" in caplog.text

    def test_log_line_with_stream_info(self, caplog):
        """Test logging a single line with stream info."""
        with caplog.at_level(logging.INFO):
            logger = KindLogger(include_stream_info=True)
            logger.log_line("Test message", "stdout")

            assert len(caplog.records) == 1
            assert "[KIND] [STDOUT] Test message" in caplog.text

    def test_log_line_strips_whitespace(self, caplog):
        """Test that log_line strips trailing whitespace."""
        with caplog.at_level(logging.INFO):
            logger = KindLogger()
            logger.log_line("Test message   \n")

            assert len(caplog.records) == 1
            assert "[KIND] Test message" in caplog.text

    def test_log_line_empty_line(self, caplog):
        """Test that empty lines are not logged."""
        with caplog.at_level(logging.INFO):
            logger = KindLogger()
            logger.log_line("")
            logger.log_line("   ")
            logger.log_line("\n")

            assert len(caplog.records) == 0

    def test_log_line_level_filtering(self, caplog):
        """Test that log level filtering works."""
        with caplog.at_level(logging.WARNING):
            logger = KindLogger(level=logging.INFO)
            logger.log_line("This should not appear")

            assert len(caplog.records) == 0

    def test_log_lines_basic(self, caplog):
        """Test logging multiple lines without stream info."""
        with caplog.at_level(logging.INFO):
            logger = KindLogger()
            logger.log_lines("Line 1\nLine 2\nLine 3")

            assert len(caplog.records) == 3
            assert "[KIND] Line 1" in caplog.text
            assert "[KIND] Line 2" in caplog.text
            assert "[KIND] Line 3" in caplog.text

    def test_log_lines_with_stream_info(self, caplog):
        """Test logging multiple lines with stream info."""
        with caplog.at_level(logging.INFO):
            logger = KindLogger(include_stream_info=True)
            logger.log_lines("Line 1\nLine 2\nLine 3", "stderr")

            assert len(caplog.records) == 3
            assert "[KIND] [STDERR] Line 1" in caplog.text
            assert "[KIND] [STDERR] Line 2" in caplog.text
            assert "[KIND] [STDERR] Line 3" in caplog.text

    def test_is_enabled(self):
        """Test is_enabled method."""
        logger = KindLogger()

        # Mock the logger's isEnabledFor method
        logger.logger.isEnabledFor = Mock(return_value=True)
        assert logger.is_enabled() is True

        logger.logger.isEnabledFor = Mock(return_value=False)
        assert logger.is_enabled() is False

    def test_repr(self):
        """Test string representation."""
        logger = KindLogger()
        repr_str = repr(logger)

        assert "KindLogger" in repr_str
        assert "level=INFO" in repr_str
        assert "logger=pytest_k8s.kind" in repr_str
        assert "include_stream_info=False" in repr_str


class TestKindLoggerFactory:
    """Test the KindLoggerFactory class."""

    def test_create_logger_defaults(self):
        """Test creating logger with defaults."""
        logger = KindLoggerFactory.create_logger()

        assert isinstance(logger, KindLogger)
        assert logger.level == logging.INFO
        assert logger.format_template == "[KIND] {message}"
        assert logger.include_stream_info is False

    def test_create_logger_custom(self):
        """Test creating logger with custom settings."""
        template = "[CUSTOM] {message}"
        logger = KindLoggerFactory.create_logger(
            level=logging.DEBUG, format_template=template, include_stream_info=True
        )

        assert logger.level == logging.DEBUG
        assert logger.format_template == template
        assert logger.include_stream_info is True

    def test_create_logger_from_config(self):
        """Test creating logger from configuration."""
        config = KindLoggingConfig(
            log_level="DEBUG", log_format="[TEST] {message}", include_stream_info=True
        )

        logger = KindLoggerFactory.create_logger_from_config(config)

        assert isinstance(logger, KindLogger)
        assert logger.level == logging.DEBUG
        assert logger.format_template == "[TEST] {message}"
        assert logger.include_stream_info is True


class TestGetKindLogger:
    """Test the get_kind_logger function."""

    def test_get_kind_logger(self):
        """Test getting the unified kind logger."""
        logger = get_kind_logger()

        assert logger.name == "pytest_k8s.kind"

    def test_get_kind_logger_returns_same_instance(self):
        """Test that multiple calls return the same logger instance."""
        logger1 = get_kind_logger()
        logger2 = get_kind_logger()

        assert logger1 is logger2


class TestBackwardCompatibility:
    """Test backward compatibility functions."""

    def test_get_kind_logger_by_stream_deprecated(self):
        """Test that the deprecated function still works but issues warning."""
        from pytest_k8s.kind.loggers import get_kind_logger_by_stream

        with pytest.warns(
            DeprecationWarning, match="get_kind_logger_by_stream is deprecated"
        ):
            logger = get_kind_logger_by_stream("stdout")

        assert logger.name == "pytest_k8s.kind"

    def test_get_kind_logger_by_stream_stderr(self):
        """Test that the deprecated function works with stderr."""
        from pytest_k8s.kind.loggers import get_kind_logger_by_stream

        with pytest.warns(DeprecationWarning):
            logger = get_kind_logger_by_stream("stderr")

        assert logger.name == "pytest_k8s.kind"


class TestIntegrationWithConfig:
    """Test integration with configuration system."""

    def test_logger_with_stream_info_disabled(self):
        """Test logger behavior when stream info is disabled."""
        config = KindLoggingConfig(include_stream_info=False)
        logger = KindLoggerFactory.create_logger_from_config(config)

        # Test that the logger was created with correct settings
        assert logger.include_stream_info is False
        assert logger.level == logging.INFO
        assert logger.format_template == "[KIND] {message}"

    def test_logger_with_stream_info_enabled(self):
        """Test logger behavior when stream info is enabled."""
        config = KindLoggingConfig(include_stream_info=True)
        logger = KindLoggerFactory.create_logger_from_config(config)

        # Test that the logger was created with correct settings
        assert logger.include_stream_info is True
        assert logger.level == logging.INFO
        assert logger.format_template == "[KIND] {message}"

    def test_logger_with_custom_format(self):
        """Test logger with custom format template."""
        config = KindLoggingConfig(
            log_format="[CUSTOM-KIND] {message}", include_stream_info=True
        )
        logger = KindLoggerFactory.create_logger_from_config(config)

        # Test that the logger was created with correct settings
        assert logger.format_template == "[CUSTOM-KIND] {message}"
        assert logger.include_stream_info is True

    def test_logger_with_different_levels(self):
        """Test logger with different log levels."""
        # Test DEBUG level
        config = KindLoggingConfig(log_level="DEBUG")
        logger = KindLoggerFactory.create_logger_from_config(config)
        assert logger.level == logging.DEBUG

        # Test ERROR level
        config = KindLoggingConfig(log_level="ERROR")
        logger = KindLoggerFactory.create_logger_from_config(config)
        assert logger.level == logging.ERROR

        # Test WARNING level
        config = KindLoggingConfig(log_level="WARNING")
        logger = KindLoggerFactory.create_logger_from_config(config)
        assert logger.level == logging.WARNING
