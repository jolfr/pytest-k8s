"""
Cluster lifecycle manager for kind (Kubernetes in Docker) clusters.

This module provides a comprehensive cluster management system for creating,
managing, and cleaning up kind clusters during testing.
"""

import logging
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Union

from .errors import (
    KindClusterError,
    KindClusterCreationError,
    KindClusterDeletionError,
)

logger = logging.getLogger(__name__)


class KindCluster:
    """
    Manages the lifecycle of a kind (Kubernetes in Docker) cluster.
    
    This class provides methods to create, manage, and clean up kind clusters
    for testing purposes. It handles kubeconfig management, cluster verification,
    and provides robust error handling.
    
    Attributes:
        name: The name of the kind cluster
        kubeconfig_path: Path to the kubeconfig file for this cluster
        config_path: Optional path to kind cluster configuration file
        timeout: Timeout in seconds for cluster operations
        keep_cluster: Whether to keep the cluster after deletion is requested
    """
    
    def __init__(
        self,
        name: Optional[str] = None,
        config_path: Optional[Union[str, Path]] = None,
        timeout: int = 300,
        keep_cluster: bool = False,
        image: Optional[str] = None,
        extra_port_mappings: Optional[List[Dict[str, Union[str, int]]]] = None,
    ):
        """
        Initialize a KindCluster instance.
        
        Args:
            name: Name for the cluster. If None, generates a unique name.
            config_path: Path to kind cluster configuration file.
            timeout: Timeout in seconds for cluster operations.
            keep_cluster: Whether to keep cluster after deletion is requested.
            image: Kubernetes node image to use.
            extra_port_mappings: Additional port mappings for the cluster.
        """
        self.name = name or self._generate_cluster_name()
        self.config_path = Path(config_path) if config_path else None
        self.timeout = timeout
        self.keep_cluster = keep_cluster
        self.image = image
        self.extra_port_mappings = extra_port_mappings or []
        
        # Initialize kubeconfig path
        self._kubeconfig_path: Optional[Path] = None
        self._kubeconfig_temp_file: Optional[tempfile.NamedTemporaryFile] = None
        
        # Track cluster state
        self._created = False
        self._verified = False
    
    @property
    def kubeconfig_path(self) -> Optional[str]:
        """Get the path to the kubeconfig file for this cluster."""
        return str(self._kubeconfig_path) if self._kubeconfig_path else None
    
    @staticmethod
    def _generate_cluster_name() -> str:
        """Generate a unique cluster name."""
        return f"pytest-k8s-{uuid.uuid4().hex[:8]}"
    
    def _run_command(
        self,
        cmd: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a command with proper error handling.
        
        Args:
            cmd: Command to run as a list of strings.
            timeout: Command timeout in seconds.
            capture_output: Whether to capture stdout/stderr.
            check: Whether to raise on non-zero exit code.
            
        Returns:
            CompletedProcess instance.
            
        Raises:
            subprocess.CalledProcessError: If command fails and check=True.
            subprocess.TimeoutExpired: If command times out.
        """
        timeout = timeout or self.timeout
        
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=check,
            )
            
            if result.stdout:
                logger.debug(f"Command stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Command stderr: {result.stderr}")
                
            return result
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"Exit code: {e.returncode}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")
            raise
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            raise
    
    def _check_kind_available(self) -> bool:
        """Check if kind command is available."""
        try:
            self._run_command(["kind", "version"], timeout=10)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _check_docker_available(self) -> bool:
        """Check if Docker is available and running."""
        try:
            self._run_command(["docker", "version"], timeout=10)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _create_cluster_config(self) -> Optional[Path]:
        """
        Create a temporary cluster configuration file if needed.
        
        Returns:
            Path to the configuration file or None.
        """
        if self.config_path:
            return self.config_path
        
        # Create default config if we have custom settings
        if self.extra_port_mappings or self.image:
            config_content = self._generate_default_config()
            
            # Create temporary config file
            temp_config = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.yaml',
                prefix='kind-config-',
                delete=False
            )
            temp_config.write(config_content)
            temp_config.flush()
            temp_config.close()
            
            return Path(temp_config.name)
        
        return None
    
    def _generate_default_config(self) -> str:
        """Generate a default kind cluster configuration."""
        config_lines = [
            "kind: Cluster",
            "apiVersion: kind.x-k8s.io/v1alpha4",
            "nodes:",
            "- role: control-plane"
        ]
        
        if self.image:
            config_lines.append(f"  image: {self.image}")
        
        if self.extra_port_mappings:
            config_lines.append("  extraPortMappings:")
            for mapping in self.extra_port_mappings:
                config_lines.append(f"  - containerPort: {mapping['containerPort']}")
                config_lines.append(f"    hostPort: {mapping['hostPort']}")
                if 'protocol' in mapping:
                    config_lines.append(f"    protocol: {mapping['protocol']}")
        
        return "\n".join(config_lines)
    
    def _setup_kubeconfig(self) -> None:
        """Set up kubeconfig for the cluster."""
        # Create temporary kubeconfig file
        self._kubeconfig_temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            prefix='kubeconfig-',
            delete=False
        )
        self._kubeconfig_path = Path(self._kubeconfig_temp_file.name)
        self._kubeconfig_temp_file.close()
        
        # Export kubeconfig
        cmd = [
            "kind", "export", "kubeconfig",
            "--name", self.name,
            "--kubeconfig", str(self._kubeconfig_path)
        ]
        
        try:
            self._run_command(cmd)
            logger.info(f"Kubeconfig exported to: {self._kubeconfig_path}")
        except subprocess.CalledProcessError as e:
            raise KindClusterCreationError(
                f"Failed to export kubeconfig: {e.stderr}"
            )
    
    def create(self) -> None:
        """
        Create the kind cluster.
        
        Raises:
            KindClusterCreationError: If cluster creation fails.
            KindClusterError: If prerequisites are not met.
        """
        if self._created:
            logger.warning(f"Cluster {self.name} already created")
            return
        
        # Check prerequisites
        if not self._check_kind_available():
            raise KindClusterError("kind command not available")
        
        if not self._check_docker_available():
            raise KindClusterError("Docker not available or not running")
        
        logger.info(f"Creating kind cluster: {self.name}")
        
        # Check if cluster already exists
        if self.exists():
            raise KindClusterCreationError(
                f"Cluster {self.name} already exists"
            )
        
        # Prepare creation command
        cmd = ["kind", "create", "cluster", "--name", self.name]
        
        # Add configuration file if provided
        config_path = self._create_cluster_config()
        if config_path:
            cmd.extend(["--config", str(config_path)])
        
        # Add wait flag
        cmd.append("--wait=60s")
        
        try:
            # Create the cluster
            self._run_command(cmd, timeout=self.timeout)
            self._created = True
            
            # Set up kubeconfig
            self._setup_kubeconfig()
            
            # Verify cluster is ready
            self.wait_for_ready()
            
            logger.info(f"Kind cluster {self.name} created successfully")
            
        except subprocess.CalledProcessError as e:
            # Clean up on failure
            try:
                self.delete()
            except Exception:
                pass  # Ignore cleanup errors
            raise KindClusterCreationError(
                f"Failed to create cluster {self.name}: {e.stderr}"
            )
        except Exception as e:
            # Clean up on failure
            try:
                self.delete()
            except Exception:
                pass  # Ignore cleanup errors
            raise KindClusterCreationError(f"Cluster creation failed: {str(e)}")
        finally:
            # Clean up temporary config file
            if config_path and config_path != self.config_path:
                try:
                    config_path.unlink()
                except Exception:
                    pass
    
    def delete(self) -> None:
        """
        Delete the kind cluster.
        
        Raises:
            KindClusterDeletionError: If cluster deletion fails.
        """
        if self.keep_cluster:
            logger.info(f"Keeping cluster {self.name} (keep_cluster=True)")
            return
        
        if not self.exists():
            logger.warning(f"Cluster {self.name} does not exist")
            return
        
        logger.info(f"Deleting kind cluster: {self.name}")
        
        cmd = ["kind", "delete", "cluster", "--name", self.name]
        
        try:
            self._run_command(cmd)
            self._created = False
            self._verified = False
            logger.info(f"Kind cluster {self.name} deleted successfully")
            
        except subprocess.CalledProcessError as e:
            raise KindClusterDeletionError(
                f"Failed to delete cluster {self.name}: {e.stderr}"
            )
        finally:
            # Clean up kubeconfig file
            if self._kubeconfig_path and self._kubeconfig_path.exists():
                try:
                    self._kubeconfig_path.unlink()
                except Exception:
                    pass
    
    def exists(self) -> bool:
        """
        Check if the cluster exists.
        
        Returns:
            True if cluster exists, False otherwise.
        """
        try:
            result = self._run_command(
                ["kind", "get", "clusters"],
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0:
                clusters = [
                    cluster.strip() 
                    for cluster in result.stdout.strip().split('\n')
                    if cluster.strip()
                ]
                return self.name in clusters
            
            return False
            
        except Exception:
            return False
    
    def wait_for_ready(self, timeout: Optional[int] = None) -> None:
        """
        Wait for the cluster to be ready.
        
        Args:
            timeout: Timeout in seconds. Uses instance timeout if None.
            
        Raises:
            KindClusterError: If cluster is not ready within timeout.
        """
        timeout = timeout or self.timeout
        start_time = time.time()
        
        logger.info(f"Waiting for cluster {self.name} to be ready...")
        
        while time.time() - start_time < timeout:
            try:
                # Check if we can access the cluster
                if self._kubeconfig_path:
                    env = os.environ.copy()
                    env['KUBECONFIG'] = str(self._kubeconfig_path)
                    
                    result = subprocess.run(
                        ["kubectl", "get", "nodes"],
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        self._verified = True
                        logger.info(f"Cluster {self.name} is ready")
                        return
                
                time.sleep(2)
                
            except Exception as e:
                logger.debug(f"Cluster not ready yet: {e}")
                time.sleep(2)
        
        raise KindClusterError(
            f"Cluster {self.name} not ready within {timeout} seconds"
        )
    
    def get_nodes(self) -> List[str]:
        """
        Get list of nodes in the cluster.
        
        Returns:
            List of node names.
            
        Raises:
            KindClusterError: If unable to get nodes.
        """
        if not self._kubeconfig_path:
            raise KindClusterError("Cluster not created or kubeconfig not available")
        
        try:
            env = os.environ.copy()
            env['KUBECONFIG'] = str(self._kubeconfig_path)
            
            result = subprocess.run(
                ["kubectl", "get", "nodes", "-o", "name"],
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                nodes = [
                    line.replace('node/', '') 
                    for line in result.stdout.strip().split('\n')
                    if line.strip()
                ]
                return nodes
            else:
                raise KindClusterError(f"Failed to get nodes: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise KindClusterError("Timeout getting cluster nodes")
        except Exception as e:
            raise KindClusterError(f"Error getting nodes: {str(e)}")
    
    def is_ready(self) -> bool:
        """
        Check if the cluster is ready.
        
        Returns:
            True if cluster is ready, False otherwise.
        """
        try:
            self.wait_for_ready(timeout=10)
            return True
        except KindClusterError:
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.create()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        try:
            self.delete()
        except Exception as e:
            logger.error(f"Error during cluster cleanup: {e}")
    
    def __str__(self) -> str:
        """String representation."""
        return f"KindCluster(name={self.name}, created={self._created})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"KindCluster(name={self.name}, created={self._created}, "
            f"verified={self._verified}, kubeconfig={self.kubeconfig_path})"
        )
