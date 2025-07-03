"""
Robust cleanup management for pytest-k8s clusters.

This module provides comprehensive cleanup mechanisms that handle normal
termination, errors, interrupts, and crashes to ensure clusters are
always properly cleaned up.
"""

import atexit
import json
import logging
import os
import signal
import threading
import time
import weakref
from pathlib import Path
from typing import Dict, Optional, Set

from .kind.cluster import KindCluster

logger = logging.getLogger(__name__)


class PersistentClusterTracker:
    """
    Tracks active clusters in persistent storage for recovery after crashes.

    This class maintains a JSON file with information about active clusters,
    allowing cleanup of orphaned clusters from previous sessions that crashed
    or were forcibly terminated.
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize the persistent cluster tracker.

        Args:
            state_dir: Directory to store state file. Defaults to ~/.pytest-k8s
        """
        if state_dir is None:
            state_dir = Path.home() / ".pytest-k8s"

        self.state_dir = state_dir
        self.state_file = state_dir / "active_clusters.json"
        self.lock_file = state_dir / "active_clusters.lock"

        # Ensure state directory exists
        self.state_dir.mkdir(exist_ok=True)

        # Initialize state
        self.state: Dict[str, dict] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load cluster state from persistent storage."""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    self.state = json.load(f)
                logger.debug(f"Loaded cluster state: {list(self.state.keys())}")
            else:
                self.state = {}
        except Exception as e:
            logger.warning(f"Failed to load cluster state: {e}")
            self.state = {}

    def _save_state(self) -> None:
        """Save cluster state to persistent storage."""
        try:
            # Use atomic write with temporary file
            temp_file = self.state_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(self.state, f, indent=2)
            temp_file.replace(self.state_file)
            logger.debug(f"Saved cluster state: {list(self.state.keys())}")
        except Exception as e:
            logger.error(f"Failed to save cluster state: {e}")

    def add_cluster(self, name: str) -> None:
        """
        Add a cluster to the tracking state.

        Args:
            name: Cluster name to track
        """
        self.state[name] = {
            "created_at": time.time(),
            "pid": os.getpid(),
            "session_id": id(self),  # Unique session identifier
        }
        self._save_state()
        logger.debug(f"Added cluster to tracking: {name}")

    def remove_cluster(self, name: str) -> None:
        """
        Remove a cluster from the tracking state.

        Args:
            name: Cluster name to remove
        """
        if name in self.state:
            del self.state[name]
            self._save_state()
            logger.debug(f"Removed cluster from tracking: {name}")

    def get_tracked_clusters(self) -> Set[str]:
        """
        Get set of currently tracked cluster names.

        Returns:
            Set of cluster names being tracked
        """
        return set(self.state.keys())

    def cleanup_orphaned_clusters(self) -> None:
        """
        Clean up clusters from previous sessions that may have crashed.

        This method identifies clusters that were created by processes that
        are no longer running and attempts to clean them up.
        """
        orphaned_clusters = []

        for name, info in list(self.state.items()):
            pid = info.get("pid")
            if pid and not self._is_process_running(pid):
                orphaned_clusters.append(name)

        if orphaned_clusters:
            logger.info(
                f"Found {len(orphaned_clusters)} orphaned clusters: {orphaned_clusters}"
            )

            for name in orphaned_clusters:
                try:
                    # Check if cluster actually exists before trying to delete
                    cluster = KindCluster(name=name)
                    if cluster.exists():
                        logger.info(f"Cleaning up orphaned cluster: {name}")
                        cluster.delete()
                    else:
                        logger.debug(f"Orphaned cluster {name} no longer exists")
                except Exception as e:
                    logger.warning(f"Failed to cleanup orphaned cluster {name}: {e}")
                finally:
                    # Remove from state regardless of cleanup success
                    self.remove_cluster(name)

    def _is_process_running(self, pid: int) -> bool:
        """
        Check if a process is still running.

        Args:
            pid: Process ID to check

        Returns:
            True if process is running, False otherwise
        """
        try:
            # Send signal 0 to check if process exists
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


class ClusterCleanupManager:
    """
    Comprehensive cluster cleanup manager with multiple safety mechanisms.

    This class provides robust cleanup handling for kind clusters, including:
    - Signal handlers for interrupts (SIGINT, SIGTERM)
    - Atexit handlers for normal termination
    - Weak references to avoid memory leaks
    - Persistent state tracking for crash recovery
    - Thread-safe operations
    """

    _instance: Optional["ClusterCleanupManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ClusterCleanupManager":
        """Singleton pattern to ensure only one cleanup manager exists."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the cleanup manager (only once due to singleton)."""
        if self._initialized:
            return

        self._initialized = True
        self._clusters: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._cleanup_in_progress = False
        self._original_handlers: Dict[int, object] = {}
        self._persistent_tracker = PersistentClusterTracker()
        self._lock = threading.RLock()

        # Register cleanup handlers
        self._register_signal_handlers()
        self._register_atexit_handler()

        # Clean up any orphaned clusters from previous runs
        try:
            self._persistent_tracker.cleanup_orphaned_clusters()
        except Exception as e:
            logger.warning(f"Failed to cleanup orphaned clusters: {e}")

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown on interrupts."""
        signals_to_handle = [signal.SIGINT, signal.SIGTERM]

        # On Windows, SIGTERM might not be available
        if os.name == "nt":
            signals_to_handle = [signal.SIGINT]

        for sig in signals_to_handle:
            try:
                original_handler = signal.signal(sig, self._signal_handler)
                self._original_handlers[sig] = original_handler
                logger.debug(f"Registered signal handler for {sig}")
            except (OSError, ValueError) as e:
                logger.debug(f"Could not register handler for signal {sig}: {e}")

    def _register_atexit_handler(self) -> None:
        """Register atexit handler for cleanup on normal termination."""
        atexit.register(self._atexit_cleanup)
        logger.debug("Registered atexit cleanup handler")

    def _signal_handler(self, signum: int, frame) -> None:
        """
        Handle interrupt signals by cleaning up clusters.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating cluster cleanup...")
        self._cleanup_all_clusters(emergency=True)

        # Call original handler if it exists
        original_handler = self._original_handlers.get(signum)
        if original_handler and callable(original_handler):
            try:
                original_handler(signum, frame)
            except Exception as e:
                logger.error(f"Error calling original signal handler: {e}")

        # For SIGINT, we might want to exit after cleanup
        if signum == signal.SIGINT:
            logger.info("Exiting after cleanup due to interrupt")
            os._exit(1)

    def _atexit_cleanup(self) -> None:
        """Cleanup handler called on normal program termination."""
        logger.debug("Atexit cleanup initiated")
        self._cleanup_all_clusters(emergency=False)

    def register_cluster(self, cluster: KindCluster) -> None:
        """
        Register a cluster for cleanup tracking.

        Args:
            cluster: KindCluster instance to track
        """
        with self._lock:
            self._clusters[cluster.name] = cluster
            self._persistent_tracker.add_cluster(cluster.name)
            logger.debug(f"Registered cluster for cleanup: {cluster.name}")

    def unregister_cluster(self, cluster: KindCluster) -> None:
        """
        Unregister a cluster from cleanup tracking.

        Args:
            cluster: KindCluster instance to stop tracking
        """
        with self._lock:
            if cluster.name in self._clusters:
                del self._clusters[cluster.name]
            self._persistent_tracker.remove_cluster(cluster.name)
            logger.debug(f"Unregistered cluster from cleanup: {cluster.name}")

    def cleanup_cluster(self, cluster: KindCluster, force: bool = False) -> bool:
        """
        Clean up a specific cluster.

        Args:
            cluster: Cluster to clean up
            force: Force cleanup even if keep_cluster is True

        Returns:
            True if cleanup was successful, False otherwise
        """
        if not force and cluster.keep_cluster:
            logger.info(f"Keeping cluster {cluster.name} (keep_cluster=True)")
            self.unregister_cluster(cluster)
            return True

        try:
            logger.info(f"Cleaning up cluster: {cluster.name}")
            cluster.delete()
            self.unregister_cluster(cluster)
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup cluster {cluster.name}: {e}")
            return False

    def _cleanup_all_clusters(self, emergency: bool = False) -> None:
        """
        Clean up all registered clusters.

        Args:
            emergency: Whether this is an emergency cleanup (ignore keep_cluster)
        """
        with self._lock:
            if self._cleanup_in_progress:
                logger.debug("Cleanup already in progress, skipping")
                return

            self._cleanup_in_progress = True

        try:
            clusters_to_cleanup = list(self._clusters.values())
            if not clusters_to_cleanup:
                logger.debug("No clusters to cleanup")
                return

            logger.info(f"Cleaning up {len(clusters_to_cleanup)} clusters...")

            cleanup_results = []
            for cluster in clusters_to_cleanup:
                try:
                    # In emergency cleanup, ignore keep_cluster setting
                    success = self.cleanup_cluster(cluster, force=emergency)
                    cleanup_results.append((cluster.name, success))
                except Exception as e:
                    logger.error(f"Error during cleanup of {cluster.name}: {e}")
                    cleanup_results.append((cluster.name, False))

            # Log summary
            successful = sum(1 for _, success in cleanup_results if success)
            total = len(cleanup_results)
            logger.info(
                f"Cleanup completed: {successful}/{total} clusters cleaned up successfully"
            )

            if successful < total:
                failed_clusters = [
                    name for name, success in cleanup_results if not success
                ]
                logger.warning(f"Failed to cleanup clusters: {failed_clusters}")

        except Exception as e:
            logger.error(f"Error during cluster cleanup: {e}")

        finally:
            self._cleanup_in_progress = False

    def get_active_clusters(self) -> Set[str]:
        """
        Get set of currently active cluster names.

        Returns:
            Set of active cluster names
        """
        with self._lock:
            return set(self._clusters.keys())

    def force_cleanup_all(self) -> None:
        """Force cleanup of all clusters, ignoring keep_cluster settings."""
        logger.info("Force cleanup initiated")
        self._cleanup_all_clusters(emergency=True)

    @classmethod
    def get_instance(cls) -> "ClusterCleanupManager":
        """Get the singleton instance of the cleanup manager."""
        return cls()


