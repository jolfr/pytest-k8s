"""
Custom loggers for kind command output streaming.

This module provides specialized loggers for streaming stdout and stderr
from kind commands with appropriate prefixes and formatting.
"""

import logging
from typing import Optional


class KindStreamLogger:
    """
    Custom logger for kind command output streams.
    
    This logger handles streaming output from kind commands with
    configurable prefixes and log levels.
    """
    
    def __init__(
        self,
        stream_name: str,
        level: int,
        format_template: str = "[KIND {stream}] {message}",
        logger_name: Optional[str] = None,
    ):
        """
        Initialize the stream logger.
        
        Args:
            stream_name: Name of the stream (e.g., "STDOUT", "STDERR")
            level: Logging level for this stream
            format_template: Format template for log messages
            logger_name: Custom logger name (defaults to pytest_k8s.kind.{stream_name})
        """
        self.stream_name = stream_name.upper()
        self.level = level
        self.format_template = format_template
        
        # Create logger with hierarchical name
        if logger_name is None:
            logger_name = f"pytest_k8s.kind.{self.stream_name.lower()}"
        
        self.logger = logging.getLogger(logger_name)
        
        # Ensure the logger propagates to the root logger
        self.logger.propagate = True
    
    def log_line(self, line: str) -> None:
        """
        Log a single line of output.
        
        Args:
            line: Line of output to log
        """
        if not line.strip():
            return
        
        # Check if logging is enabled for this level
        if self.logger.isEnabledFor(self.level):
            formatted_message = self.format_template.format(
                stream=self.stream_name,
                message=line.rstrip()
            )
            self.logger.log(self.level, formatted_message)
    
    def log_lines(self, lines: str) -> None:
        """
        Log multiple lines of output.
        
        Args:
            lines: Multi-line string to log
        """
        for line in lines.splitlines():
            self.log_line(line)
    
    def is_enabled(self) -> bool:
        """
        Check if logging is enabled for this stream's level.
        
        Returns:
            True if logging is enabled, False otherwise
        """
        return self.logger.isEnabledFor(self.level)
    
    def __repr__(self) -> str:
        """String representation of the logger."""
        return (
            f"KindStreamLogger("
            f"stream={self.stream_name}, "
            f"level={logging.getLevelName(self.level)}, "
            f"logger={self.logger.name}"
            f")"
        )


class KindStdoutLogger(KindStreamLogger):
    """
    Specialized logger for kind stdout output.
    
    This logger is specifically configured for handling stdout
    from kind commands with appropriate formatting.
    """
    
    def __init__(
        self,
        level: int = logging.INFO,
        format_template: str = "[KIND STDOUT] {message}",
    ):
        """
        Initialize the stdout logger.
        
        Args:
            level: Logging level for stdout messages
            format_template: Format template for stdout messages
        """
        super().__init__(
            stream_name="STDOUT",
            level=level,
            format_template=format_template,
            logger_name="pytest_k8s.kind.stdout"
        )


class KindStderrLogger(KindStreamLogger):
    """
    Specialized logger for kind stderr output.
    
    This logger is specifically configured for handling stderr
    from kind commands with appropriate formatting.
    """
    
    def __init__(
        self,
        level: int = logging.WARNING,
        format_template: str = "[KIND STDERR] {message}",
    ):
        """
        Initialize the stderr logger.
        
        Args:
            level: Logging level for stderr messages
            format_template: Format template for stderr messages
        """
        super().__init__(
            stream_name="STDERR",
            level=level,
            format_template=format_template,
            logger_name="pytest_k8s.kind.stderr"
        )


class KindLoggerFactory:
    """
    Factory for creating kind stream loggers with consistent configuration.
    
    This factory ensures that all kind loggers are created with
    consistent settings based on the plugin configuration.
    """
    
    @staticmethod
    def create_stdout_logger(
        level: int = logging.INFO,
        format_template: str = "[KIND STDOUT] {message}",
    ) -> KindStdoutLogger:
        """
        Create a stdout logger.
        
        Args:
            level: Logging level for stdout messages
            format_template: Format template for stdout messages
            
        Returns:
            Configured KindStdoutLogger instance
        """
        return KindStdoutLogger(level=level, format_template=format_template)
    
    @staticmethod
    def create_stderr_logger(
        level: int = logging.WARNING,
        format_template: str = "[KIND STDERR] {message}",
    ) -> KindStderrLogger:
        """
        Create a stderr logger.
        
        Args:
            level: Logging level for stderr messages
            format_template: Format template for stderr messages
            
        Returns:
            Configured KindStderrLogger instance
        """
        return KindStderrLogger(level=level, format_template=format_template)
    
    @staticmethod
    def create_loggers_from_config(config) -> tuple[KindStdoutLogger, KindStderrLogger]:
        """
        Create stdout and stderr loggers from configuration.
        
        Args:
            config: KindLoggingConfig instance
            
        Returns:
            Tuple of (stdout_logger, stderr_logger)
        """
        stdout_logger = KindLoggerFactory.create_stdout_logger(
            level=config.stdout_level,
            format_template=config.log_format.replace("{stream}", "STDOUT")
        )
        
        stderr_logger = KindLoggerFactory.create_stderr_logger(
            level=config.stderr_level,
            format_template=config.log_format.replace("{stream}", "STDERR")
        )
        
        return stdout_logger, stderr_logger


def get_kind_logger(stream_name: str) -> logging.Logger:
    """
    Get a kind logger by stream name.
    
    Args:
        stream_name: Name of the stream ("stdout" or "stderr")
        
    Returns:
        Logger instance for the specified stream
        
    Raises:
        ValueError: If stream_name is not valid
    """
    stream_name = stream_name.lower()
    if stream_name not in ("stdout", "stderr"):
        raise ValueError(f"Invalid stream name: {stream_name}. Must be 'stdout' or 'stderr'")
    
    return logging.getLogger(f"pytest_k8s.kind.{stream_name}")
