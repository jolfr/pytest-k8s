"""
Tests for the kind cluster manager.

This module contains tests for the KindClusterManager class,
including unit tests with mocking.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from pytest_k8s.kind.cluster import KindCluster
from pytest_k8s.kind.cluster_manager import KindClusterManager
from pytest_k8s.kind.errors import KindClusterNotFoundError


class TestKindClusterManager:
    """Test cases for KindClusterManager class."""

    def test_init(self):
        """Test KindClusterManager initialization."""
        manager = KindClusterManager()

        assert len(manager._clusters) == 0
        assert manager._default_config == {
            "timeout": 300,
            "keep_cluster": False,
            "image": None,
        }

    @patch.object(KindCluster, "create")
    def test_create_cluster_success(self, mock_create):
        """Test successful cluster creation through manager."""
        manager = KindClusterManager()

        cluster = manager.create_cluster(name="test-cluster", timeout=600)

        assert cluster.name == "test-cluster"
        assert cluster.config.timeout == 600
        assert manager._clusters["test-cluster"] is cluster
        mock_create.assert_called_once()

    @patch.object(KindCluster, "create")
    def test_create_cluster_auto_name(self, mock_create):
        """Test cluster creation with auto-generated name."""
        manager = KindClusterManager()

        cluster = manager.create_cluster()

        assert cluster.name.startswith("pytest-k8s-")
        assert manager._clusters[cluster.name] is cluster
        mock_create.assert_called_once()

    @patch("yaml.safe_load")
    @patch("builtins.open")
    @patch.object(KindCluster, "create")
    def test_create_cluster_with_config_path(self, mock_create, mock_open, mock_yaml):
        """Test cluster creation with config path."""
        mock_yaml.return_value = {
            "kind": "Cluster",
            "apiVersion": "kind.x-k8s.io/v1alpha4",
            "nodes": [{"role": "control-plane"}],
        }

        manager = KindClusterManager()
        config_path = "/tmp/kind-config.yaml"

        cluster = manager.create_cluster(name="test-cluster", config_path=config_path)

        assert cluster.name == "test-cluster"
        # Config should be loaded from file (additional params like image are not applied to file-loaded configs)
        assert cluster.config is not None
        mock_create.assert_called_once()

    @patch.object(KindCluster, "create")
    def test_create_cluster_with_extra_port_mappings(self, mock_create):
        """Test cluster creation with extra port mappings."""
        manager = KindClusterManager()
        port_mappings = [{"containerPort": 80, "hostPort": 8080}]

        cluster = manager.create_cluster(
            name="test-cluster", extra_port_mappings=port_mappings
        )

        assert cluster.name == "test-cluster"
        # Port mappings should be in the config
        assert len(cluster.config.nodes[0].extra_port_mappings) == 1
        mock_create.assert_called_once()

    @patch.object(KindCluster, "create")
    def test_create_cluster_filters_invalid_kwargs(self, mock_create):
        """Test that invalid kwargs are filtered out."""
        manager = KindClusterManager()

        cluster = manager.create_cluster(
            name="test-cluster",
            timeout=600,
            keep_cluster=True,
            image="custom-image",
            extra_port_mappings=[{"containerPort": 80, "hostPort": 8080}],
            invalid_arg="should_be_filtered",  # This should be filtered out
        )

        assert cluster.name == "test-cluster"
        assert cluster.config.timeout == 600
        assert cluster.keep_cluster is True
        assert cluster.config.image == "custom-image"
        # invalid_arg should not be passed to KindCluster
        assert not hasattr(cluster, "invalid_arg")
        mock_create.assert_called_once()

    @patch.object(KindCluster, "create")
    def test_create_cluster_merges_default_config(self, mock_create):
        """Test that default config is merged with provided config."""
        manager = KindClusterManager()

        # Override one default value, others should remain default
        cluster = manager.create_cluster(
            name="test-cluster",
            timeout=600,  # Override default timeout
            # keep_cluster and image should use defaults
        )

        assert cluster.name == "test-cluster"
        assert cluster.config.timeout == 600  # Overridden
        assert cluster.keep_cluster is False  # Default
        assert cluster.config.image is None  # Default
        mock_create.assert_called_once()

    def test_get_cluster_exists(self):
        """Test getting an existing cluster."""
        manager = KindClusterManager()
        cluster = KindCluster(name="test-cluster")
        manager._clusters["test-cluster"] = cluster

        result = manager.get_cluster("test-cluster")
        assert result is cluster

    def test_get_cluster_not_exists(self):
        """Test getting a non-existent cluster."""
        manager = KindClusterManager()

        result = manager.get_cluster("nonexistent")
        assert result is None

    @patch.object(KindCluster, "delete")
    def test_delete_cluster_success(self, mock_delete):
        """Test successful cluster deletion through manager."""
        manager = KindClusterManager()
        cluster = KindCluster(name="test-cluster")
        manager._clusters["test-cluster"] = cluster

        manager.delete_cluster("test-cluster")

        mock_delete.assert_called_once()
        assert "test-cluster" not in manager._clusters

    def test_delete_cluster_not_found(self):
        """Test deleting a non-existent cluster."""
        manager = KindClusterManager()

        with pytest.raises(KindClusterNotFoundError, match="not found"):
            manager.delete_cluster("nonexistent")

    def test_list_clusters_empty(self):
        """Test listing clusters when none exist."""
        manager = KindClusterManager()

        clusters = manager.list_clusters()
        assert clusters == []

    def test_list_clusters_with_clusters(self):
        """Test listing clusters when some exist."""
        manager = KindClusterManager()
        cluster1 = KindCluster(name="cluster1")
        cluster2 = KindCluster(name="cluster2")
        manager._clusters["cluster1"] = cluster1
        manager._clusters["cluster2"] = cluster2

        clusters = manager.list_clusters()
        assert set(clusters) == {"cluster1", "cluster2"}

    @patch.object(KindCluster, "delete")
    def test_cleanup_all_success(self, mock_delete):
        """Test successful cleanup of all clusters."""
        manager = KindClusterManager()
        cluster1 = KindCluster(name="cluster1")
        cluster2 = KindCluster(name="cluster2")
        manager._clusters["cluster1"] = cluster1
        manager._clusters["cluster2"] = cluster2

        manager.cleanup_all()

        assert len(manager._clusters) == 0
        assert mock_delete.call_count == 2

    @patch.object(KindCluster, "delete")
    def test_cleanup_all_with_errors(self, mock_delete):
        """Test cleanup with some clusters failing to delete."""
        mock_delete.side_effect = [Exception("Delete failed"), None]

        manager = KindClusterManager()
        cluster1 = KindCluster(name="cluster1")
        cluster2 = KindCluster(name="cluster2")
        manager._clusters["cluster1"] = cluster1
        manager._clusters["cluster2"] = cluster2

        # Should not raise exception, just log errors
        manager.cleanup_all()

        assert len(manager._clusters) == 0
        assert mock_delete.call_count == 2

    def test_len(self):
        """Test length operator."""
        manager = KindClusterManager()
        assert len(manager) == 0

        cluster = KindCluster(name="test-cluster")
        manager._clusters["test-cluster"] = cluster
        assert len(manager) == 1

        cluster2 = KindCluster(name="test-cluster-2")
        manager._clusters["test-cluster-2"] = cluster2
        assert len(manager) == 2

    def test_iter(self):
        """Test iteration over clusters."""
        manager = KindClusterManager()
        cluster1 = KindCluster(name="cluster1")
        cluster2 = KindCluster(name="cluster2")
        manager._clusters["cluster1"] = cluster1
        manager._clusters["cluster2"] = cluster2

        clusters = list(manager)
        assert len(clusters) == 2
        assert cluster1 in clusters
        assert cluster2 in clusters

    def test_iter_empty(self):
        """Test iteration over empty manager."""
        manager = KindClusterManager()

        clusters = list(manager)
        assert clusters == []

    @patch("yaml.safe_load")
    @patch("builtins.open")
    @patch.object(KindCluster, "create")
    def test_create_cluster_with_path_object(self, mock_create, mock_open, mock_yaml):
        """Test cluster creation with Path object for config_path."""
        mock_yaml.return_value = {
            "kind": "Cluster",
            "apiVersion": "kind.x-k8s.io/v1alpha4",
            "nodes": [{"role": "control-plane"}],
        }

        manager = KindClusterManager()
        config_path = Path("/tmp/kind-config.yaml")

        cluster = manager.create_cluster(name="test-cluster", config_path=config_path)

        assert cluster.name == "test-cluster"
        assert cluster.config is not None
        mock_create.assert_called_once()

    @patch.object(KindCluster, "create")
    def test_create_cluster_with_all_valid_kwargs(self, mock_create):
        """Test cluster creation with all valid kwargs."""
        manager = KindClusterManager()

        cluster = manager.create_cluster(
            name="test-cluster",
            timeout=600,
            keep_cluster=True,
            image="kindest/node:v1.25.0",
            extra_port_mappings=[
                {"containerPort": 80, "hostPort": 8080, "protocol": "TCP"},
                {"containerPort": 443, "hostPort": 8443},
            ],
        )

        assert cluster.name == "test-cluster"
        assert cluster.config.timeout == 600
        assert cluster.keep_cluster is True
        assert cluster.config.image == "kindest/node:v1.25.0"
        assert len(cluster.config.nodes[0].extra_port_mappings) == 2
        mock_create.assert_called_once()

    def test_manager_state_isolation(self):
        """Test that multiple managers maintain separate state."""
        manager1 = KindClusterManager()
        manager2 = KindClusterManager()

        cluster1 = KindCluster(name="cluster1")
        cluster2 = KindCluster(name="cluster2")

        manager1._clusters["cluster1"] = cluster1
        manager2._clusters["cluster2"] = cluster2

        # Each manager should only know about its own clusters
        assert len(manager1) == 1
        assert len(manager2) == 1
        assert "cluster1" in manager1.list_clusters()
        assert "cluster2" in manager2.list_clusters()
        assert "cluster2" not in manager1.list_clusters()
        assert "cluster1" not in manager2.list_clusters()

    def test_default_config_immutability(self):
        """Test that modifying default config doesn't affect other instances."""
        manager1 = KindClusterManager()
        manager2 = KindClusterManager()

        # Modify one manager's default config
        manager1._default_config["timeout"] = 600

        # Other manager should be unaffected
        assert manager2._default_config["timeout"] == 300

        # Original values should be preserved
        assert manager1._default_config["keep_cluster"] is False
        assert manager1._default_config["image"] is None
        assert manager2._default_config["keep_cluster"] is False
        assert manager2._default_config["image"] is None
