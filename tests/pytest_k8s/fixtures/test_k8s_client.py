"""
Tests for the k8s client fixtures.

This module contains comprehensive tests for the k8s client fixtures,
including tests for different usage patterns and error scenarios.
"""

import pytest
from unittest.mock import Mock, patch

from pytest_k8s.fixtures.k8s_client import KubernetesClient, k8s_client
from pytest_k8s.kind.cluster import KindCluster


class TestKubernetesClient:
    """Test the KubernetesClient class."""

    def test_init_with_valid_cluster(self):
        """Test KubernetesClient initialization with valid cluster."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config") as mock_load_config:
            client = KubernetesClient(mock_cluster)

            assert client.cluster is mock_cluster
            mock_load_config.assert_called_once_with(
                config_file="/tmp/kubeconfig", context="kind-test-cluster"
            )

    def test_init_with_no_kubeconfig_path(self):
        """Test KubernetesClient initialization fails without kubeconfig path."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = None

        with pytest.raises(ValueError, match="Cluster does not have a kubeconfig path"):
            KubernetesClient(mock_cluster)

    def test_init_with_invalid_kubeconfig(self):
        """Test KubernetesClient initialization fails with invalid kubeconfig."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/invalid-kubeconfig"

        with patch("kubernetes.config.load_kube_config") as mock_load_config:
            mock_load_config.side_effect = Exception("Invalid kubeconfig")

            with pytest.raises(RuntimeError, match="Failed to load kubeconfig"):
                KubernetesClient(mock_cluster)

    def test_api_client_property(self):
        """Test api_client property creates and caches client."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            with patch("kubernetes.client.ApiClient") as mock_api_client:
                mock_client_instance = Mock()
                mock_api_client.return_value = mock_client_instance

                client = KubernetesClient(mock_cluster)

                # First access should create the client
                api_client1 = client.api_client
                assert api_client1 is mock_client_instance
                mock_api_client.assert_called_once()

                # Second access should return cached client
                api_client2 = client.api_client
                assert api_client2 is mock_client_instance
                assert mock_api_client.call_count == 1

    def test_core_v1_api_property(self):
        """Test CoreV1Api property creates and caches client."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            with patch("kubernetes.client.ApiClient") as mock_api_client:
                with patch("kubernetes.client.CoreV1Api") as mock_core_v1:
                    mock_api_instance = Mock()
                    mock_core_instance = Mock()
                    mock_api_client.return_value = mock_api_instance
                    mock_core_v1.return_value = mock_core_instance

                    client = KubernetesClient(mock_cluster)

                    # First access should create the client
                    core_v1_1 = client.CoreV1Api
                    assert core_v1_1 is mock_core_instance
                    mock_core_v1.assert_called_once_with(mock_api_instance)

                    # Second access should return cached client
                    core_v1_2 = client.CoreV1Api
                    assert core_v1_2 is mock_core_instance
                    assert mock_core_v1.call_count == 1

    def test_apps_v1_api_property(self):
        """Test AppsV1Api property creates and caches client."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            with patch("kubernetes.client.ApiClient") as mock_api_client:
                with patch("kubernetes.client.AppsV1Api") as mock_apps_v1:
                    mock_api_instance = Mock()
                    mock_apps_instance = Mock()
                    mock_api_client.return_value = mock_api_instance
                    mock_apps_v1.return_value = mock_apps_instance

                    client = KubernetesClient(mock_cluster)

                    apps_v1 = client.AppsV1Api
                    assert apps_v1 is mock_apps_instance
                    mock_apps_v1.assert_called_once_with(mock_api_instance)

    def test_networking_v1_api_property(self):
        """Test NetworkingV1Api property creates and caches client."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            with patch("kubernetes.client.ApiClient") as mock_api_client:
                with patch("kubernetes.client.NetworkingV1Api") as mock_networking_v1:
                    mock_api_instance = Mock()
                    mock_networking_instance = Mock()
                    mock_api_client.return_value = mock_api_instance
                    mock_networking_v1.return_value = mock_networking_instance

                    client = KubernetesClient(mock_cluster)

                    networking_v1 = client.NetworkingV1Api
                    assert networking_v1 is mock_networking_instance
                    mock_networking_v1.assert_called_once_with(mock_api_instance)

    def test_rbac_authorization_v1_api_property(self):
        """Test RbacAuthorizationV1Api property creates and caches client."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            with patch("kubernetes.client.ApiClient") as mock_api_client:
                with patch("kubernetes.client.RbacAuthorizationV1Api") as mock_rbac_v1:
                    mock_api_instance = Mock()
                    mock_rbac_instance = Mock()
                    mock_api_client.return_value = mock_api_instance
                    mock_rbac_v1.return_value = mock_rbac_instance

                    client = KubernetesClient(mock_cluster)

                    rbac_v1 = client.RbacAuthorizationV1Api
                    assert rbac_v1 is mock_rbac_instance
                    mock_rbac_v1.assert_called_once_with(mock_api_instance)

    def test_custom_objects_api_property(self):
        """Test CustomObjectsApi property creates and caches client."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            with patch("kubernetes.client.ApiClient") as mock_api_client:
                with patch("kubernetes.client.CustomObjectsApi") as mock_custom_objects:
                    mock_api_instance = Mock()
                    mock_custom_instance = Mock()
                    mock_api_client.return_value = mock_api_instance
                    mock_custom_objects.return_value = mock_custom_instance

                    client = KubernetesClient(mock_cluster)

                    custom_objects = client.CustomObjectsApi
                    assert custom_objects is mock_custom_instance
                    mock_custom_objects.assert_called_once_with(mock_api_instance)

    def test_close(self):
        """Test close method cleans up resources."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            with patch("kubernetes.client.ApiClient") as mock_api_client:
                mock_api_instance = Mock()
                mock_api_client.return_value = mock_api_instance

                client = KubernetesClient(mock_cluster)

                # Access some properties to create cached clients
                _ = client.api_client
                _ = client.CoreV1Api

                # Close should clean up
                client.close()

                mock_api_instance.close.assert_called_once()
                assert client._api_client is None
                assert client._core_v1_api is None

    def test_str_representation(self):
        """Test string representation."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            client = KubernetesClient(mock_cluster)
            assert str(client) == "KubernetesClient(cluster=test-cluster)"

    def test_repr_representation(self):
        """Test detailed string representation."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            client = KubernetesClient(mock_cluster)
            assert (
                repr(client)
                == "KubernetesClient(cluster=test-cluster, kubeconfig=/tmp/kubeconfig)"
            )


