# pytest-kubernetes

A pytest plugin that provides fixtures for testing Python applications with Kubernetes dependencies. Automatically manages kind-based test clusters and provides easy-to-use fixtures for creating and managing Kubernetes resources during tests.

## Features

- 🚀 **Automatic cluster management** - Spins up and tears down kind clusters automatically
- 🧪 **pytest fixtures** - Clean, intuitive fixtures for Kubernetes resources
- 🔧 **Python Kubernetes client integration** - Works seamlessly with the official Kubernetes Python client
- 🧹 **Robust cleanup** - Multiple cleanup mechanisms ensure clusters are always cleaned up
- ⚙️ **Configurable cluster sharing** - Share clusters across tests, classes, or sessions
- 🛡️ **Robust error handling** - Gracefully handles cluster creation failures and interrupts
- 🔒 **Signal handling** - Handles interrupts (Ctrl+C) and crashes with automatic cleanup
- 💾 **Persistent state tracking** - Recovers and cleans up orphaned clusters from previous runs

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


def test_deployment_creation(k8s_client):
    """Test creating a simple deployment."""
    # Access the Apps V1 API directly from the client
    apps_v1 = k8s_client.AppsV1Api
    
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
        namespace="default",
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
Provides a configured Kubernetes API client wrapper with direct access to all API clients.

```python
def test_with_client(k8s_client):
    """Use the Kubernetes client directly."""
    # Access API clients directly from the wrapper
    core_v1 = k8s_client.CoreV1Api
    apps_v1 = k8s_client.AppsV1Api
    networking_v1 = k8s_client.NetworkingV1Api
    rbac_v1 = k8s_client.RbacAuthorizationV1Api
    custom_objects = k8s_client.CustomObjectsApi
    
    # List nodes using the Core V1 API
    nodes = core_v1.list_node()
    assert len(nodes.items) > 0
```

The `k8s_client` fixture automatically connects to a cluster and provides convenient access to:
- `CoreV1Api` - Core Kubernetes resources (pods, services, namespaces, etc.)
- `AppsV1Api` - Application resources (deployments, daemonsets, etc.)
- `NetworkingV1Api` - Networking resources (ingresses, network policies, etc.)
- `RbacAuthorizationV1Api` - RBAC resources (roles, bindings, etc.)
- `CustomObjectsApi` - Custom resource definitions

#### Usage Patterns

```python
# Implicit cluster usage - just declare k8s_client
def test_simple(k8s_client):
    core_v1 = k8s_client.CoreV1Api
    namespaces = core_v1.list_namespace()
    assert len(namespaces.items) > 0

# Explicit cluster usage - both cluster and client
def test_explicit(k8s_cluster, k8s_client):
    assert k8s_client.cluster is k8s_cluster
    core_v1 = k8s_client.CoreV1Api
    # Use the client...

# Parameterized cluster usage
@pytest.mark.parametrize("k8s_cluster", [
    {"name": "test-cluster", "timeout": 600}
], indirect=True)
def test_parameterized(k8s_cluster, k8s_client):
    assert k8s_cluster.name == "test-cluster"
    core_v1 = k8s_client.CoreV1Api
    # Use the client...
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
def test_deployment_scaling(k8s_client):
    """Test deployment scaling functionality."""
    # Access the Apps V1 API directly
    apps_v1 = k8s_client.AppsV1Api
    
    # Create deployment
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name="scalable-app"),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": "scalable-app"}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "scalable-app"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="app",
                            image="nginx:alpine",
                            ports=[client.V1ContainerPort(container_port=80)]
                        )
                    ]
                )
            )
        )
    )
    
    # Create the deployment
    created = apps_v1.create_namespaced_deployment(
        namespace="default",
        body=deployment
    )
    assert created.spec.replicas == 1
    
    # Scale up
    deployment.spec.replicas = 3
    apps_v1.patch_namespaced_deployment(
        name="scalable-app",
        namespace="default",
        body=deployment
    )
    
    # Verify scaling
    updated = apps_v1.read_namespaced_deployment("scalable-app", "default")
    assert updated.spec.replicas == 3
    
    # Cleanup
    apps_v1.delete_namespaced_deployment(name="scalable-app", namespace="default")
```

### Testing Services

