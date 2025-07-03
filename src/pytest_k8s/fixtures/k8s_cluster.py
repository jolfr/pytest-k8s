"""
Kubernetes cluster fixtures for pytest-k8s.

This module provides pytest fixtures for creating and managing Kubernetes clusters
during testing. The fixtures support configurable scopes and automatic cleanup.
"""

import logging
import pytest
from typing import Dict, Optional, Union
from pathlib import Path

from ..kind.cluster import KindCluster
from ..kind.cluster_manager import KindClusterManager
from ..kind.config import KindClusterConfig
from ..config import get_plugin_config
from ..cleanup import get_cleanup_manager

logger = logging.getLogger(__name__)


class ClusterFixtureManager:
    """
    Manages cluster fixtures with different scopes and configurations.

    This class handles the creation, configuration, and cleanup of clusters
    for pytest fixtures with different scopes.
    """

    def __init__(self):
        """Initialize the cluster fixture manager."""
        self._cluster_manager = KindClusterManager()
        self._active_clusters: Dict[str, KindCluster] = {}

    def create_cluster(
        self,
        scope: str = "session",
        name: Optional[str] = None,
        config: Optional[KindClusterConfig] = None,
        config_path: Optional[Union[str, Path]] = None,
        timeout: Optional[int] = None,
        keep_cluster: Optional[bool] = None,
        image: Optional[str] = None,
        extra_port_mappings: Optional[list] = None,
        **kwargs,
    ) -> KindCluster:
        """
        Create a cluster with the specified configuration.

        Args:
            scope: Fixture scope (function, class, module, package, session)
            name: Cluster name. Generated if None.
            config: Cluster configuration object.
            config_path: Path to cluster configuration file.
            timeout: Timeout in seconds for cluster operations.
            keep_cluster: Whether to keep cluster after deletion is requested.
            image: Kubernetes node image to use.
            extra_port_mappings: Additional port mappings for the cluster.
            **kwargs: Additional cluster configuration options.

        Returns:
            KindCluster instance.
        """
        # Get plugin configuration for defaults
        plugin_config = get_plugin_config()

        # Set defaults from plugin config if not specified
        if timeout is None:
            timeout = plugin_config.cluster.default_timeout
        if keep_cluster is None:
            keep_cluster = plugin_config.cluster.default_keep_cluster

        # Create cluster configuration
        cluster_config = {}
        if timeout is not None:
            cluster_config["timeout"] = timeout
        if keep_cluster is not None:
            cluster_config["keep_cluster"] = keep_cluster
        if image is not None:
            cluster_config["image"] = image
        if extra_port_mappings is not None:
            cluster_config["extra_port_mappings"] = extra_port_mappings

        # Merge with additional kwargs
        cluster_config.update(kwargs)

        # Create the cluster
        if config:
            cluster = KindCluster(name=name, config=config, **cluster_config)
        elif config_path:
            cluster = KindCluster(name=name, config_path=config_path, **cluster_config)
        else:
            cluster = KindCluster(name=name, **cluster_config)

        # Track the cluster
        self._active_clusters[cluster.name] = cluster

        logger.info(f"Creating {scope}-scoped cluster: {cluster.name}")
        cluster.create()

        return cluster

    def cleanup_cluster(self, cluster: KindCluster) -> None:
        """
        Clean up a cluster.

        Args:
            cluster: Cluster to clean up.
        """
        if cluster.name in self._active_clusters:
            logger.info(f"Cleaning up cluster: {cluster.name}")
            try:
                cluster.delete()
            except Exception as e:
                logger.error(f"Error cleaning up cluster {cluster.name}: {e}")
            finally:
                del self._active_clusters[cluster.name]

    def cleanup_all(self) -> None:
        """Clean up all active clusters."""
        for cluster in list(self._active_clusters.values()):
            self.cleanup_cluster(cluster)


# Global fixture manager instance
_fixture_manager = ClusterFixtureManager()


def _create_scoped_cluster_fixture(scope: str):
    """
    Create a cluster fixture with the specified scope.

    Args:
        scope: Fixture scope (function, class, module, package, session)

    Returns:
        Pytest fixture function.
    """

    @pytest.fixture(scope=scope)
    def cluster_fixture(request):
        """
        Create and manage a Kubernetes cluster for testing.

        This fixture creates a kind-based Kubernetes cluster that can be used
        for testing applications with Kubernetes dependencies.

        Args:
            request: Pytest request object containing fixture parameters.

        Returns:
            KindCluster instance ready for testing.

        Fixture Parameters:
            name (str, optional): Cluster name. Generated if not provided.
            config (KindClusterConfig, optional): Cluster configuration object.
            config_path (str|Path, optional): Path to cluster configuration file.
            timeout (int, optional): Timeout for cluster operations (default: 300).
            keep_cluster (bool, optional): Keep cluster after tests (default: False).
            image (str, optional): Kubernetes node image to use.
            extra_port_mappings (list, optional): Additional port mappings.
            scope (str, optional): Override the fixture scope for this specific cluster.

        Example:
            @pytest.mark.parametrize("k8s_cluster", [
                {"name": "test-cluster", "timeout": 600, "scope": "function"}
            ], indirect=True)
            def test_with_custom_cluster(k8s_cluster):
                assert k8s_cluster.is_ready()
        """
        # Get fixture parameters
        params = getattr(request, "param", {})
        if not isinstance(params, dict):
            params = {}

        # Extract scope override if provided
        effective_scope = params.pop("scope", scope)

        # Create the cluster
        cluster = _fixture_manager.create_cluster(scope=effective_scope, **params)

        # Register cleanup
        def cleanup():
            _fixture_manager.cleanup_cluster(cluster)

        request.addfinalizer(cleanup)

        return cluster

    return cluster_fixture


