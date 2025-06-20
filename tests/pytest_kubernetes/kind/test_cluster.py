"""
Tests for the kind cluster lifecycle manager.

This module contains comprehensive tests for the KindCluster class,
including unit tests with mocking and integration tests.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from pytest_kubernetes.kind.cluster import KindCluster
from pytest_kubernetes.kind.errors import (
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
        assert cluster.config_path is None
        assert cluster.timeout == 300
        assert cluster.keep_cluster is False
        assert cluster.image is None
        assert cluster.extra_port_mappings == []
        assert cluster.kubeconfig_path is None
        assert not cluster._created
        assert not cluster._verified
    
    def test_init_with_custom_values(self):
        """Test KindCluster initialization with custom values."""
        config_path = "/tmp/kind-config.yaml"
        port_mappings = [{"containerPort": 80, "hostPort": 8080}]
        
        cluster = KindCluster(
            name="test-cluster",
            config_path=config_path,
            timeout=600,
            keep_cluster=True,
            image="kindest/node:v1.25.0",
            extra_port_mappings=port_mappings,
        )
        
        assert cluster.name == "test-cluster"
        assert str(cluster.config_path) == config_path
        assert cluster.timeout == 600
        assert cluster.keep_cluster is True
        assert cluster.image == "kindest/node:v1.25.0"
        assert cluster.extra_port_mappings == port_mappings
    
    def test_generate_cluster_name(self):
        """Test cluster name generation."""
        name1 = KindCluster._generate_cluster_name()
        name2 = KindCluster._generate_cluster_name()
        
        assert name1.startswith("pytest-k8s-")
        assert name2.startswith("pytest-k8s-")
        assert name1 != name2
        assert len(name1) == len(name2) == 19
    
    @patch('subprocess.run')
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
    
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test command execution failure."""
        error = subprocess.CalledProcessError(1, ["false"])
        error.stdout = ""
        error.stderr = "command failed"
        mock_run.side_effect = error
        
        cluster = KindCluster()
        
        with pytest.raises(subprocess.CalledProcessError):
            cluster._run_command(["false"])
    
    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_run):
        """Test command execution timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["sleep", "10"], 5)
        
        cluster = KindCluster()
        
        with pytest.raises(subprocess.TimeoutExpired):
            cluster._run_command(["sleep", "10"], timeout=5)
    
    @patch.object(KindCluster, '_run_command')
    def test_check_kind_available_success(self, mock_run_command):
        """Test successful kind availability check."""
        mock_run_command.return_value = Mock()
        
        cluster = KindCluster()
        assert cluster._check_kind_available() is True
        
        mock_run_command.assert_called_once_with(["kind", "version"], timeout=10)
    
    @patch.object(KindCluster, '_run_command')
    def test_check_kind_available_failure(self, mock_run_command):
        """Test kind availability check failure."""
        mock_run_command.side_effect = FileNotFoundError()
        
        cluster = KindCluster()
        assert cluster._check_kind_available() is False
    
    @patch.object(KindCluster, '_run_command')
    def test_check_docker_available_success(self, mock_run_command):
        """Test successful Docker availability check."""
        mock_run_command.return_value = Mock()
        
        cluster = KindCluster()
        assert cluster._check_docker_available() is True
        
        mock_run_command.assert_called_once_with(["docker", "version"], timeout=10)
    
    @patch.object(KindCluster, '_run_command')
    def test_check_docker_available_failure(self, mock_run_command):
        """Test Docker availability check failure."""
        mock_run_command.side_effect = subprocess.CalledProcessError(1, ["docker"])
        
        cluster = KindCluster()
        assert cluster._check_docker_available() is False
    
    def test_create_cluster_config_existing_path(self):
        """Test cluster config creation with existing path."""
        config_path = "/tmp/existing-config.yaml"
        cluster = KindCluster(config_path=config_path)
        
        result = cluster._create_cluster_config()
        assert result == Path(config_path)
    
    @patch('tempfile.NamedTemporaryFile')
    def test_create_cluster_config_with_custom_settings(self, mock_temp_file):
        """Test cluster config creation with custom settings."""
        mock_file = Mock()
        mock_file.name = "/tmp/temp-config.yaml"
        mock_temp_file.return_value = mock_file
        
        cluster = KindCluster(
            image="kindest/node:v1.25.0",
            extra_port_mappings=[
                {"containerPort": 80, "hostPort": 8080, "protocol": "TCP"}
            ]
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
    
    def test_generate_default_config(self):
        """Test default config generation."""
        cluster = KindCluster(
            image="kindest/node:v1.25.0",
            extra_port_mappings=[
                {"containerPort": 80, "hostPort": 8080, "protocol": "TCP"},
                {"containerPort": 443, "hostPort": 8443}
            ]
        )
        
        config = cluster._generate_default_config()
        
        expected_lines = [
            "kind: Cluster",
            "apiVersion: kind.x-k8s.io/v1alpha4",
            "nodes:",
            "- role: control-plane",
            "  image: kindest/node:v1.25.0",
            "  extraPortMappings:",
            "  - containerPort: 80",
            "    hostPort: 8080",
            "    protocol: TCP",
            "  - containerPort: 443",
            "    hostPort: 8443"
        ]
        
        assert config == "\n".join(expected_lines)
    
    @patch('tempfile.NamedTemporaryFile')
    @patch.object(KindCluster, '_run_command')
    def test_setup_kubeconfig_success(self, mock_run_command, mock_temp_file):
        """Test successful kubeconfig setup."""
        mock_file = Mock()
        mock_file.name = "/tmp/kubeconfig.yaml"
        mock_temp_file.return_value = mock_file
        
        cluster = KindCluster(name="test-cluster")
        cluster._setup_kubeconfig()
        
        assert cluster._kubeconfig_path == Path("/tmp/kubeconfig.yaml")
        mock_run_command.assert_called_once_with([
            "kind", "export", "kubeconfig",
            "--name", "test-cluster",
            "--kubeconfig", "/tmp/kubeconfig.yaml"
        ])
    
    @patch('tempfile.NamedTemporaryFile')
    @patch.object(KindCluster, '_run_command')
    def test_setup_kubeconfig_failure(self, mock_run_command, mock_temp_file):
        """Test kubeconfig setup failure."""
        mock_file = Mock()
        mock_file.name = "/tmp/kubeconfig.yaml"
        mock_temp_file.return_value = mock_file
        
        mock_run_command.side_effect = subprocess.CalledProcessError(
            1, ["kind"], stderr="export failed"
        )
        
        cluster = KindCluster(name="test-cluster")
        
        with pytest.raises(KindClusterCreationError, match="Failed to export kubeconfig"):
            cluster._setup_kubeconfig()
    
    @patch.object(KindCluster, '_check_kind_available')
    @patch.object(KindCluster, '_check_docker_available')
    @patch.object(KindCluster, 'exists')
    @patch.object(KindCluster, '_create_cluster_config')
    @patch.object(KindCluster, '_run_command')
    @patch.object(KindCluster, '_setup_kubeconfig')
    @patch.object(KindCluster, 'wait_for_ready')
    def test_create_success(
        self,
        mock_wait_ready,
        mock_setup_kubeconfig,
        mock_run_command,
        mock_create_config,
        mock_exists,
        mock_check_docker,
        mock_check_kind,
    ):
        """Test successful cluster creation."""
        mock_check_kind.return_value = True
        mock_check_docker.return_value = True
        mock_exists.return_value = False
        mock_create_config.return_value = None
        
        cluster = KindCluster(name="test-cluster")
        cluster.create()
        
        assert cluster._created is True
        mock_run_command.assert_called_once_with(
            ["kind", "create", "cluster", "--name", "test-cluster", "--wait=60s"],
            timeout=300
        )
        mock_setup_kubeconfig.assert_called_once()
        mock_wait_ready.assert_called_once()
    
    @patch.object(KindCluster, '_check_kind_available')
    def test_create_kind_not_available(self, mock_check_kind):
        """Test cluster creation when kind is not available."""
        mock_check_kind.return_value = False
        
        cluster = KindCluster()
        
        with pytest.raises(KindClusterError, match="kind command not available"):
            cluster.create()
    
    @patch.object(KindCluster, '_check_kind_available')
    @patch.object(KindCluster, '_check_docker_available')
    def test_create_docker_not_available(self, mock_check_docker, mock_check_kind):
        """Test cluster creation when Docker is not available."""
        mock_check_kind.return_value = True
        mock_check_docker.return_value = False
        
        cluster = KindCluster()
        
        with pytest.raises(KindClusterError, match="Docker not available"):
            cluster.create()
    
    @patch.object(KindCluster, '_check_kind_available')
    @patch.object(KindCluster, '_check_docker_available')
    @patch.object(KindCluster, 'exists')
    def test_create_cluster_already_exists(self, mock_exists, mock_check_docker, mock_check_kind):
        """Test cluster creation when cluster already exists."""
        mock_check_kind.return_value = True
        mock_check_docker.return_value = True
        mock_exists.return_value = True
        
        cluster = KindCluster(name="existing-cluster")
        
        with pytest.raises(KindClusterCreationError, match="already exists"):
            cluster.create()
    
    def test_create_already_created(self):
        """Test create method when cluster is already created."""
        cluster = KindCluster()
        cluster._created = True
        
        # Should return early without error
        cluster.create()
        assert cluster._created is True
    
    @patch.object(KindCluster, 'exists')
    @patch.object(KindCluster, '_run_command')
    def test_delete_success(self, mock_run_command, mock_exists):
        """Test successful cluster deletion."""
        mock_exists.return_value = True
        
        cluster = KindCluster(name="test-cluster")
        cluster._created = True
        cluster._verified = True
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):
            cluster.delete()
        
        assert cluster._created is False
        assert cluster._verified is False
        mock_run_command.assert_called_once_with(
            ["kind", "delete", "cluster", "--name", "test-cluster"]
        )
    
    @patch.object(KindCluster, 'exists')
    def test_delete_keep_cluster(self, mock_exists):
        """Test delete method with keep_cluster=True."""
        mock_exists.return_value = True
        
        cluster = KindCluster(name="test-cluster", keep_cluster=True)
        cluster.delete()
        
        # Should not attempt deletion
        mock_exists.assert_not_called()
    
    @patch.object(KindCluster, 'exists')
    def test_delete_cluster_not_exists(self, mock_exists):
        """Test delete method when cluster doesn't exist."""
        mock_exists.return_value = False
        
        cluster = KindCluster(name="test-cluster")
        cluster.delete()
        
        # Should return early without error
        mock_exists.assert_called_once()
    
    @patch.object(KindCluster, 'exists')
    @patch.object(KindCluster, '_run_command')
    def test_delete_failure(self, mock_run_command, mock_exists):
        """Test cluster deletion failure."""
        mock_exists.return_value = True
        mock_run_command.side_effect = subprocess.CalledProcessError(
            1, ["kind"], stderr="deletion failed"
        )
        
        cluster = KindCluster(name="test-cluster")
        
        with pytest.raises(KindClusterDeletionError, match="Failed to delete cluster"):
            cluster.delete()
    
    @patch.object(KindCluster, '_run_command')
    def test_exists_true(self, mock_run_command):
        """Test exists method when cluster exists."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "cluster1\ntest-cluster\ncluster2"
        mock_run_command.return_value = mock_result
        
        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is True
        
        mock_run_command.assert_called_once_with(
            ["kind", "get", "clusters"],
            capture_output=True,
            check=False
        )
    
    @patch.object(KindCluster, '_run_command')
    def test_exists_false(self, mock_run_command):
        """Test exists method when cluster doesn't exist."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "cluster1\nother-cluster\ncluster2"
        mock_run_command.return_value = mock_result
        
        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is False
    
    @patch.object(KindCluster, '_run_command')
    def test_exists_command_failure(self, mock_run_command):
        """Test exists method when command fails."""
        mock_run_command.side_effect = Exception("Command failed")
        
        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is False
    
    @patch('subprocess.run')
    @patch('time.time')
    @patch('time.sleep')
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
            timeout=10
        )
    
    @patch('subprocess.run')
    @patch('time.time')
    @patch('time.sleep')
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
    
    @patch('subprocess.run')
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
            timeout=30
        )
    
    def test_get_nodes_no_kubeconfig(self):
        """Test get_nodes when kubeconfig is not available."""
        cluster = KindCluster()
        
        with pytest.raises(KindClusterError, match="kubeconfig not available"):
            cluster.get_nodes()
    
    @patch('subprocess.run')
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
    
    @patch.object(KindCluster, 'wait_for_ready')
    def test_is_ready_true(self, mock_wait_ready):
        """Test is_ready when cluster is ready."""
        cluster = KindCluster()
        assert cluster.is_ready() is True
        mock_wait_ready.assert_called_once_with(timeout=10)
    
    @patch.object(KindCluster, 'wait_for_ready')
    def test_is_ready_false(self, mock_wait_ready):
        """Test is_ready when cluster is not ready."""
        mock_wait_ready.side_effect = KindClusterError("Not ready")
        
        cluster = KindCluster()
        assert cluster.is_ready() is False
    
    @patch.object(KindCluster, 'create')
    @patch.object(KindCluster, 'delete')
    def test_context_manager(self, mock_delete, mock_create):
        """Test context manager functionality."""
        cluster = KindCluster(name="test-cluster")
        
        with cluster as c:
            assert c is cluster
            mock_create.assert_called_once()
        
        mock_delete.assert_called_once()
    
    @patch.object(KindCluster, 'create')
    @patch.object(KindCluster, 'delete')
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