```python
def test_service_creation(k8s_client):
    """Test service creation and configuration."""
    # Access the Core V1 API directly
    core_v1 = k8s_client.CoreV1Api
    
    service = client.V1Service(
        metadata=client.V1ObjectMeta(name="test-service"),
        spec=client.V1ServiceSpec(
            selector={"app": "test"},
            ports=[client.V1ServicePort(port=80, target_port=8080)],
            type="ClusterIP"
        )
    )
    
    # Create the service
    created = core_v1.create_namespaced_service(
        namespace="default",
        body=service
    )
    assert created.spec.type == "ClusterIP"
    assert created.spec.ports[0].port == 80
    
    # Cleanup
    core_v1.delete_namespaced_service(name="test-service", namespace="default")
```

### Testing ConfigMaps and Secrets

```python
def test_configmap_data(k8s_client):
    """Test ConfigMap data handling."""
    # Access the Core V1 API directly
    core_v1 = k8s_client.CoreV1Api
    
    configmap = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name="app-config"),
        data={
            "database_url": "postgresql://localhost:5432/testdb",
            "debug": "true"
        }
    )
    
    # Create the ConfigMap
    created = core_v1.create_namespaced_config_map(
        namespace="default",
        body=configmap
    )
    assert created.data["database_url"] == "postgresql://localhost:5432/testdb"
    assert created.data["debug"] == "true"
    
    # Cleanup
    core_v1.delete_namespaced_config_map(name="app-config", namespace="default")
```

### Testing with Multiple API Clients

```python
def test_complete_application_stack(k8s_client):
    """Test deploying a complete application stack."""
    # Access multiple API clients
    core_v1 = k8s_client.CoreV1Api
    apps_v1 = k8s_client.AppsV1Api
    networking_v1 = k8s_client.NetworkingV1Api
    
    app_name = "test-app"
    namespace = "default"
    
    try:
        # 1. Create ConfigMap
        configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=f"{app_name}-config"),
            data={"app.properties": "debug=true\nport=8080"}
        )
        core_v1.create_namespaced_config_map(namespace, configmap)
        
        # 2. Create Deployment
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
                                name=app_name,
                                image="nginx:alpine",
                                ports=[client.V1ContainerPort(container_port=80)]
                            )
                        ]
                    )
                )
            )
        )
        apps_v1.create_namespaced_deployment(namespace, deployment)
        
        # 3. Create Service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=f"{app_name}-service"),
            spec=client.V1ServiceSpec(
                selector={"app": app_name},
                ports=[client.V1ServicePort(port=80, target_port=80)]
            )
        )
        core_v1.create_namespaced_service(namespace, service)
        
        # 4. Verify everything was created
        assert core_v1.read_namespaced_config_map(f"{app_name}-config", namespace)
        assert apps_v1.read_namespaced_deployment(f"{app_name}-deployment", namespace)
        assert core_v1.read_namespaced_service(f"{app_name}-service", namespace)
        
        print(f"✓ Successfully deployed {app_name} stack")
        
    finally:
        # Cleanup
        try:
            apps_v1.delete_namespaced_deployment(f"{app_name}-deployment", namespace)
            core_v1.delete_namespaced_service(f"{app_name}-service", namespace)
            core_v1.delete_namespaced_config_map(f"{app_name}-config", namespace)
        except:
            pass  # Ignore cleanup errors
```

## Configuration

### Cluster Scope Configuration

Control how clusters are shared across tests with configurable scopes:

#### Default Scope Configuration

Set the default cluster scope in your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--k8s-cluster-scope=session",  # Default cluster scope
]
```

Available scopes:
- `session` - One cluster for the entire test session (default)
- `module` - One cluster per test module
- `class` - One cluster per test class
- `function` - New cluster for each test function

#### Command Line Override

Override the default scope for a test run:

```bash
# Use function scope for all tests
pytest --k8s-cluster-scope=function

# Use module scope for better isolation
pytest --k8s-cluster-scope=module
```

#### Per-Test Scope Override with Parametrize

Override the scope for specific tests using `pytest.mark.parametrize`:

```python
import pytest

# Override scope to function for this specific test
@pytest.mark.parametrize("k8s_cluster", [
    {"name": "isolated-cluster", "scope": "function"}
], indirect=True)
def test_with_isolated_cluster(k8s_cluster):
    """This test gets its own dedicated cluster."""
    assert k8s_cluster.name == "isolated-cluster"

