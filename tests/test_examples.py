"""
Example fixture usage for pytest-k8s.

This module demonstrates various ways to use the pytest-k8s fixtures,
including different scope configurations, parameterization, and common
testing patterns with Kubernetes resources.
"""

import pytest
from kubernetes import client
from pathlib import Path


# =============================================================================
# Basic Fixture Usage Examples
# =============================================================================


@pytest.mark.integration
def test_basic_cluster_usage(k8s_cluster):
    """
    Basic cluster fixture usage with default configuration.

    The k8s_cluster fixture provides a KindCluster instance that can be used
    to access cluster information and perform cluster-level operations.
    """
    # Verify cluster is created and ready
    assert k8s_cluster.name.startswith("pytest-k8s-")
    assert k8s_cluster.kubeconfig_path is not None
    assert Path(k8s_cluster.kubeconfig_path).exists()

    # Check cluster status
    assert k8s_cluster.is_ready()

    print(f"✓ Cluster '{k8s_cluster.name}' is ready")


@pytest.mark.integration
def test_basic_client_usage(k8s_client):
    """
    Basic client fixture usage with automatic cluster connection.

    The k8s_client fixture automatically connects to a cluster and provides
    convenient access to all Kubernetes API clients.
    """
    # Access the Core V1 API for basic operations
    core_v1 = k8s_client.CoreV1Api

    # List nodes to verify cluster connectivity
    nodes = core_v1.list_node()
    assert len(nodes.items) > 0

    # Verify we have at least one control-plane node
    control_plane_nodes = [
        node
        for node in nodes.items
        if "node-role.kubernetes.io/control-plane" in node.metadata.labels
    ]
    assert len(control_plane_nodes) > 0

    print(f"✓ Connected to cluster with {len(nodes.items)} nodes")


@pytest.mark.integration
def test_cluster_and_client_together(k8s_cluster, k8s_client):
    """
    Using both cluster and client fixtures together.

    When both fixtures are used, the client automatically connects to the
    same cluster instance provided by the cluster fixture.
    """
    # Verify the client is connected to the same cluster
    assert k8s_client.cluster is k8s_cluster
    assert k8s_client.cluster.name == k8s_cluster.name

    # Use both cluster and client information
    print(f"✓ Cluster: {k8s_cluster.name}")
    print(f"✓ Kubeconfig: {k8s_cluster.kubeconfig_path}")
    print(f"✓ Client connected to: {k8s_client.cluster.name}")


# =============================================================================
# Scope Parameter Examples
# =============================================================================


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster",
    [{"name": "session-scoped-cluster", "scope": "session"}],
    indirect=True,
)
def test_session_scoped_cluster(k8s_cluster):
    """
    Example of using session-scoped cluster.

    Session-scoped clusters are shared across all tests in the test session,
    providing the fastest test execution but less isolation between tests.
    """
    assert k8s_cluster.name == "session-scoped-cluster"

    # Session-scoped clusters are ideal for:
    # - Fast test execution
    # - Tests that don't modify cluster state
    # - Integration tests that can share resources

    print(f"✓ Using session-scoped cluster: {k8s_cluster.name}")


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster",
    [{"name": "function-scoped-cluster", "scope": "function"}],
    indirect=True,
)
def test_function_scoped_cluster(k8s_cluster):
    """
    Example of using function-scoped cluster.

    Function-scoped clusters create a new cluster for each test function,
    providing maximum isolation but slower test execution.
    """
    assert k8s_cluster.name == "function-scoped-cluster"

    # Function-scoped clusters are ideal for:
    # - Tests that modify cluster configuration
    # - Tests that need complete isolation
    # - Tests that might leave cluster in inconsistent state

    print(f"✓ Using function-scoped cluster: {k8s_cluster.name}")


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster", [{"name": "module-scoped-cluster", "scope": "module"}], indirect=True
)
def test_module_scoped_cluster(k8s_cluster):
    """
    Example of using module-scoped cluster.

    Module-scoped clusters are shared across all tests in the same module,
    providing a balance between performance and isolation.
    """
    assert k8s_cluster.name == "module-scoped-cluster"

    # Module-scoped clusters are ideal for:
    # - Related tests that can share cluster state
    # - Moderate isolation requirements
    # - Balance between speed and isolation

    print(f"✓ Using module-scoped cluster: {k8s_cluster.name}")


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster", [{"name": "class-scoped-cluster", "scope": "class"}], indirect=True
)
def test_class_scoped_cluster(k8s_cluster):
    """
    Example of using class-scoped cluster.

    Class-scoped clusters are shared across all test methods in the same class,
    useful for organizing related tests that can share cluster resources.
    """
    assert k8s_cluster.name == "class-scoped-cluster"

    # Class-scoped clusters are ideal for:
    # - Test classes with related test methods
    # - Shared setup/teardown within a test class
    # - Moderate isolation with good performance

    print(f"✓ Using class-scoped cluster: {k8s_cluster.name}")


