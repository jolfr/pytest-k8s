"""
Pytest fixtures for Kubernetes testing.

This module provides pytest fixtures for creating and managing Kubernetes
resources during testing, including clusters, clients, and namespaces.
"""

from .k8s_cluster import (
    k8s_cluster,
    k8s_cluster_session,
    k8s_cluster_module,
    k8s_cluster_class,
    k8s_cluster_function,
    k8s_cluster_factory,
    k8s_cluster_per_test,
    k8s_cluster_per_class,
    k8s_cluster_per_module,
    k8s_cluster_per_session,
    ClusterFixtureManager,
)

__all__ = [
    # Main cluster fixtures
    "k8s_cluster",
    "k8s_cluster_session",
    "k8s_cluster_module", 
    "k8s_cluster_class",
    "k8s_cluster_function",
    "k8s_cluster_factory",
    
    # Descriptive aliases
    "k8s_cluster_per_test",
    "k8s_cluster_per_class",
    "k8s_cluster_per_module",
    "k8s_cluster_per_session",
    
    # Manager class
    "ClusterFixtureManager",
]
