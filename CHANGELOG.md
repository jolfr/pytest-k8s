# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Robust cleanup mechanism**: Comprehensive cleanup system that ensures clusters are always properly cleaned up
  - **Signal handlers**: Catches SIGINT (Ctrl+C) and SIGTERM signals for graceful cleanup during interrupts
  - **Persistent state tracking**: Maintains state file (`~/.pytest-k8s/active_clusters.json`) to track active clusters
  - **Orphaned cluster recovery**: Automatically detects and cleans up clusters from previous crashed sessions
  - **Multiple cleanup layers**: Fixture cleanup, signal handlers, atexit handlers, and context managers
  - **Emergency cleanup function**: `cleanup_all_clusters()` for manual cleanup when needed
  - **New command line options**:
    - `--k8s-cleanup-on-interrupt` to enable cleanup on interrupt signals (default: true)
    - `--k8s-no-cleanup-on-interrupt` to disable cleanup on interrupt signals
    - `--k8s-cleanup-orphaned` to enable orphaned cluster cleanup (default: true)
    - `--k8s-no-cleanup-orphaned` to disable orphaned cluster cleanup
- **k8s_client fixture**: New comprehensive Kubernetes API client fixture with direct access to all API clients
  - `CoreV1Api` - Core Kubernetes resources (pods, services, namespaces, etc.)
  - `AppsV1Api` - Application resources (deployments, daemonsets, etc.)
  - `NetworkingV1Api` - Networking resources (ingresses, network policies, etc.)
  - `RbacAuthorizationV1Api` - RBAC resources (roles, bindings, etc.)
  - `CustomObjectsApi` - Custom resource definitions
- **KubernetesClient wrapper class**: Provides convenient access to Kubernetes API clients with automatic cluster integration
- **Automatic cluster detection**: k8s_client fixture automatically detects and uses existing cluster fixtures
- **Multiple usage patterns**: Supports implicit cluster usage, explicit cluster usage, and parameterized cluster usage
- **Comprehensive test examples**: Added `tests/test_examples.py` with real-world usage examples
- **Configurable cluster scope**: Added support for configuring default cluster scope via command line and configuration files
- **Scope override via parametrize**: Added ability to override cluster scope per test using `pytest.mark.parametrize`
- **New command line options**: 
  - `--k8s-cluster-scope` to set default cluster scope (function, class, module, session)
  - `--k8s-cluster-timeout` to set default timeout for cluster operations (default: 300 seconds)
  - `--k8s-cluster-keep` to keep clusters after tests complete by default
  - `--k8s-no-cluster-keep` to explicitly disable keeping clusters (overrides --k8s-cluster-keep)
- **Enhanced cluster configuration**: Added `ClusterConfig` class for managing cluster-specific settings including:
  - `default_scope` - Default fixture scope for clusters
  - `default_timeout` - Default timeout in seconds for cluster operations
  - `default_keep_cluster` - Default behavior for keeping clusters after tests
- **Configuration-based defaults**: Cluster creation now uses configuration values instead of hardcoded defaults
- **Comprehensive scope testing**: Added extensive test coverage for all scope configurations and override scenarios

### Enhanced
- **Fixture system**: Enhanced all cluster fixtures to support scope override via parameters
- **Configuration system**: Extended `PluginConfig` to include cluster configuration management
- **Plugin registration**: Updated plugin to properly register k8s_client fixture
- **Documentation**: Updated README.md with comprehensive examples of k8s_client usage and scope configuration

### Configuration
- **pyproject.toml support**: Default cluster scope can now be configured in `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  addopts = ["--k8s-cluster-scope=session"]
  ```
- **Per-test scope override**: Tests can override scope using parametrize:
  ```python
  @pytest.mark.parametrize("k8s_cluster", [
      {"name": "custom", "scope": "function"}
  ], indirect=True)
  def test_custom(k8s_cluster):
      pass
  ```

### Technical Details
- Added `scope` parameter support to all cluster fixtures
- Enhanced `ClusterFixtureManager` to handle scope-specific cluster creation
- Updated plugin hooks to support new configuration options
- Added comprehensive test suite with 33 test cases covering all scenarios

## [0.1.0] - Initial Release

### Added
- Basic k8s cluster fixtures with configurable scopes
- Kind-based cluster management
- Automatic cluster cleanup
- Multiple fixture scopes (function, class, module, session)
- Cluster factory fixture for multiple clusters
- Comprehensive logging and error handling
- Integration with pytest ecosystem