# =============================================================================
# Client Fixture with Scope Examples
# =============================================================================


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster",
    [{"name": "client-session-cluster", "scope": "session"}],
    indirect=True,
)
def test_client_with_session_scope(k8s_cluster, k8s_client):
    """
    Example of using client with session-scoped cluster.

    The client automatically connects to the session-scoped cluster,
    allowing efficient resource sharing across tests.
    """
    # Verify client is connected to session-scoped cluster
    assert k8s_client.cluster.name == "client-session-cluster"

    # Use client for operations that don't modify cluster state
    core_v1 = k8s_client.CoreV1Api
    namespaces = core_v1.list_namespace()

    # Session scope is great for read-only operations
    default_ns = next(
        (ns for ns in namespaces.items if ns.metadata.name == "default"), None
    )
    assert default_ns is not None

    print(f"✓ Client connected to session cluster: {k8s_client.cluster.name}")


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster",
    [{"name": "client-function-cluster", "scope": "function"}],
    indirect=True,
)
def test_client_with_function_scope(k8s_cluster, k8s_client):
    """
    Example of using client with function-scoped cluster.

    The client connects to a dedicated cluster for this test,
    providing complete isolation for operations that modify cluster state.
    """
    # Verify client is connected to function-scoped cluster
    assert k8s_client.cluster.name == "client-function-cluster"

    # Use client for operations that modify cluster state
    core_v1 = k8s_client.CoreV1Api

    # Create a test namespace (safe with function scope)
    test_namespace = client.V1Namespace(
        metadata=client.V1ObjectMeta(name="test-isolation")
    )

    created_ns = core_v1.create_namespace(body=test_namespace)
    assert created_ns.metadata.name == "test-isolation"

    # Function scope ensures this doesn't affect other tests
    print(f"✓ Created namespace in function cluster: {k8s_client.cluster.name}")

    # Cleanup (optional with function scope, but good practice)
    core_v1.delete_namespace(name="test-isolation")


# =============================================================================
# Advanced Configuration Examples
# =============================================================================


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster",
    [
        {
            "name": "custom-timeout-cluster",
            "scope": "function",
            "timeout": 600,  # 10 minutes timeout
            "keep_cluster": False,  # Don't keep after test
        }
    ],
    indirect=True,
)
def test_cluster_with_custom_timeout(k8s_cluster):
    """
    Example of cluster with custom timeout configuration.

    Demonstrates how to configure cluster creation timeout and
    cleanup behavior for specific test requirements.
    """
    assert k8s_cluster.name == "custom-timeout-cluster"

    # This cluster was created with a 10-minute timeout
    # and will be automatically cleaned up after the test

    print(f"✓ Custom timeout cluster ready: {k8s_cluster.name}")


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster",
    [
        {
            "name": "custom-image-cluster",
            "scope": "function",
            "image": "kindest/node:v1.27.0",  # Specific Kubernetes version
        }
    ],
    indirect=True,
)
def test_cluster_with_custom_image(k8s_cluster, k8s_client):
    """
    Example of cluster with custom Kubernetes version.

    Demonstrates how to test against specific Kubernetes versions
    by specifying the node image.
    """
    assert k8s_cluster.name == "custom-image-cluster"

    # Verify we're running the expected Kubernetes version
    core_v1 = k8s_client.CoreV1Api
    nodes = core_v1.list_node()

    # Check node version information
    for node in nodes.items:
        kubelet_version = node.status.node_info.kubelet_version
        print(f"✓ Node {node.metadata.name} running kubelet {kubelet_version}")
        # Should be v1.27.x
        assert kubelet_version.startswith("v1.27")