class TestKindClusterIntegration:
    """Integration tests for KindCluster (requires kind and Docker)."""
    
    @pytest.fixture
    def skip_if_no_kind(self):
        """Skip tests if kind is not available."""
        try:
            subprocess.run(
                ["kind", "version"],
                capture_output=True,
                check=True
            )
            subprocess.run(
                ["docker", "version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("kind or Docker not available")
    
    @pytest.fixture
    def integration_cluster_name(self):
        """Generate a unique cluster name for integration tests."""
        return f"pytest-integration-{int(time.time())}"
    
    def test_cluster_lifecycle_integration(self, skip_if_no_kind, integration_cluster_name):
        """Test complete cluster lifecycle integration."""
        cluster = KindCluster(
            name=integration_cluster_name,
            timeout=600,
            keep_cluster=False
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
            except Exception as e:
                # Best effort cleanup
                try:
                    subprocess.run(
                        ["kind", "delete", "cluster", "--name", integration_cluster_name],
                        capture_output=True
                    )
                except Exception:
                    pass
    
    def test_context_manager_integration(self, skip_if_no_kind, integration_cluster_name):
        """Test context manager integration."""
        with KindCluster(name=integration_cluster_name, timeout=600) as cluster:
            assert cluster.exists()
            assert cluster.is_ready()
            nodes = cluster.get_nodes()
            assert len(nodes) > 0
        
        # Cluster should be deleted after context exit
        assert not cluster.exists()
    
    def test_cluster_with_custom_config_integration(self, skip_if_no_kind, integration_cluster_name):
        """Test cluster creation with custom configuration."""
        # Create temporary config file
        config_content = """
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 8080
        """.strip()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            cluster = KindCluster(
                name=integration_cluster_name,
                config_path=config_path,
                timeout=600
            )
            
            try:
                cluster.create()
                assert cluster.exists()
                assert cluster.is_ready()
                
                nodes = cluster.get_nodes()
                assert len(nodes) > 0
                
            finally:
                cluster.delete()
                
        finally:
            # Clean up config file
            try:
                Path(config_path).unlink()
            except Exception:
                pass
    


class TestKindClusterErrorHandling:
    """Test error handling and edge cases."""
    
    @patch.object(KindCluster, '_run_command')
    def test_create_with_command_failure_cleanup(self, mock_run_command):
        """Test cleanup when cluster creation fails."""
        # Mock successful prerequisite checks
        mock_run_command.side_effect = [
            Mock(),  # kind version check
            Mock(),  # docker version check
            Mock(returncode=0, stdout=""),  # kind get clusters (empty)
            subprocess.CalledProcessError(1, ["kind"], stderr="creation failed")  # create fails
        ]
        
        cluster = KindCluster(name="test-cluster")
        
        with patch.object(cluster, 'delete') as mock_delete:
            with pytest.raises(KindClusterCreationError):
                cluster.create()
            
            # Should attempt cleanup
            mock_delete.assert_called_once()
    
    @patch.object(KindCluster, '_run_command')
    def test_wait_for_ready_with_partial_failures(self, mock_run_command):
        """Test wait_for_ready with initial failures then success."""
        cluster = KindCluster(name="test-cluster")
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")
        
        # First call fails, second succeeds
        with patch('subprocess.run') as mock_run, \
             patch('time.time') as mock_time, \
             patch('time.sleep') as mock_sleep:
            
            mock_time.side_effect = [0, 1, 2, 3]  # Simulate time progression
            
            # First kubectl call fails, second succeeds
            mock_run.side_effect = [
                Mock(returncode=1),  # First call fails
                Mock(returncode=0)   # Second call succeeds
            ]
            
            cluster.wait_for_ready()
            
            assert cluster._verified is True
            assert mock_run.call_count == 2
            mock_sleep.assert_called()
    
    def test_kubeconfig_path_property_none(self):
        """Test kubeconfig_path property when path is None."""
        cluster = KindCluster()
        assert cluster.kubeconfig_path is None
    
    def test_kubeconfig_path_property_set(self):
        """Test kubeconfig_path property when path is set."""
        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/test.yaml")
        assert cluster.kubeconfig_path == "/tmp/test.yaml"
    
    @patch.object(KindCluster, '_run_command')
    def test_get_nodes_timeout_error(self, mock_run_command):
        """Test get_nodes with timeout error."""
        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(["kubectl"], 30)
            
            with pytest.raises(KindClusterError, match="Timeout getting cluster nodes"):
                cluster.get_nodes()
    
    @patch.object(KindCluster, '_run_command')
    def test_get_nodes_generic_error(self, mock_run_command):
        """Test get_nodes with generic error."""
        cluster = KindCluster()
        cluster._kubeconfig_path = Path("/tmp/kubeconfig.yaml")
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = ValueError("Generic error")
            
            with pytest.raises(KindClusterError, match="Error getting nodes"):
                cluster.get_nodes()
    
    def test_generate_default_config_image_only(self):
        """Test config generation with only image specified."""
        cluster = KindCluster(image="kindest/node:v1.25.0")
        
        config = cluster._generate_default_config()
        
        expected_lines = [
            "kind: Cluster",
            "apiVersion: kind.x-k8s.io/v1alpha4",
            "nodes:",
            "- role: control-plane",
            "  image: kindest/node:v1.25.0"
        ]
        
        assert config == "\n".join(expected_lines)
    
    def test_generate_default_config_port_mappings_only(self):
        """Test config generation with only port mappings specified."""
        cluster = KindCluster(
            extra_port_mappings=[
                {"containerPort": 80, "hostPort": 8080}
            ]
        )
        
        config = cluster._generate_default_config()
        
        expected_lines = [
            "kind: Cluster",
            "apiVersion: kind.x-k8s.io/v1alpha4",
            "nodes:",
            "- role: control-plane",
            "  extraPortMappings:",
            "  - containerPort: 80",
            "    hostPort: 8080"
        ]
        
        assert config == "\n".join(expected_lines)


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
        assert cluster.timeout == 0
        
        # Test negative timeout
        cluster = KindCluster(timeout=-1)
        assert cluster.timeout == -1
        
        # Test very large timeout
        cluster = KindCluster(timeout=86400)
        assert cluster.timeout == 86400
    
    def test_empty_port_mappings(self):
        """Test empty port mappings."""
        cluster = KindCluster(extra_port_mappings=[])
        assert cluster.extra_port_mappings == []
        
        # Should not create config for empty mappings
        config_path = cluster._create_cluster_config()
        assert config_path is None
    
    def test_path_handling(self):
        """Test path handling for config_path."""
        # Test string path
        cluster = KindCluster(config_path="/tmp/config.yaml")
        assert isinstance(cluster.config_path, Path)
        assert str(cluster.config_path) == "/tmp/config.yaml"
        
        # Test Path object
        path_obj = Path("/tmp/config2.yaml")
        cluster = KindCluster(config_path=path_obj)
        assert cluster.config_path == path_obj
        
        # Test None path
        cluster = KindCluster(config_path=None)
        assert cluster.config_path is None
    
    @patch.object(KindCluster, '_run_command')
    def test_exists_with_empty_output(self, mock_run_command):
        """Test exists method with empty cluster list."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run_command.return_value = mock_result
        
        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is False
    
    @patch.object(KindCluster, '_run_command')
    def test_exists_with_single_newline(self, mock_run_command):
        """Test exists method with single newline output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "\n"
        mock_run_command.return_value = mock_result
        
        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is False
    
    @patch.object(KindCluster, '_run_command')
    def test_exists_with_whitespace_cluster_names(self, mock_run_command):
        """Test exists method with whitespace in cluster names."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = " cluster1 \n test-cluster \n cluster2 "
        mock_run_command.return_value = mock_result
        
        cluster = KindCluster(name="test-cluster")
        assert cluster.exists() is True
