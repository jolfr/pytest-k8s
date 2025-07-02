"""
Configuration management for kind clusters.

This module provides type-safe configuration classes and validation
for kind cluster operations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from .errors import KindClusterConfigError


@dataclass
class PortMapping:
    """
    Port mapping configuration for kind clusters.

    Attributes:
        container_port: Port inside the container
        host_port: Port on the host
        protocol: Protocol (TCP/UDP)
        listen_address: Address to listen on (defaults to 0.0.0.0)
    """

    container_port: int
    host_port: int
    protocol: str = "TCP"
    listen_address: str = "0.0.0.0"

    def __post_init__(self):
        """Validate port mapping configuration."""
        if not (1 <= self.container_port <= 65535):
            raise KindClusterConfigError(
                f"Invalid container port: {self.container_port}"
            )

        if not (1 <= self.host_port <= 65535):
            raise KindClusterConfigError(f"Invalid host port: {self.host_port}")

        if self.protocol not in ("TCP", "UDP"):
            raise KindClusterConfigError(f"Invalid protocol: {self.protocol}")

    def to_dict(self) -> Dict[str, Union[str, int]]:
        """Convert to dictionary format for kind configuration."""
        result = {
            "containerPort": self.container_port,
            "hostPort": self.host_port,
        }
        if self.protocol != "TCP":
            result["protocol"] = self.protocol
        if self.listen_address != "0.0.0.0":
            result["listenAddress"] = self.listen_address
        return result


@dataclass
class NodeConfig:
    """
    Configuration for a single kind node.

    Attributes:
        role: Node role (control-plane or worker)
        image: Container image to use for the node
        extra_mounts: Extra volume mounts for the node
        extra_port_mappings: Port mappings for the node
        labels: Node labels
    """

    role: str = "control-plane"
    image: Optional[str] = None
    extra_mounts: List[Dict[str, str]] = field(default_factory=list)
    extra_port_mappings: List[PortMapping] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate node configuration."""
        if self.role not in ("control-plane", "worker"):
            raise KindClusterConfigError(f"Invalid node role: {self.role}")