# =============================================================================
# Multiple API Client Examples
# =============================================================================


@pytest.mark.integration
def test_multiple_api_clients(k8s_client):
    """
    Example of using multiple Kubernetes API clients.

    Demonstrates accessing different API groups through the client wrapper
    for comprehensive Kubernetes resource management.
    """
    # Access different API clients
    core_v1 = k8s_client.CoreV1Api
    apps_v1 = k8s_client.AppsV1Api
    networking_v1 = k8s_client.NetworkingV1Api
    rbac_v1 = k8s_client.RbacAuthorizationV1Api
    custom_objects = k8s_client.CustomObjectsApi  # noqa: F841

    # Test Core V1 API (pods, services, namespaces, etc.)
    namespaces = core_v1.list_namespace()
    assert (
        len(namespaces.items) >= 4
    )  # default, kube-system, kube-public, kube-node-lease

    # Test Apps V1 API (deployments, daemonsets, etc.)
    deployments = apps_v1.list_deployment_for_all_namespaces()  # noqa: F841
    # Should have system deployments

    # Test Networking V1 API (network policies, ingresses, etc.)
    network_policies = networking_v1.list_network_policy_for_all_namespaces()  # noqa: F841
    # May be empty in basic cluster

    # Test RBAC V1 API (roles, bindings, etc.)
    cluster_roles = rbac_v1.list_cluster_role()
    assert len(cluster_roles.items) > 0  # Should have system cluster roles

    print("✓ Successfully accessed all API client types")


@pytest.mark.integration
def test_deployment_lifecycle(k8s_client):
    """
    Example of complete deployment lifecycle testing.

    Demonstrates creating, scaling, and managing deployments using
    the Apps V1 API client with function-scoped isolation.
    """
    apps_v1 = k8s_client.AppsV1Api
    core_v1 = k8s_client.CoreV1Api

    deployment_name = "test-nginx-deployment"
    namespace = "default"

    try:
        # 1. Create deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1DeploymentSpec(
                replicas=2,
                selector=client.V1LabelSelector(match_labels={"app": "test-nginx"}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": "test-nginx"}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="nginx",
                                image="nginx:alpine",
                                ports=[client.V1ContainerPort(container_port=80)],
                            )
                        ]
                    ),
                ),
            ),
        )

        created_deployment = apps_v1.create_namespaced_deployment(
            namespace=namespace, body=deployment
        )
        assert created_deployment.metadata.name == deployment_name
        assert created_deployment.spec.replicas == 2

        print(f"✓ Created deployment: {deployment_name}")

        # 2. Scale deployment
        deployment.spec.replicas = 3
        scaled_deployment = apps_v1.patch_namespaced_deployment(
            name=deployment_name, namespace=namespace, body=deployment
        )
        assert scaled_deployment.spec.replicas == 3

        print(f"✓ Scaled deployment to {scaled_deployment.spec.replicas} replicas")

        # 3. Verify pods are created
        import time

        time.sleep(2)  # Give pods time to be scheduled

        pods = core_v1.list_namespaced_pod(
            namespace=namespace, label_selector="app=test-nginx"
        )
        print(f"✓ Found {len(pods.items)} pods for deployment")

    finally:
        # Cleanup
        try:
            apps_v1.delete_namespaced_deployment(
                name=deployment_name, namespace=namespace
            )
            print(f"✓ Cleaned up deployment: {deployment_name}")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")


# =============================================================================
# Resource Management Examples
# =============================================================================