class ClusterContext:
    """
    Context manager for guaranteed cluster cleanup.

    This context manager ensures that clusters are cleaned up even if
    exceptions occur during test execution.
    """

    def __init__(
        self,
        cluster: KindCluster,
        cleanup_manager: Optional[ClusterCleanupManager] = None,
    ):
        """
        Initialize the cluster context.

        Args:
            cluster: Cluster to manage
            cleanup_manager: Cleanup manager to use (creates one if None)
        """
        self.cluster = cluster
        self.cleanup_manager = cleanup_manager or ClusterCleanupManager.get_instance()
        self._cleanup_done = False

    def __enter__(self) -> KindCluster:
        """Enter the context and register the cluster for cleanup."""
        self.cleanup_manager.register_cluster(self.cluster)
        return self.cluster

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the context and ensure cleanup happens."""
        self._cleanup()
        return False  # Don't suppress exceptions

    def __del__(self):
        """Destructor to ensure cleanup happens even if context manager isn't used properly."""
        if not self._cleanup_done:
            try:
                self._cleanup()
            except Exception as e:
                logger.error(f"Error in ClusterContext destructor: {e}")

    def _cleanup(self) -> None:
        """Perform the actual cleanup."""
        if not self._cleanup_done:
            try:
                self.cleanup_manager.cleanup_cluster(self.cluster)
            except Exception as e:
                logger.error(f"Error during cluster context cleanup: {e}")
            finally:
                self._cleanup_done = True


# Global cleanup manager instance
_cleanup_manager = ClusterCleanupManager.get_instance()


def get_cleanup_manager() -> ClusterCleanupManager:
    """Get the global cleanup manager instance."""
    return _cleanup_manager


def cleanup_all_clusters() -> None:
    """Convenience function to cleanup all clusters."""
    _cleanup_manager.force_cleanup_all()