@dataclass
class KindClusterConfig:
    """
    Complete configuration for a kind cluster.

    Attributes:
        name: Cluster name
        timeout: Operation timeout in seconds
        keep_cluster: Whether to keep cluster after deletion
        image: Default node image
        nodes: List of node configurations
        api_version: Kind API version
        networking: Networking configuration
        feature_gates: Kubernetes feature gates
        runtime_config: Kubernetes runtime configuration
        kubeadm_config_patches: Kubeadm configuration patches
        kubeadm_config_patch_json6902: JSON6902 patches for kubeadm config
    """

    name: Optional[str] = None
    timeout: int = 300
    keep_cluster: bool = False
    image: Optional[str] = None
    nodes: List[NodeConfig] = field(default_factory=lambda: [NodeConfig()])
    api_version: str = "kind.x-k8s.io/v1alpha4"
    networking: Dict[str, Union[str, int]] = field(default_factory=dict)
    feature_gates: Dict[str, bool] = field(default_factory=dict)
    runtime_config: Dict[str, str] = field(default_factory=dict)
    kubeadm_config_patches: List[str] = field(default_factory=list)
    kubeadm_config_patch_json6902: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        """Validate cluster configuration."""
        if self.timeout < 0:
            raise KindClusterConfigError(f"Invalid timeout: {self.timeout}")

        if not self.nodes:
            raise KindClusterConfigError("At least one node must be configured")

        # Ensure at least one control-plane node
        control_plane_nodes = [n for n in self.nodes if n.role == "control-plane"]
        if not control_plane_nodes:
            raise KindClusterConfigError("At least one control-plane node is required")

    def __setattr__(self, name: str, value) -> None:
        """Override setattr to validate timeout when it's set."""
        if name == "timeout" and hasattr(
            self, "timeout"
        ):  # Only validate after initialization
            if value < 0:
                raise KindClusterConfigError(f"Invalid timeout: {value}")
        super().__setattr__(name, value)

    @property
    def control_plane_count(self) -> int:
        """Get number of control-plane nodes."""
        return len([n for n in self.nodes if n.role == "control-plane"])

    @property
    def worker_count(self) -> int:
        """Get number of worker nodes."""
        return len([n for n in self.nodes if n.role == "worker"])

    @property
    def total_nodes(self) -> int:
        """Get total number of nodes."""
        return len(self.nodes)

    def add_worker_node(self, **kwargs) -> None:
        """Add a worker node to the cluster."""
        self.nodes.append(NodeConfig(role="worker", **kwargs))

    def add_control_plane_node(self, **kwargs) -> None:
        """Add a control-plane node to the cluster."""
        self.nodes.append(NodeConfig(role="control-plane", **kwargs))

    def add_port_mapping(
        self,
        container_port: int,
        host_port: int,
        protocol: str = "TCP",
        listen_address: str = "0.0.0.0",
    ) -> None:
        """Add a port mapping to the first control-plane node."""
        control_plane_nodes = [n for n in self.nodes if n.role == "control-plane"]
        if not control_plane_nodes:
            raise KindClusterConfigError("No control-plane nodes found")

        port_mapping = PortMapping(
            container_port=container_port,
            host_port=host_port,
            protocol=protocol,
            listen_address=listen_address,
        )
        control_plane_nodes[0].extra_port_mappings.append(port_mapping)

    def to_yaml_dict(self) -> Dict:
        """Convert configuration to YAML dictionary format."""
        config = {"kind": "Cluster", "apiVersion": self.api_version, "nodes": []}

        for node in self.nodes:
            node_config = {"role": node.role}

            # Add image if specified
            if node.image or self.image:
                node_config["image"] = node.image or self.image

            # Add extra port mappings
            if node.extra_port_mappings:
                node_config["extraPortMappings"] = [
                    pm.to_dict() for pm in node.extra_port_mappings
                ]

            # Add extra mounts
            if node.extra_mounts:
                node_config["extraMounts"] = node.extra_mounts

            # Add labels
            if node.labels:
                node_config["labels"] = node.labels

            config["nodes"].append(node_config)

        # Add networking configuration
        if self.networking:
            config["networking"] = self.networking

        # Add feature gates
        if self.feature_gates:
            config["featureGates"] = self.feature_gates

        # Add runtime config
        if self.runtime_config:
            config["runtimeConfig"] = self.runtime_config

        # Add kubeadm config patches
        if self.kubeadm_config_patches:
            config["kubeadmConfigPatches"] = self.kubeadm_config_patches

        # Add JSON6902 patches
        if self.kubeadm_config_patch_json6902:
            config["kubeadmConfigPatchesJSON6902"] = self.kubeadm_config_patch_json6902

        return config

    @classmethod
    def from_dict(cls, data: Dict) -> "KindClusterConfig":
        """Create configuration from dictionary."""
        config = cls()

        # Parse nodes
        if "nodes" in data:
            config.nodes = []
            for node_data in data["nodes"]:
                node = NodeConfig(role=node_data.get("role", "control-plane"))

                if "image" in node_data:
                    node.image = node_data["image"]

                if "extraPortMappings" in node_data:
                    for pm_data in node_data["extraPortMappings"]:
                        port_mapping = PortMapping(
                            container_port=pm_data["containerPort"],
                            host_port=pm_data["hostPort"],
                            protocol=pm_data.get("protocol", "TCP"),
                            listen_address=pm_data.get("listenAddress", "0.0.0.0"),
                        )
                        node.extra_port_mappings.append(port_mapping)

                if "extraMounts" in node_data:
                    node.extra_mounts = node_data["extraMounts"]

                if "labels" in node_data:
                    node.labels = node_data["labels"]

                config.nodes.append(node)

        # Parse other configuration
        if "apiVersion" in data:
            config.api_version = data["apiVersion"]

        if "networking" in data:
            config.networking = data["networking"]

        if "featureGates" in data:
            config.feature_gates = data["featureGates"]

        if "runtimeConfig" in data:
            config.runtime_config = data["runtimeConfig"]

        if "kubeadmConfigPatches" in data:
            config.kubeadm_config_patches = data["kubeadmConfigPatches"]

        if "kubeadmConfigPatchesJSON6902" in data:
            config.kubeadm_config_patch_json6902 = data["kubeadmConfigPatchesJSON6902"]

        return config


def create_simple_config(
    name: Optional[str] = None,
    worker_nodes: int = 0,
    image: Optional[str] = None,
    port_mappings: Optional[List[Dict[str, Union[str, int]]]] = None,
) -> KindClusterConfig:
    """
    Create a simple cluster configuration.

    Args:
        name: Cluster name
        worker_nodes: Number of worker nodes
        image: Node image
        port_mappings: Port mappings for control-plane node

    Returns:
        KindClusterConfig instance
    """
    config = KindClusterConfig(name=name, image=image)

    # Add worker nodes
    for _ in range(worker_nodes):
        config.add_worker_node()

    # Add port mappings to control-plane
    if port_mappings:
        for mapping in port_mappings:
            config.add_port_mapping(
                container_port=mapping["containerPort"],
                host_port=mapping["hostPort"],
                protocol=mapping.get("protocol", "TCP"),
                listen_address=mapping.get("listenAddress", "0.0.0.0"),
            )

    return config


def create_ha_config(
    name: Optional[str] = None,
    control_plane_nodes: int = 3,
    worker_nodes: int = 2,
    image: Optional[str] = None,
) -> KindClusterConfig:
    """
    Create a high-availability cluster configuration.

    Args:
        name: Cluster name
        control_plane_nodes: Number of control-plane nodes
        worker_nodes: Number of worker nodes
        image: Node image

    Returns:
        KindClusterConfig instance
    """
    nodes = []

    # Add control-plane nodes
    for _ in range(control_plane_nodes):
        nodes.append(NodeConfig(role="control-plane", image=image))

    # Add worker nodes
    for _ in range(worker_nodes):
        nodes.append(NodeConfig(role="worker", image=image))

    return KindClusterConfig(name=name, image=image, nodes=nodes)
