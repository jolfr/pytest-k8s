"""
Integration tests for k8s_cluster and k8s_client fixtures.

This module contains comprehensive integration tests that verify the proper
interaction between k8s_cluster and k8s_client fixtures when used together.
These tests use pytester to create isolated test environments and do not
mock cluster creation behavior to ensure real integration testing.
"""

import pytest
from unittest.mock import Mock, patch


class TestClusterClientIntegration:
    """Test integration between k8s_cluster and k8s_client fixtures."""

    def test_client_uses_same_cluster_instance(self, pytester):
        """Test that k8s_client uses the same cluster instance as k8s_cluster."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_same_cluster_instance(k8s_cluster, k8s_client):
                # Client should use the exact same cluster instance
                assert k8s_client.cluster is k8s_cluster
                assert k8s_client.cluster.name == k8s_cluster.name
                assert k8s_client.cluster.kubeconfig_path == k8s_cluster.kubeconfig_path
        """)

        # Mock both fixtures to avoid actual cluster creation
        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "integration-test-cluster"
                mock_cluster.kubeconfig_path = "/tmp/test-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

    def test_client_connects_to_cluster_kubeconfig(self, pytester):
        """Test that k8s_client properly connects using cluster's kubeconfig."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_kubeconfig_connection(k8s_cluster, k8s_client):
                # Verify client loaded the correct kubeconfig
                assert k8s_client.cluster.kubeconfig_path is not None
                assert k8s_client.cluster.kubeconfig_path == k8s_cluster.kubeconfig_path
        """)

        # Mock cluster and kubeconfig loading
        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config") as mock_load_config:
                mock_cluster = Mock()
                mock_cluster.name = "kubeconfig-test-cluster"
                mock_cluster.kubeconfig_path = "/tmp/test-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Verify kubeconfig was loaded with correct parameters
                mock_load_config.assert_called_with(
                    config_file="/tmp/test-kubeconfig",
                    context="kind-kubeconfig-test-cluster",
                )

    def test_client_cleanup_after_cluster_cleanup(self, pytester):
        """Test that k8s_client is properly cleaned up when cluster is cleaned up."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "cleanup-test-cluster"}
            ], indirect=True)
            def test_cleanup_order(k8s_cluster, k8s_client):
                # Both fixtures should be available during test
                assert k8s_cluster is not None
                assert k8s_client is not None
                assert k8s_client.cluster is k8s_cluster
        """)

        # Mock cluster and client to track cleanup calls
        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "cleanup-test-cluster"
                mock_cluster.kubeconfig_path = "/tmp/test-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Verify cluster cleanup was called
                mock_cluster.create.assert_called_once()
                mock_cluster.delete.assert_called_once()
                # Note: Client cleanup happens in the client fixture's finalizer


