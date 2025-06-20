# pytest-kubernetes

A pytest plugin that provides fixtures for testing Python applications with Kubernetes dependencies. Automatically manages kind-based test clusters and provides easy-to-use fixtures for creating and managing Kubernetes resources during tests.

## Features

- 🚀 **Automatic cluster management** - Spins up and tears down kind clusters automatically
- 🧪 **pytest fixtures** - Clean, intuitive fixtures for Kubernetes resources
- 🔧 **Python Kubernetes client integration** - Works seamlessly with the official Kubernetes Python client
- 🧹 **Automatic cleanup** - Resources are automatically cleaned up after tests
- ⚙️ **Configurable cluster sharing** - Share clusters across tests, classes, or sessions
- 🛡️ **Robust error handling** - Gracefully handles cluster creation failures

## Installation

```bash
pip install pytest-kubernetes
```

### Prerequisites

- Docker (for running kind clusters)
- kubectl (for cluster interaction)
- kind (for local Kubernetes clusters)

```bash
# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/kubectl
```

## Quick Start

```python
import pytest
from kubernetes import client


def test_deployment_creation(k8s_client, k8s_namespace):
    """Test creating a simple deployment."""
    apps_v1 = client.AppsV1Api(k8s_client)
    
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="test-deployment"),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": "test"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "test"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="nginx",
                            image="nginx:latest",
                            ports=[client.V1ContainerPort(container_port=80)]
                        )
                    ]
                )
            )
        )
    )
    
    # Create the deployment
    created = apps_v1.create_namespaced_deployment(
        namespace=k8s_namespace,
        body=deployment
    )
    
    assert created.metadata.name == "test-deployment"
    assert created.spec.replicas == 1
```

## Core Fixtures

### `k8s_cluster`
Manages the lifecycle of a kind cluster for testing.

```python
def test_cluster_info(k8s_cluster):
    """Access cluster information."""
    assert k8s_cluster.name.startswith("pytest-k8s-")
    assert k8s_cluster.kubeconfig_path is not None
```

### `k8s_client`
Provides a configured Kubernetes API client.

```python
def test_with_client(k8s_client):
    """Use the Kubernetes client directly."""
    v1 = client.CoreV1Api(k8s_client)
    nodes = v1.list_node()
    assert len(nodes.items) > 0
```

### `k8s_namespace`
Creates an isolated namespace for each test.

```python
def test_namespace_isolation(k8s_client, k8s_namespace):
    """Each test gets its own namespace."""
    v1 = client.CoreV1Api(k8s_client)
    namespace = v1.read_namespace(k8s_namespace)
    assert namespace.metadata.name == k8s_namespace
```

### `k8s_resource`
Helper fixture for creating and managing arbitrary Kubernetes resources.

```python
def test_custom_resource(k8s_resource):
    """Create and manage custom resources."""
    configmap = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "test-config"},
        "data": {"key": "value"}
    }
    
    created = k8s_resource(configmap)
    assert created["metadata"]["name"] == "test-config"
```

## Usage Examples

### Testing Deployments

```python
def test_deployment_scaling(k8s_client, k8s_namespace):
    """Test deployment scaling functionality."""
    apps_v1 = client.AppsV1Api(k8s_client)
    
    # Create deployment
    deployment = create_test_deployment("scalable-app", replicas=1)
    apps_v1.create_namespaced_deployment(k8s_namespace, deployment)
    
    # Scale up
    deployment.spec.replicas = 3
    apps_v1.patch_namespaced_deployment(
        name="scalable-app",
        namespace=k8s_namespace,
        body=deployment
    )
    
    # Verify scaling
    updated = apps_v1.read_namespaced_deployment("scalable-app", k8s_namespace)
    assert updated.spec.replicas == 3
```

### Testing Services

```python
def test_service_creation(k8s_client, k8s_namespace):
    """Test service creation and configuration."""
    v1 = client.CoreV1Api(k8s_client)
    
    service = client.V1Service(
        metadata=client.V1ObjectMeta(name="test-service"),
        spec=client.V1ServiceSpec(
            selector={"app": "test"},
            ports=[client.V1ServicePort(port=80, target_port=8080)],
            type="ClusterIP"
        )
    )
    
    created = v1.create_namespaced_service(k8s_namespace, service)
    assert created.spec.type == "ClusterIP"
    assert created.spec.ports[0].port == 80
```

### Testing ConfigMaps and Secrets

```python
def test_configmap_data(k8s_client, k8s_namespace):
    """Test ConfigMap data handling."""
    v1 = client.CoreV1Api(k8s_client)
    
    configmap = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name="app-config"),
        data={
            "database_url": "postgresql://localhost:5432/testdb",
            "debug": "true"
        }
    )
    
    created = v1.create_namespaced_config_map(k8s_namespace, configmap)
    assert created.data["database_url"] == "postgresql://localhost:5432/testdb"
    assert created.data["debug"] == "true"
```

## Configuration

### Cluster Sharing

Control how clusters are shared across tests:

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
k8s_cluster_scope = "session"  # session, class, or function
```

### Error Handling

Configure how cluster creation failures are handled:

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
k8s_fail_on_cluster_error = false  # true to raise errors, false to skip tests
```

### Cluster Configuration

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
k8s_cluster_timeout = 300  # seconds to wait for cluster creation
k8s_keep_cluster = false   # true to keep cluster after tests (for debugging)
```

## Requirements

- Python >= 3.13
- Docker (running)
- kubectl
- kind
- kubernetes Python client

## Development

### Setting up for development

```bash
git clone https://github.com/yourusername/pytest-kubernetes.git
cd pytest-kubernetes
pip install -e ".[dev]"
```

### Running tests

```bash
pytest tests/
```

### Testing the plugin itself

```bash
# Run tests that verify the plugin works correctly
pytest tests/test_plugin.py -v
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Guidelines

1. Write tests for new features
2. Ensure all tests pass
3. Follow PEP 8 style guidelines
4. Add documentation for new fixtures or features

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Roadmap

- [ ] Support for multiple Kubernetes versions
- [ ] Integration with Helm charts
- [ ] Custom resource definition (CRD) testing utilities
- [ ] Performance testing helpers
- [ ] Integration with popular CI/CD platforms
- [ ] Support for remote clusters (not just kind)

## Acknowledgments

- Built on top of the excellent [kind](https://kind.sigs.k8s.io/) project
- Inspired by the pytest ecosystem and community
- Uses the official [Kubernetes Python client](https://github.com/kubernetes-client/python)
