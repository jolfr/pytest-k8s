"""
Tests for the robust cleanup mechanism.

This module tests the cleanup manager, signal handling, and various
cleanup scenarios to ensure clusters are always properly cleaned up.
"""

import os
import signal
import subprocess
import time
import pytest
from unittest.mock import Mock, patch

from pytest_k8s.cleanup import (
    ClusterCleanupManager,
    PersistentClusterTracker,
    ClusterContext,
    get_cleanup_manager,
    cleanup_all_clusters,
)
from pytest_k8s.kind.cluster import KindCluster
from pytest_k8s.kind.errors import KindClusterError


class TestPersistentClusterTracker:
    """Test the persistent cluster tracker."""

    def test_init_creates_state_directory(self, tmp_path):
        """Test that initialization creates the state directory."""
        state_dir = tmp_path / "test_state"
        tracker = PersistentClusterTracker(state_dir)

        assert state_dir.exists()
        assert tracker.state_file == state_dir / "active_clusters.json"

    def test_add_and_remove_cluster(self, tmp_path):
        """Test adding and removing clusters from tracking."""
        tracker = PersistentClusterTracker(tmp_path)

        # Add cluster
        tracker.add_cluster("test-cluster")
        assert "test-cluster" in tracker.get_tracked_clusters()

        # Verify state is persisted
        assert tracker.state_file.exists()

        # Remove cluster
        tracker.remove_cluster("test-cluster")
        assert "test-cluster" not in tracker.get_tracked_clusters()

    def test_load_existing_state(self, tmp_path):
        """Test loading existing state from file."""
        # Create initial tracker and add cluster
        tracker1 = PersistentClusterTracker(tmp_path)
        tracker1.add_cluster("existing-cluster")

        # Create new tracker instance - should load existing state
        tracker2 = PersistentClusterTracker(tmp_path)
        assert "existing-cluster" in tracker2.get_tracked_clusters()

    def test_cleanup_orphaned_clusters(self, tmp_path):
        """Test cleanup of orphaned clusters."""
        tracker = PersistentClusterTracker(tmp_path)

        # Add cluster with fake PID that doesn't exist
        tracker.state["orphaned-cluster"] = {
            "created_at": time.time(),
            "pid": 999999,  # Non-existent PID
            "session_id": 12345,
        }
        tracker._save_state()

        # Mock KindCluster to avoid actual cluster operations
        with patch("pytest_k8s.cleanup.KindCluster") as mock_cluster_class:
            mock_cluster = Mock()
            mock_cluster.exists.return_value = True
            mock_cluster_class.return_value = mock_cluster

            tracker.cleanup_orphaned_clusters()

            # Verify cluster was attempted to be deleted
            mock_cluster.delete.assert_called_once()

        # Verify cluster was removed from state
        assert "orphaned-cluster" not in tracker.get_tracked_clusters()

    def test_is_process_running(self, tmp_path):
        """Test process running detection."""
        tracker = PersistentClusterTracker(tmp_path)

        # Test with current process (should be running)
        assert tracker._is_process_running(os.getpid()) is True

        # Test with non-existent PID
        assert tracker._is_process_running(999999) is False