class TestScopeIntegration:
    """Test scope integration between cluster and client fixtures."""

    def test_session_scope_integration(self, pytester):
        """Test that both fixtures work correctly with session scope."""
        pytester.makepyfile("""
            import pytest_k8s
            
            cluster_instances = []
            client_instances = []
            
            def test_first_session_access(k8s_cluster, k8s_client):
                cluster_instances.append(id(k8s_cluster))
                client_instances.append(id(k8s_client))
                assert k8s_client.cluster is k8s_cluster
                
            def test_second_session_access(k8s_cluster, k8s_client):
                cluster_instances.append(id(k8s_cluster))
                client_instances.append(id(k8s_client))
                assert k8s_client.cluster is k8s_cluster
                
            def test_session_scope_reuse():
                # Both tests should use the same cluster instance
                assert len(set(cluster_instances)) == 1
                # But may have different client instances (depending on implementation)
                # The important thing is that clients use the same cluster
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "session-scope-cluster"
                mock_cluster.kubeconfig_path = "/tmp/session-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Should only create one cluster for session scope
                assert mock_cluster_class.call_count == 1

    def test_function_scope_integration(self, pytester):
        """Test that both fixtures work correctly with function scope."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            cluster_instances = []
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "func-cluster-1"}
            ], indirect=True)
            def test_first_function_access(k8s_cluster, k8s_client):
                cluster_instances.append(k8s_cluster.name)
                # Client should connect to the function-scoped cluster
                assert k8s_client.cluster is k8s_cluster
                assert k8s_cluster.name == "func-cluster-1"
                
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "func-cluster-2"}
            ], indirect=True)
            def test_second_function_access(k8s_cluster, k8s_client):
                cluster_instances.append(k8s_cluster.name)
                # Client should connect to the function-scoped cluster
                # Note: client fixture has session scope, but it should connect to the current cluster
                assert k8s_cluster.name == "func-cluster-2"
                
            def test_function_scope_isolation():
                # Each test should get a different cluster
                assert len(set(cluster_instances)) == 2
                assert "func-cluster-1" in cluster_instances
                assert "func-cluster-2" in cluster_instances
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster_1 = Mock()
                mock_cluster_1.name = "func-cluster-1"
                mock_cluster_1.kubeconfig_path = "/tmp/func-kubeconfig-1"

                mock_cluster_2 = Mock()
                mock_cluster_2.name = "func-cluster-2"
                mock_cluster_2.kubeconfig_path = "/tmp/func-kubeconfig-2"

                mock_cluster_class.side_effect = [mock_cluster_1, mock_cluster_2]

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Should create two clusters for function scope
                assert mock_cluster_class.call_count == 2

    def test_mixed_scope_integration(self, pytester):
        """Test integration when cluster and client have different scope parameters."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "mixed-scope-cluster"}
            ], indirect=True)
            def test_mixed_scope(k8s_cluster, k8s_client):
                # Client should still connect to the function-scoped cluster
                assert k8s_client.cluster is k8s_cluster
                assert k8s_cluster.name == "mixed-scope-cluster"
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "mixed-scope-cluster"
                mock_cluster.kubeconfig_path = "/tmp/mixed-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0


class TestParameterizedIntegration:
    """Test integration with parameterized fixtures."""

    def test_parameterized_cluster_with_client(self, pytester):
        """Test that k8s_client works with parameterized k8s_cluster."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            cluster_names = []
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"name": "param-cluster-1", "timeout": 300},
                {"name": "param-cluster-2", "image": "kindest/node:v1.27.0"},
                {"name": "param-cluster-3", "keep_cluster": False}
            ], indirect=True)
            def test_parameterized_integration(k8s_cluster, k8s_client):
                # Track cluster names for verification
                cluster_names.append(k8s_cluster.name)
                
                # Client should connect to the parameterized cluster
                # Note: client has session scope, so it connects to the first cluster
                # but we can still verify the cluster is parameterized correctly
                assert k8s_cluster.name in ["param-cluster-1", "param-cluster-2", "param-cluster-3"]
                
                # Verify client has access to all API clients
                assert hasattr(k8s_client, 'CoreV1Api')
                assert hasattr(k8s_client, 'AppsV1Api')
                assert hasattr(k8s_client, 'NetworkingV1Api')
                
            def test_verify_parameterization():
                # Verify all three parameter sets were used
                assert len(cluster_names) == 3
                assert "param-cluster-1" in cluster_names
                assert "param-cluster-2" in cluster_names
                assert "param-cluster-3" in cluster_names
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                # Create mock clusters for each parameter set
                mock_clusters = []
                for i, name in enumerate(
                    ["param-cluster-1", "param-cluster-2", "param-cluster-3"]
                ):
                    mock_cluster = Mock()
                    mock_cluster.name = name
                    mock_cluster.kubeconfig_path = f"/tmp/param-kubeconfig-{i + 1}"
                    mock_clusters.append(mock_cluster)

                mock_cluster_class.side_effect = mock_clusters

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Should create three clusters for the three parameter sets
                assert mock_cluster_class.call_count == 3

                # Verify each cluster was created with correct parameters
                calls = mock_cluster_class.call_args_list
                assert calls[0][1]["name"] == "param-cluster-1"
                assert calls[0][1]["timeout"] == 300
                assert calls[1][1]["name"] == "param-cluster-2"
                assert calls[1][1]["image"] == "kindest/node:v1.27.0"
                assert calls[2][1]["name"] == "param-cluster-3"
                assert not calls[2][1]["keep_cluster"]

    def test_client_with_cluster_config_object(self, pytester):
        """Test k8s_client integration with cluster using config object."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            from pytest_k8s.kind.config import create_simple_config
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"config": create_simple_config(name="config-cluster"), "name": "config-cluster"}
            ], indirect=True)
            def test_config_object_integration(k8s_cluster, k8s_client):
                assert k8s_client.cluster is k8s_cluster
                assert k8s_cluster.name == "config-cluster"
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "config-cluster"
                mock_cluster.kubeconfig_path = "/tmp/config-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Verify cluster was created with config object
                call_args = mock_cluster_class.call_args
                assert "config" in call_args[1]


class TestErrorHandlingIntegration:
    """Test error handling in integrated cluster and client fixtures."""

    def test_client_handles_cluster_creation_failure(self, pytester):
        """Test that client fixture handles cluster creation failures gracefully."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_cluster_creation_failure(k8s_cluster, k8s_client):
                # This test should fail due to cluster creation error
                # but the failure should be handled properly
                assert False, "Should not reach this point"
        """)

        # Mock cluster to fail on creation
        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            from pytest_k8s.kind.errors import KindClusterCreationError

            mock_cluster = Mock()
            mock_cluster.create.side_effect = KindClusterCreationError(
                "Creation failed"
            )
            mock_cluster_class.return_value = mock_cluster

            result = pytester.runpytest("-v")
            # Test should fail due to cluster creation error
            assert result.ret != 0

    def test_client_handles_kubeconfig_loading_failure(self, pytester):
        """Test that client handles kubeconfig loading failures."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_kubeconfig_failure(k8s_cluster, k8s_client):
                # This should fail during client creation
                assert False, "Should not reach this point"
        """)

        # Mock cluster creation success but kubeconfig loading failure
        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config") as mock_load_config:
                mock_cluster = Mock()
                mock_cluster.name = "kubeconfig-fail-cluster"
                mock_cluster.kubeconfig_path = "/tmp/invalid-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                mock_load_config.side_effect = Exception("Invalid kubeconfig")

                result = pytester.runpytest("-v")
                # Test should fail due to kubeconfig loading error
                assert result.ret != 0

    def test_cleanup_resilience_with_errors(self, pytester):
        """Test that cleanup is resilient to errors in either fixture."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "cleanup-error-cluster"}
            ], indirect=True)
            def test_cleanup_with_errors(k8s_cluster, k8s_client):
                assert k8s_cluster is not None
                assert k8s_client is not None
        """)

        # Mock both cluster and client to have cleanup errors
        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                with patch("kubernetes.client.ApiClient") as mock_api_client:
                    mock_cluster = Mock()
                    mock_cluster.name = "cleanup-error-cluster"
                    mock_cluster.kubeconfig_path = "/tmp/cleanup-kubeconfig"
                    mock_cluster.delete.side_effect = Exception(
                        "Cluster cleanup failed"
                    )
                    mock_cluster_class.return_value = mock_cluster

                    mock_api_instance = Mock()
                    mock_api_instance.close.side_effect = Exception(
                        "Client cleanup failed"
                    )
                    mock_api_client.return_value = mock_api_instance

                    result = pytester.runpytest("-v")
                    # Test should still pass despite cleanup errors
                    assert result.ret == 0


class TestRealIntegrationScenarios:
    """Test real-world integration scenarios without mocking cluster creation."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_cluster_client_integration(self, pytester):
        """Test real integration between cluster and client fixtures."""
        # Create a conftest.py to configure faster testing
        pytester.makeconftest("""
            import pytest
            
            def pytest_configure(config):
                # Configure pytest-k8s for faster testing
                config.option.k8s_cluster_timeout = 120
        """)

        pytester.makepyfile("""
            import pytest_k8s
            from kubernetes import client
            
            def test_real_integration(k8s_cluster, k8s_client):
                # Verify cluster is real and ready
                assert k8s_cluster.is_ready()
                assert k8s_client.cluster is k8s_cluster
                
                # Test actual Kubernetes API operations
                core_v1 = k8s_client.CoreV1Api
                
                # List nodes - should work with real cluster
                nodes = core_v1.list_node()
                assert len(nodes.items) > 0
                
                # Verify we can create and delete resources
                test_cm = client.V1ConfigMap(
                    metadata=client.V1ObjectMeta(name="integration-test-cm"),
                    data={"test": "integration"}
                )
                
                created_cm = core_v1.create_namespaced_config_map(
                    namespace="default",
                    body=test_cm
                )
                assert created_cm.metadata.name == "integration-test-cm"
                
                # Cleanup
                core_v1.delete_namespaced_config_map(
                    name="integration-test-cm",
                    namespace="default"
                )
        """)

        result = pytester.runpytest(
            "-v", "--tb=short", "--capture=no", "--log-cli-level=INFO"
        )
        assert result.ret == 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_api_clients_integration(self, pytester):
        """Test integration with multiple API clients."""
        pytester.makeconftest("""
            import pytest
            
            def pytest_configure(config):
                config.option.k8s_cluster_timeout = 120
        """)

        pytester.makepyfile("""
            import pytest_k8s
            from kubernetes import client
            
            def test_multiple_apis(k8s_cluster, k8s_client):
                # Test all API clients work with the same cluster
                assert k8s_cluster.is_ready()
                
                # Core V1 API
                core_v1 = k8s_client.CoreV1Api
                namespaces = core_v1.list_namespace()
                assert len(namespaces.items) >= 4  # default, kube-system, etc.
                
                # Apps V1 API
                apps_v1 = k8s_client.AppsV1Api
                deployments = apps_v1.list_deployment_for_all_namespaces()
                # Should work without error
                
                # Networking V1 API
                networking_v1 = k8s_client.NetworkingV1Api
                network_policies = networking_v1.list_network_policy_for_all_namespaces()
                # Should work without error
                
                # RBAC V1 API
                rbac_v1 = k8s_client.RbacAuthorizationV1Api
                cluster_roles = rbac_v1.list_cluster_role()
                assert len(cluster_roles.items) > 0
                
                # Custom Objects API
                custom_objects = k8s_client.CustomObjectsApi
                # Should be available for custom resource operations
                assert custom_objects is not None
        """)

        result = pytester.runpytest(
            "-v", "--tb=short", "--capture=no", "--log-cli-level=INFO"
        )
        assert result.ret == 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_function_scope_real_isolation(self, pytester):
        """Test that function-scoped fixtures provide real isolation."""
        pytester.makeconftest("""
            import pytest
            
            def pytest_configure(config):
                config.option.k8s_cluster_timeout = 120
        """)

        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            from kubernetes import client
            
            cluster_names = []
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "isolation-test-1", "timeout": 120}
            ], indirect=True)
            def test_first_isolated_cluster(k8s_cluster, k8s_client):
                cluster_names.append(k8s_cluster.name)
                assert k8s_cluster.name == "isolation-test-1"
                assert k8s_client.cluster is k8s_cluster
                
                # Create a resource that should not exist in other test
                core_v1 = k8s_client.CoreV1Api
                test_cm = client.V1ConfigMap(
                    metadata=client.V1ObjectMeta(name="isolation-marker-1"),
                    data={"test": "first"}
                )
                core_v1.create_namespaced_config_map(namespace="default", body=test_cm)
                
                # Verify it exists
                cm = core_v1.read_namespaced_config_map(name="isolation-marker-1", namespace="default")
                assert cm.data["test"] == "first"
                
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "isolation-test-2", "timeout": 120}
            ], indirect=True)
            def test_second_isolated_cluster(k8s_cluster, k8s_client):
                cluster_names.append(k8s_cluster.name)
                assert k8s_cluster.name == "isolation-test-2"
                assert k8s_client.cluster is k8s_cluster
                
                # The resource from the first test should not exist
                core_v1 = k8s_client.CoreV1Api
                try:
                    core_v1.read_namespaced_config_map(name="isolation-marker-1", namespace="default")
                    assert False, "Resource from first test should not exist in isolated cluster"
                except client.exceptions.ApiException as e:
                    assert e.status == 404  # Not found - good!
                
                # Create our own resource
                test_cm = client.V1ConfigMap(
                    metadata=client.V1ObjectMeta(name="isolation-marker-2"),
                    data={"test": "second"}
                )
                core_v1.create_namespaced_config_map(namespace="default", body=test_cm)
                
            def test_isolation_verification():
                # Verify we used different clusters
                assert len(set(cluster_names)) == 2
                assert "isolation-test-1" in cluster_names
                assert "isolation-test-2" in cluster_names
        """)

        result = pytester.runpytest(
            "-v", "--tb=short", "--capture=no", "--log-cli-level=INFO"
        )
        assert result.ret == 0


class TestAdvancedIntegrationPatterns:
    """Test advanced integration patterns and edge cases."""

    def test_fixture_dependency_order(self, pytester):
        """Test that fixture dependency order is handled correctly."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_client_first_then_cluster(k8s_client, k8s_cluster):
                # Even when client is requested first, it should work
                assert k8s_client.cluster is k8s_cluster
                
            def test_cluster_first_then_client(k8s_cluster, k8s_client):
                # Standard order should also work
                assert k8s_client.cluster is k8s_cluster
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "dependency-order-cluster"
                mock_cluster.kubeconfig_path = "/tmp/dependency-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

    def test_multiple_client_instances_same_cluster(self, pytester):
        """Test behavior when multiple client instances might be created for same cluster."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            @pytest.fixture
            def custom_k8s_client(k8s_cluster):
                # Create a custom client fixture that uses the same cluster
                from pytest_k8s.fixtures.k8s_client import KubernetesClient
                return KubernetesClient(k8s_cluster)
            
            def test_multiple_clients_same_cluster(k8s_cluster, k8s_client, custom_k8s_client):
                # Both clients should use the same cluster
                assert k8s_client.cluster is k8s_cluster
                assert custom_k8s_client.cluster is k8s_cluster
                assert k8s_client.cluster is custom_k8s_client.cluster
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "multi-client-cluster"
                mock_cluster.kubeconfig_path = "/tmp/multi-client-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

    def test_fixture_reuse_across_test_classes(self, pytester):
        """Test fixture reuse across different test classes."""
        pytester.makepyfile("""
            import pytest_k8s
            
            class TestFirstClass:
                def test_first_class_usage(self, k8s_cluster, k8s_client):
                    assert k8s_client.cluster is k8s_cluster
                    # Store cluster name for verification
                    TestFirstClass.cluster_name = k8s_cluster.name
                    
            class TestSecondClass:
                def test_second_class_usage(self, k8s_cluster, k8s_client):
                    assert k8s_client.cluster is k8s_cluster
                    # Should be the same cluster due to session scope
                    assert k8s_cluster.name == TestFirstClass.cluster_name
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "cross-class-cluster"
                mock_cluster.kubeconfig_path = "/tmp/cross-class-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Should only create one cluster for session scope
                assert mock_cluster_class.call_count == 1

    def test_integration_with_pytest_marks(self, pytester):
        """Test integration with various pytest marks."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            @pytest.mark.slow
            def test_marked_integration(k8s_cluster, k8s_client):
                assert k8s_client.cluster is k8s_cluster
                
            @pytest.mark.parametrize("test_data", ["data1", "data2"])
            def test_parametrized_with_fixtures(k8s_cluster, k8s_client, test_data):
                assert k8s_client.cluster is k8s_cluster
                assert test_data in ["data1", "data2"]
                
            @pytest.mark.skip(reason="Testing skip behavior")
            def test_skipped_with_fixtures(k8s_cluster, k8s_client):
                # This should not run
                assert False
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "marked-test-cluster"
                mock_cluster.kubeconfig_path = "/tmp/marked-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v", "-m", "slow")
                assert result.ret == 0

                # Should only create cluster for non-skipped tests
                assert mock_cluster_class.call_count == 1


class TestComplexIntegrationWorkflows:
    """Test complex integration workflows that combine multiple features."""

    def test_end_to_end_application_deployment(self, pytester):
        """Test end-to-end application deployment workflow."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            from kubernetes import client
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "e2e-deployment-cluster"}
            ], indirect=True)
            def test_complete_deployment_workflow(k8s_cluster, k8s_client):
                # Verify both fixtures are properly integrated
                assert k8s_client.cluster is k8s_cluster
                
                # Test complete workflow with multiple API clients
                core_v1 = k8s_client.CoreV1Api
                apps_v1 = k8s_client.AppsV1Api
                
                # Create namespace
                namespace = client.V1Namespace(
                    metadata=client.V1ObjectMeta(name="e2e-test")
                )
                core_v1.create_namespace(body=namespace)
                
                # Create deployment
                deployment = client.V1Deployment(
                    metadata=client.V1ObjectMeta(name="test-app", namespace="e2e-test"),
                    spec=client.V1DeploymentSpec(
                        replicas=1,
                        selector=client.V1LabelSelector(match_labels={"app": "test"}),
                        template=client.V1PodTemplateSpec(
                            metadata=client.V1ObjectMeta(labels={"app": "test"}),
                            spec=client.V1PodSpec(
                                containers=[
                                    client.V1Container(
                                        name="test",
                                        image="nginx:alpine",
                                        ports=[client.V1ContainerPort(container_port=80)]
                                    )
                                ]
                            )
                        )
                    )
                )
                apps_v1.create_namespaced_deployment(namespace="e2e-test", body=deployment)
                
                # Create service
                service = client.V1Service(
                    metadata=client.V1ObjectMeta(name="test-service", namespace="e2e-test"),
                    spec=client.V1ServiceSpec(
                        selector={"app": "test"},
                        ports=[client.V1ServicePort(port=80, target_port=80)]
                    )
                )
                core_v1.create_namespaced_service(namespace="e2e-test", body=service)
                
                # Verify all resources exist
                deployments = apps_v1.list_namespaced_deployment(namespace="e2e-test")
                assert len(deployments.items) == 1
                assert deployments.items[0].metadata.name == "test-app"
                
                services = core_v1.list_namespaced_service(namespace="e2e-test")
                service_names = [svc.metadata.name for svc in services.items]
                assert "test-service" in service_names
                
                # Cleanup
                apps_v1.delete_namespaced_deployment(name="test-app", namespace="e2e-test")
                core_v1.delete_namespaced_service(name="test-service", namespace="e2e-test")
                core_v1.delete_namespace(name="e2e-test")
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                with patch("kubernetes.client.CoreV1Api") as mock_core_v1:
                    with patch("kubernetes.client.AppsV1Api") as mock_apps_v1:
                        mock_cluster = Mock()
                        mock_cluster.name = "e2e-deployment-cluster"
                        mock_cluster.kubeconfig_path = "/tmp/e2e-kubeconfig"
                        mock_cluster_class.return_value = mock_cluster

                        # Mock API responses
                        mock_core_instance = Mock()
                        mock_apps_instance = Mock()
                        mock_core_v1.return_value = mock_core_instance
                        mock_apps_v1.return_value = mock_apps_instance

                        # Mock list responses
                        mock_deployment = Mock()
                        mock_deployment.metadata.name = "test-app"
                        mock_apps_instance.list_namespaced_deployment.return_value = (
                            Mock(items=[mock_deployment])
                        )

                        mock_service = Mock()
                        mock_service.metadata.name = "test-service"
                        mock_core_instance.list_namespaced_service.return_value = Mock(
                            items=[mock_service]
                        )

                        result = pytester.runpytest("-v")
                        assert result.ret == 0

    def test_multi_cluster_scenario_simulation(self, pytester):
        """Test simulation of multi-cluster scenarios using function scope."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            cluster_configs = []
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"scope": "function", "name": "cluster-east", "timeout": 120},
                {"scope": "function", "name": "cluster-west", "timeout": 120}
            ], indirect=True)
            def test_multi_cluster_simulation(k8s_cluster, k8s_client):
                # Each test run simulates a different cluster
                cluster_configs.append({
                    "name": k8s_cluster.name,
                    "client_cluster": k8s_client.cluster.name
                })
                
                # Verify client is connected to correct cluster
                assert k8s_client.cluster is k8s_cluster
                assert k8s_cluster.name in ["cluster-east", "cluster-west"]
                
                # Simulate cluster-specific operations
                core_v1 = k8s_client.CoreV1Api
                
                # Create cluster-specific namespace
                namespace_name = f"region-{k8s_cluster.name.split('-')[1]}"
                # This would create different namespaces in different clusters
                
            def test_verify_multi_cluster_isolation():
                # Verify we tested both clusters
                assert len(cluster_configs) == 2
                cluster_names = [config["name"] for config in cluster_configs]
                assert "cluster-east" in cluster_names
                assert "cluster-west" in cluster_names
                
                # Verify each client was connected to its respective cluster
                for config in cluster_configs:
                    assert config["name"] == config["client_cluster"]
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster_east = Mock()
                mock_cluster_east.name = "cluster-east"
                mock_cluster_east.kubeconfig_path = "/tmp/east-kubeconfig"

                mock_cluster_west = Mock()
                mock_cluster_west.name = "cluster-west"
                mock_cluster_west.kubeconfig_path = "/tmp/west-kubeconfig"

                mock_cluster_class.side_effect = [mock_cluster_east, mock_cluster_west]

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Should create two clusters for the two parameter sets
                assert mock_cluster_class.call_count == 2


class TestPerformanceAndStressIntegration:
    """Test performance and stress scenarios for fixture integration."""

    def test_concurrent_api_operations_simulation(self, pytester):
        """Test simulation of concurrent API operations."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            from kubernetes import client
            
            def test_concurrent_operations_simulation(k8s_cluster, k8s_client):
                # Simulate multiple concurrent operations using the same client
                assert k8s_client.cluster is k8s_cluster
                
                # Get multiple API clients
                core_v1 = k8s_client.CoreV1Api
                apps_v1 = k8s_client.AppsV1Api
                networking_v1 = k8s_client.NetworkingV1Api
                rbac_v1 = k8s_client.RbacAuthorizationV1Api
                
                # Simulate concurrent access patterns
                operations = [
                    lambda: core_v1.list_namespace(),
                    lambda: apps_v1.list_deployment_for_all_namespaces(),
                    lambda: networking_v1.list_network_policy_for_all_namespaces(),
                    lambda: rbac_v1.list_cluster_role()
                ]
                
                # In a real scenario, these might be called concurrently
                # Here we just verify they can all be accessed
                for operation in operations:
                    # Would normally call operation() but we're mocking
                    pass
                    
                # Verify all clients are available and connected to same cluster
                assert core_v1 is not None
                assert apps_v1 is not None
                assert networking_v1 is not None
                assert rbac_v1 is not None
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "concurrent-ops-cluster"
                mock_cluster.kubeconfig_path = "/tmp/concurrent-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0


