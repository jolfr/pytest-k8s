"""
Tests for the kind cluster configuration management.

This module contains tests for the configuration classes and utilities
including PortMapping, NodeConfig, KindClusterConfig, and helper functions.
"""

import pytest

from pytest_k8s.kind.config import (
    KindClusterConfig,
    NodeConfig,
    PortMapping,
    create_ha_config,
    create_simple_config,
)
from pytest_k8s.kind.errors import KindClusterConfigError


class TestPortMapping:
    """Test cases for PortMapping class."""

    def test_init_valid(self):
        """Test PortMapping initialization with valid values."""
        pm = PortMapping(container_port=80, host_port=8080)

        assert pm.container_port == 80
        assert pm.host_port == 8080
        assert pm.protocol == "TCP"
        assert pm.listen_address == "0.0.0.0"

    def test_init_with_custom_values(self):
        """Test PortMapping initialization with custom values."""
        pm = PortMapping(
            container_port=443,
            host_port=8443,
            protocol="UDP",
            listen_address="127.0.0.1",
        )

        assert pm.container_port == 443
        assert pm.host_port == 8443
        assert pm.protocol == "UDP"
        assert pm.listen_address == "127.0.0.1"

    def test_invalid_container_port(self):
        """Test PortMapping with invalid container port."""
        with pytest.raises(KindClusterConfigError, match="Invalid container port"):
            PortMapping(container_port=0, host_port=8080)

        with pytest.raises(KindClusterConfigError, match="Invalid container port"):
            PortMapping(container_port=65536, host_port=8080)

    def test_invalid_host_port(self):
        """Test PortMapping with invalid host port."""
        with pytest.raises(KindClusterConfigError, match="Invalid host port"):
            PortMapping(container_port=80, host_port=0)

        with pytest.raises(KindClusterConfigError, match="Invalid host port"):
            PortMapping(container_port=80, host_port=65536)

    def test_invalid_protocol(self):
        """Test PortMapping with invalid protocol."""
        with pytest.raises(KindClusterConfigError, match="Invalid protocol"):
            PortMapping(container_port=80, host_port=8080, protocol="HTTP")

    def test_to_dict(self):
        """Test PortMapping to_dict method."""
        pm = PortMapping(container_port=80, host_port=8080)
        result = pm.to_dict()

        expected = {
            "containerPort": 80,
            "hostPort": 8080,
        }
        assert result == expected

    def test_to_dict_with_custom_values(self):
        """Test PortMapping to_dict with custom values."""
        pm = PortMapping(
            container_port=443,
            host_port=8443,
            protocol="UDP",
            listen_address="127.0.0.1",
        )
        result = pm.to_dict()

        expected = {
            "containerPort": 443,
            "hostPort": 8443,
            "protocol": "UDP",
            "listenAddress": "127.0.0.1",
        }
        assert result == expected


class TestNodeConfig:
    """Test cases for NodeConfig class."""

    def test_init_default(self):
        """Test NodeConfig initialization with defaults."""
        node = NodeConfig()

        assert node.role == "control-plane"
        assert node.image is None
        assert node.extra_mounts == []
        assert node.extra_port_mappings == []
        assert node.labels == {}

    def test_init_with_custom_values(self):
        """Test NodeConfig initialization with custom values."""
        port_mapping = PortMapping(container_port=80, host_port=8080)

        node = NodeConfig(
            role="worker",
            image="kindest/node:v1.25.0",
            extra_mounts=[{"hostPath": "/tmp", "containerPath": "/data"}],
            extra_port_mappings=[port_mapping],
            labels={"type": "worker"},
        )

        assert node.role == "worker"
        assert node.image == "kindest/node:v1.25.0"
        assert node.extra_mounts == [{"hostPath": "/tmp", "containerPath": "/data"}]
        assert node.extra_port_mappings == [port_mapping]
        assert node.labels == {"type": "worker"}

    def test_invalid_role(self):
        """Test NodeConfig with invalid role."""
        with pytest.raises(KindClusterConfigError, match="Invalid node role"):
            NodeConfig(role="invalid")