@pytest.mark.integration
def test_configmap_and_secret_management(k8s_client):
    """
    Example of ConfigMap and Secret management.

    Demonstrates creating and managing configuration resources
    using the Core V1 API client.
    """
    core_v1 = k8s_client.CoreV1Api
    namespace = "default"

    try:
        # 1. Create ConfigMap
        configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name="app-config"),
            data={
                "database_url": "postgresql://localhost:5432/testdb",
                "debug": "true",
                "app.properties": "key1=value1\nkey2=value2",
            },
        )

        created_cm = core_v1.create_namespaced_config_map(
            namespace=namespace, body=configmap
        )
        assert created_cm.data["database_url"] == "postgresql://localhost:5432/testdb"
        assert created_cm.data["debug"] == "true"

        print("✓ Created ConfigMap with application configuration")

        # 2. Create Secret
        import base64

        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name="app-secrets"),
            type="Opaque",
            data={
                "username": base64.b64encode(b"admin").decode("utf-8"),
                "password": base64.b64encode(b"secret123").decode("utf-8"),
            },
        )

        created_secret = core_v1.create_namespaced_secret(
            namespace=namespace, body=secret
        )
        assert "username" in created_secret.data
        assert "password" in created_secret.data

        print("✓ Created Secret with credentials")

        # 3. Verify resources exist
        cm_list = core_v1.list_namespaced_config_map(namespace=namespace)
        cm_names = [cm.metadata.name for cm in cm_list.items]
        assert "app-config" in cm_names

        secret_list = core_v1.list_namespaced_secret(namespace=namespace)
        secret_names = [s.metadata.name for s in secret_list.items]
        assert "app-secrets" in secret_names

        print("✓ Verified ConfigMap and Secret exist in cluster")

    finally:
        # Cleanup
        try:
            core_v1.delete_namespaced_config_map(name="app-config", namespace=namespace)
            core_v1.delete_namespaced_secret(name="app-secrets", namespace=namespace)
            print("✓ Cleaned up ConfigMap and Secret")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")


# =============================================================================
# Service and Networking Examples
# =============================================================================


@pytest.mark.integration
def test_service_creation_and_discovery(k8s_client):
    """
    Example of Service creation and service discovery.

    Demonstrates creating services and testing Kubernetes networking
    using Core V1 and Apps V1 API clients.
    """
    core_v1 = k8s_client.CoreV1Api
    apps_v1 = k8s_client.AppsV1Api
    namespace = "default"

    app_name = "web-service-test"

    try:
        # 1. Create a deployment to back the service
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=f"{app_name}-deployment"),
            spec=client.V1DeploymentSpec(
                replicas=2,
                selector=client.V1LabelSelector(match_labels={"app": app_name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": app_name}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="web",
                                image="nginx:alpine",
                                ports=[client.V1ContainerPort(container_port=80)],
                            )
                        ]
                    ),
                ),
            ),
        )

        apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        print(f"✓ Created backing deployment: {app_name}-deployment")

        # 2. Create ClusterIP service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=f"{app_name}-service"),
            spec=client.V1ServiceSpec(
                selector={"app": app_name},
                ports=[client.V1ServicePort(port=80, target_port=80)],
                type="ClusterIP",
            ),
        )

        created_service = core_v1.create_namespaced_service(
            namespace=namespace, body=service
        )
        assert created_service.spec.type == "ClusterIP"
        assert created_service.spec.ports[0].port == 80

        print(f"✓ Created ClusterIP service: {app_name}-service")

        # 3. Create NodePort service for external access
        nodeport_service = client.V1Service(
            metadata=client.V1ObjectMeta(name=f"{app_name}-nodeport"),
            spec=client.V1ServiceSpec(
                selector={"app": app_name},
                ports=[client.V1ServicePort(port=80, target_port=80, node_port=30080)],
                type="NodePort",
            ),
        )

        created_nodeport = core_v1.create_namespaced_service(
            namespace=namespace, body=nodeport_service
        )
        assert created_nodeport.spec.type == "NodePort"
        assert created_nodeport.spec.ports[0].node_port == 30080

        print(f"✓ Created NodePort service: {app_name}-nodeport")

        # 4. Verify service discovery
        services = core_v1.list_namespaced_service(namespace=namespace)
        service_names = [svc.metadata.name for svc in services.items]
        assert f"{app_name}-service" in service_names
        assert f"{app_name}-nodeport" in service_names

        print("✓ Verified service discovery works")

    finally:
        # Cleanup
        try:
            apps_v1.delete_namespaced_deployment(f"{app_name}-deployment", namespace)
            core_v1.delete_namespaced_service(f"{app_name}-service", namespace)
            core_v1.delete_namespaced_service(f"{app_name}-nodeport", namespace)
            print("✓ Cleaned up deployment and services")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")