# Multiple configurations with different scopes
@pytest.mark.parametrize("k8s_cluster", [
    {"name": "fast-cluster", "scope": "session", "timeout": 300},
    {"name": "slow-cluster", "scope": "function", "timeout": 600},
], indirect=True)
def test_with_different_configs(k8s_cluster):
    """Test with different cluster configurations."""
    assert k8s_cluster.name in ["fast-cluster", "slow-cluster"]

# Override scope with additional configuration
@pytest.mark.parametrize("k8s_cluster", [
    {
        "name": "custom-cluster",
        "scope": "function",
        "image": "kindest/node:v1.25.0",
        "timeout": 600,
        "keep_cluster": False
    }
], indirect=True)
def test_with_custom_cluster(k8s_cluster):
    """Test with completely custom cluster configuration."""
    assert k8s_cluster.name == "custom-cluster"
```

#### Available Cluster Fixture

The `k8s_cluster` fixture provides flexible scope configuration:

```python
# Default fixture (uses configured default scope)
def test_default_scope(k8s_cluster):
    pass

# Override scope via parametrize
@pytest.mark.parametrize("k8s_cluster", [
    {"scope": "session"}
], indirect=True)
def test_session_cluster(k8s_cluster):
    pass

@pytest.mark.parametrize("k8s_cluster", [
    {"scope": "module"}
], indirect=True)
def test_module_cluster(k8s_cluster):
    pass

@pytest.mark.parametrize("k8s_cluster", [
    {"scope": "class"}
], indirect=True)
def test_class_cluster(k8s_cluster):
    pass

@pytest.mark.parametrize("k8s_cluster", [
    {"scope": "function"}
], indirect=True)
def test_function_cluster(k8s_cluster):
    pass
```

### Advanced Parametrize Examples

#### Testing Across Multiple Kubernetes Versions

```python
@pytest.mark.parametrize("k8s_cluster", [
    {"name": "k8s-1-25", "image": "kindest/node:v1.25.0", "scope": "function"},
    {"name": "k8s-1-26", "image": "kindest/node:v1.26.0", "scope": "function"},
    {"name": "k8s-1-27", "image": "kindest/node:v1.27.0", "scope": "function"},
], indirect=True)
def test_across_k8s_versions(k8s_cluster):
    """Test compatibility across different Kubernetes versions."""
    # Your test logic here
    pass
```

#### Performance Testing with Different Cluster Configurations

```python
@pytest.mark.parametrize("k8s_cluster", [
    {
        "name": "single-node",
        "scope": "function",
        "config": create_single_node_config()
    },
    {
        "name": "multi-node", 
        "scope": "function",
        "config": create_multi_node_config()
    }
], indirect=True)
def test_performance_scenarios(k8s_cluster):
    """Test performance with different cluster topologies."""
    # Performance test logic here
    pass
```

#### Conditional Scope Based on Test Marks

```python
# Fast tests use session scope for speed
@pytest.mark.fast
@pytest.mark.parametrize("k8s_cluster", [
    {"scope": "session"}
], indirect=True)
def test_fast_operation(k8s_cluster):
    pass

# Slow tests use function scope for isolation
@pytest.mark.slow
@pytest.mark.parametrize("k8s_cluster", [
    {"scope": "function"}
], indirect=True)
def test_slow_operation(k8s_cluster):
    pass
```

### Cluster Configuration Options

Configure default behavior for cluster creation:

```toml
[tool.pytest.ini_options]
addopts = [
    "--k8s-cluster-scope=session",               # Default cluster scope
    "--k8s-cluster-timeout=300",                 # Default timeout in seconds (default: 300)
    "--k8s-cluster-keep",                        # Keep clusters after tests by default
]
```

Command line options:

```bash
# Set custom timeout for cluster operations
pytest --k8s-cluster-timeout=600

# Keep clusters after tests complete (useful for debugging)
pytest --k8s-cluster-keep

# Explicitly disable keeping clusters (overrides --k8s-cluster-keep)
pytest --k8s-no-cluster-keep

# Combine multiple options
pytest --k8s-cluster-scope=function --k8s-cluster-timeout=600 --k8s-cluster-keep
```

### Kind Log Streaming

Control how kind command output is logged and streamed:

```toml
[tool.pytest.ini_options]
addopts = [
    "--k8s-kind-stream-logs",                    # Enable log streaming (default: true)
    "--k8s-kind-log-level=INFO",                 # Log level (DEBUG, INFO, WARNING, ERROR)
    "--k8s-kind-log-format=[KIND] {message}",    # Log message format
    "--k8s-kind-include-stream-info",            # Include stream info for debugging
]
```

Command line options:

```bash
# Disable log streaming
pytest --k8s-no-kind-stream-logs

