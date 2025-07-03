from kubernetes import client
from typing import List, Dict

def get_client_with_token(token: str) -> client.CoreV1Api:
    """
    Creates a Kubernetes CoreV1Api client using the provided Bearer token.

    Args:
        token (str): The Kubernetes Bearer token of the user.

    Returns:
        CoreV1Api: A configured CoreV1Api client.
    """
    configuration = client.Configuration()
    configuration.host = "https://kubernetes.default.svc"
    configuration.verify_ssl = False  # or set configuration.ssl_ca_cert
    configuration.api_key = {"authorization": f"Bearer {token}"}

    return client.CoreV1Api(client.ApiClient(configuration))


def get_user_pvcs(token: str) -> List[Dict]:
    """
    Lists all PVCs visible to the user represented by the token.

    Args:
        token (str): The user's Kubernetes token.

    Returns:
        List[Dict]: A list of PVC info dictionaries.
    """
    v1 = get_client_with_token(token)
    pvc_list = v1.list_persistent_volume_claim_for_all_namespaces()
    
    results = []
    for pvc in pvc_list.items:
        results.append({
            "namespace": pvc.metadata.namespace,
            "name": pvc.metadata.name,
            "storage": pvc.spec.resources.requests.get("storage"),
            "status": pvc.status.phase
        })
    return results


def patch_user_pvc_size(token: str, namespace: str, pvc_name: str, new_size: str) -> None:
    """
    Patches the requested storage size of a PVC.

    Args:
        token (str): The user's Kubernetes token.
        namespace (str): Namespace of the PVC.
        pvc_name (str): Name of the PVC.
        new_size (str): New storage size string like '2Gi'.
    """
    v1 = get_client_with_token(token)
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
