## 1.0.0 (2025-07-07)

### ⚠ BREAKING CHANGES

* **fixtures:** Removed scope-specific fixtures. Users should migrate to using
the k8s_cluster fixture with parametrize for scope control.

[cline-generated]
Signed-off-by: jolfr <thomas.jack.carroll@gmail.com>
* **kind:** KindCluster initialization API has changed to use
configuration objects. Error constructors now require message parameter.

Signed-off-by: Thomas Jack Carroll <thomas.jack.carroll@gmail.com>

### Features

* add kind cluster lifecycle manager with comprehensive testing ([54ae125](https://github.com/jolfr/pytest-k8s/commit/54ae12517d732bfc9d758ed6d18f761823271073))
* **ci:** add comprehensive release workflow with conventional commits ([c51ed67](https://github.com/jolfr/pytest-k8s/commit/c51ed676df8f7c3b101902ba4a1267eaf8c3a311))
* **ci:** consolidate PyPI publishing into release workflow ([557b147](https://github.com/jolfr/pytest-k8s/commit/557b14763c6f83f8a96b4fa6e8b53c984e942e98))
* **cleanup:** implement robust cluster cleanup mechanism ([b8f57d6](https://github.com/jolfr/pytest-k8s/commit/b8f57d67600731733af30d598f5df56b97eb7085))
* configure pytest plugin entry point for automatic discovery ([fcab05f](https://github.com/jolfr/pytest-k8s/commit/fcab05f709171e56864de11ed892fdc5e332188e))
* **examples:** add comprehensive fixture usage examples and fix client connection issues ([356210f](https://github.com/jolfr/pytest-k8s/commit/356210fba5ec54c020642f0f1279a1ebb629695f))
* **fixtures:** add configurable cluster scope with parametrize override support ([2fb41e1](https://github.com/jolfr/pytest-k8s/commit/2fb41e141452dbad7902b39c3a5192f5ac53fc78))
* **fixtures:** add k8s_client fixture with comprehensive Kubernetes API client support ([987ebfc](https://github.com/jolfr/pytest-k8s/commit/987ebfce0ba4d441ec076c8bd6245dd95351dbfa))
* **fixtures:** align k8s_client scope with k8s_cluster scope ([85c887a](https://github.com/jolfr/pytest-k8s/commit/85c887a5493988c15543aff134d20dc4d2eb94b4))
* **kind:** enhance and refactor kind cluster management ([c94b8f7](https://github.com/jolfr/pytest-k8s/commit/c94b8f732449cc3a7bb6066f728cf77256b2f70b))
* **kind:** implement real-time log streaming with configurable levels ([6436c47](https://github.com/jolfr/pytest-k8s/commit/6436c47b9adce4a2308303eb41a230a531f1ba8d))
* **logging:** unify KIND stdout and stderr logging at INFO level ([c135cc9](https://github.com/jolfr/pytest-k8s/commit/c135cc93993e9963a4f59b6448a5579a809ecc73))
* **pytest:** configure stdout output and verbose logging ([efb150d](https://github.com/jolfr/pytest-k8s/commit/efb150d88d8a508d9635a0077cd6b790c2af5a9d))
* **tests:** add comprehensive integration tests for k8s_cluster and k8s_client fixtures ([7718208](https://github.com/jolfr/pytest-k8s/commit/7718208fb396ad7bd970b6b79459dce5777f41bd))

### Bug Fixes

* **cleanup:** resolve ruff linting issues in test file ([473e2c8](https://github.com/jolfr/pytest-k8s/commit/473e2c8dcc603f4cb0eef5d6e75c8dcfce26bbb8))
* **config:** use plugin configuration for cluster defaults ([d8859a0](https://github.com/jolfr/pytest-k8s/commit/d8859a0b8520c4b29ea5be4cbf0b8a9e721b491b))
* **kind:** update error tests for new error API ([914fe9e](https://github.com/jolfr/pytest-k8s/commit/914fe9efc6afa47c5c76ebe5b15ce8ac70665605))
* prevent real cluster creation in unit tests for k8s_client ([4757394](https://github.com/jolfr/pytest-k8s/commit/475739424b387d654e1f07bde04dc596be7a3bac))
* removed specifying release name ([fa9a26c](https://github.com/jolfr/pytest-k8s/commit/fa9a26c36fa6d0890bd9fa35d9093d053551f10c))
* restore proper timeout field in KindClusterConfig ([6b121f8](https://github.com/jolfr/pytest-k8s/commit/6b121f8495d0f555517983d08b9cf327dc0a0ad5))
* **test:** prevent signal handler test from killing CI runner ([99610d9](https://github.com/jolfr/pytest-k8s/commit/99610d9d9061075c66ae40adf77e0d88935a6099))

### Documentation

* add comprehensive README for pytest-kubernetes project ([72f625f](https://github.com/jolfr/pytest-k8s/commit/72f625f70b68fc318f69784acc441f6f6f8cc1c7))

### Code Refactoring

* **fixtures:** consolidate to single k8s_cluster fixture ([32b98cc](https://github.com/jolfr/pytest-k8s/commit/32b98cc1c8b4402ad5c1cc610a00d7d999b979df))
* **kind:** move KindClusterManager and errors to separate modules ([68cd627](https://github.com/jolfr/pytest-k8s/commit/68cd62764b5702322d10c857d89b82f2120b8a0b))
