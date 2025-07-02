"""
Cluster manager for kind (Kubernetes in Docker) clusters.

This module provides higher-level operations for managing multiple clusters,
tracking cluster state, and providing cluster registry functionality.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from .cluster import KindCluster
from .errors import KindClusterNotFoundError

logger = logging.getLogger(__name__)


class KindClusterManager:
    """
    Manages multiple kind clusters and provides cluster lifecycle operations.

    This class provides higher-level operations for managing multiple clusters,
    tracking cluster state, and providing cluster registry functionality.
    """

    def __init__(self):
        """Initialize the cluster manager."""
        self._clusters: Dict[str, KindCluster] = {}
        self._default_config = {
            "timeout": 300,
            "keep_cluster": False,
            "image": None,
        }

    def create_cluster(
        self,
        name: Optional[str] = None,
        config_path: Optional[Union[str, Path]] = None,
        **kwargs,
    ) -> KindCluster:
        """
        Create a new kind cluster.

        Args:
            name: Cluster name. Generated if None.
            config_path: Path to cluster configuration.
            **kwargs: Additional cluster configuration options.

        Returns:
            KindCluster instance.

        Raises:
            KindClusterCreationError: If cluster creation fails.
        """
        # Merge with default config
        config = {**self._default_config, **kwargs}

        # Filter out unknown kwargs that KindCluster doesn't accept
        valid_kwargs = {"timeout", "keep_cluster", "image", "extra_port_mappings"}
        filtered_config = {k: v for k, v in config.items() if k in valid_kwargs}

        cluster = KindCluster(name=name, config_path=config_path, **filtered_config)

        cluster.create()
        self._clusters[cluster.name] = cluster

        return cluster

    def get_cluster(self, name: str) -> Optional[KindCluster]:
        """
        Get a cluster by name.

        Args:
            name: Cluster name.

        Returns:
            KindCluster instance or None if not found.
        """
        return self._clusters.get(name)

    def delete_cluster(self, name: str) -> None:
        """
        Delete a cluster by name.

        Args:
            name: Cluster name.

        Raises:
            KindClusterNotFoundError: If cluster not found.
        """
        cluster = self._clusters.get(name)
        if not cluster:
            raise KindClusterNotFoundError(f"Cluster {name} not found")

        cluster.delete()
        del self._clusters[name]

    def list_clusters(self) -> List[str]:
        """
        List all managed cluster names.

        Returns:
            List of cluster names.
        """
        return list(self._clusters.keys())

    def cleanup_all(self) -> None:
        """Clean up all managed clusters."""
        for cluster in list(self._clusters.values()):
            try:
                cluster.delete()
            except Exception as e:
                logger.error(f"Error cleaning up cluster {cluster.name}: {e}")

        self._clusters.clear()

    def __len__(self) -> int:
        """Return number of managed clusters."""
        return len(self._clusters)

    def __iter__(self):
        """Iterate over managed clusters."""
        return iter(self._clusters.values())
