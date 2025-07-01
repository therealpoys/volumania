# Copyright 2025 Volumania
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from kubernetes import client, config
import os
import re
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def load_k8s_config():
    try:
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            config.load_incluster_config()
        else:
            config.load_kube_config()
    except Exception as e:
        raise RuntimeError(f"Could not load Kubernetes config: {e}")

load_k8s_config()  # einmal beim Import ausführen


def patch_pvc_size(namespace: str, pvc_name: str, new_size: str):
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
    """Parst eine K8s-Size-Angabe wie '500Mi', '2Gi' in MiB"""
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
    """Liest die aktuelle angeforderte PVC-Größe aus dem Cluster (z. B. '1Gi', '500Mi')."""
    v1 = client.CoreV1Api()
    pvc = v1.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)
    return pvc.spec.resources.requests['storage']

def format_size(mib: int) -> str:
    """Formatiert MiB wieder als z. B. '5Gi'"""
    if mib % (1024 * 1024) == 0:
        return f"{mib // (1024 * 1024)}Ti"
    elif mib % 1024 == 0:
        return f"{mib // 1024}Gi"
    else:
        return f"{mib}Mi"

def compute_new_size(current: str, step: str) -> str:
    cur_mib = parse_size(current)
    step_mib = parse_size(step)
    return format_size(cur_mib + step_mib)

def is_smaller_or_equal(a: str, b: str) -> bool:
    return parse_size(a) <= parse_size(b)


def get_serviceaccount_token():
    with open("/var/run/secrets/kubernetes.io/serviceaccount/token", 'r') as f:
        return f.read().strip()

def get_kubelet_metrics(node_name, token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://kubernetes.default.svc/api/v1/nodes/{node_name}/proxy/metrics"
    resp = requests.get(url, headers=headers, verify=False, timeout=5)
    resp.raise_for_status()
    return resp.text

def parse_pvc_usage(metrics_text):
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

def get_label_value(line, label):
    start = line.find(f'{label}="')
    if start == -1:
        return None
    start += len(label) + 2
    end = line.find('"', start)
    return line[start:end]

def fetch_all_pvc_usages_from_cluster():
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
