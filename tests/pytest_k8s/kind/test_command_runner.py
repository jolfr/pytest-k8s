"""
Tests for the command execution utilities.

This module contains comprehensive tests for the CommandRunner, KindCommandRunner,
and KubectlCommandRunner classes, including unit tests with mocking and error handling.
"""

import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from pytest_k8s.kind.command_runner import (
    CommandRunner,
    KindCommandRunner,
    KubectlCommandRunner,
)
from pytest_k8s.kind.errors import (
    DockerNotRunningError,
    KindClusterError,
    KindClusterTimeoutError,
    KindNotInstalledError,
)


class TestCommandRunner:
    """Test cases for CommandRunner base class."""

    def test_init(self):
        """Test CommandRunner initialization."""
        runner = CommandRunner()
        assert runner.default_timeout == 300

        runner = CommandRunner(default_timeout=600)
        assert runner.default_timeout == 600

    @patch("subprocess.run")
    def test_run_success(self, mock_run):
        """Test successful command execution."""
        mock_result = Mock()
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        runner = CommandRunner()
        result = runner.run(["echo", "test"])

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["echo", "test"],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
            env=None,
            cwd=None,
            input=None,
        )

    @patch("subprocess.run")
    def test_run_with_env_and_cwd(self, mock_run):
        """Test command execution with environment and working directory."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = CommandRunner()
        env = {"TEST_VAR": "test_value"}
        cwd = "/tmp"

        result = runner.run(["echo", "test"], env=env, cwd=cwd, timeout=60)

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["echo", "test"],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
            env=env,
            cwd=cwd,
            input=None,
        )

    @patch("subprocess.run")
    def test_run_with_input_data(self, mock_run):
        """Test command execution with input data."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = CommandRunner()
        result = runner.run(["cat"], input_data="test input")

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["cat"],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
            env=None,
            cwd=None,
            input="test input",
        )

    @patch("subprocess.run")
    def test_run_capture_output_false(self, mock_run):
        """Test command execution without capturing output."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = CommandRunner()
        result = runner.run(["echo", "test"], capture_output=False)

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["echo", "test"],
            capture_output=False,
            text=True,
            timeout=300,
            check=True,
            env=None,
            cwd=None,
            input=None,
        )

    @patch("subprocess.run")
    def test_run_check_false(self, mock_run):
        """Test command execution without raising on non-zero exit."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        runner = CommandRunner()
        result = runner.run(["false"], check=False)

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["false"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
            env=None,
            cwd=None,
            input=None,
        )

    @patch("subprocess.run")
    def test_run_command_error(self, mock_run):
        """Test command execution with CalledProcessError."""
        error = subprocess.CalledProcessError(1, ["false"])
        error.stdout = "error output"
        error.stderr = "error message"
        mock_run.side_effect = error

        runner = CommandRunner()

        with pytest.raises(subprocess.CalledProcessError):
            runner.run(["false"])

    @patch("subprocess.run")
    def test_run_timeout_error(self, mock_run):
        """Test command execution with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["sleep", "10"], 5)

        runner = CommandRunner()

        with pytest.raises(KindClusterTimeoutError) as exc_info:
            runner.run(["sleep", "10"], timeout=5)

        assert exc_info.value.timeout == 5
        assert "timed out after 5 seconds" in str(exc_info.value)

    @patch("subprocess.run")
    def test_run_generic_exception(self, mock_run):
        """Test command execution with generic exception."""
        mock_run.side_effect = ValueError("Generic error")

        runner = CommandRunner()

        with pytest.raises(KindClusterError, match="Command execution failed"):
            runner.run(["echo", "test"])

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_run_with_retry_success(self, mock_sleep, mock_run):
        """Test retry logic with eventual success."""
        # First call fails, second succeeds
        error = subprocess.CalledProcessError(1, ["test"])
        mock_result = Mock()
        mock_run.side_effect = [error, mock_result]

        runner = CommandRunner()
        result = runner.run_with_retry(["test"], max_retries=2, retry_delay=1.0)

        assert result == mock_result
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_run_with_retry_all_failures(self, mock_sleep, mock_run):
        """Test retry logic with all attempts failing."""
        error = subprocess.CalledProcessError(1, ["test"])
        mock_run.side_effect = error

        runner = CommandRunner()

        with pytest.raises(subprocess.CalledProcessError):
            runner.run_with_retry(["test"], max_retries=2, retry_delay=0.1)

        assert mock_run.call_count == 3  # Initial + 2 retries
        assert mock_sleep.call_count == 2

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_run_with_retry_timeout(self, mock_sleep, mock_run):
        """Test retry logic with timeout on final attempt."""
        # First attempts fail with CalledProcessError, final with timeout
        error = subprocess.CalledProcessError(1, ["test"])
        timeout_error = subprocess.TimeoutExpired(["test"], 30)
        mock_run.side_effect = [error, timeout_error]

        runner = CommandRunner()

        with pytest.raises(KindClusterTimeoutError):
            runner.run_with_retry(["test"], max_retries=1, retry_delay=0.1)

        assert mock_run.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

    @patch.object(CommandRunner, "run")
    def test_check_command_available_true(self, mock_run):
        """Test command availability check when command exists."""
        mock_run.return_value = Mock()

        runner = CommandRunner()
        assert runner.check_command_available("kind") is True

        mock_run.assert_called_once_with(["kind", "--version"], timeout=10, check=True)

    @patch.object(CommandRunner, "run")
    def test_check_command_available_false_called_process_error(self, mock_run):
        """Test command availability check with CalledProcessError."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["kind"])

        runner = CommandRunner()
        assert runner.check_command_available("kind") is False

    @patch.object(CommandRunner, "run")
    def test_check_command_available_false_file_not_found(self, mock_run):
        """Test command availability check with FileNotFoundError."""
        mock_run.side_effect = FileNotFoundError()

        runner = CommandRunner()
        assert runner.check_command_available("kind") is False

    @patch.object(CommandRunner, "run")
    def test_check_command_available_false_kind_cluster_error(self, mock_run):
        """Test command availability check with KindClusterError."""
        mock_run.side_effect = KindClusterError("Test error")

        runner = CommandRunner()
        assert runner.check_command_available("kind") is False

    @patch.object(CommandRunner, "run")
    def test_get_command_output_success(self, mock_run):
        """Test getting command output as string."""
        mock_result = Mock()
        mock_result.stdout = "  test output  \n"
        mock_run.return_value = mock_result

        runner = CommandRunner()
        output = runner.get_command_output(["echo", "test"])

        assert output == "test output"
        mock_run.assert_called_once_with(
            ["echo", "test"], timeout=None, capture_output=True, check=True
        )

    @patch.object(CommandRunner, "run")
    def test_get_command_output_no_strip(self, mock_run):
        """Test getting command output without stripping."""
        mock_result = Mock()
        mock_result.stdout = "  test output  \n"
        mock_run.return_value = mock_result

        runner = CommandRunner()
        output = runner.get_command_output(["echo", "test"], strip=False)

        assert output == "  test output  \n"

    @patch.object(CommandRunner, "run")
    def test_get_command_output_with_timeout(self, mock_run):
        """Test getting command output with custom timeout."""
        mock_result = Mock()
        mock_result.stdout = "test output"
        mock_run.return_value = mock_result

        runner = CommandRunner()
        runner.get_command_output(["echo", "test"], timeout=60)

        mock_run.assert_called_once_with(
            ["echo", "test"], timeout=60, capture_output=True, check=True
        )

    @patch.object(CommandRunner, "get_command_output")
    def test_get_command_lines_success(self, mock_get_output):
        """Test getting command output as lines."""
        mock_get_output.return_value = "line1\nline2\nline3"

        runner = CommandRunner()
        lines = runner.get_command_lines(["echo", "test"])

        assert lines == ["line1", "line2", "line3"]
        mock_get_output.assert_called_once_with(
            ["echo", "test"], timeout=None, strip=True
        )

    @patch.object(CommandRunner, "get_command_output")
    def test_get_command_lines_empty_output(self, mock_get_output):
        """Test getting command lines with empty output."""
        mock_get_output.return_value = ""

        runner = CommandRunner()
        lines = runner.get_command_lines(["echo", ""])

        assert lines == []

    @patch.object(CommandRunner, "get_command_output")
    def test_get_command_lines_filter_empty(self, mock_get_output):
        """Test getting command lines with empty line filtering."""
        mock_get_output.return_value = "line1\n\nline3\n  \n"

        runner = CommandRunner()
        lines = runner.get_command_lines(["echo", "test"], filter_empty=True)

        assert lines == ["line1", "line3"]

    @patch.object(CommandRunner, "get_command_output")
    def test_get_command_lines_no_filter_empty(self, mock_get_output):
        """Test getting command lines without empty line filtering."""
        mock_get_output.return_value = "line1\n\nline3"

        runner = CommandRunner()
        lines = runner.get_command_lines(["echo", "test"], filter_empty=False)

        assert lines == ["line1", "", "line3"]

    @patch.object(CommandRunner, "get_command_output")
    def test_get_command_lines_with_timeout(self, mock_get_output):
        """Test getting command lines with custom timeout."""
        mock_get_output.return_value = "line1\nline2"

        runner = CommandRunner()
        runner.get_command_lines(["echo", "test"], timeout=60)

        mock_get_output.assert_called_once_with(
            ["echo", "test"], timeout=60, strip=True
        )


