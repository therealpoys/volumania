from kubernetes import client, config
import os

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
