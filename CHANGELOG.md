# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Configurable cluster scope**: Added support for configuring default cluster scope via command line and configuration files
- **Scope override via parametrize**: Added ability to override cluster scope per test using `pytest.mark.parametrize`
- **New command line option**: `--k8s-cluster-scope` to set default cluster scope (function, class, module, session)
- **Enhanced cluster configuration**: Added `ClusterConfig` class for managing cluster-specific settings
- **Comprehensive scope testing**: Added extensive test coverage for all scope configurations and override scenarios

### Enhanced
- **Fixture system**: Enhanced all cluster fixtures to support scope override via parameters
- **Configuration system**: Extended `PluginConfig` to include cluster configuration management
- **Documentation**: Updated README.md with comprehensive examples of scope configuration and parametrize usage

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
