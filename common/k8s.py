from kubernetes import client, config
import os
import re
import requests
import urllib3
from typing import Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_k8s_config() -> None:
    """
    Loads the Kubernetes configuration.

    Automatically detects if running inside a cluster (uses incluster config)
    or outside (uses local kubeconfig).

    Raises:
        RuntimeError: If the Kubernetes config cannot be loaded.
    """
    try:
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            config.load_incluster_config()
        else:
            config.load_kube_config()
    except Exception as e:
        raise RuntimeError(f"Could not load Kubernetes config: {e}")


load_k8s_config()  # einmal beim Import ausführen


def patch_pvc_size(namespace: str, pvc_name: str, new_size: str) -> None:
    """
    Changes the size of a PVC in the given namespace to the new size.

    Args:
        namespace (str): The Kubernetes namespace.
        pvc_name (str): The name of the PVC.
        new_size (str): The new size string, e.g. '500Mi', '2Gi'.
    """
    v1 = client.CoreV1Api()
    body = {
        "spec": {
            "resources": {
                "requests": {
                    "storage": new_size
                }
            }
        }
    }
    v1.patch_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace, body=body)


def parse_size(size_str: str) -> int:
    """
    Parses a size string like '500Mi' or '2Gi' into an integer in MiB.

    Args:
        size_str (str): The size string.

    Returns:
        int: The size in MiB.

    Raises:
        ValueError: If the size format is unsupported.
    """
    units = {
        'Mi': 1,
        'Gi': 1024,
        'Ti': 1024 * 1024,
        'M': 1,
        'G': 1024,
        'T': 1024 * 1024
    }
    match = re.match(r"^(\d+)([MGT]i?)$", size_str)
    if not match:
        raise ValueError(f"Unsupported size format: {size_str}")
    value, unit = match.groups()
    return int(value) * units[unit]


def get_pvc_size(namespace: str, pvc_name: str) -> str:
    """
    Reads the requested storage size of a PVC.

    Args:
        namespace (str): The Kubernetes namespace.
        pvc_name (str): The name of the PVC.

    Returns:
        str: The size string like '500Mi', '2Gi'.
    """
    v1 = client.CoreV1Api()
    pvc = v1.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)
    return pvc.spec.resources.requests['storage']


def format_size(mib: int) -> str:
    """
    Formats a size in MiB into a human-readable string like '500Mi', '2Gi', etc.

    Args:
        mib (int): The size in MiB.

    Returns:
        str: The formatted size string.
    """
    if mib % (1024 * 1024) == 0:
        return f"{mib // (1024 * 1024)}Ti"
    elif mib % 1024 == 0:
        return f"{mib // 1024}Gi"
    else:
        return f"{mib}Mi"


def compute_new_size(current: str, step: str) -> str:
    """
    Computes a new size by adding the step size to the current size.

    Args:
        current (str): The current size string, e.g. '500Mi'.
        step (str): The step to add, e.g. '100Mi'.

    Returns:
        str: The resulting size string.
    """
    cur_mib = parse_size(current)
    step_mib = parse_size(step)
    return format_size(cur_mib + step_mib)


def is_smaller_or_equal(a: str, b: str) -> bool:
    """
    Checks if size 'a' is smaller than or equal to size 'b'.

    Args:
        a (str): Size string like '500Mi'.
        b (str): Size string like '1Gi'.

    Returns:
        bool: True if 'a' <= 'b', else False.
    """
    return parse_size(a) <= parse_size(b)


def get_serviceaccount_token() -> str:
    """
    Reads the Kubernetes service account token from the mounted file in the pod.

    Returns:
        str: The service account token.
    """
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token", 'r') as f:
        return f.read().strip()


def get_kubelet_metrics(node_name: str, token: str) -> str:
    """
    Fetches kubelet metrics from the specified node.

    Args:
        node_name (str): The name of the node.
        token (str): The bearer token for authentication.

    Returns:
        str: The metrics text.

    Raises:
        requests.HTTPError: If the HTTP request fails.
    """
    kube_host = os.getenv("KUBERNETES_SERVICE_HOST")
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://{kube_host}/api/v1/nodes/{node_name}/proxy/metrics"
    resp = requests.get(url, headers=headers, verify=False, timeout=5)
    resp.raise_for_status()
    return resp.text


def parse_pvc_usage(metrics_text: str) -> list[dict[str, Any]]:
    """
    Parses the kubelet metrics text to extract PVC usage information.

    Args:
        metrics_text (str): The raw metrics text.

    Returns:
        list[dict[str, Any]]: A list of dicts with namespace, pvc, and usage_percent.
    """
    usages = []
    pvc_usages = {}
    for line in metrics_text.splitlines():
        if "persistentvolumeclaim=" in line:
            parts = line.split()
            metric = parts[0]
            value = float(parts[-1])
            ns = get_label_value(line, "namespace")
            pvc = get_label_value(line, "persistentvolumeclaim")
            key = f"{ns}/{pvc}"

            if key not in pvc_usages:
                pvc_usages[key] = {}

            if metric.startswith("kubelet_volume_stats_used_bytes"):
                pvc_usages[key]["used"] = value
            elif metric.startswith("kubelet_volume_stats_capacity_bytes"):
                pvc_usages[key]["capacity"] = value

    for key, data in pvc_usages.items():
        if "used" in data and "capacity" in data:
            usages.append({
                "namespace": key.split("/")[0],
                "pvc": key.split("/")[1],
                "usage_percent": data["used"] / data["capacity"] * 100
            })
    return usages


def get_label_value(line: str, label: str) -> str | None:
    """
    Extracts the value of a specific label from a metrics line.

    Args:
        line (str): The metrics line.
        label (str): The label to extract.

    Returns:
        str | None: The value of the label, or None if not found.
    """
    start = line.find(f'{label}="')
    if start == -1:
        return None
    start += len(label) + 2
    end = line.find('"', start)
    return line[start:end]


def fetch_all_pvc_usages_from_cluster() -> list[dict[str, Any]]:
    """
    Fetches PVC usage metrics from all nodes in the cluster.

    Returns:
        list[dict[str, Any]]: A list of PVC usage data across the cluster.
    """
    token = get_serviceaccount_token()
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    all_usages = []

    for node in nodes:
        try:
            metrics = get_kubelet_metrics(node.metadata.name, token)
            usages = parse_pvc_usage(metrics)
            all_usages.extend(usages)
        except Exception as e:
            print(f"❌ Failed to scrape node {node.metadata.name}: {e}")

    return all_usages
