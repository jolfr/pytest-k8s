"""
Command execution utilities for kind clusters.

This module provides robust command execution with proper error handling,
logging, and timeout management.
"""

import logging
import subprocess
from typing import Dict, List, Optional

from .errors import KindClusterError, KindClusterTimeoutError
from .loggers import KindLoggerFactory
from .streaming import StreamingSubprocess
from ..config import get_plugin_config

logger = logging.getLogger(__name__)


class CommandRunner:
    """
    Handles command execution with proper error handling and logging.

    This class provides a centralized way to execute commands with consistent
    error handling, logging, and timeout management.
    """

    def __init__(self, default_timeout: int = 300):
        """
        Initialize the command runner.

        Args:
            default_timeout: Default timeout for command execution in seconds
        """
        self.default_timeout = default_timeout

    def run(
        self,
        cmd: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = True,
        check: bool = True,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """
        Run a command with proper error handling.

        Args:
            cmd: Command to run as a list of strings
            timeout: Command timeout in seconds (uses default if None)
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise on non-zero exit code
            env: Environment variables for the command
            cwd: Working directory for the command
            input_data: Input data to send to the command

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If command fails and check=True
            KindClusterTimeoutError: If command times out
            KindClusterError: For other execution errors
        """
        timeout = timeout or self.default_timeout

        logger.debug(f"Running command: {' '.join(cmd)}")
        if env:
            logger.debug(f"Environment variables: {env}")
        if cwd:
            logger.debug(f"Working directory: {cwd}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=check,
                env=env,
                cwd=cwd,
                input=input_data,
            )

            if result.stdout:
                logger.debug(f"Command stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Command stderr: {result.stderr}")

            return result

        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"Exit code: {e.returncode}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
            raise
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            raise KindClusterTimeoutError(
                f"Command timed out after {timeout} seconds: {' '.join(cmd)}", timeout
            )
        except Exception as e:
            logger.error(f"Unexpected error running command {' '.join(cmd)}: {e}")
            raise KindClusterError(f"Command execution failed: {e}")

    def run_with_retry(
        self, cmd: List[str], max_retries: int = 3, retry_delay: float = 1.0, **kwargs
    ) -> subprocess.CompletedProcess:
        """
        Run a command with retry logic.

        Args:
            cmd: Command to run as a list of strings
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            **kwargs: Additional arguments to pass to run()

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If all retries fail
            KindClusterTimeoutError: If command times out on final attempt
        """
        import time

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return self.run(cmd, **kwargs)
            except (subprocess.CalledProcessError, KindClusterError) as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(
                        f"Command failed (attempt {attempt + 1}/{max_retries + 1}): "
                        f"{' '.join(cmd)}. Retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Command failed after {max_retries + 1} attempts")
                    break

        # Re-raise the last exception
        if last_exception:
            raise last_exception

        # This should never be reached
        raise KindClusterError("Command execution failed unexpectedly")

    def check_command_available(self, command: str, timeout: int = 10) -> bool:
        """
        Check if a command is available on the system.

        Args:
            command: Command name to check
            timeout: Timeout for the check in seconds

        Returns:
            True if command is available, False otherwise
        """
        try:
            self.run([command, "--version"], timeout=timeout, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, KindClusterError):
            return False

    def get_command_output(
        self, cmd: List[str], timeout: Optional[int] = None, strip: bool = True
    ) -> str:
        """
        Get the output of a command as a string.

        Args:
            cmd: Command to run as a list of strings
            timeout: Command timeout in seconds
            strip: Whether to strip whitespace from output

        Returns:
            Command output as string

        Raises:
            subprocess.CalledProcessError: If command fails
            KindClusterTimeoutError: If command times out
        """
        result = self.run(cmd, timeout=timeout, capture_output=True, check=True)
        output = result.stdout
        return output.strip() if strip else output

    def get_command_lines(
        self, cmd: List[str], timeout: Optional[int] = None, filter_empty: bool = True
    ) -> List[str]:
        """
        Get the output of a command as a list of lines.

        Args:
            cmd: Command to run as a list of strings
            timeout: Command timeout in seconds
            filter_empty: Whether to filter out empty lines

        Returns:
            Command output as list of lines

        Raises:
            subprocess.CalledProcessError: If command fails
            KindClusterTimeoutError: If command times out
        """
        output = self.get_command_output(cmd, timeout=timeout, strip=True)
        lines = output.split("\n") if output else []

        if filter_empty:
            lines = [line.strip() for line in lines if line.strip()]

        return lines


class KindCommandRunner(CommandRunner):
    """
    Specialized command runner for kind operations.

    This class provides kind-specific command execution with enhanced
    error handling and validation, including real-time log streaming.
    """

    def __init__(self, default_timeout: int = 300):
        """Initialize the kind command runner."""
        super().__init__(default_timeout)
        self._kind_available = None
        self._docker_available = None
        self._streaming_subprocess = None
        self._logger = None
        self._setup_streaming()

    def _setup_streaming(self) -> None:
        """Set up streaming logger based on plugin configuration."""
        config = get_plugin_config()

        if config.kind_logging.stream_logs:
            # Create unified logger from configuration
            self._logger = KindLoggerFactory.create_logger_from_config(
                config.kind_logging
            )

            # Create streaming subprocess
            self._streaming_subprocess = StreamingSubprocess(
                logger=self._logger,
            )

    def run(
        self,
        cmd: List[str],
        stream_output: Optional[bool] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> subprocess.CompletedProcess:
        """
        Run a command with optional streaming output.

        Args:
            cmd: Command to run as a list of strings
            stream_output: Whether to stream output (overrides config default)
            timeout: Command timeout in seconds
            **kwargs: Additional arguments for run()

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If command fails and check=True
            KindClusterTimeoutError: If command times out
            KindClusterError: For other execution errors
        """
        # Determine if we should stream output
        config = get_plugin_config()
        should_stream = (
            stream_output
            if stream_output is not None
            else config.kind_logging.stream_logs
        )

        if should_stream and self._streaming_subprocess:
            return self._run_with_streaming(cmd, timeout=timeout, **kwargs)
        else:
            return super().run(cmd, timeout=timeout, **kwargs)

    def _run_with_streaming(
        self,
        cmd: List[str],
        timeout: Optional[int] = None,
        check: bool = True,
        env: Optional[Dict[str, str]] = None,
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
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If command fails and check=True
            KindClusterTimeoutError: If command times out
            KindClusterError: For other execution errors
        """
        timeout = timeout or self.default_timeout

        logger.debug(f"Running command with streaming: {' '.join(cmd)}")
        if env:
            logger.debug(f"Environment variables: {env}")
        if cwd:
            logger.debug(f"Working directory: {cwd}")

        try:
            result = self._streaming_subprocess.run(
                cmd=cmd,
                timeout=timeout,
                check=check,
                env=env,
                cwd=cwd,
                input_data=input_data,
            )

            return result

        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"Exit code: {e.returncode}")
            raise
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
            raise KindClusterTimeoutError(
                f"Command timed out after {timeout} seconds: {' '.join(cmd)}", timeout
            )
        except Exception as e:
            logger.error(f"Unexpected error running command {' '.join(cmd)}: {e}")
            raise KindClusterError(f"Command execution failed: {e}")

    def check_kind_available(self) -> bool:
        """
        Check if kind command is available.

        Returns:
            True if kind is available, False otherwise
        """
        if self._kind_available is None:
            self._kind_available = self.check_command_available("kind")
        return self._kind_available

    def check_docker_available(self) -> bool:
        """
        Check if Docker is available and running.

        Returns:
            True if Docker is available, False otherwise
        """
        if self._docker_available is None:
            self._docker_available = self.check_command_available("docker")
        return self._docker_available

    def validate_prerequisites(self) -> None:
        """
        Validate that all prerequisites are available.

        Raises:
            KindNotInstalledError: If kind is not available
            DockerNotRunningError: If Docker is not available
        """
        from .errors import KindNotInstalledError, DockerNotRunningError

        if not self.check_kind_available():
            raise KindNotInstalledError()

        if not self.check_docker_available():
            raise DockerNotRunningError()

    def get_clusters(self) -> List[str]:
        """
        Get list of existing kind clusters.

        Returns:
            List of cluster names

        Raises:
            KindClusterError: If unable to get cluster list
        """
        try:
            return self.get_command_lines(["kind", "get", "clusters"])
        except subprocess.CalledProcessError as e:
            if e.returncode == 1 and "No kind clusters found" in (e.stderr or ""):
                return []
            raise KindClusterError(f"Failed to get cluster list: {e.stderr}")

    def cluster_exists(self, name: str) -> bool:
        """
        Check if a cluster exists.

        Args:
            name: Cluster name to check

        Returns:
            True if cluster exists, False otherwise
        """
        try:
            clusters = self.get_clusters()
            return name in clusters
        except KindClusterError:
            return False

    def create_cluster(
        self,
        name: str,
        config_path: Optional[str] = None,
        wait_timeout: int = 60,
        **kwargs,
    ) -> None:
        """
        Create a kind cluster.

        Args:
            name: Cluster name
            config_path: Path to cluster configuration file
            wait_timeout: Timeout for cluster to be ready
            **kwargs: Additional arguments for run()

        Raises:
            subprocess.CalledProcessError: If cluster creation fails
            KindClusterTimeoutError: If operation times out
        """
        cmd = ["kind", "create", "cluster", "--name", name]

        if config_path:
            cmd.extend(["--config", config_path])

        cmd.append(f"--wait={wait_timeout}s")

        self.run(cmd, **kwargs)

    def delete_cluster(self, name: str, **kwargs) -> None:
        """
        Delete a kind cluster.

        Args:
            name: Cluster name
            **kwargs: Additional arguments for run()

        Raises:
            subprocess.CalledProcessError: If cluster deletion fails
        """
        cmd = ["kind", "delete", "cluster", "--name", name]
        self.run(cmd, **kwargs)

    def export_kubeconfig(
        self, cluster_name: str, kubeconfig_path: str, **kwargs
    ) -> None:
        """
        Export kubeconfig for a cluster.

        Args:
            cluster_name: Name of the cluster
            kubeconfig_path: Path to save kubeconfig
            **kwargs: Additional arguments for run()

        Raises:
            subprocess.CalledProcessError: If export fails
        """
        cmd = [
            "kind",
            "export",
            "kubeconfig",
            "--name",
            cluster_name,
            "--kubeconfig",
            kubeconfig_path,
        ]
        self.run(cmd, **kwargs)


class KubectlCommandRunner(CommandRunner):
    """
    Specialized command runner for kubectl operations.

    This class provides kubectl-specific command execution with
    kubeconfig management.
    """

    def __init__(
        self, kubeconfig_path: Optional[str] = None, default_timeout: int = 30
    ):
        """
        Initialize the kubectl command runner.

        Args:
            kubeconfig_path: Path to kubeconfig file
            default_timeout: Default timeout for kubectl operations
        """
        super().__init__(default_timeout)
        self.kubeconfig_path = kubeconfig_path

    def run_kubectl(
        self, args: List[str], kubeconfig_path: Optional[str] = None, **kwargs
    ) -> subprocess.CompletedProcess:
        """
        Run a kubectl command.

        Args:
            args: kubectl arguments (without 'kubectl')
            kubeconfig_path: Path to kubeconfig (overrides instance setting)
            **kwargs: Additional arguments for run()

        Returns:
            CompletedProcess instance
        """
        cmd = ["kubectl"] + args

        # Set up environment with kubeconfig
        env = kwargs.pop("env", None) or {}
        config_path = kubeconfig_path or self.kubeconfig_path
        if config_path:
            env = {**env, "KUBECONFIG": config_path}

        return self.run(cmd, env=env, **kwargs)

    def get_nodes(self, **kwargs) -> List[str]:
        """
        Get list of cluster nodes.

        Args:
            **kwargs: Additional arguments for run_kubectl()

        Returns:
            List of node names
        """
        result = self.run_kubectl(["get", "nodes", "-o", "name"], **kwargs)
        nodes = [
            line.replace("node/", "").strip()
            for line in result.stdout.strip().split("\n")
            if line.strip()
        ]
        return nodes

    def cluster_ready(self, **kwargs) -> bool:
        """
        Check if cluster is ready by trying to get nodes.

        Args:
            **kwargs: Additional arguments for run_kubectl()

        Returns:
            True if cluster is ready, False otherwise
        """
        try:
            self.run_kubectl(["get", "nodes"], check=True, **kwargs)
            return True
        except (subprocess.CalledProcessError, KindClusterError):
            return False