class TestKindClusterConfig:
    """Test cases for KindClusterConfig class."""

    def test_init_default(self):
        """Test KindClusterConfig initialization with defaults."""
        config = KindClusterConfig()

        assert config.name is None
        assert config.timeout == 300
        assert config.keep_cluster is False
        assert config.image is None
        assert len(config.nodes) == 1
        assert config.nodes[0].role == "control-plane"
        assert config.api_version == "kind.x-k8s.io/v1alpha4"
        assert config.networking == {}
        assert config.feature_gates == {}
        assert config.runtime_config == {}
        assert config.kubeadm_config_patches == []
        assert config.kubeadm_config_patch_json6902 == []

    def test_init_with_custom_values(self):
        """Test KindClusterConfig initialization with custom values."""
        nodes = [
            NodeConfig(role="control-plane"),
            NodeConfig(role="worker"),
        ]

        config = KindClusterConfig(
            name="test-cluster",
            timeout=600,
            keep_cluster=True,
            image="kindest/node:v1.25.0",
            nodes=nodes,
            networking={"podSubnet": "10.244.0.0/16"},
            feature_gates={"SomeFeature": True},
            runtime_config={"api/all": "true"},
        )

        assert config.name == "test-cluster"
        assert config.timeout == 600
        assert config.keep_cluster is True
        assert config.image == "kindest/node:v1.25.0"
        assert len(config.nodes) == 2
        assert config.networking == {"podSubnet": "10.244.0.0/16"}
        assert config.feature_gates == {"SomeFeature": True}
        assert config.runtime_config == {"api/all": "true"}

    def test_validation_negative_timeout(self):
        """Test KindClusterConfig validation with negative timeout."""
        with pytest.raises(KindClusterConfigError, match="Invalid timeout"):
            KindClusterConfig(timeout=-1)

    def test_validation_no_nodes(self):
        """Test KindClusterConfig validation with no nodes."""
        with pytest.raises(
            KindClusterConfigError, match="At least one node must be configured"
        ):
            KindClusterConfig(nodes=[])

    def test_validation_no_control_plane(self):
        """Test KindClusterConfig validation with no control-plane nodes."""
        nodes = [NodeConfig(role="worker")]

        with pytest.raises(
            KindClusterConfigError, match="At least one control-plane node is required"
        ):
            KindClusterConfig(nodes=nodes)

    def test_control_plane_count(self):
        """Test control_plane_count property."""
        nodes = [
            NodeConfig(role="control-plane"),
            NodeConfig(role="control-plane"),
            NodeConfig(role="worker"),
        ]
        config = KindClusterConfig(nodes=nodes)

        assert config.control_plane_count == 2

    def test_worker_count(self):
        """Test worker_count property."""
        nodes = [
            NodeConfig(role="control-plane"),
            NodeConfig(role="worker"),
            NodeConfig(role="worker"),
        ]
        config = KindClusterConfig(nodes=nodes)

        assert config.worker_count == 2

    def test_total_nodes(self):
        """Test total_nodes property."""
        nodes = [
            NodeConfig(role="control-plane"),
            NodeConfig(role="worker"),
            NodeConfig(role="worker"),
        ]
        config = KindClusterConfig(nodes=nodes)

        assert config.total_nodes == 3

    def test_add_worker_node(self):
        """Test add_worker_node method."""
        config = KindClusterConfig()
        initial_count = config.total_nodes

        config.add_worker_node(image="custom-image")

        assert config.total_nodes == initial_count + 1
        assert config.worker_count == 1
        assert config.nodes[-1].role == "worker"
        assert config.nodes[-1].image == "custom-image"

    def test_add_control_plane_node(self):
        """Test add_control_plane_node method."""
        config = KindClusterConfig()
        initial_count = config.control_plane_count

        config.add_control_plane_node(image="custom-image")

        assert config.control_plane_count == initial_count + 1
        assert config.nodes[-1].role == "control-plane"
        assert config.nodes[-1].image == "custom-image"

    def test_add_port_mapping(self):
        """Test add_port_mapping method."""
        config = KindClusterConfig()

        config.add_port_mapping(container_port=80, host_port=8080)

        control_plane_nodes = [n for n in config.nodes if n.role == "control-plane"]
        assert len(control_plane_nodes) > 0
        assert len(control_plane_nodes[0].extra_port_mappings) == 1

        port_mapping = control_plane_nodes[0].extra_port_mappings[0]
        assert port_mapping.container_port == 80
        assert port_mapping.host_port == 8080

    def test_add_port_mapping_no_control_plane(self):
        """Test add_port_mapping with no control-plane nodes."""
        nodes = [NodeConfig(role="worker")]

        # This should fail during config validation, but let's test the port mapping logic
        with pytest.raises(KindClusterConfigError):
            KindClusterConfig(nodes=nodes)

    def test_to_yaml_dict_minimal(self):
        """Test to_yaml_dict with minimal configuration."""
        config = KindClusterConfig()
        result = config.to_yaml_dict()

        expected = {
            "kind": "Cluster",
            "apiVersion": "kind.x-k8s.io/v1alpha4",
            "nodes": [{"role": "control-plane"}],
        }
        assert result == expected

    def test_to_yaml_dict_complex(self):
        """Test to_yaml_dict with complex configuration."""
        port_mapping = PortMapping(container_port=80, host_port=8080)
        nodes = [
            NodeConfig(
                role="control-plane",
                image="kindest/node:v1.25.0",
                extra_port_mappings=[port_mapping],
                labels={"type": "control-plane"},
            ),
            NodeConfig(role="worker", image="kindest/node:v1.25.0"),
        ]

        config = KindClusterConfig(
            nodes=nodes,
            networking={"podSubnet": "10.244.0.0/16"},
            feature_gates={"SomeFeature": True},
        )

        result = config.to_yaml_dict()

        expected = {
            "kind": "Cluster",
            "apiVersion": "kind.x-k8s.io/v1alpha4",
            "nodes": [
                {
                    "role": "control-plane",
                    "image": "kindest/node:v1.25.0",
                    "extraPortMappings": [{"containerPort": 80, "hostPort": 8080}],
                    "labels": {"type": "control-plane"},
                },
                {"role": "worker", "image": "kindest/node:v1.25.0"},
            ],
            "networking": {"podSubnet": "10.244.0.0/16"},
            "featureGates": {"SomeFeature": True},
        }
        assert result == expected

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "apiVersion": "kind.x-k8s.io/v1alpha4",
            "kind": "Cluster",
            "nodes": [
                {
                    "role": "control-plane",
                    "image": "kindest/node:v1.25.0",
                    "extraPortMappings": [
                        {"containerPort": 80, "hostPort": 8080, "protocol": "TCP"}
                    ],
                    "labels": {"type": "control-plane"},
                },
                {"role": "worker"},
            ],
            "networking": {"podSubnet": "10.244.0.0/16"},
            "featureGates": {"SomeFeature": True},
        }

        config = KindClusterConfig.from_dict(data)

        assert config.api_version == "kind.x-k8s.io/v1alpha4"
        assert len(config.nodes) == 2
        assert config.nodes[0].role == "control-plane"
        assert config.nodes[0].image == "kindest/node:v1.25.0"
        assert len(config.nodes[0].extra_port_mappings) == 1
        assert config.nodes[0].extra_port_mappings[0].container_port == 80
        assert config.nodes[0].labels == {"type": "control-plane"}
        assert config.nodes[1].role == "worker"
        assert config.networking == {"podSubnet": "10.244.0.0/16"}
        assert config.feature_gates == {"SomeFeature": True}