# Set custom log level
pytest --k8s-kind-log-level=DEBUG

# Custom log format
pytest --k8s-kind-log-format="[CUSTOM] {message}"
```

### Robust Cleanup Mechanism

pytest-k8s includes a comprehensive cleanup system that ensures clusters are always properly cleaned up, even in error conditions:

#### Multiple Cleanup Layers

1. **Fixture Cleanup** - Standard pytest fixture cleanup
2. **Signal Handlers** - Handles interrupts (Ctrl+C, SIGTERM)
3. **Atexit Handlers** - Cleanup on normal program termination
4. **Persistent State Tracking** - Recovers orphaned clusters from crashed sessions

#### Cleanup Configuration

```toml
[tool.pytest.ini_options]
addopts = [
    "--k8s-cleanup-on-interrupt",                # Clean up on interrupt signals (default: true)
    "--k8s-cleanup-orphaned",                    # Clean up orphaned clusters (default: true)
]
```

Command line options:

```bash
# Disable cleanup on interrupt (not recommended)
pytest --k8s-no-cleanup-on-interrupt

# Disable orphaned cluster cleanup
pytest --k8s-no-cleanup-orphaned
```

#### How It Works

The cleanup system provides multiple safety nets:

- **Signal Handling**: Catches SIGINT (Ctrl+C) and SIGTERM signals to ensure cleanup happens even when tests are interrupted
- **Persistent Tracking**: Maintains a state file (`~/.pytest-k8s/active_clusters.json`) to track active clusters across sessions
- **Orphaned Cleanup**: On startup, automatically detects and cleans up clusters from previous sessions that crashed or were forcibly terminated
- **Context Managers**: Uses context managers for guaranteed cleanup even if exceptions occur
- **Multiple Finalizers**: Registers multiple cleanup mechanisms to ensure clusters are deleted

#### Emergency Cleanup

If you need to manually clean up all clusters:

```python
from pytest_k8s.cleanup import cleanup_all_clusters

# Force cleanup of all tracked clusters
cleanup_all_clusters()
```

Or use the command line:

```bash
# Clean up any orphaned clusters
python -c "from pytest_k8s.cleanup import cleanup_all_clusters; cleanup_all_clusters()"
```

### Configuration in conftest.py

Override settings programmatically in your `conftest.py`:

```python
def pytest_configure(config):
    # Use function scope in CI for better isolation
    if os.getenv("CI"):
        config.option.k8s_cluster_scope = "function"
    
    # Use session scope locally for faster development
    else:
        config.option.k8s_cluster_scope = "session"
    
    # Disable streaming in CI environments
    if os.getenv("CI"):
        config.option.k8s_kind_stream_logs = False
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
5. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages

### Commit Message Format

This project uses Conventional Commits for automated versioning and changelog generation. Please format your commit messages as follows:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types

- `feat`: A new feature (triggers minor version bump)
- `fix`: A bug fix (triggers patch version bump)
- `perf`: Performance improvements (triggers patch version bump)
- `docs`: Documentation only changes
- `style`: Changes that don't affect code meaning (white-space, formatting, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `test`: Adding or updating tests
- `chore`: Changes to build process or auxiliary tools
- `ci`: Changes to CI configuration files and scripts

#### Examples

```bash
# Feature
feat: add support for custom cluster configurations

# Bug fix
fix: handle cluster cleanup on interrupt signals

# Breaking change (triggers major version bump)
feat!: change k8s_client fixture API

BREAKING CHANGE: k8s_client now returns a wrapper object instead of raw client

# Documentation
docs: update installation instructions for macOS

# With scope
feat(fixtures): add new k8s_namespace fixture for isolated testing
```

### Release Process

Releases are automated using GitHub Actions and semantic-release. When commits are pushed to the `main` branch:

1. Tests are run to ensure code quality
2. The workflow analyzes commit messages to determine if a release is needed
3. If a release is needed, it automatically:
   - Bumps the version in `pyproject.toml`
   - Updates the `CHANGELOG.md`
   - Creates a git tag
   - Creates a GitHub release with release notes
4. When a release is published, a separate workflow automatically:
   - Builds the Python package
   - Publishes to PyPI

No manual version management is required - just use conventional commits and the automation handles the rest.

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