# =============================================================================
# Error Handling and Edge Cases
# =============================================================================


@pytest.mark.integration
def test_cluster_error_handling(k8s_client):
    """
    Example of error handling with cluster and client fixtures.

    Demonstrates proper error handling when working with Kubernetes
    resources and API operations.
    """
    core_v1 = k8s_client.CoreV1Api

    # Test handling of non-existent resources
    with pytest.raises(client.exceptions.ApiException) as exc_info:
        core_v1.read_namespaced_pod(name="non-existent-pod", namespace="default")

    assert exc_info.value.status == 404
    print("✓ Properly handled 404 error for non-existent resource")

    # Test handling of invalid operations
    with pytest.raises(client.exceptions.ApiException) as exc_info:
        invalid_pod = client.V1Pod(
            metadata=client.V1ObjectMeta(name="invalid-pod"),
            # Missing required spec field
        )
        core_v1.create_namespaced_pod(namespace="default", body=invalid_pod)

    assert exc_info.value.status == 422  # Unprocessable Entity
    print("✓ Properly handled validation error for invalid resource")


# =============================================================================
# Performance and Load Testing Examples
# =============================================================================


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster",
    [{"name": "performance-test-cluster", "scope": "function", "timeout": 900}],
    indirect=True,
)
def test_bulk_resource_operations(k8s_cluster, k8s_client):
    """
    Example of bulk resource operations for performance testing.

    Demonstrates creating and managing multiple resources efficiently
    using batch operations where possible.
    """
    core_v1 = k8s_client.CoreV1Api
    namespace = "default"

    # Create multiple ConfigMaps efficiently
    configmaps_created = []

    try:
        for i in range(10):
            configmap = client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=f"bulk-config-{i}"),
                data={"index": str(i), "data": f"bulk-data-{i}"},
            )

            created = core_v1.create_namespaced_config_map(
                namespace=namespace, body=configmap
            )
            configmaps_created.append(created.metadata.name)

        print(f"✓ Created {len(configmaps_created)} ConfigMaps efficiently")

        # Verify all were created
        cm_list = core_v1.list_namespaced_config_map(namespace=namespace)
        bulk_cms = [
            cm for cm in cm_list.items if cm.metadata.name.startswith("bulk-config-")
        ]
        assert len(bulk_cms) == 10

        print("✓ Verified all bulk ConfigMaps exist")

    finally:
        # Bulk cleanup
        for cm_name in configmaps_created:
            try:
                core_v1.delete_namespaced_config_map(name=cm_name, namespace=namespace)
            except Exception as e:
                print(f"⚠ Cleanup warning for {cm_name}: {e}")

        print(f"✓ Cleaned up {len(configmaps_created)} ConfigMaps")


# =============================================================================
# Integration Testing Examples
# =============================================================================


