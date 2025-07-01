"""
Tests for kind logging functionality.

This module tests the custom loggers for kind command output streaming.
"""

import logging
import pytest
from unittest.mock import Mock, patch

from pytest_k8s.kind.loggers import (
    KindStreamLogger,
    KindStdoutLogger,
    KindStderrLogger,
    KindLoggerFactory,
    get_kind_logger,
)
from pytest_k8s.config import KindLoggingConfig


class TestKindStreamLogger:
    """Test the KindStreamLogger class."""
    
    def test_init(self):
        """Test logger initialization."""
        logger = KindStreamLogger("STDOUT", logging.INFO)
        
        assert logger.stream_name == "STDOUT"
        assert logger.level == logging.INFO
        assert logger.format_template == "[KIND {stream}] {message}"
        assert logger.logger.name == "pytest_k8s.kind.stdout"
        assert logger.logger.propagate is True
    
    def test_init_with_custom_template(self):
        """Test logger initialization with custom template."""
        template = "[CUSTOM {stream}] {message}"
        logger = KindStreamLogger("STDERR", logging.WARNING, template)
        
        assert logger.format_template == template
    
    def test_init_with_custom_logger_name(self):
        """Test logger initialization with custom logger name."""
        logger = KindStreamLogger("STDOUT", logging.INFO, logger_name="custom.logger")
        
        assert logger.logger.name == "custom.logger"
    
    def test_log_line(self, caplog):
        """Test logging a single line."""
        with caplog.at_level(logging.INFO):
            logger = KindStreamLogger("STDOUT", logging.INFO)
            logger.log_line("Test message")
            
            assert len(caplog.records) == 1
            assert "[KIND STDOUT] Test message" in caplog.text
    
    def test_log_line_strips_whitespace(self, caplog):
        """Test that log_line strips trailing whitespace."""
        with caplog.at_level(logging.INFO):
            logger = KindStreamLogger("STDOUT", logging.INFO)
            logger.log_line("Test message   \n")
            
            assert len(caplog.records) == 1
            assert "[KIND STDOUT] Test message" in caplog.text
    
    def test_log_line_empty_line(self, caplog):
        """Test that empty lines are not logged."""
        with caplog.at_level(logging.INFO):
            logger = KindStreamLogger("STDOUT", logging.INFO)
            logger.log_line("")
            logger.log_line("   ")
            logger.log_line("\n")
            
            assert len(caplog.records) == 0
    
    def test_log_line_level_filtering(self, caplog):
        """Test that log level filtering works."""
        with caplog.at_level(logging.WARNING):
            logger = KindStreamLogger("STDOUT", logging.INFO)
            logger.log_line("This should not appear")
            
            assert len(caplog.records) == 0
    
    def test_log_lines(self, caplog):
        """Test logging multiple lines."""
        with caplog.at_level(logging.INFO):
            logger = KindStreamLogger("STDOUT", logging.INFO)
            logger.log_lines("Line 1\nLine 2\nLine 3")
            
            assert len(caplog.records) == 3
            assert "[KIND STDOUT] Line 1" in caplog.text
            assert "[KIND STDOUT] Line 2" in caplog.text
            assert "[KIND STDOUT] Line 3" in caplog.text
    
    def test_is_enabled(self):
        """Test is_enabled method."""
        logger = KindStreamLogger("STDOUT", logging.INFO)
        
        # Mock the logger's isEnabledFor method
        logger.logger.isEnabledFor = Mock(return_value=True)
        assert logger.is_enabled() is True
        
        logger.logger.isEnabledFor = Mock(return_value=False)
        assert logger.is_enabled() is False
    
    def test_repr(self):
        """Test string representation."""
        logger = KindStreamLogger("STDOUT", logging.INFO)
        repr_str = repr(logger)
        
        assert "KindStreamLogger" in repr_str
        assert "stream=STDOUT" in repr_str
        assert "level=INFO" in repr_str
        assert "logger=pytest_k8s.kind.stdout" in repr_str