class TestClusterCleanupManager:
    """Test the cluster cleanup manager."""

    def test_singleton_pattern(self):
        """Test that cleanup manager follows singleton pattern."""
        manager1 = ClusterCleanupManager()
        manager2 = ClusterCleanupManager()
        assert manager1 is manager2

    def test_get_instance(self):
        """Test getting the singleton instance."""
        manager = ClusterCleanupManager.get_instance()
        assert isinstance(manager, ClusterCleanupManager)

    def test_register_and_unregister_cluster(self):
        """Test registering and unregistering clusters."""
        manager = ClusterCleanupManager()

        # Create mock cluster
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "test-cluster"

        # Register cluster
        with patch.object(manager._persistent_tracker, "add_cluster"):
            manager.register_cluster(mock_cluster)
            assert "test-cluster" in manager.get_active_clusters()

        # Unregister cluster
        with patch.object(manager._persistent_tracker, "remove_cluster"):
            manager.unregister_cluster(mock_cluster)
            assert "test-cluster" not in manager.get_active_clusters()

    def test_cleanup_cluster_respects_keep_cluster(self):
        """Test that cleanup respects keep_cluster setting."""
        manager = ClusterCleanupManager()

        # Create mock cluster with keep_cluster=True
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "keep-cluster"
        mock_cluster.keep_cluster = True

        with patch.object(manager, "unregister_cluster") as mock_unregister:
            result = manager.cleanup_cluster(mock_cluster)

            assert result is True
            mock_cluster.delete.assert_not_called()
            mock_unregister.assert_called_once_with(mock_cluster)

    def test_cleanup_cluster_force_ignores_keep_cluster(self):
        """Test that force cleanup ignores keep_cluster setting."""
        manager = ClusterCleanupManager()

        # Create mock cluster with keep_cluster=True
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "force-cleanup-cluster"
        mock_cluster.keep_cluster = True

        with patch.object(manager, "unregister_cluster"):
            result = manager.cleanup_cluster(mock_cluster, force=True)

            assert result is True
            mock_cluster.delete.assert_called_once()

    def test_cleanup_cluster_handles_exceptions(self):
        """Test that cleanup handles exceptions gracefully."""
        manager = ClusterCleanupManager()

        # Create mock cluster that raises exception on delete
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "error-cluster"
        mock_cluster.keep_cluster = False
        mock_cluster.delete.side_effect = Exception("Delete failed")

        result = manager.cleanup_cluster(mock_cluster)
        assert result is False

    def test_signal_handler_registration(self):
        """Test that signal handlers are registered."""
        # Since ClusterCleanupManager is a singleton, we need to test differently
        # We'll check that the signal handlers are actually set
        ClusterCleanupManager.get_instance()

        # Check that signal handlers are registered by verifying they're not the default
        current_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGINT, current_sigint_handler)  # Restore

        # The handler should not be the default handler
        assert current_sigint_handler != signal.SIG_DFL
        assert callable(current_sigint_handler)

    def test_signal_handler_cleanup(self):
        """Test that signal handler triggers cleanup."""
        manager = ClusterCleanupManager()

        # Create mock cluster
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "signal-test-cluster"
        mock_cluster.keep_cluster = False

        manager._clusters["signal-test-cluster"] = mock_cluster

        # Mock the original handler to prevent it from being called
        manager._original_handlers[signal.SIGINT] = None

        with patch.object(manager, "_cleanup_all_clusters") as mock_cleanup:
            # Mock os._exit to prevent actual process termination
            with patch("os._exit") as mock_exit:
                # Simulate signal handler call
                manager._signal_handler(signal.SIGINT, None)
                mock_cleanup.assert_called_once_with(emergency=True)
                # Verify that os._exit was called with status 1 for SIGINT
                mock_exit.assert_called_once_with(1)

    def test_atexit_handler_registration(self):
        """Test that atexit handler is registered."""
        # Since ClusterCleanupManager is a singleton, we need to patch before the first instance
        # Reset the singleton instance for this test
        original_instance = ClusterCleanupManager._instance
        ClusterCleanupManager._instance = None

        try:
            with patch("atexit.register") as mock_atexit:
                manager = ClusterCleanupManager()
                mock_atexit.assert_called_with(manager._atexit_cleanup)
        finally:
            # Restore the original instance
            ClusterCleanupManager._instance = original_instance

    def test_force_cleanup_all(self):
        """Test force cleanup of all clusters."""
        manager = ClusterCleanupManager()

        with patch.object(manager, "_cleanup_all_clusters") as mock_cleanup:
            manager.force_cleanup_all()
            mock_cleanup.assert_called_once_with(emergency=True)


