# pytest k8s

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

## Table of Contents

- [Installation](#installation)
  - [Install the Plugin](#install-the-plugin)
  - [Using the Plugin](#using-the-plugin)
  - [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Core Fixtures](#core-fixtures)
  - [`k8s_cluster`](#k8s_cluster)
  - [`k8s_client`](#k8s_client)
- [Configuration](#configuration)
  - [Command Line Parameters](#command-line-parameters)
  - [Fixture Parameters](#fixture-parameters)
  - [Cluster Scopes](#cluster-scopes)
  - [Advanced Parametrize Examples](#advanced-parametrize-examples)
  - [Cleanup Mechanism](#cleanup-mechanism)
  - [Configuration in conftest.py](#configuration-in-conftestpy)
- [Usage Examples](#usage-examples)
  - [Testing Deployments](#testing-deployments)
  - [Testing Services](#testing-services)
  - [Testing ConfigMaps and Secrets](#testing-configmaps-and-secrets)
  - [Testing with Multiple API Clients](#testing-with-multiple-api-clients)
- [Requirements](#requirements)
- [Development](#development)
  - [Setting up for development](#setting-up-for-development)
  - [Running tests](#running-tests)
  - [Commit Standards with Commitizen](#commit-standards-with-commitizen)
- [Contributing](#contributing)
  - [Development Guidelines](#development-guidelines)
  - [Commit Message Format](#commit-message-format)
  - [Release Process](#release-process)
- [License](#license)
- [Roadmap](#roadmap)
- [Acknowledgments](#acknowledgments)

## Installation

### Install the Plugin

Using pip:
```bash
pip install pytest-k8s
```

Using uv:
```bash
uv add pytest-k8s
```

### Using the Plugin

The plugin automatically registers itself when installed. No additional configuration is needed - just start using the fixtures in your tests.

For explicit control, you can:
- Load via `pytest_plugins = ["pytest_k8s"]` in your test file or root `conftest.py`
- Use command line: `pytest -p pytest_k8s` or disable with `pytest -p no:pytest_k8s`

### Prerequisites

- Docker (for running kind clusters)
- kubectl (for cluster interaction)
- kind (for local Kubernetes clusters)

```bash
# Install Docker (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
# Add your user to the docker group
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect

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
Provides a configured Kubernetes API client wrapper with direct access to all API clients:
- `CoreV1Api` - Core resources (pods, services, namespaces)
- `AppsV1Api` - Application resources (deployments, daemonsets)
- `NetworkingV1Api` - Networking resources (ingresses, network policies)
- `RbacAuthorizationV1Api` - RBAC resources (roles, bindings)
- `CustomObjectsApi` - Custom resource definitions

```python
def test_with_client(k8s_client):
    """Use the Kubernetes client directly."""
    core_v1 = k8s_client.CoreV1Api
    nodes = core_v1.list_node()
    assert len(nodes.items) > 0
```

## Configuration

### Command Line Parameters

The following table lists all available command line parameters for pytest-k8s:

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `--k8s-cluster-scope` | Scope for cluster sharing | `session` | `--k8s-cluster-scope=function` |
| `--k8s-cluster-timeout` | Timeout for cluster operations (seconds) | `300` | `--k8s-cluster-timeout=600` |
| `--k8s-cluster-keep` | Keep clusters after tests complete | `False` | `--k8s-cluster-keep` |
| `--k8s-no-cluster-keep` | Explicitly disable keeping clusters | - | `--k8s-no-cluster-keep` |
| `--k8s-kind-stream-logs` | Enable kind log streaming | `True` | `--k8s-kind-stream-logs` |
| `--k8s-no-kind-stream-logs` | Disable kind log streaming | - | `--k8s-no-kind-stream-logs` |
| `--k8s-kind-log-level` | Log level for kind output | `INFO` | `--k8s-kind-log-level=DEBUG` |
| `--k8s-kind-log-format` | Format for kind log messages | `[KIND] {message}` | `--k8s-kind-log-format="[CUSTOM] {message}"` |
| `--k8s-kind-include-stream-info` | Include stream info in logs | `False` | `--k8s-kind-include-stream-info` |
| `--k8s-cleanup-on-interrupt` | Clean up on interrupt signals | `True` | `--k8s-cleanup-on-interrupt` |
| `--k8s-no-cleanup-on-interrupt` | Disable cleanup on interrupt | - | `--k8s-no-cleanup-on-interrupt` |
| `--k8s-cleanup-orphaned` | Clean up orphaned clusters | `True` | `--k8s-cleanup-orphaned` |
| `--k8s-no-cleanup-orphaned` | Disable orphaned cluster cleanup | - | `--k8s-no-cleanup-orphaned` |

These can either be set ephemerally at runtime, or persisted by setting in your `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--k8s-cluster-scope=session",  # Default cluster scope
]
```

### Fixture Parameters

When using `pytest.mark.parametrize` with the `k8s_cluster` fixture, the following parameters are available:

| Parameter | Description | Type | Example |
|-----------|-------------|------|---------|
| `name` | Custom cluster name | `str` | `"test-cluster"` |
| `scope` | Override cluster scope | `str` | `"function"` |
| `image` | Kind node image | `str` | `"kindest/node:v1.25.0"` |
| `timeout` | Cluster creation timeout | `int` | `600` |
| `keep_cluster` | Keep cluster after test | `bool` | `False` |
| `config` | Custom kind configuration | `dict` | `{"apiVersion": "kind.x-k8s.io/v1alpha4", ...}` |

Example usage:
```python
@pytest.mark.parametrize("k8s_cluster", [
    {
        "name": "custom-cluster",
        "scope": "function",
        "image": "kindest/node:v1.25.0",
        "timeout": 600,
        "keep_cluster": False,
        "config": {
            "apiVersion": "kind.x-k8s.io/v1alpha4",
            "kind": "Cluster",
            "nodes": [{"role": "control-plane"}]
        }
    }
], indirect=True)
def test_with_custom_cluster(k8s_cluster):
    assert k8s_cluster.name == "custom-cluster"
```

### Cluster Scopes

Available scopes:
- `session` - One cluster for the entire test session (default)
- `module` - One cluster per test module
- `class` - One cluster per test class
- `function` - New cluster for each test function

Set default scope in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
addopts = ["--k8s-cluster-scope=session"]
```

Override via command line: `pytest --k8s-cluster-scope=function`

Override per test with parametrize:
```python
@pytest.mark.parametrize("k8s_cluster", [
    {"name": "isolated-cluster", "scope": "function"}
], indirect=True)
def test_with_isolated_cluster(k8s_cluster):
    assert k8s_cluster.name == "isolated-cluster"
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


### Cleanup Mechanism

pytest-k8s ensures clusters are always cleaned up through multiple layers:
1. Standard pytest fixture cleanup
2. Signal handlers for interrupts (Ctrl+C, SIGTERM)
3. Atexit handlers for normal termination
4. Persistent state tracking to recover orphaned clusters

The cleanup system maintains a state file (`~/.pytest-k8s/active_clusters.json`) to track active clusters across sessions.

For emergency cleanup:
```bash
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

## Requirements

- Python >= 3.13
- Docker (running)
- kubectl
- kind
- kubernetes Python client

## Development

### Setting up for development

First, install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone and set up the development environment:
```bash
git clone https://github.com/yourusername/pytest-kubernetes.git
cd pytest-kubernetes
uv sync --frozen
```

### Running tests

```bash
uv run pytest tests/
```

### Commit Standards with Commitizen

This project uses [commitizen](https://commitizen-tools.github.io/commitizen/) to enforce conventional commit standards. Pre-commit hooks are configured to validate commit messages before they are accepted.

#### Pre-commit Setup

The project includes pre-commit hooks configured in `.pre-commit-config.yaml` that will:
- Validate commit message format using commitizen
- Check branch names on push

To set up pre-commit hooks:
```bash
# Install pre-commit hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

#### Making Commits with Commitizen

You can use commitizen to help create properly formatted commits:
```bash
# Interactive commit creation
uv run cz commit

# Or use git commit with conventional format
git commit -m "feat: add new k8s fixture" -s
```

Commitizen will guide you through creating a properly formatted commit message that follows the Conventional Commits specification.

#### Commit Message Validation

All commits must follow the Conventional Commits format. The pre-commit hook will automatically validate your commit messages and reject any that don't conform to the standard. If a commit is rejected, you'll see an error message explaining the required format.


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

Releases are automated using GitHub Actions and commitizen. When commits are pushed to the `main` branch:

1. Tests are run to ensure code quality
2. The workflow analyzes commit messages to determine if a release is needed
3. If a release is needed, it automatically:
   - Bumps the version in `pyproject.toml`
   - Updates the `CHANGELOG.md`
   - Creates a git tag
   - Creates a GitHub release with release notes
   - Builds the Python package
   - Publishes to PyPI

No manual version management is required - just use conventional commits and the automation handles the rest.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Roadmap

- [X] Support for multiple Kubernetes versions
- [ ] Kubernetes isolated namespace fixture
- [ ] Integration with Helm charts
- [ ] Deep mocking fixtures for lightweight tests
- [ ] Custom resource definition (CRD) testing utilities
- [ ] Performance testing helpers
- [ ] Integration with popular CI/CD platforms
- [ ] Support for remote clusters (not just kind)

## Acknowledgments

- Built on top of the excellent [kind](https://kind.sigs.k8s.io/) project
- Inspired by the pytest ecosystem and community
- Uses the official [Kubernetes Python client](https://github.com/kubernetes-client/python)
- Commit standards enforced by [commitizen](https://commitizen-tools.github.io/commitizen/)