class TestHelperFunctions:
    """Test cases for helper functions."""

    def test_create_simple_config_defaults(self):
        """Test create_simple_config with defaults."""
        config = create_simple_config()

        assert config.name is None
        assert config.image is None
        assert config.total_nodes == 1
        assert config.control_plane_count == 1
        assert config.worker_count == 0

    def test_create_simple_config_with_workers(self):
        """Test create_simple_config with worker nodes."""
        config = create_simple_config(
            name="test-cluster", worker_nodes=2, image="kindest/node:v1.25.0"
        )

        assert config.name == "test-cluster"
        assert config.image == "kindest/node:v1.25.0"
        assert config.total_nodes == 3  # 1 control-plane + 2 workers
        assert config.control_plane_count == 1
        assert config.worker_count == 2

    def test_create_simple_config_with_port_mappings(self):
        """Test create_simple_config with port mappings."""
        port_mappings = [
            {"containerPort": 80, "hostPort": 8080},
            {"containerPort": 443, "hostPort": 8443, "protocol": "TCP"},
        ]

        config = create_simple_config(port_mappings=port_mappings)

        control_plane_nodes = [n for n in config.nodes if n.role == "control-plane"]
        assert len(control_plane_nodes) == 1
        assert len(control_plane_nodes[0].extra_port_mappings) == 2

        pm1 = control_plane_nodes[0].extra_port_mappings[0]
        assert pm1.container_port == 80
        assert pm1.host_port == 8080

        pm2 = control_plane_nodes[0].extra_port_mappings[1]
        assert pm2.container_port == 443
        assert pm2.host_port == 8443

    def test_create_ha_config_defaults(self):
        """Test create_ha_config with defaults."""
        config = create_ha_config()

        assert config.name is None
        assert config.image is None
        assert config.total_nodes == 5  # 3 control-plane + 2 workers
        assert config.control_plane_count == 3
        assert config.worker_count == 2

    def test_create_ha_config_custom(self):
        """Test create_ha_config with custom values."""
        config = create_ha_config(
            name="ha-cluster",
            control_plane_nodes=5,
            worker_nodes=3,
            image="kindest/node:v1.25.0",
        )

        assert config.name == "ha-cluster"
        assert config.image == "kindest/node:v1.25.0"
        assert config.total_nodes == 8  # 5 control-plane + 3 workers
        assert config.control_plane_count == 5
        assert config.worker_count == 3
