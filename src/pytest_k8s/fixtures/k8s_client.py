"""
Kubernetes client fixtures for pytest-k8s.

This module provides pytest fixtures for creating and managing Kubernetes API clients
during testing. The fixtures automatically connect to clusters created by k8s_cluster fixtures.
"""

import logging
import pytest
from typing import Optional

import kubernetes
from kubernetes import client, config

from .k8s_cluster import k8s_cluster
from ..kind.cluster import KindCluster

logger = logging.getLogger(__name__)


class KubernetesClient:
    """
    Wrapper for Kubernetes API clients with cluster integration.
    
    This class provides convenient access to various Kubernetes API clients
    while maintaining the connection to the underlying cluster.
    """
    
    def __init__(self, cluster: KindCluster):
        """
        Initialize the Kubernetes client wrapper.
        
        Args:
            cluster: The KindCluster instance to connect to.
        """
        self.cluster = cluster
        self._api_client: Optional[client.ApiClient] = None
        self._core_v1_api: Optional[client.CoreV1Api] = None
        self._apps_v1_api: Optional[client.AppsV1Api] = None
        self._networking_v1_api: Optional[client.NetworkingV1Api] = None
        self._rbac_authorization_v1_api: Optional[client.RbacAuthorizationV1Api] = None
        self._custom_objects_api: Optional[client.CustomObjectsApi] = None
        
        # Load the kubeconfig for this cluster
        self._load_kubeconfig()
    
    def _load_kubeconfig(self) -> None:
        """Load the kubeconfig for the associated cluster."""
        if not self.cluster.kubeconfig_path:
            raise ValueError("Cluster does not have a kubeconfig path")
        
        try:
            # The context name for kind clusters is "kind-{cluster_name}"
            context_name = f"kind-{self.cluster.name}"
            
            # Load the kubeconfig from the cluster's kubeconfig file with specific context
            config.load_kube_config(
                config_file=self.cluster.kubeconfig_path,
                context=context_name
            )
            logger.info(f"Loaded kubeconfig from: {self.cluster.kubeconfig_path} with context: {context_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to load kubeconfig: {e}")
    
    @property
    def api_client(self) -> client.ApiClient:
        """Get the base Kubernetes API client."""
        if self._api_client is None:
            self._api_client = client.ApiClient()
        return self._api_client
    
    @property
    def CoreV1Api(self) -> client.CoreV1Api:
        """Get the Kubernetes Core V1 API client."""
        if self._core_v1_api is None:
            self._core_v1_api = client.CoreV1Api(self.api_client)
        return self._core_v1_api
    
    @property
    def AppsV1Api(self) -> client.AppsV1Api:
        """Get the Kubernetes Apps V1 API client."""
        if self._apps_v1_api is None:
            self._apps_v1_api = client.AppsV1Api(self.api_client)
        return self._apps_v1_api
    
    @property
    def NetworkingV1Api(self) -> client.NetworkingV1Api:
        """Get the Kubernetes Networking V1 API client."""
        if self._networking_v1_api is None:
            self._networking_v1_api = client.NetworkingV1Api(self.api_client)
        return self._networking_v1_api
    
    @property
    def RbacAuthorizationV1Api(self) -> client.RbacAuthorizationV1Api:
        """Get the Kubernetes RBAC Authorization V1 API client."""
        if self._rbac_authorization_v1_api is None:
            self._rbac_authorization_v1_api = client.RbacAuthorizationV1Api(self.api_client)
        return self._rbac_authorization_v1_api
    
    @property
    def CustomObjectsApi(self) -> client.CustomObjectsApi:
        """Get the Kubernetes Custom Objects API client."""
        if self._custom_objects_api is None:
            self._custom_objects_api = client.CustomObjectsApi(self.api_client)
        return self._custom_objects_api
    
    def close(self) -> None:
        """Close the API client and clean up resources."""
        if self._api_client:
            try:
                self._api_client.close()
            except Exception as e:
                logger.warning(f"Error closing API client: {e}")
            finally:
                self._api_client = None
        
        # Reset all API clients
        self._core_v1_api = None
        self._apps_v1_api = None
        self._networking_v1_api = None
        self._rbac_authorization_v1_api = None
        self._custom_objects_api = None
    
    def __str__(self) -> str:
        """String representation."""
        return f"KubernetesClient(cluster={self.cluster.name})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"KubernetesClient(cluster={self.cluster.name}, kubeconfig={self.cluster.kubeconfig_path})"


@pytest.fixture(scope="session")
def k8s_client(request):
    """
    Create and manage a Kubernetes API client for testing.
    
    This fixture creates a Kubernetes client that connects to a kind cluster.
    It automatically uses the k8s_cluster fixture to get cluster connection details.
    The scope matches the k8s_cluster fixture scope based on plugin configuration.
    
    Args:
        request: Pytest request object containing fixture parameters.
        
    Returns:
        KubernetesClient instance ready for testing.
        
    Fixture Parameters:
        scope (str, optional): Override the default scope for this specific client.
        
    Example:
        def test_with_client(k8s_client):
            v1 = k8s_client.CoreV1Api
            nodes = v1.list_node()
            assert len(nodes.items) > 0
            
        def test_with_both(k8s_cluster, k8s_client):
            # k8s_client uses the same cluster as k8s_cluster
            assert k8s_client.cluster is k8s_cluster
            
        @pytest.mark.parametrize("k8s_client", [
            {"scope": "function"}
        ], indirect=True)
        def test_with_function_scope(k8s_client):
            # This client will have function scope
            assert k8s_client.cluster.is_ready()
    """
    # Get fixture parameters
    params = getattr(request, 'param', {})
    if not isinstance(params, dict):
        params = {}
    
    # Get the default scope from configuration (same as k8s_cluster)
    from ..config import get_plugin_config
    plugin_config = get_plugin_config()
    default_scope = plugin_config.cluster.default_scope
    
    # Extract scope override if provided
    effective_scope = params.pop('scope', default_scope)
    
    # Check if cluster is already provided in the request
    cluster = None
    for fixture_name in request.fixturenames:
        if fixture_name.startswith('k8s_cluster'):
            cluster = request.getfixturevalue(fixture_name)
            break
    
    # If no cluster found, request the default cluster
    if cluster is None:
        cluster = request.getfixturevalue("k8s_cluster")
    
    # Create the client
    logger.info(f"Creating Kubernetes client for cluster: {cluster.name} (scope: {effective_scope})")
    k8s_client_instance = KubernetesClient(cluster)
    
    # Register cleanup
    def cleanup():
        logger.info(f"Cleaning up Kubernetes client for cluster: {cluster.name}")
        k8s_client_instance.close()
    
    request.addfinalizer(cleanup)
    
    return k8s_client_instance
