"""
Streaming utilities for real-time command output capture.

This module provides utilities for streaming stdout and stderr from
subprocess commands in real-time with proper logging integration.
"""

import subprocess
import threading
import time
from typing import Optional, TextIO, List

from .loggers import KindLogger


class StreamReader:
    """
    Reads from a subprocess stream in a separate thread.

    This class handles reading from stdout or stderr streams
    in real-time and forwards the output to a unified logger.
    """

    def __init__(
        self,
        stream: TextIO,
        logger: KindLogger,
        stream_name: str,
        name: str = "StreamReader",
    ):
        """
        Initialize the stream reader.

        Args:
            stream: The stream to read from (stdout or stderr)
            logger: Unified logger to send output to
            stream_name: Name of the stream (stdout or stderr)
            name: Name for the reader thread
        """
        self.stream = stream
        self.logger = logger
        self.stream_name = stream_name
        self.name = name
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.lines: List[str] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start reading from the stream in a separate thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._read_stream,
            name=f"{self.name}-{self.stream_name}",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        """Stop reading from the stream."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _read_stream(self) -> None:
        """Read from the stream and log each line."""
        try:
            while self.running:
                line = self.stream.readline()
                if not line:
                    # End of stream
                    break

                # Store line for later retrieval
                with self._lock:
                    self.lines.append(line)

                # Log the line if logger is enabled
                if self.logger.is_enabled():
                    self.logger.log_line(line, self.stream_name)

        except Exception as e:
            # Log any errors in reading
            if self.logger.is_enabled():
                self.logger.log_line(f"Error reading stream: {e}", self.stream_name)
        finally:
            self.running = False

    def get_output(self) -> str:
        """
        Get all captured output as a string.

        Returns:
            All captured output joined as a single string
        """
        with self._lock:
            return "".join(self.lines)

    def get_lines(self) -> List[str]:
        """
        Get all captured lines.

        Returns:
            List of captured lines
        """
        with self._lock:
            return self.lines.copy()


class LoggingStreamHandler:
    """
    Handles streaming output from subprocess commands with logging.

    This class coordinates multiple stream readers and manages
    the overall streaming process for a subprocess using a unified logger.
    """

    def __init__(
        self,
        logger: Optional[KindLogger] = None,
    ):
        """
        Initialize the stream handler.

        Args:
            logger: Unified logger for both stdout and stderr output
        """
        self.logger = logger
        self.stdout_reader: Optional[StreamReader] = None
        self.stderr_reader: Optional[StreamReader] = None

    def start_streaming(
        self,
        process: subprocess.Popen,
        command_name: str = "command",
    ) -> None:
        """
        Start streaming output from a subprocess.

        Args:
            process: The subprocess to stream from
            command_name: Name of the command for logging context
        """
        # Create and start stdout reader
        if process.stdout and self.logger:
            self.stdout_reader = StreamReader(
                stream=process.stdout,
                logger=self.logger,
                stream_name="stdout",
                name=f"{command_name}-stdout",
            )
            self.stdout_reader.start()

        # Create and start stderr reader
        if process.stderr and self.logger:
            self.stderr_reader = StreamReader(
                stream=process.stderr,
                logger=self.logger,
                stream_name="stderr",
                name=f"{command_name}-stderr",
            )
            self.stderr_reader.start()

    def stop_streaming(self) -> None:
        """Stop all stream readers."""
        if self.stdout_reader:
            self.stdout_reader.stop()
        if self.stderr_reader:
            self.stderr_reader.stop()

    def wait_for_completion(self, timeout: Optional[float] = None) -> None:
        """
        Wait for all stream readers to complete.

        Args:
            timeout: Maximum time to wait for completion
        """
        start_time = time.time()

        while True:
            stdout_done = not self.stdout_reader or not self.stdout_reader.running
            stderr_done = not self.stderr_reader or not self.stderr_reader.running

            if stdout_done and stderr_done:
                break

            if timeout and (time.time() - start_time) > timeout:
                break

            time.sleep(0.1)

    def get_captured_output(self) -> tuple[str, str]:
        """
        Get all captured output from both streams.

        Returns:
            Tuple of (stdout_output, stderr_output)
        """
        stdout_output = ""
        stderr_output = ""

        if self.stdout_reader:
            stdout_output = self.stdout_reader.get_output()

        if self.stderr_reader:
            stderr_output = self.stderr_reader.get_output()

        return stdout_output, stderr_output


class StreamingSubprocess:
    """
    Wrapper for subprocess execution with real-time streaming.

    This class provides a high-level interface for running subprocesses
    with real-time output streaming and logging using a unified logger.
    """

    def __init__(
        self,
        logger: Optional[KindLogger] = None,
    ):
        """
        Initialize the streaming subprocess wrapper.

        Args:
            logger: Unified logger for both stdout and stderr output
        """
        self.logger = logger

    def run(
        self,
        cmd: List[str],
        timeout: Optional[float] = None,
        check: bool = True,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """
        Run a command with streaming output.

        Args:
            cmd: Command to run as a list of strings
            timeout: Command timeout in seconds
            check: Whether to raise on non-zero exit code
            env: Environment variables for the command
            cwd: Working directory for the command
            input_data: Input data to send to the command

        Returns:
            CompletedProcess instance with captured output

        Raises:
            subprocess.CalledProcessError: If command fails and check=True
            subprocess.TimeoutExpired: If command times out
        """
        # Determine if we should capture output
        capture_output = self.logger is not None

        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            stdin=subprocess.PIPE if input_data else None,
            text=True,
            env=env,
            cwd=cwd,
        )

        # Set up streaming
        stream_handler = LoggingStreamHandler(logger=self.logger)

        try:
            # Start streaming output
            stream_handler.start_streaming(process, command_name=cmd[0])

            # Send input if provided
            if input_data:
                process.stdin.write(input_data)
                process.stdin.close()

            # Wait for process completion
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stream_handler.stop_streaming()
                raise

            # Wait for stream readers to finish
            stream_handler.wait_for_completion(timeout=5.0)

            # Get captured output
            stdout_output, stderr_output = stream_handler.get_captured_output()

            # Create result object
            result = subprocess.CompletedProcess(
                args=cmd,
                returncode=return_code,
                stdout=stdout_output,
                stderr=stderr_output,
            )

            # Check return code if requested
            if check and return_code != 0:
                raise subprocess.CalledProcessError(
                    return_code, cmd, stdout_output, stderr_output
                )

            return result

        finally:
            # Ensure cleanup
            stream_handler.stop_streaming()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.kill()


def create_streaming_subprocess(
    logger: Optional[KindLogger] = None,
) -> StreamingSubprocess:
    """
    Create a streaming subprocess instance.

    Args:
        logger: Unified logger for both stdout and stderr output

    Returns:
        Configured StreamingSubprocess instance
    """
    return StreamingSubprocess(logger=logger)