class TestKindCommandRunner:
    """Test cases for KindCommandRunner class."""

    def test_init(self):
        """Test KindCommandRunner initialization."""
        runner = KindCommandRunner()
        assert runner.default_timeout == 300
        assert runner._kind_available is None
        assert runner._docker_available is None

        runner = KindCommandRunner(default_timeout=600)
        assert runner.default_timeout == 600

    @patch.object(KindCommandRunner, "check_command_available")
    def test_check_kind_available_true(self, mock_check):
        """Test kind availability check when available."""
        mock_check.return_value = True

        runner = KindCommandRunner()
        assert runner.check_kind_available() is True
        assert runner._kind_available is True

        mock_check.assert_called_once_with("kind")

    @patch.object(KindCommandRunner, "check_command_available")
    def test_check_kind_available_false(self, mock_check):
        """Test kind availability check when not available."""
        mock_check.return_value = False

        runner = KindCommandRunner()
        assert runner.check_kind_available() is False
        assert runner._kind_available is False

    @patch.object(KindCommandRunner, "check_command_available")
    def test_check_kind_available_cached(self, mock_check):
        """Test kind availability check caching."""
        mock_check.return_value = True

        runner = KindCommandRunner()
        runner._kind_available = True  # Pre-set cache

        assert runner.check_kind_available() is True
        mock_check.assert_not_called()  # Should use cached value

    @patch.object(KindCommandRunner, "check_command_available")
    def test_check_docker_available_true(self, mock_check):
        """Test Docker availability check when available."""
        mock_check.return_value = True

        runner = KindCommandRunner()
        assert runner.check_docker_available() is True
        assert runner._docker_available is True

        mock_check.assert_called_once_with("docker")

    @patch.object(KindCommandRunner, "check_command_available")
    def test_check_docker_available_false(self, mock_check):
        """Test Docker availability check when not available."""
        mock_check.return_value = False

        runner = KindCommandRunner()
        assert runner.check_docker_available() is False
        assert runner._docker_available is False

    @patch.object(KindCommandRunner, "check_docker_available")
    @patch.object(KindCommandRunner, "check_kind_available")
    def test_validate_prerequisites_success(self, mock_kind, mock_docker):
        """Test successful prerequisites validation."""
        mock_kind.return_value = True
        mock_docker.return_value = True

        runner = KindCommandRunner()
        runner.validate_prerequisites()  # Should not raise

        mock_kind.assert_called_once()
        mock_docker.assert_called_once()

    @patch.object(KindCommandRunner, "check_kind_available")
    def test_validate_prerequisites_kind_missing(self, mock_kind):
        """Test prerequisites validation when kind is missing."""
        mock_kind.return_value = False

        runner = KindCommandRunner()

        with pytest.raises(KindNotInstalledError):
            runner.validate_prerequisites()

    @patch.object(KindCommandRunner, "check_docker_available")
    @patch.object(KindCommandRunner, "check_kind_available")
    def test_validate_prerequisites_docker_missing(self, mock_kind, mock_docker):
        """Test prerequisites validation when Docker is missing."""
        mock_kind.return_value = True
        mock_docker.return_value = False

        runner = KindCommandRunner()

        with pytest.raises(DockerNotRunningError):
            runner.validate_prerequisites()

    @patch.object(KindCommandRunner, "get_command_lines")
    def test_get_clusters_success(self, mock_get_lines):
        """Test getting cluster list successfully."""
        mock_get_lines.return_value = ["cluster1", "cluster2", "test-cluster"]

        runner = KindCommandRunner()
        clusters = runner.get_clusters()

        assert clusters == ["cluster1", "cluster2", "test-cluster"]
        mock_get_lines.assert_called_once_with(["kind", "get", "clusters"])

    def test_get_clusters_empty(self):
        """Test getting cluster list when empty."""
        runner = KindCommandRunner()

        # Test "No kind clusters found" case - should return empty list
        with patch.object(runner, "get_command_lines") as mock_get_lines:
            error = subprocess.CalledProcessError(1, ["kind"])
            error.stderr = "No kind clusters found"
            mock_get_lines.side_effect = error

            clusters = runner.get_clusters()
            assert clusters == []

    @patch.object(KindCommandRunner, "get_command_lines")
    def test_get_clusters_error(self, mock_get_lines):
        """Test getting cluster list with error."""
        mock_get_lines.side_effect = subprocess.CalledProcessError(
            1, ["kind"], stderr="Command failed"
        )

        runner = KindCommandRunner()

        with pytest.raises(KindClusterError, match="Failed to get cluster list"):
            runner.get_clusters()

    @patch.object(KindCommandRunner, "get_clusters")
    def test_cluster_exists_true(self, mock_get_clusters):
        """Test cluster existence check when cluster exists."""
        mock_get_clusters.return_value = ["cluster1", "test-cluster", "cluster2"]

        runner = KindCommandRunner()
        assert runner.cluster_exists("test-cluster") is True

    @patch.object(KindCommandRunner, "get_clusters")
    def test_cluster_exists_false(self, mock_get_clusters):
        """Test cluster existence check when cluster doesn't exist."""
        mock_get_clusters.return_value = ["cluster1", "cluster2"]

        runner = KindCommandRunner()
        assert runner.cluster_exists("test-cluster") is False

    @patch.object(KindCommandRunner, "get_clusters")
    def test_cluster_exists_error(self, mock_get_clusters):
        """Test cluster existence check with error."""
        mock_get_clusters.side_effect = KindClusterError("Get clusters failed")

        runner = KindCommandRunner()
        assert runner.cluster_exists("test-cluster") is False

    @patch.object(KindCommandRunner, "run")
    def test_create_cluster_basic(self, mock_run):
        """Test basic cluster creation."""
        runner = KindCommandRunner()
        runner.create_cluster("test-cluster")

        expected_cmd = [
            "kind",
            "create",
            "cluster",
            "--name",
            "test-cluster",
            "--wait=60s",
        ]
        mock_run.assert_called_once_with(expected_cmd)

    @patch.object(KindCommandRunner, "run")
    def test_create_cluster_with_config(self, mock_run):
        """Test cluster creation with config file."""
        runner = KindCommandRunner()
        runner.create_cluster(
            "test-cluster", config_path="/tmp/config.yaml", wait_timeout=120
        )

        expected_cmd = [
            "kind",
            "create",
            "cluster",
            "--name",
            "test-cluster",
            "--config",
            "/tmp/config.yaml",
            "--wait=120s",
        ]
        mock_run.assert_called_once_with(expected_cmd)

    @patch.object(KindCommandRunner, "run")
    def test_create_cluster_with_kwargs(self, mock_run):
        """Test cluster creation with additional kwargs."""
        runner = KindCommandRunner()
        runner.create_cluster("test-cluster", timeout=600, capture_output=False)

        expected_cmd = [
            "kind",
            "create",
            "cluster",
            "--name",
            "test-cluster",
            "--wait=60s",
        ]
        mock_run.assert_called_once_with(
            expected_cmd, timeout=600, capture_output=False
        )

    @patch.object(KindCommandRunner, "run")
    def test_delete_cluster(self, mock_run):
        """Test cluster deletion."""
        runner = KindCommandRunner()
        runner.delete_cluster("test-cluster")

        expected_cmd = ["kind", "delete", "cluster", "--name", "test-cluster"]
        mock_run.assert_called_once_with(expected_cmd)

    @patch.object(KindCommandRunner, "run")
    def test_delete_cluster_with_kwargs(self, mock_run):
        """Test cluster deletion with additional kwargs."""
        runner = KindCommandRunner()
        runner.delete_cluster("test-cluster", timeout=120)

        expected_cmd = ["kind", "delete", "cluster", "--name", "test-cluster"]
        mock_run.assert_called_once_with(expected_cmd, timeout=120)

    @patch.object(KindCommandRunner, "run")
    def test_export_kubeconfig(self, mock_run):
        """Test kubeconfig export."""
        runner = KindCommandRunner()
        runner.export_kubeconfig("test-cluster", "/tmp/kubeconfig.yaml")

        expected_cmd = [
            "kind",
            "export",
            "kubeconfig",
            "--name",
            "test-cluster",
            "--kubeconfig",
            "/tmp/kubeconfig.yaml",
        ]
        mock_run.assert_called_once_with(expected_cmd)

    @patch.object(KindCommandRunner, "run")
    def test_export_kubeconfig_with_kwargs(self, mock_run):
        """Test kubeconfig export with additional kwargs."""
        runner = KindCommandRunner()
        runner.export_kubeconfig("test-cluster", "/tmp/kubeconfig.yaml", timeout=120)

        expected_cmd = [
            "kind",
            "export",
            "kubeconfig",
            "--name",
            "test-cluster",
            "--kubeconfig",
            "/tmp/kubeconfig.yaml",
        ]
        mock_run.assert_called_once_with(expected_cmd, timeout=120)


