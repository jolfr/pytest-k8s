"""
Custom loggers for kind command output streaming.

This module provides a unified logger for streaming stdout and stderr
from kind commands with consistent formatting and log levels.
"""

import logging
from typing import Optional


class KindLogger:
    """
    Unified logger for kind command output streams.

    This logger handles streaming output from both stdout and stderr
    of kind commands with consistent formatting and log levels.
    """

    def __init__(
        self,
        level: int = logging.INFO,
        format_template: str = "[KIND] {message}",
        logger_name: str = "pytest_k8s.kind",
        include_stream_info: bool = False,
    ):
        """
        Initialize the unified kind logger.

        Args:
            level: Logging level for all kind messages
            format_template: Format template for log messages
            logger_name: Logger name for hierarchical logging
            include_stream_info: Whether to include stream info in messages
        """
        self.level = level
        self.format_template = format_template
        self.include_stream_info = include_stream_info

        # Create logger with hierarchical name
        self.logger = logging.getLogger(logger_name)

        # Ensure the logger propagates to the root logger
        self.logger.propagate = True

    def log_line(self, line: str, stream_name: Optional[str] = None) -> None:
        """
        Log a single line of output.

        Args:
            line: Line of output to log
            stream_name: Name of the stream (for debugging purposes)
        """
        if not line.strip():
            return

        # Check if logging is enabled for this level
        if self.logger.isEnabledFor(self.level):
            # Format the message
            if self.include_stream_info and stream_name:
                # Include stream info for debugging
                formatted_message = self.format_template.format(
                    message=f"[{stream_name.upper()}] {line.rstrip()}"
                )
            else:
                # Standard unified format
                formatted_message = self.format_template.format(message=line.rstrip())

            self.logger.log(self.level, formatted_message)

    def log_lines(self, lines: str, stream_name: Optional[str] = None) -> None:
        """
        Log multiple lines of output.

        Args:
            lines: Multi-line string to log
            stream_name: Name of the stream (for debugging purposes)
        """
        for line in lines.splitlines():
            self.log_line(line, stream_name)

    def is_enabled(self) -> bool:
        """
        Check if logging is enabled for this logger's level.

        Returns:
            True if logging is enabled, False otherwise
        """
        return self.logger.isEnabledFor(self.level)

    def __repr__(self) -> str:
        """String representation of the logger."""
        return (
            f"KindLogger("
            f"level={logging.getLevelName(self.level)}, "
            f"logger={self.logger.name}, "
            f"include_stream_info={self.include_stream_info}"
            f")"
        )


class KindLoggerFactory:
    """
    Factory for creating kind loggers with consistent configuration.

    This factory ensures that all kind loggers are created with
    consistent settings based on the plugin configuration.
    """

    @staticmethod
    def create_logger(
        level: int = logging.INFO,
        format_template: str = "[KIND] {message}",
        include_stream_info: bool = False,
    ) -> KindLogger:
        """
        Create a unified kind logger.

        Args:
            level: Logging level for kind messages
            format_template: Format template for log messages
            include_stream_info: Whether to include stream info in messages

        Returns:
            Configured KindLogger instance
        """
        return KindLogger(
            level=level,
            format_template=format_template,
            include_stream_info=include_stream_info,
        )

    @staticmethod
    def create_logger_from_config(config) -> KindLogger:
        """
        Create a kind logger from configuration.

        Args:
            config: KindLoggingConfig instance

        Returns:
            Configured KindLogger instance
        """
        return KindLoggerFactory.create_logger(
            level=config.log_level,
            format_template=config.log_format,
            include_stream_info=config.include_stream_info,
        )


def get_kind_logger() -> logging.Logger:
    """
    Get the unified kind logger.

    Returns:
        Logger instance for kind operations
    """
    return logging.getLogger("pytest_k8s.kind")


# Backward compatibility - deprecated functions
def get_kind_logger_by_stream(stream_name: str) -> logging.Logger:
    """
    Get a kind logger by stream name (deprecated).

    Args:
        stream_name: Name of the stream ("stdout" or "stderr")

    Returns:
        Logger instance for kind operations

    Note:
        This function is deprecated. Use get_kind_logger() instead.
    """
    import warnings

    warnings.warn(
        "get_kind_logger_by_stream is deprecated. Use get_kind_logger() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_kind_logger()