def _create_dynamic_cluster_fixture():
    """
    Create a cluster fixture that uses the configured default scope.

    Returns:
        Pytest fixture function.
    """

    def cluster_fixture(request):
        """
        Create and manage a Kubernetes cluster for testing.

        This fixture creates a kind-based Kubernetes cluster that can be used
        for testing applications with Kubernetes dependencies. The scope is
        determined by the plugin configuration or can be overridden via parameters.

        Args:
            request: Pytest request object containing fixture parameters.

        Returns:
            KindCluster instance ready for testing.

        Fixture Parameters:
            name (str, optional): Cluster name. Generated if not provided.
            config (KindClusterConfig, optional): Cluster configuration object.
            config_path (str|Path, optional): Path to cluster configuration file.
            timeout (int, optional): Timeout for cluster operations (default: 300).
            keep_cluster (bool, optional): Keep cluster after tests (default: False).
            image (str, optional): Kubernetes node image to use.
            extra_port_mappings (list, optional): Additional port mappings.
            scope (str, optional): Override the default scope for this specific cluster.

        Example:
            @pytest.mark.parametrize("k8s_cluster", [
                {"name": "test-cluster", "timeout": 600, "scope": "function"}
            ], indirect=True)
            def test_with_custom_cluster(k8s_cluster):
                assert k8s_cluster.is_ready()
        """
        # Get fixture parameters
        params = getattr(request, "param", {})
        if not isinstance(params, dict):
            params = {}

        # Get the default scope from configuration
        plugin_config = get_plugin_config()
        default_scope = plugin_config.cluster.default_scope

        # Extract scope override if provided
        effective_scope = params.pop("scope", default_scope)

        # Create the cluster
        cluster = _fixture_manager.create_cluster(scope=effective_scope, **params)

        # Register cleanup
        def cleanup():
            _fixture_manager.cleanup_cluster(cluster)

        request.addfinalizer(cleanup)

        return cluster

    return cluster_fixture


# Create the main k8s_cluster fixture using dynamic scope
@pytest.fixture(scope="session")
def k8s_cluster(request):
    """
    Create and manage a Kubernetes cluster for testing.

    This fixture creates a kind-based Kubernetes cluster that can be used
    for testing applications with Kubernetes dependencies. The scope is
    determined by the plugin configuration or can be overridden via parameters.

    Args:
        request: Pytest request object containing fixture parameters.

    Returns:
        KindCluster instance ready for testing.

    Fixture Parameters:
        name (str, optional): Cluster name. Generated if not provided.
        config (KindClusterConfig, optional): Cluster configuration object.
        config_path (str|Path, optional): Path to cluster configuration file.
        timeout (int, optional): Timeout for cluster operations (default: 300).
        keep_cluster (bool, optional): Keep cluster after tests (default: False).
        image (str, optional): Kubernetes node image to use.
        extra_port_mappings (list, optional): Additional port mappings.
        scope (str, optional): Override the default scope for this specific cluster.

    Example:
        @pytest.mark.parametrize("k8s_cluster", [
            {"name": "test-cluster", "timeout": 600, "scope": "function"}
        ], indirect=True)
        def test_with_custom_cluster(k8s_cluster):
            assert k8s_cluster.is_ready()
    """
    # Get fixture parameters
    params = getattr(request, "param", {})
    if not isinstance(params, dict):
        params = {}

    # Get the default scope from configuration
    plugin_config = get_plugin_config()
    default_scope = plugin_config.cluster.default_scope

    # Extract scope override if provided
    effective_scope = params.pop("scope", default_scope)

    # Get the cleanup manager
    cleanup_manager = get_cleanup_manager()
    cluster = None

    try:
        # Create the cluster
        cluster = _fixture_manager.create_cluster(scope=effective_scope, **params)

        # Register with the robust cleanup manager
        cleanup_manager.register_cluster(cluster)

        # Register multiple cleanup mechanisms for maximum safety
        def fixture_cleanup():
            try:
                _fixture_manager.cleanup_cluster(cluster)
            except Exception as e:
                logger.error(f"Fixture cleanup failed: {e}")
            finally:
                # Ensure cleanup manager also removes it
                cleanup_manager.unregister_cluster(cluster)

        request.addfinalizer(fixture_cleanup)

        # Return the cluster (context manager will be handled by cleanup mechanisms)
        return cluster

    except Exception:
        # Ensure cleanup even if creation fails
        if cluster:
            try:
                cleanup_manager.cleanup_cluster(cluster, force=True)
            except Exception as cleanup_error:
                logger.error(f"Emergency cleanup failed: {cleanup_error}")
        raise


@pytest.fixture(scope="session", autouse=True)
def _cleanup_all_clusters():
    """
    Auto-use fixture to ensure all clusters are cleaned up at session end.

    This fixture automatically runs at the end of the test session to ensure
    that any remaining clusters are properly cleaned up.
    """
    yield

    # Cleanup any remaining clusters
    _fixture_manager.cleanup_all()
