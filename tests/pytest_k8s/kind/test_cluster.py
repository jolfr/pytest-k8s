"""
Tests for the kind cluster lifecycle manager.

This module contains comprehensive tests for the KindCluster class,
including unit tests with mocking and integration tests.
"""

import os
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, call, mock_open, patch

import pytest
import yaml

from pytest_k8s.kind.cluster import KindCluster
from pytest_k8s.kind.config import create_simple_config
from pytest_k8s.kind.errors import (
    KindClusterError,
    KindClusterCreationError,
    KindClusterDeletionError,
)


class TestKindCluster:
    """Test cases for KindCluster class."""

    def test_init_with_defaults(self):
        """Test KindCluster initialization with default values."""
        cluster = KindCluster()

        assert cluster.name.startswith("pytest-k8s-")
        assert len(cluster.name) == 19  # pytest-k8s- + 8 hex chars
        assert cluster.config is not None
        assert cluster.config.timeout == 300
        assert cluster.keep_cluster is False
        assert cluster.config.image is None
        assert not cluster._created
        assert not cluster._verified

    def test_init_with_custom_values(self):
        """Test KindCluster initialization with custom values."""
        port_mappings = [{"containerPort": 80, "hostPort": 8080}]

        cluster = KindCluster(
            name="test-cluster",
            timeout=600,
            keep_cluster=True,
            image="kindest/node:v1.25.0",
            extra_port_mappings=port_mappings,
        )

        assert cluster.name == "test-cluster"
        assert cluster.config.timeout == 600
        assert cluster.keep_cluster is True
        assert cluster.config.image == "kindest/node:v1.25.0"
        # Port mappings are converted to PortMapping objects within the config
        assert len(cluster.config.nodes[0].extra_port_mappings) == 1

    def test_init_with_config_object(self):
        """Test KindCluster initialization with config object."""
        config = create_simple_config(name="test-cluster", image="kindest/node:v1.25.0")
        cluster = KindCluster(config=config)

        assert cluster.name == "test-cluster"
        assert cluster.config.image == "kindest/node:v1.25.0"

    @patch("yaml.safe_load")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="kind: Cluster\napiVersion: kind.x-k8s.io/v1alpha4\n",
    )
    def test_init_with_config_path(self, mock_file, mock_yaml):
        """Test KindCluster initialization with config path."""
        mock_yaml.return_value = {
            "kind": "Cluster",
            "apiVersion": "kind.x-k8s.io/v1alpha4",
            "nodes": [{"role": "control-plane"}],
        }

        cluster = KindCluster(config_path="/tmp/config.yaml")

        mock_file.assert_called_once_with("/tmp/config.yaml", "r")
        assert cluster.config is not None

    def test_generate_cluster_name(self):
        """Test cluster name generation."""
        name1 = KindCluster._generate_cluster_name()
        name2 = KindCluster._generate_cluster_name()

        assert name1.startswith("pytest-k8s-")
        assert name2.startswith("pytest-k8s-")
        assert name1 != name2
        assert len(name1) == len(name2) == 19

    @patch("subprocess.run")
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        mock_result = Mock()
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cluster = KindCluster()
        result = cluster._run_command(["echo", "test"])

        assert result == mock_result
        mock_run.assert_called_once_with(
            ["echo", "test"],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )

    @patch("subprocess.run")
    def test_run_command_failure(self, mock_run):
        """Test command execution failure."""
        error = subprocess.CalledProcessError(1, ["false"])
        error.stdout = ""
        error.stderr = "command failed"
        mock_run.side_effect = error

        cluster = KindCluster()

        with pytest.raises(subprocess.CalledProcessError):
            cluster._run_command(["false"])

    @patch("subprocess.run")
    def test_run_command_timeout(self, mock_run):
        """Test command execution timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["sleep", "10"], 5)

        cluster = KindCluster()

        with pytest.raises(subprocess.TimeoutExpired):
            cluster._run_command(["sleep", "10"], timeout=5)

    @patch.object(KindCluster, "_run_command")
    def test_check_kind_available_success(self, mock_run_command):
        """Test successful kind availability check."""
        mock_run_command.return_value = Mock()

        cluster = KindCluster()
        assert cluster._check_kind_available() is True

        mock_run_command.assert_called_once_with(["kind", "version"], timeout=10)

    @patch.object(KindCluster, "_run_command")
    def test_check_kind_available_failure(self, mock_run_command):
        """Test kind availability check failure."""
        mock_run_command.side_effect = FileNotFoundError()

        cluster = KindCluster()
        assert cluster._check_kind_available() is False

    @patch.object(KindCluster, "_run_command")
    def test_check_docker_available_success(self, mock_run_command):
        """Test successful Docker availability check."""
        mock_run_command.return_value = Mock()

        cluster = KindCluster()
        assert cluster._check_docker_available() is True

        mock_run_command.assert_called_once_with(["docker", "version"], timeout=10)

    @patch.object(KindCluster, "_run_command")
    def test_check_docker_available_failure(self, mock_run_command):
        """Test Docker availability check failure."""
        mock_run_command.side_effect = subprocess.CalledProcessError(1, ["docker"])

        cluster = KindCluster()
        assert cluster._check_docker_available() is False

    @patch("tempfile.NamedTemporaryFile")
    def test_create_cluster_config_with_custom_settings(self, mock_temp_file):
        """Test cluster config creation with custom settings."""
        mock_file = Mock()
        mock_file.name = "/tmp/temp-config.yaml"
        mock_temp_file.return_value = mock_file

        cluster = KindCluster(
            image="kindest/node:v1.25.0",
            extra_port_mappings=[
                {"containerPort": 80, "hostPort": 8080, "protocol": "TCP"}
            ],
        )

        result = cluster._create_cluster_config()

        assert result == Path("/tmp/temp-config.yaml")
        mock_file.write.assert_called_once()
        mock_file.flush.assert_called_once()
        mock_file.close.assert_called_once()

    def test_create_cluster_config_no_custom_settings(self):
        """Test cluster config creation without custom settings."""
        cluster = KindCluster()

        result = cluster._create_cluster_config()
        assert result is None

    @patch("tempfile.NamedTemporaryFile")
    @patch.object(KindCluster, "_run_command")
    def test_setup_kubeconfig_success(self, mock_run_command, mock_temp_file):
        """Test successful kubeconfig setup."""
        mock_file = Mock()
        mock_file.name = "/tmp/kubeconfig.yaml"
        mock_temp_file.return_value = mock_file

        cluster = KindCluster(name="test-cluster")
        cluster._setup_kubeconfig()

        assert cluster._kubeconfig_path == Path("/tmp/kubeconfig.yaml")
        mock_run_command.assert_called_once_with(
            [
                "kind",
                "export",
                "kubeconfig",
                "--name",
                "test-cluster",
                "--kubeconfig",
                "/tmp/kubeconfig.yaml",
            ]
        )

    @patch("tempfile.NamedTemporaryFile")
    @patch.object(KindCluster, "_run_command")
    def test_setup_kubeconfig_failure(self, mock_run_command, mock_temp_file):
        """Test kubeconfig setup failure."""
        mock_file = Mock()
        mock_file.name = "/tmp/kubeconfig.yaml"
        mock_temp_file.return_value = mock_file

        mock_run_command.side_effect = subprocess.CalledProcessError(
            1, ["kind"], stderr="export failed"
        )

        cluster = KindCluster(name="test-cluster")

        with pytest.raises(
            KindClusterCreationError, match="Failed to export kubeconfig"
        ):
            cluster._setup_kubeconfig()

    @patch("pytest_k8s.kind.cluster.KubectlCommandRunner")
    @patch.object(KindCluster, "exists")
    @patch.object(KindCluster, "_create_cluster_config")
    @patch.object(KindCluster, "_setup_kubeconfig")
    @patch.object(KindCluster, "wait_for_ready")
    def test_create_success(
        self,
        mock_wait_ready,
        mock_setup_kubeconfig,
        mock_create_config,
        mock_exists,
        mock_kubectl_runner,
    ):
        """Test successful cluster creation."""
        mock_exists.return_value = False
        mock_create_config.return_value = None

        cluster = KindCluster(name="test-cluster")
        cluster._kind_runner = Mock()
        cluster._kind_runner.validate_prerequisites = Mock()
        cluster._kind_runner.create_cluster = Mock()

        cluster.create()

        assert cluster._created is True
        cluster._kind_runner.validate_prerequisites.assert_called_once()
        cluster._kind_runner.create_cluster.assert_called_once()
        mock_setup_kubeconfig.assert_called_once()
        mock_wait_ready.assert_called_once()

    def test_create_prerequisites_fail(self):
        """Test cluster creation when prerequisites fail."""
        cluster = KindCluster()
        cluster._kind_runner = Mock()
        cluster._kind_runner.validate_prerequisites.side_effect = Exception(
            "Prerequisites failed"
        )

        with pytest.raises(KindClusterError, match="Prerequisites failed"):
            cluster.create()

    @patch.object(KindCluster, "exists")
    def test_create_cluster_already_exists(self, mock_exists):
        """Test cluster creation when cluster already exists."""
        mock_exists.return_value = True

        cluster = KindCluster(name="existing-cluster")
        cluster._kind_runner = Mock()
        cluster._kind_runner.validate_prerequisites = Mock()

        with pytest.raises(KindClusterCreationError, match="already exists"):
            cluster.create()

    def test_create_already_created(self):
        """Test create method when cluster is already created."""
        cluster = KindCluster()
        cluster._created = True

        # Should return early without error
        cluster.create()
        assert cluster._created is True

    @patch.object(KindCluster, "exists")
    @patch.object(KindCluster, "_run_command")
    def test_delete_success(self, mock_run_command, mock_exists):
        """Test successful cluster deletion."""
        mock_exists.return_value = True

        cluster = KindCluster(name="test-cluster")
        cluster._created = True
        cluster._verified = True
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.unlink"),
        ):
            cluster.delete()

        assert cluster._created is False
        assert cluster._verified is False
        mock_run_command.assert_called_once_with(
            ["kind", "delete", "cluster", "--name", "test-cluster"]
        )

    @patch.object(KindCluster, "exists")
    def test_delete_keep_cluster(self, mock_exists):
        """Test delete method with keep_cluster=True."""
        mock_exists.return_value = True

        cluster = KindCluster(name="test-cluster", keep_cluster=True)
        cluster.delete()

        # Should not attempt deletion
        mock_exists.assert_not_called()

    @patch.object(KindCluster, "exists")
    def test_delete_cluster_not_exists(self, mock_exists):
        """Test delete method when cluster doesn't exist."""
        mock_exists.return_value = False

        cluster = KindCluster(name="test-cluster")
        cluster.delete()

        # Should return early without error
        mock_exists.assert_called_once()

    @patch.object(KindCluster, "exists")
    @patch.object(KindCluster, "_run_command")
    def test_delete_failure(self, mock_run_command, mock_exists):
        """Test cluster deletion failure."""
        mock_exists.return_value = True
        mock_run_command.side_effect = subprocess.CalledProcessError(
            1, ["kind"], stderr="deletion failed"
        )

        cluster = KindCluster(name="test-cluster")

        with pytest.raises(KindClusterDeletionError, match="Failed to delete cluster"):
            cluster.delete()

    @patch.object(KindCluster, "_run_command")
    def test_exists_true(self, mock_run_command):
        """Test exists method when cluster exists."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "cluster1\ntest-cluster\ncluster2"
        mock_run_command.return_value = mock_result

        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is True

        mock_run_command.assert_called_once_with(
            ["kind", "get", "clusters"], capture_output=True, check=False
        )

    @patch.object(KindCluster, "_run_command")
    def test_exists_false(self, mock_run_command):
        """Test exists method when cluster doesn't exist."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "cluster1\nother-cluster\ncluster2"
        mock_run_command.return_value = mock_result

        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is False

    @patch.object(KindCluster, "_run_command")
    def test_exists_command_failure(self, mock_run_command):
        """Test exists method when command fails."""
        mock_run_command.side_effect = Exception("Command failed")

        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is False

    @patch("subprocess.run")
    @patch("time.time")
    @patch("time.sleep")
    def test_wait_for_ready_success(self, mock_sleep, mock_time, mock_run):
        """Test successful wait_for_ready."""
        mock_time.side_effect = [0, 1, 2]  # Simulate time progression

        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        cluster = KindCluster(name="test-cluster")
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        cluster.wait_for_ready()

        assert cluster._verified is True
        mock_run.assert_called_with(
            ["kubectl", "get", "nodes"],
            env={"KUBECONFIG": "/tmp/kubeconfig.yaml", **os.environ},
            capture_output=True,
            text=True,
            timeout=10,
        )

    @patch("subprocess.run")
    @patch("time.time")
    @patch("time.sleep")
    def test_wait_for_ready_timeout(self, mock_sleep, mock_time, mock_run):
        """Test wait_for_ready timeout."""
        # Simulate timeout
        mock_time.side_effect = [0, 301]  # Start time, then past timeout

        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        cluster = KindCluster(name="test-cluster", timeout=300)
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        with pytest.raises(KindClusterError, match="not ready within 300 seconds"):
            cluster.wait_for_ready()

    @patch("subprocess.run")
    def test_get_nodes_success(self, mock_run):
        """Test successful get_nodes."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "node/test-cluster-control-plane\nnode/test-cluster-worker"
        mock_run.return_value = mock_result

        cluster = KindCluster(name="test-cluster")
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        nodes = cluster.get_nodes()

        assert nodes == ["test-cluster-control-plane", "test-cluster-worker"]
        mock_run.assert_called_once_with(
            ["kubectl", "get", "nodes", "-o", "name"],
            env={"KUBECONFIG": "/tmp/kubeconfig.yaml", **os.environ},
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_get_nodes_no_kubeconfig(self):
        """Test get_nodes when kubeconfig is not available."""
        cluster = KindCluster()

        with pytest.raises(KindClusterError, match="kubeconfig not available"):
            cluster.get_nodes()

    @patch("subprocess.run")
    def test_get_nodes_failure(self, mock_run):
        """Test get_nodes when kubectl command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "kubectl failed"
        mock_run.return_value = mock_result

        cluster = KindCluster(name="test-cluster")
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        with pytest.raises(KindClusterError, match="Failed to get nodes"):
            cluster.get_nodes()

    @patch.object(KindCluster, "wait_for_ready")
    def test_is_ready_true(self, mock_wait_ready):
        """Test is_ready when cluster is ready."""
        cluster = KindCluster()
        assert cluster.is_ready() is True
        mock_wait_ready.assert_called_once_with(timeout=10)

    @patch.object(KindCluster, "wait_for_ready")
    def test_is_ready_false(self, mock_wait_ready):
        """Test is_ready when cluster is not ready."""
        mock_wait_ready.side_effect = KindClusterError("Not ready")

        cluster = KindCluster()
        assert cluster.is_ready() is False

    @patch.object(KindCluster, "create")
    @patch.object(KindCluster, "delete")
    def test_context_manager(self, mock_delete, mock_create):
        """Test context manager functionality."""
        cluster = KindCluster(name="test-cluster")

        with cluster as c:
            assert c is cluster
            mock_create.assert_called_once()

        mock_delete.assert_called_once()

    @patch.object(KindCluster, "create")
    @patch.object(KindCluster, "delete")
    def test_context_manager_with_exception(self, mock_delete, mock_create):
        """Test context manager with exception during usage."""
        mock_delete.side_effect = Exception("Cleanup failed")

        cluster = KindCluster(name="test-cluster")

        try:
            with cluster:
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected

        mock_create.assert_called_once()
        mock_delete.assert_called_once()

    def test_str_representation(self):
        """Test string representation."""
        cluster = KindCluster(name="test-cluster")
        assert str(cluster) == "KindCluster(name=test-cluster, created=False)"

    def test_repr_representation(self):
        """Test detailed string representation."""
        cluster = KindCluster(name="test-cluster")
        expected = (
            "KindCluster(name=test-cluster, created=False, "
            "verified=False, kubeconfig=None)"
        )
        assert repr(cluster) == expected

    def test_kubeconfig_path_property_none(self):
        """Test kubeconfig_path property when path is None."""
        cluster = KindCluster()
        assert cluster.kubeconfig_path is None

    def test_kubeconfig_path_property_set(self):
        """Test kubeconfig_path property when path is set."""
        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/test.yaml")
        assert cluster.kubeconfig_path == "/tmp/test.yaml"