class TestKubectlCommandRunner:
    """Test cases for KubectlCommandRunner class."""

    def test_init_default(self):
        """Test KubectlCommandRunner initialization with defaults."""
        runner = KubectlCommandRunner()
        assert runner.default_timeout == 30
        assert runner.kubeconfig_path is None

    def test_init_with_kubeconfig(self):
        """Test KubectlCommandRunner initialization with kubeconfig."""
        runner = KubectlCommandRunner(
            kubeconfig_path="/tmp/kubeconfig.yaml", default_timeout=60
        )
        assert runner.default_timeout == 60
        assert runner.kubeconfig_path == "/tmp/kubeconfig.yaml"

    @patch.object(KubectlCommandRunner, "run")
    def test_run_kubectl_basic(self, mock_run):
        """Test basic kubectl command execution."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = KubectlCommandRunner()
        result = runner.run_kubectl(["get", "nodes"])

        assert result == mock_result
        mock_run.assert_called_once_with(["kubectl", "get", "nodes"], env={})

    @patch.object(KubectlCommandRunner, "run")
    def test_run_kubectl_with_kubeconfig(self, mock_run):
        """Test kubectl command with kubeconfig."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = KubectlCommandRunner(kubeconfig_path="/tmp/kubeconfig.yaml")
        result = runner.run_kubectl(["get", "nodes"])

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["kubectl", "get", "nodes"], env={"KUBECONFIG": "/tmp/kubeconfig.yaml"}
        )

    @patch.object(KubectlCommandRunner, "run")
    def test_run_kubectl_override_kubeconfig(self, mock_run):
        """Test kubectl command with kubeconfig override."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = KubectlCommandRunner(kubeconfig_path="/tmp/default.yaml")
        result = runner.run_kubectl(
            ["get", "nodes"], kubeconfig_path="/tmp/override.yaml"
        )

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["kubectl", "get", "nodes"], env={"KUBECONFIG": "/tmp/override.yaml"}
        )

    @patch.object(KubectlCommandRunner, "run")
    def test_run_kubectl_with_existing_env(self, mock_run):
        """Test kubectl command with existing environment variables."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = KubectlCommandRunner(kubeconfig_path="/tmp/kubeconfig.yaml")
        result = runner.run_kubectl(["get", "nodes"], env={"EXISTING_VAR": "value"})

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["kubectl", "get", "nodes"],
            env={"EXISTING_VAR": "value", "KUBECONFIG": "/tmp/kubeconfig.yaml"},
        )

    @patch.object(KubectlCommandRunner, "run")
    def test_run_kubectl_with_kwargs(self, mock_run):
        """Test kubectl command with additional kwargs."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = KubectlCommandRunner()
        result = runner.run_kubectl(["get", "nodes"], timeout=120, capture_output=False)

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["kubectl", "get", "nodes"], env={}, timeout=120, capture_output=False
        )

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_get_nodes_success(self, mock_run_kubectl):
        """Test getting nodes successfully."""
        mock_result = Mock()
        mock_result.stdout = "node/control-plane\nnode/worker-1\nnode/worker-2"
        mock_run_kubectl.return_value = mock_result

        runner = KubectlCommandRunner()
        nodes = runner.get_nodes()

        assert nodes == ["control-plane", "worker-1", "worker-2"]
        mock_run_kubectl.assert_called_once_with(["get", "nodes", "-o", "name"])

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_get_nodes_empty(self, mock_run_kubectl):
        """Test getting nodes when none exist."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run_kubectl.return_value = mock_result

        runner = KubectlCommandRunner()
        nodes = runner.get_nodes()

        assert nodes == []

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_get_nodes_with_kwargs(self, mock_run_kubectl):
        """Test getting nodes with additional kwargs."""
        mock_result = Mock()
        mock_result.stdout = "node/test-node"
        mock_run_kubectl.return_value = mock_result

        runner = KubectlCommandRunner()
        nodes = runner.get_nodes(timeout=120)

        assert nodes == ["test-node"]
        mock_run_kubectl.assert_called_once_with(
            ["get", "nodes", "-o", "name"], timeout=120
        )

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_cluster_ready_true(self, mock_run_kubectl):
        """Test cluster readiness check when cluster is ready."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run_kubectl.return_value = mock_result

        runner = KubectlCommandRunner()
        assert runner.cluster_ready() is True

        mock_run_kubectl.assert_called_once_with(["get", "nodes"], check=True)

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_cluster_ready_false(self, mock_run_kubectl):
        """Test cluster readiness check when cluster is not ready."""
        mock_run_kubectl.side_effect = subprocess.CalledProcessError(1, ["kubectl"])

        runner = KubectlCommandRunner()
        assert runner.cluster_ready() is False

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_cluster_ready_kind_cluster_error(self, mock_run_kubectl):
        """Test cluster readiness check with KindClusterError."""
        mock_run_kubectl.side_effect = KindClusterError("Connection failed")

        runner = KubectlCommandRunner()
        assert runner.cluster_ready() is False

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_cluster_ready_with_kwargs(self, mock_run_kubectl):
        """Test cluster readiness check with additional kwargs."""
        mock_result = Mock()
        mock_run_kubectl.return_value = mock_result

        runner = KubectlCommandRunner()
        runner.cluster_ready(timeout=60)

        mock_run_kubectl.assert_called_once_with(
            ["get", "nodes"], check=True, timeout=60
        )


class TestCommandRunnerEdgeCases:
    """Test edge cases and error conditions for command runners."""

    @patch("subprocess.run")
    def test_run_with_unicode_input(self, mock_run):
        """Test command execution with unicode input data."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = CommandRunner()
        unicode_input = "test 测试 🚀"

        result = runner.run(["cat"], input_data=unicode_input)

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["cat"],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
            env=None,
            cwd=None,
            input=unicode_input,
        )

    @patch("subprocess.run")
    def test_run_with_very_long_command(self, mock_run):
        """Test command execution with very long command line."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = CommandRunner()
        long_cmd = ["echo"] + ["x" * 1000 for _ in range(10)]  # Very long command

        result = runner.run(long_cmd)

        assert result == mock_result
        mock_run.assert_called_once_with(
            long_cmd,
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
            env=None,
            cwd=None,
            input=None,
        )

    @patch("subprocess.run")
    def test_run_with_empty_env(self, mock_run):
        """Test command execution with empty environment."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        runner = CommandRunner()
        result = runner.run(["echo", "test"], env={})

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["echo", "test"],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
            env={},
            cwd=None,
            input=None,
        )

    def test_run_with_retry_zero_retries(self):
        """Test retry logic with zero retries."""
        runner = CommandRunner()

        with patch.object(runner, "run") as mock_run:
            error = subprocess.CalledProcessError(1, ["test"])
            mock_run.side_effect = error

            with pytest.raises(subprocess.CalledProcessError):
                runner.run_with_retry(["test"], max_retries=0)

            mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch("time.sleep")
    def test_run_with_retry_negative_delay(self, mock_sleep, mock_run):
        """Test retry logic with negative delay (should work)."""
        error = subprocess.CalledProcessError(1, ["test"])
        mock_result = Mock()
        mock_run.side_effect = [error, mock_result]

        runner = CommandRunner()
        result = runner.run_with_retry(
            ["test"],
            max_retries=1,
            retry_delay=-1.0,  # Negative delay
        )

        assert result == mock_result
        mock_sleep.assert_called_once_with(
            -1.0
        )  # Should still call sleep with negative value

    def test_get_command_lines_single_line(self):
        """Test getting command lines with single line output."""
        runner = CommandRunner()

        with patch.object(runner, "get_command_output") as mock_get_output:
            mock_get_output.return_value = "single line"
            lines = runner.get_command_lines(["echo", "test"])
            assert lines == ["single line"]

    def test_get_command_lines_trailing_newlines(self):
        """Test getting command lines with trailing newlines."""
        runner = CommandRunner()

        with patch.object(runner, "get_command_output") as mock_get_output:
            mock_get_output.return_value = "line1\nline2\n\n\n"
            lines = runner.get_command_lines(["echo", "test"], filter_empty=True)
            assert lines == ["line1", "line2"]

    def test_kind_command_runner_prerequisites_state_reset(self):
        """Test that availability checks can change state."""
        runner = KindCommandRunner()

        with patch.object(runner, "check_command_available") as mock_check:
            # First check: available
            mock_check.return_value = True
            assert runner.check_kind_available() is True
            assert runner._kind_available is True

            # Reset state and check again: not available
            runner._kind_available = None
            mock_check.return_value = False
            assert runner.check_kind_available() is False
            assert runner._kind_available is False

    def test_get_clusters_real_implementation(self):
        """Test get_clusters with actual implementation logic."""
        runner = KindCommandRunner()

        # Test successful case
        with patch.object(runner, "run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "cluster1\ncluster2\n"
            mock_run.return_value = mock_result

            clusters = runner.get_clusters()
            assert clusters == ["cluster1", "cluster2"]

        # Test "No kind clusters found" case
        with patch.object(runner, "run") as mock_run:
            error = subprocess.CalledProcessError(1, ["kind"])
            error.stderr = "No kind clusters found"
            mock_run.side_effect = error

            clusters = runner.get_clusters()
            assert clusters == []

        # Test other error case
        with patch.object(runner, "run") as mock_run:
            error = subprocess.CalledProcessError(1, ["kind"])
            error.stderr = "Some other error"
            mock_run.side_effect = error

            with pytest.raises(KindClusterError, match="Failed to get cluster list"):
                runner.get_clusters()

    @patch.object(KubectlCommandRunner, "run")
    def test_kubectl_env_merging_complex(self, mock_run):
        """Test complex environment variable merging in kubectl runner."""
        mock_result = Mock()
        mock_run.return_value = mock_result

        # Start with system environment
        original_env = os.environ.copy()
        original_env.update({"SYSTEM_VAR": "system_value"})

        with patch.dict(os.environ, original_env, clear=True):
            runner = KubectlCommandRunner(kubeconfig_path="/tmp/kubeconfig.yaml")

            # Pass additional env vars
            runner.run_kubectl(
                ["get", "nodes"],
                env={
                    "CUSTOM_VAR": "custom_value",
                    "KUBECONFIG": "should_be_overridden",  # This should be overridden
                },
            )

            # Check that the final env has the right precedence
            expected_env = {
                "CUSTOM_VAR": "custom_value",
                "KUBECONFIG": "/tmp/kubeconfig.yaml",  # Should override passed value
            }

            mock_run.assert_called_once_with(
                ["kubectl", "get", "nodes"], env=expected_env
            )

    def test_kubectl_no_kubeconfig_no_override(self):
        """Test kubectl runner with no kubeconfig set anywhere."""
        runner = KubectlCommandRunner()

        with patch.object(runner, "run") as mock_run:
            mock_result = Mock()
            mock_run.return_value = mock_result

            runner.run_kubectl(["get", "nodes"])

            mock_run.assert_called_once_with(["kubectl", "get", "nodes"], env={})

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_get_nodes_whitespace_handling(self, mock_run_kubectl):
        """Test node parsing with various whitespace scenarios."""
        mock_result = Mock()
        mock_result.stdout = (
            "  node/control-plane  \n\nnode/worker-1\n  \nnode/worker-2  \n"
        )
        mock_run_kubectl.return_value = mock_result

        runner = KubectlCommandRunner()
        nodes = runner.get_nodes()

        # Implementation now strips all whitespace from node names after removing 'node/' prefix
        assert nodes == ["control-plane", "worker-1", "worker-2"]

    @patch.object(KubectlCommandRunner, "run_kubectl")
    def test_get_nodes_no_node_prefix(self, mock_run_kubectl):
        """Test node parsing when output doesn't have 'node/' prefix."""
        mock_result = Mock()
        mock_result.stdout = "control-plane\nworker-1\nworker-2"
        mock_run_kubectl.return_value = mock_result

        runner = KubectlCommandRunner()
        nodes = runner.get_nodes()

        # Should handle nodes without the 'node/' prefix
        assert nodes == ["control-plane", "worker-1", "worker-2"]

    def test_command_runner_timeout_precedence(self):
        """Test timeout precedence in command runner."""
        runner = CommandRunner(default_timeout=600)

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_run.return_value = mock_result

            # Test default timeout
            runner.run(["echo", "test"])
            mock_run.assert_called_with(
                ["echo", "test"],
                capture_output=True,
                text=True,
                timeout=600,  # Should use default
                check=True,
                env=None,
                cwd=None,
                input=None,
            )

            # Test explicit timeout override
            mock_run.reset_mock()
            runner.run(["echo", "test"], timeout=120)
            mock_run.assert_called_with(
                ["echo", "test"],
                capture_output=True,
                text=True,
                timeout=120,  # Should use explicit value
                check=True,
                env=None,
                cwd=None,
                input=None,
            )