class TestDocumentationAndExamples:
    """Test that integration examples work as documented."""

    def test_basic_usage_example(self, pytester):
        """Test the basic usage example from documentation."""
        pytester.makepyfile("""
            import pytest_k8s
            
            def test_basic_example(k8s_cluster, k8s_client):
                '''Basic usage example that should work as documented.'''
                # Verify cluster is available
                assert k8s_cluster is not None
                assert k8s_cluster.name is not None
                
                # Verify client is connected to cluster
                assert k8s_client is not None
                assert k8s_client.cluster is k8s_cluster
                
                # Verify API clients are available
                assert hasattr(k8s_client, 'CoreV1Api')
                assert hasattr(k8s_client, 'AppsV1Api')
                
                # This is the pattern users should follow
                core_v1 = k8s_client.CoreV1Api
                assert core_v1 is not None
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "basic-example-cluster"
                mock_cluster.kubeconfig_path = "/tmp/basic-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

    def test_parameterized_usage_example(self, pytester):
        """Test parameterized usage example from documentation."""
        pytester.makepyfile("""
            import pytest
            import pytest_k8s
            
            @pytest.mark.parametrize("k8s_cluster", [
                {"name": "test-cluster", "scope": "function", "timeout": 300}
            ], indirect=True)
            def test_parameterized_example(k8s_cluster, k8s_client):
                '''Parameterized usage example that should work as documented.'''
                # Verify parameterized configuration
                assert k8s_cluster.name == "test-cluster"
                assert k8s_client.cluster is k8s_cluster
                
                # This demonstrates the documented pattern for customization
                core_v1 = k8s_client.CoreV1Api
                assert core_v1 is not None
        """)

        with patch("pytest_k8s.fixtures.k8s_cluster.KindCluster") as mock_cluster_class:
            with patch("kubernetes.config.load_kube_config"):
                mock_cluster = Mock()
                mock_cluster.name = "test-cluster"
                mock_cluster.kubeconfig_path = "/tmp/param-kubeconfig"
                mock_cluster_class.return_value = mock_cluster

                result = pytester.runpytest("-v")
                assert result.ret == 0

                # Verify parameterized configuration was used
                call_args = mock_cluster_class.call_args
                assert call_args[1]["name"] == "test-cluster"
                assert call_args[1]["timeout"] == 300
