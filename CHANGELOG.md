## v1.0.0 (2025-07-07)

### BREAKING CHANGE

- Removed scope-specific fixtures. Users should migrate to using
the k8s_cluster fixture with parametrize for scope control.
- KindCluster initialization API has changed to use
configuration objects. Error constructors now require message parameter.

### Feat

- v1 release
- **ci**: consolidate PyPI publishing into release workflow
- **ci**: add comprehensive release workflow with conventional commits
- **cleanup**: implement robust cluster cleanup mechanism
- **tests**: add comprehensive integration tests for k8s_cluster and k8s_client fixtures
- **fixtures**: align k8s_client scope with k8s_cluster scope
- **examples**: add comprehensive fixture usage examples and fix client connection issues
- **fixtures**: add k8s_client fixture with comprehensive Kubernetes API client support
- **fixtures**: add configurable cluster scope with parametrize override support
- **logging**: unify KIND stdout and stderr logging at INFO level
- **kind**: implement real-time log streaming with configurable levels
- configure pytest plugin entry point for automatic discovery
- **pytest**: configure stdout output and verbose logging
- **kind**: enhance and refactor kind cluster management
- add kind cluster lifecycle manager with comprehensive testing

### Fix

- **ci**: replace URL-based artifact download with GitHub Actions artifacts
- **ci**: attempting fix of semantic release workflow
- removed specifying release name
- **test**: prevent signal handler test from killing CI runner
- prevent real cluster creation in unit tests for k8s_client
- **cleanup**: resolve ruff linting issues in test file
- **config**: use plugin configuration for cluster defaults
- restore proper timeout field in KindClusterConfig
- **kind**: update error tests for new error API

### Refactor

- **fixtures**: consolidate to single k8s_cluster fixture
- **kind**: move KindClusterManager and errors to separate modules