class TestKindStdoutLogger:
    """Test the KindStdoutLogger class."""
    
    def test_init_defaults(self):
        """Test default initialization."""
        logger = KindStdoutLogger()
        
        assert logger.stream_name == "STDOUT"
        assert logger.level == logging.INFO
        assert logger.format_template == "[KIND STDOUT] {message}"
        assert logger.logger.name == "pytest_k8s.kind.stdout"
    
    def test_init_custom_level(self):
        """Test initialization with custom level."""
        logger = KindStdoutLogger(level=logging.DEBUG)
        
        assert logger.level == logging.DEBUG
    
    def test_init_custom_template(self):
        """Test initialization with custom template."""
        template = "[CUSTOM STDOUT] {message}"
        logger = KindStdoutLogger(format_template=template)
        
        assert logger.format_template == template


class TestKindStderrLogger:
    """Test the KindStderrLogger class."""
    
    def test_init_defaults(self):
        """Test default initialization."""
        logger = KindStderrLogger()
        
        assert logger.stream_name == "STDERR"
        assert logger.level == logging.WARNING
        assert logger.format_template == "[KIND STDERR] {message}"
        assert logger.logger.name == "pytest_k8s.kind.stderr"
    
    def test_init_custom_level(self):
        """Test initialization with custom level."""
        logger = KindStderrLogger(level=logging.ERROR)
        
        assert logger.level == logging.ERROR
    
    def test_init_custom_template(self):
        """Test initialization with custom template."""
        template = "[CUSTOM STDERR] {message}"
        logger = KindStderrLogger(format_template=template)
        
        assert logger.format_template == template


class TestKindLoggerFactory:
    """Test the KindLoggerFactory class."""
    
    def test_create_stdout_logger(self):
        """Test creating stdout logger."""
        logger = KindLoggerFactory.create_stdout_logger()
        
        assert isinstance(logger, KindStdoutLogger)
        assert logger.level == logging.INFO
        assert logger.format_template == "[KIND STDOUT] {message}"
    
    def test_create_stdout_logger_custom(self):
        """Test creating stdout logger with custom settings."""
        template = "[CUSTOM] {message}"
        logger = KindLoggerFactory.create_stdout_logger(
            level=logging.DEBUG,
            format_template=template
        )
        
        assert logger.level == logging.DEBUG
        assert logger.format_template == template
    
    def test_create_stderr_logger(self):
        """Test creating stderr logger."""
        logger = KindLoggerFactory.create_stderr_logger()
        
        assert isinstance(logger, KindStderrLogger)
        assert logger.level == logging.WARNING
        assert logger.format_template == "[KIND STDERR] {message}"
    
    def test_create_stderr_logger_custom(self):
        """Test creating stderr logger with custom settings."""
        template = "[CUSTOM] {message}"
        logger = KindLoggerFactory.create_stderr_logger(
            level=logging.ERROR,
            format_template=template
        )
        
        assert logger.level == logging.ERROR
        assert logger.format_template == template
    
    def test_create_loggers_from_config(self):
        """Test creating loggers from configuration."""
        config = KindLoggingConfig(
            stdout_level="DEBUG",
            stderr_level="ERROR",
            log_format="[TEST {stream}] {message}"
        )
        
        stdout_logger, stderr_logger = KindLoggerFactory.create_loggers_from_config(config)
        
        assert isinstance(stdout_logger, KindStdoutLogger)
        assert isinstance(stderr_logger, KindStderrLogger)
        assert stdout_logger.level == logging.DEBUG
        assert stderr_logger.level == logging.ERROR
        assert stdout_logger.format_template == "[TEST STDOUT] {message}"
        assert stderr_logger.format_template == "[TEST STDERR] {message}"


class TestGetKindLogger:
    """Test the get_kind_logger function."""
    
    def test_get_stdout_logger(self):
        """Test getting stdout logger."""
        logger = get_kind_logger("stdout")
        
        assert logger.name == "pytest_k8s.kind.stdout"
    
    def test_get_stderr_logger(self):
        """Test getting stderr logger."""
        logger = get_kind_logger("stderr")
        
        assert logger.name == "pytest_k8s.kind.stderr"
    
    def test_get_logger_case_insensitive(self):
        """Test that logger names are case insensitive."""
        logger1 = get_kind_logger("STDOUT")
        logger2 = get_kind_logger("stdout")
        logger3 = get_kind_logger("StdOut")
        
        assert logger1.name == logger2.name == logger3.name
    
    def test_invalid_stream_name(self):
        """Test that invalid stream names raise ValueError."""
        with pytest.raises(ValueError, match="Invalid stream name"):
            get_kind_logger("invalid")
        
        with pytest.raises(ValueError, match="Invalid stream name"):
            get_kind_logger("stdin")