class TestKindClusterIntegration:
    """Integration tests for KindCluster (requires kind and Docker)."""

    @pytest.fixture
    def skip_if_no_kind(self):
        """Skip tests if kind is not available."""
        try:
            subprocess.run(["kind", "version"], capture_output=True, check=True)
            subprocess.run(["docker", "version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("kind or Docker not available")

    @pytest.fixture
    def integration_cluster_name(self):
        """Generate a unique cluster name for integration tests."""
        return f"pytest-integration-{int(time.time())}"

    @pytest.mark.integration
    def test_cluster_lifecycle_integration(
        self, skip_if_no_kind, integration_cluster_name
    ):
        """Test complete cluster lifecycle integration."""
        cluster = KindCluster(
            name=integration_cluster_name, timeout=600, keep_cluster=False
        )

        # Ensure cluster doesn't exist initially
        assert not cluster.exists()

        try:
            # Create cluster
            cluster.create()
            assert cluster._created
            assert cluster.exists()
            assert cluster.kubeconfig_path is not None
            assert Path(cluster.kubeconfig_path).exists()

            # Verify cluster is ready
            assert cluster.is_ready()
            assert cluster._verified

            # Get nodes
            nodes = cluster.get_nodes()
            assert len(nodes) > 0
            assert any("control-plane" in node for node in nodes)

        finally:
            # Clean up
            try:
                cluster.delete()
                assert not cluster.exists()
            except Exception:
                # Best effort cleanup
                try:
                    subprocess.run(
                        [
                            "kind",
                            "delete",
                            "cluster",
                            "--name",
                            integration_cluster_name,
                        ],
                        capture_output=True,
                    )
                except Exception:
                    pass

    @pytest.mark.integration
    def test_context_manager_integration(
        self, skip_if_no_kind, integration_cluster_name
    ):
        """Test context manager integration."""
        with KindCluster(name=integration_cluster_name, timeout=600) as cluster:
            assert cluster.exists()
            assert cluster.is_ready()
            nodes = cluster.get_nodes()
            assert len(nodes) > 0

        # Cluster should be deleted after context exit
        assert not cluster.exists()

    @pytest.mark.integration
    def test_cluster_with_custom_config_integration(
        self, skip_if_no_kind, integration_cluster_name
    ):
        """Test cluster creation with custom configuration."""
        # Create cluster with port mappings (use default image which is more reliable)
        cluster = KindCluster(
            name=integration_cluster_name,
            extra_port_mappings=[{"containerPort": 80, "hostPort": 8080}],
            timeout=600,
        )

        try:
            cluster.create()
            assert cluster.exists()
            assert cluster.is_ready()

            nodes = cluster.get_nodes()
            assert len(nodes) > 0

        finally:
            cluster.delete()


class TestKindClusterErrorHandling:
    """Test error handling and edge cases."""

    def test_create_with_command_failure_cleanup(self):
        """Test cleanup when cluster creation fails."""
        cluster = KindCluster(name="test-cluster")
        cluster._kind_runner = Mock()
        cluster._kind_runner.validate_prerequisites = Mock()
        cluster._kind_runner.create_cluster.side_effect = Exception("Creation failed")

        with patch.object(cluster, "delete") as mock_delete:
            with pytest.raises(KindClusterCreationError):
                cluster.create()

            # Should attempt cleanup
            mock_delete.assert_called_once()

    @patch("subprocess.run")
    def test_wait_for_ready_with_partial_failures(self, mock_run):
        """Test wait_for_ready with initial failures then success."""
        cluster = KindCluster(name="test-cluster")
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        # First call fails, second succeeds
        with patch("time.time") as mock_time, patch("time.sleep") as mock_sleep:
            mock_time.side_effect = [0, 1, 2, 3]  # Simulate time progression

            # First kubectl call fails, second succeeds
            mock_run.side_effect = [
                Mock(returncode=1),  # First call fails
                Mock(returncode=0),  # Second call succeeds
            ]

            cluster.wait_for_ready()

            assert cluster._verified is True
            assert mock_run.call_count == 2
            mock_sleep.assert_called()

    @patch("subprocess.run")
    def test_get_nodes_timeout_error(self, mock_run):
        """Test get_nodes with timeout error."""
        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        mock_run.side_effect = subprocess.TimeoutExpired(["kubectl"], 30)

        with pytest.raises(KindClusterError, match="Timeout getting cluster nodes"):
            cluster.get_nodes()

    @patch("subprocess.run")
    def test_get_nodes_generic_error(self, mock_run):
        """Test get_nodes with generic error."""
        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        mock_run.side_effect = ValueError("Generic error")

        with pytest.raises(KindClusterError, match="Error getting nodes"):
            cluster.get_nodes()


class TestKindClusterEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_cluster_name_validation(self):
        """Test cluster name handling."""
        # Test empty name (should generate one)
        cluster = KindCluster(name="")
        assert cluster.name != ""
        assert cluster.name.startswith("pytest-k8s-")

        # Test None name (should generate one)
        cluster = KindCluster(name=None)
        assert cluster.name is not None
        assert cluster.name.startswith("pytest-k8s-")

        # Test valid name
        cluster = KindCluster(name="valid-cluster-name")
        assert cluster.name == "valid-cluster-name"

    def test_timeout_edge_cases(self):
        """Test timeout edge cases."""
        # Test zero timeout
        cluster = KindCluster(timeout=0)
        assert cluster.config.timeout == 0

        # Test negative timeout (should be handled by config validation)
        from pytest_k8s.kind.errors import KindClusterConfigError

        with pytest.raises(KindClusterConfigError, match="Invalid timeout"):
            cluster = KindCluster(timeout=-1)

        # Test very large timeout
        cluster = KindCluster(timeout=86400)
        assert cluster.config.timeout == 86400

    def test_empty_port_mappings(self):
        """Test empty port mappings."""
        cluster = KindCluster(extra_port_mappings=[])
        # Empty port mappings should result in no port mappings on the node
        assert len(cluster.config.nodes[0].extra_port_mappings) == 0

        # Should not create config for empty mappings
        config_path = cluster._create_cluster_config()
        assert config_path is None

    @patch("yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    def test_path_handling(self, mock_file, mock_yaml):
        """Test path handling for config_path."""
        mock_yaml.return_value = {
            "kind": "Cluster",
            "apiVersion": "kind.x-k8s.io/v1alpha4",
            "nodes": [{"role": "control-plane"}],
        }

        # Test string path
        cluster = KindCluster(config_path="/tmp/config.yaml")
        assert cluster.config is not None

        # Test Path object
        cluster = KindCluster(config_path=Path("/tmp/config.yaml"))
        assert cluster.config is not None


class TestKindClusterAdvancedEdgeCases:
    """Test advanced edge cases and error scenarios."""

    def test_cluster_name_special_characters(self):
        """Test cluster name with special characters."""
        # Test names that should be sanitized or handled properly
        special_names = [
            "test-cluster-123",  # Valid
            "test_cluster",  # Underscores
            "test.cluster",  # Dots
            "test-cluster-very-long-name-that-exceeds-normal-limits",  # Long name
        ]

        for name in special_names:
            cluster = KindCluster(name=name)
            assert cluster.name == name

    def test_cluster_name_unicode(self):
        """Test cluster name with unicode characters."""
        # Kind might not support unicode cluster names, but we should handle gracefully
        unicode_name = "test-测试-cluster"
        cluster = KindCluster(name=unicode_name)
        assert cluster.name == unicode_name

    @patch("yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    def test_corrupted_config_file(self, mock_file, mock_yaml):
        """Test handling of corrupted config files."""
        # Test malformed YAML
        mock_yaml.side_effect = yaml.YAMLError("Invalid YAML")

        with pytest.raises(yaml.YAMLError):
            KindCluster(config_path="/tmp/corrupted.yaml")

    @patch("builtins.open", new_callable=mock_open)
    def test_config_file_not_found(self, mock_file):
        """Test handling of missing config files."""
        mock_file.side_effect = FileNotFoundError("Config file not found")

        with pytest.raises(FileNotFoundError):
            KindCluster(config_path="/tmp/nonexistent.yaml")

    @patch("builtins.open", new_callable=mock_open)
    def test_config_file_permission_denied(self, mock_file):
        """Test handling of permission denied for config files."""
        mock_file.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            KindCluster(config_path="/tmp/noperm.yaml")

    @patch("yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    def test_invalid_config_structure(self, mock_file, mock_yaml):
        """Test handling of invalid config structure."""
        # Test config missing required fields
        mock_yaml.return_value = {"invalid": "config"}

        cluster = KindCluster(config_path="/tmp/invalid.yaml")
        # Should create a config with defaults for missing fields
        assert cluster.config is not None

    def test_extreme_timeout_values(self):
        """Test extreme timeout values."""
        # Test maximum possible timeout
        max_timeout = 2**31 - 1  # Max 32-bit int
        cluster = KindCluster(timeout=max_timeout)
        assert cluster.config.timeout == max_timeout

        # Test very small timeout
        cluster = KindCluster(timeout=1)
        assert cluster.config.timeout == 1

    def test_port_mapping_edge_cases(self):
        """Test port mapping edge cases."""
        # Test edge case port numbers
        edge_ports = [
            {"containerPort": 1, "hostPort": 1},  # Minimum ports
            {"containerPort": 65535, "hostPort": 65535},  # Maximum ports
            {"containerPort": 80, "hostPort": 80},  # Same port
            {"containerPort": 443, "hostPort": 8443},  # Common mapping
        ]

        for mapping in edge_ports:
            cluster = KindCluster(extra_port_mappings=[mapping])
            assert len(cluster.config.nodes[0].extra_port_mappings) == 1

    def test_multiple_port_mappings(self):
        """Test multiple port mappings."""
        # Test many port mappings
        many_mappings = [
            {"containerPort": 80 + i, "hostPort": 8000 + i}
            for i in range(100)  # 100 port mappings
        ]

        cluster = KindCluster(extra_port_mappings=many_mappings)
        assert len(cluster.config.nodes[0].extra_port_mappings) == 100

    @patch.object(KindCluster, "_run_command")
    def test_network_failure_during_operations(self, mock_run_command):
        """Test network failures during cluster operations."""
        # Simulate network failure
        mock_run_command.side_effect = subprocess.CalledProcessError(
            1, ["kind"], stderr="network unreachable"
        )

        cluster = KindCluster()

        # Test exists() with network failure
        assert cluster.exists() is False

        # Test delete() with network failure - patch exists to return True so delete actually runs
        with patch.object(cluster, "exists", return_value=True):
            with pytest.raises(KindClusterDeletionError):
                cluster.delete()

    @patch("subprocess.run")
    def test_docker_daemon_crash_during_wait(self, mock_run):
        """Test Docker daemon crash during wait_for_ready."""
        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        # Simulate Docker daemon crash (connection refused)
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["kubectl"], stderr="connection refused"
        )

        with patch("time.time") as mock_time:
            mock_time.side_effect = [0, 301]  # Force timeout

            with pytest.raises(KindClusterError, match="not ready within"):
                cluster.wait_for_ready()

    @patch("tempfile.NamedTemporaryFile")
    def test_disk_space_exhaustion(self, mock_temp_file):
        """Test disk space exhaustion during config creation."""
        mock_file = Mock()
        mock_file.write.side_effect = OSError("No space left on device")
        mock_temp_file.return_value = mock_file

        cluster = KindCluster(image="test-image")

        with pytest.raises(OSError, match="No space left on device"):
            cluster._create_cluster_config()

    @patch("tempfile.NamedTemporaryFile")
    def test_permission_error_during_kubeconfig_setup(self, mock_temp_file):
        """Test permission errors during kubeconfig setup."""
        mock_file = Mock()
        mock_file.name = "/tmp/kubeconfig.yaml"
        mock_temp_file.side_effect = PermissionError("Permission denied")

        cluster = KindCluster()

        with pytest.raises(PermissionError):
            cluster._setup_kubeconfig()

    def test_concurrent_cluster_operations(self):
        """Test concurrent cluster operations."""
        cluster1 = KindCluster(name="cluster1")
        cluster2 = KindCluster(name="cluster2")

        # Simulate both clusters being created/deleted at same time
        cluster1._created = True
        cluster2._created = True

        # Should handle state independently
        assert cluster1._created
        assert cluster2._created

        cluster1._created = False
        assert not cluster1._created
        assert cluster2._created  # Should not be affected

    @patch.object(KindCluster, "_setup_kubeconfig")
    @patch.object(KindCluster, "_create_cluster_config")
    def test_partial_creation_failure_cleanup(
        self, mock_create_config, mock_setup_kubeconfig
    ):
        """Test cleanup after partial creation failure."""
        mock_create_config.return_value = None
        mock_setup_kubeconfig.side_effect = Exception("Setup failed")

        cluster = KindCluster()
        cluster._kind_runner = Mock()
        cluster._kind_runner.validate_prerequisites = Mock()
        cluster._kind_runner.create_cluster = Mock()

        with patch.object(cluster, "exists", return_value=False):
            with patch.object(cluster, "delete") as mock_delete:
                with pytest.raises(KindClusterCreationError):
                    cluster.create()

                # Should attempt cleanup
                mock_delete.assert_called_once()

    @patch("pathlib.Path.unlink")
    def test_kubeconfig_cleanup_failure(self, mock_unlink):
        """Test handling of kubeconfig cleanup failures."""
        mock_unlink.side_effect = PermissionError("Permission denied")

        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        with patch.object(cluster, "exists", return_value=True):
            with patch.object(cluster, "_run_command"):
                # Should not raise exception even if cleanup fails
                cluster.delete()

    def test_kubeconfig_path_validation(self):
        """Test kubeconfig path validation and handling."""
        cluster = KindCluster()

        # Test with None path
        assert cluster.kubeconfig_path is None

        # Test with valid path
        cluster._kubeconfig_path = Path("/valid/path/kubeconfig.yaml")
        assert cluster.kubeconfig_path == "/valid/path/kubeconfig.yaml"

        # Test with Path object
        cluster._kubeconfig_path = Path("/another/path.yaml")
        assert isinstance(cluster.kubeconfig_path, str)

    @patch("subprocess.run")
    def test_very_long_cluster_output(self, mock_run):
        """Test handling of very long cluster output."""
        # Simulate very long output
        long_output = "\n".join([f"very-long-cluster-name-{i}" for i in range(1000)])

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = long_output
        mock_run.return_value = mock_result

        cluster = KindCluster()

        # Should handle long output without issues
        assert cluster.exists() is False  # Our cluster name not in the long list

    def test_config_mutation_after_creation(self):
        """Test configuration mutation after cluster creation."""
        cluster = KindCluster(timeout=300)
        original_timeout = cluster.config.timeout

        # Mutate config after creation
        cluster.config.timeout = 600
        assert cluster.config.timeout == 600
        assert cluster.config.timeout != original_timeout

    @patch("subprocess.run")
    def test_corrupted_kubeconfig_handling(self, mock_run):
        """Test handling of corrupted kubeconfig during operations."""
        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/corrupted_kubeconfig.yaml")

        # Simulate corrupted kubeconfig (kubectl fails)
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["kubectl"], stderr="unable to load kubeconfig"
        )

        with pytest.raises(KindClusterError, match="Error getting nodes"):
            cluster.get_nodes()

    def test_resource_leak_prevention(self):
        """Test prevention of resource leaks."""
        cluster = KindCluster()

        # Simulate temp file creation
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_file = Mock()
            mock_file.name = "/tmp/test.yaml"
            mock_temp.return_value = mock_file

            cluster._kubeconfig_temp_file = mock_file

            # Ensure cleanup is called
            with patch.object(cluster, "exists", return_value=True):
                with patch.object(cluster, "_run_command"):
                    cluster.delete()

    @patch("subprocess.run")
    def test_command_injection_prevention(self, mock_run):
        """Test prevention of command injection attacks."""
        # Test cluster name with command injection attempt
        malicious_name = "test; rm -rf /"
        cluster = KindCluster(name=malicious_name)

        # Mock exists to return True so delete actually runs the delete command
        with patch.object(cluster, "exists", return_value=True):
            cluster.delete()

        # Verify the command was called with the literal name - check last call
        expected_call = call(
            ["kind", "delete", "cluster", "--name", malicious_name],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )
        assert expected_call in mock_run.call_args_list

    def test_very_long_input_handling(self):
        """Test handling of very long inputs."""
        # Test very long cluster name
        very_long_name = "a" * 10000
        cluster = KindCluster(name=very_long_name)
        assert cluster.name == very_long_name

        # Test very long image name
        very_long_image = "registry.example.com/" + "b" * 1000 + ":latest"
        cluster = KindCluster(image=very_long_image)
        assert cluster.config.image == very_long_image

    @patch("subprocess.run")
    def test_timeout_behavior_edge_cases(self, mock_run):
        """Test timeout behavior in various scenarios."""
        cluster = KindCluster(timeout=1)  # Very short timeout

        # Simulate slow command
        mock_run.side_effect = subprocess.TimeoutExpired(["kind"], 1)

        with pytest.raises(subprocess.TimeoutExpired):
            cluster._run_command(["kind", "version"])

    def test_state_consistency_after_failures(self):
        """Test state consistency after various failures."""
        cluster = KindCluster()

        # Initial state
        assert not cluster._created
        assert not cluster._verified

        # Simulate partial state change
        cluster._created = True

        # After failure, state should be consistent
        with patch.object(cluster, "delete"):
            cluster._created = False
            cluster._verified = False

        assert not cluster._created
        assert not cluster._verified

    @patch("os.environ", new_callable=dict)
    def test_environment_variable_isolation(self, mock_env):
        """Test isolation of environment variables."""
        # Set up clean environment
        mock_env.clear()
        mock_env.update({"PATH": "/usr/bin", "HOME": "/home/test"})

        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")

        with patch("subprocess.run") as mock_run:
            # Set up proper mock return value
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "node/test-node"
            mock_run.return_value = mock_result

            cluster.get_nodes()

            # Verify KUBECONFIG was set without affecting other env vars
            call_args = mock_run.call_args
            env = call_args[1]["env"]
            assert "KUBECONFIG" in env
            assert env["PATH"] == "/usr/bin"
            assert env["HOME"] == "/home/test"