class TestClientFixtureIntegration:
    """Test client fixture integration behavior with mocked components."""

    def test_k8s_client_fixture_basic(self):
        """Test that k8s_client fixture works correctly with mocked cluster."""
        # Create a mock cluster
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            # Create client directly to test the class behavior
            client = KubernetesClient(mock_cluster)

            # The client should have been created and should work
            assert client is not None
            assert client.cluster is not None
            assert hasattr(client, "CoreV1Api")
            assert hasattr(client, "AppsV1Api")
            assert hasattr(client, "NetworkingV1Api")
            assert hasattr(client, "RbacAuthorizationV1Api")
            assert hasattr(client, "CustomObjectsApi")

    def test_k8s_client_cluster_relationship(self):
        """Test that k8s_client maintains correct relationship with cluster."""
        # Create a mock cluster
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "relationship-test-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            client = KubernetesClient(mock_cluster)

            assert client is not None
            assert client.cluster is mock_cluster
            assert client.cluster.name == "relationship-test-cluster"

    def test_k8s_client_with_custom_cluster_config(self):
        """Test that k8s_client works with custom cluster configuration."""
        # Create a mock cluster with custom configuration
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "custom-config-cluster"
        mock_cluster.kubeconfig_path = "/tmp/custom-kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            client = KubernetesClient(mock_cluster)

            assert client is not None
            assert client.cluster is not None
            assert client.cluster.name == "custom-config-cluster"
            assert hasattr(client, "CoreV1Api")


class TestClientFixtureDocumentation:
    """Test that client fixtures are properly documented and discoverable."""

    def test_client_fixture_import_availability(self):
        """Test that client fixtures can be imported directly."""
        # Test that the client fixture can be imported

        # Verify it's a callable fixture
        assert callable(k8s_client)

    def test_kubernetes_client_class_import(self):
        """Test that KubernetesClient class can be imported."""
        from pytest_k8s.fixtures.k8s_client import KubernetesClient

        # Verify it's a class
        assert isinstance(KubernetesClient, type)

        # Verify it has expected methods
        assert hasattr(KubernetesClient, "__init__")
        assert hasattr(KubernetesClient, "close")
        assert hasattr(KubernetesClient, "CoreV1Api")
        assert hasattr(KubernetesClient, "AppsV1Api")
        assert hasattr(KubernetesClient, "NetworkingV1Api")
        assert hasattr(KubernetesClient, "RbacAuthorizationV1Api")
        assert hasattr(KubernetesClient, "CustomObjectsApi")


class TestClientErrorHandling:
    """Test error handling in client fixtures."""

    def test_client_creation_with_invalid_cluster(self):
        """Test client creation with invalid cluster."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "invalid-cluster"
        mock_cluster.kubeconfig_path = None

        with pytest.raises(ValueError, match="Cluster does not have a kubeconfig path"):
            KubernetesClient(mock_cluster)

    def test_client_creation_with_kubeconfig_failure(self):
        """Test client creation when kubeconfig loading fails."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "kubeconfig-error-cluster"
        mock_cluster.kubeconfig_path = "/tmp/invalid-kubeconfig"

        with patch("kubernetes.config.load_kube_config") as mock_load_config:
            mock_load_config.side_effect = Exception("Invalid kubeconfig")

            with pytest.raises(RuntimeError, match="Failed to load kubeconfig"):
                KubernetesClient(mock_cluster)

    def test_client_cleanup_error_handling(self):
        """Test that client cleanup errors don't prevent test completion."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "cleanup-error-cluster"
        mock_cluster.kubeconfig_path = "/tmp/kubeconfig"

        with patch("kubernetes.config.load_kube_config"):
            with patch("kubernetes.client.ApiClient") as mock_api_client:
                mock_api_instance = Mock()
                mock_api_instance.close.side_effect = Exception("Cleanup failed")
                mock_api_client.return_value = mock_api_instance

                client = KubernetesClient(mock_cluster)

                # Access the api client to create it
                _ = client.api_client

                # Close should handle the error gracefully
                client.close()

                # Verify cleanup was attempted
                mock_api_instance.close.assert_called_once()
                assert client._api_client is None