@pytest.mark.integration
@pytest.mark.parametrize(
    "k8s_cluster",
    [{"name": "integration-test-cluster", "scope": "function"}],
    indirect=True,
)
def test_complete_application_stack(k8s_cluster, k8s_client):
    """
    Example of complete application stack integration testing.

    Demonstrates deploying and testing a complete application stack
    with multiple interconnected components.
    """
    core_v1 = k8s_client.CoreV1Api
    apps_v1 = k8s_client.AppsV1Api
    namespace = "default"

    app_name = "integration-app"

    try:
        # 1. Create application configuration
        configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=f"{app_name}-config"),
            data={
                "database_host": "db-service",
                "database_port": "5432",
                "app_port": "8080",
            },
        )
        core_v1.create_namespaced_config_map(namespace, configmap)

        # 2. Create application secrets
        import base64

        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=f"{app_name}-secrets"),
            data={"db_password": base64.b64encode(b"secretpass").decode("utf-8")},
        )
        core_v1.create_namespaced_secret(namespace, secret)

        # 3. Create database deployment
        db_deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=f"{app_name}-db"),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": f"{app_name}-db"}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": f"{app_name}-db"}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="postgres",
                                image="postgres:13-alpine",
                                env=[
                                    client.V1EnvVar(
                                        name="POSTGRES_PASSWORD", value="secretpass"
                                    ),
                                    client.V1EnvVar(name="POSTGRES_DB", value="appdb"),
                                ],
                                ports=[client.V1ContainerPort(container_port=5432)],
                            )
                        ]
                    ),
                ),
            ),
        )
        apps_v1.create_namespaced_deployment(namespace, db_deployment)

        # 4. Create database service
        db_service = client.V1Service(
            metadata=client.V1ObjectMeta(name="db-service"),
            spec=client.V1ServiceSpec(
                selector={"app": f"{app_name}-db"},
                ports=[client.V1ServicePort(port=5432, target_port=5432)],
            ),
        )
        core_v1.create_namespaced_service(namespace, db_service)

        # 5. Create application deployment
        app_deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=f"{app_name}-app"),
            spec=client.V1DeploymentSpec(
                replicas=2,
                selector=client.V1LabelSelector(
                    match_labels={"app": f"{app_name}-app"}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": f"{app_name}-app"}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="app",
                                image="nginx:alpine",  # Placeholder for actual app
                                env_from=[
                                    client.V1EnvFromSource(
                                        config_map_ref=client.V1ConfigMapEnvSource(
                                            name=f"{app_name}-config"
                                        )
                                    )
                                ],
                                ports=[client.V1ContainerPort(container_port=8080)],
                            )
                        ]
                    ),
                ),
            ),
        )
        apps_v1.create_namespaced_deployment(namespace, app_deployment)

        # 6. Create application service
        app_service = client.V1Service(
            metadata=client.V1ObjectMeta(name=f"{app_name}-service"),
            spec=client.V1ServiceSpec(
                selector={"app": f"{app_name}-app"},
                ports=[client.V1ServicePort(port=80, target_port=8080)],
                type="ClusterIP",
            ),
        )
        core_v1.create_namespaced_service(namespace, app_service)

        print("✓ Deployed complete application stack")

        # 7. Verify all components are created
        deployments = apps_v1.list_namespaced_deployment(namespace)
        deployment_names = [d.metadata.name for d in deployments.items]
        assert f"{app_name}-db" in deployment_names
        assert f"{app_name}-app" in deployment_names

        services = core_v1.list_namespaced_service(namespace)
        service_names = [s.metadata.name for s in services.items]
        assert "db-service" in service_names
        assert f"{app_name}-service" in service_names

        print("✓ Verified all stack components exist")

        # 8. Test inter-service connectivity (basic check)
        import time

        time.sleep(5)  # Allow services to stabilize

        # Check that services have endpoints
        db_endpoints = core_v1.read_namespaced_endpoints("db-service", namespace)
        app_endpoints = core_v1.read_namespaced_endpoints(
            f"{app_name}-service", namespace
        )

        print(
            f"✓ Database service has {len(db_endpoints.subsets or [])} endpoint subsets"
        )
        print(
            f"✓ Application service has {len(app_endpoints.subsets or [])} endpoint subsets"
        )

    finally:
        # Cleanup all stack components
        try:
            # Delete deployments
            apps_v1.delete_namespaced_deployment(f"{app_name}-db", namespace)
            apps_v1.delete_namespaced_deployment(f"{app_name}-app", namespace)

            # Delete services
            core_v1.delete_namespaced_service("db-service", namespace)
            core_v1.delete_namespaced_service(f"{app_name}-service", namespace)

            # Delete config and secrets
            core_v1.delete_namespaced_config_map(f"{app_name}-config", namespace)
            core_v1.delete_namespaced_secret(f"{app_name}-secrets", namespace)

            print("✓ Cleaned up complete application stack")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")