class TestClusterContext:
    """Test the cluster context manager."""

    def test_context_manager_success(self):
        """Test context manager with successful execution."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "context-cluster"

        mock_cleanup_manager = Mock()

        with ClusterContext(mock_cluster, mock_cleanup_manager) as cluster:
            assert cluster is mock_cluster
            mock_cleanup_manager.register_cluster.assert_called_once_with(mock_cluster)

        # Verify cleanup was called
        mock_cleanup_manager.cleanup_cluster.assert_called_once_with(mock_cluster)

    def test_context_manager_with_exception(self):
        """Test context manager when exception occurs."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "exception-cluster"

        mock_cleanup_manager = Mock()

        with pytest.raises(ValueError):
            with ClusterContext(mock_cluster, mock_cleanup_manager):
                raise ValueError("Test exception")

        # Verify cleanup was still called
        mock_cleanup_manager.cleanup_cluster.assert_called_once_with(mock_cluster)

    def test_context_manager_cleanup_exception(self):
        """Test context manager when cleanup itself fails."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "cleanup-error-cluster"

        mock_cleanup_manager = Mock()
        mock_cleanup_manager.cleanup_cluster.side_effect = Exception("Cleanup failed")

        # Should not raise exception even if cleanup fails
        with ClusterContext(mock_cluster, mock_cleanup_manager) as cluster:
            assert cluster is mock_cluster

    def test_destructor_cleanup(self):
        """Test that destructor performs cleanup if not already done."""
        mock_cluster = Mock(spec=KindCluster)
        mock_cleanup_manager = Mock()

        context = ClusterContext(mock_cluster, mock_cleanup_manager)
        context.__enter__()

        # Simulate destructor call without proper context exit
        context.__del__()

        # Verify cleanup was called
        mock_cleanup_manager.cleanup_cluster.assert_called()


class TestCleanupIntegration:
    """Integration tests for the cleanup system."""

    def test_get_cleanup_manager_returns_singleton(self):
        """Test that get_cleanup_manager returns the singleton instance."""
        manager1 = get_cleanup_manager()
        manager2 = get_cleanup_manager()
        assert manager1 is manager2

    def test_cleanup_all_clusters_function(self):
        """Test the convenience cleanup function."""
        with patch("pytest_k8s.cleanup._cleanup_manager") as mock_manager:
            cleanup_all_clusters()
            mock_manager.force_cleanup_all.assert_called_once()

    @pytest.mark.integration
    def test_real_cluster_cleanup(self):
        """Integration test with real cluster creation and cleanup."""
        # This test requires kind to be available
        pytest.importorskip("subprocess")

        # Check if kind is available
        try:
            subprocess.run(["kind", "version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("kind not available")

        manager = ClusterCleanupManager()
        cluster_name = f"cleanup-test-{int(time.time())}"

        try:
            # Create a real cluster
            cluster = KindCluster(name=cluster_name, timeout=60)
            cluster.create()

            # Register with cleanup manager
            manager.register_cluster(cluster)

            # Verify cluster exists
            assert cluster.exists()
            assert cluster_name in manager.get_active_clusters()

            # Test cleanup
            success = manager.cleanup_cluster(cluster)
            assert success is True
            assert cluster_name not in manager.get_active_clusters()

            # Verify cluster was actually deleted
            assert not cluster.exists()

        except Exception as e:
            # Ensure cleanup even if test fails
            try:
                if "cluster" in locals():
                    cluster.delete()
            except Exception:
                pass
            raise e


class TestCleanupConfiguration:
    """Test cleanup configuration and options."""

    def test_cleanup_manager_handles_orphaned_clusters_on_init(self):
        """Test that cleanup manager handles orphaned clusters on initialization."""
        # Reset the singleton instance for this test
        original_instance = ClusterCleanupManager._instance
        ClusterCleanupManager._instance = None

        try:
            with patch(
                "pytest_k8s.cleanup.PersistentClusterTracker"
            ) as mock_tracker_class:
                mock_tracker = Mock()
                mock_tracker_class.return_value = mock_tracker

                # Create new cleanup manager instance
                ClusterCleanupManager()

                # Verify orphaned cleanup was attempted
                mock_tracker.cleanup_orphaned_clusters.assert_called_once()
        finally:
            # Restore the original instance
            ClusterCleanupManager._instance = original_instance

    def test_cleanup_manager_handles_orphaned_cleanup_errors(self):
        """Test that cleanup manager handles errors during orphaned cleanup."""
        with patch("pytest_k8s.cleanup.PersistentClusterTracker") as mock_tracker_class:
            mock_tracker = Mock()
            mock_tracker.cleanup_orphaned_clusters.side_effect = Exception(
                "Cleanup error"
            )
            mock_tracker_class.return_value = mock_tracker

            # Should not raise exception even if orphaned cleanup fails
            manager = ClusterCleanupManager()
            assert manager is not None


class TestCleanupErrorHandling:
    """Test error handling in cleanup scenarios."""

    def test_cleanup_with_cluster_delete_failure(self):
        """Test cleanup when cluster deletion fails."""
        manager = ClusterCleanupManager()

        mock_cluster = Mock(spec=KindCluster)
        mock_cluster.name = "delete-fail-cluster"
        mock_cluster.keep_cluster = False
        mock_cluster.delete.side_effect = KindClusterError("Delete failed")

        result = manager.cleanup_cluster(mock_cluster)
        assert result is False

    def test_cleanup_all_with_mixed_results(self):
        """Test cleanup all when some clusters fail to clean up."""
        manager = ClusterCleanupManager()

        # Create mock clusters - one succeeds, one fails
        success_cluster = Mock(spec=KindCluster)
        success_cluster.name = "success-cluster"
        success_cluster.keep_cluster = False

        fail_cluster = Mock(spec=KindCluster)
        fail_cluster.name = "fail-cluster"
        fail_cluster.keep_cluster = False
        fail_cluster.delete.side_effect = Exception("Delete failed")

        manager._clusters = {
            "success-cluster": success_cluster,
            "fail-cluster": fail_cluster,
        }

        with patch.object(manager, "cleanup_cluster", side_effect=[True, False]):
            manager._cleanup_all_clusters()

        # Should complete without raising exception

    def test_persistent_tracker_handles_corrupted_state_file(self, tmp_path):
        """Test that persistent tracker handles corrupted state files."""
        state_file = tmp_path / "active_clusters.json"

        # Create corrupted JSON file
        state_file.write_text("{ invalid json")

        # Should handle corrupted file gracefully
        tracker = PersistentClusterTracker(tmp_path)
        assert tracker.state == {}

    def test_persistent_tracker_handles_permission_errors(self, tmp_path):
        """Test that persistent tracker handles permission errors."""
        # Make directory read-only to simulate permission error
        state_dir = tmp_path / "readonly"
        state_dir.mkdir()

        if os.name != "nt":  # Skip on Windows due to different permission model
            state_dir.chmod(0o444)

            # Should handle permission error gracefully
            tracker = PersistentClusterTracker(state_dir)

            # Try to add cluster (should not raise exception)
            tracker.add_cluster("test-cluster")

            # Restore permissions for cleanup
            state_dir.chmod(0o755)
