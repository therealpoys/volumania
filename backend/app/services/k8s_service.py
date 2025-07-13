from common import k8s


def get_all_pvcs(token: str):
    """
    Uses the common functions to get all PVCs visible to this service account.
    """
    v1 = k8s.client.CoreV1Api()
    pvc_list = v1.list_persistent_volume_claim_for_all_namespaces()
    result = []
    for pvc in pvc_list.items:
        result.append({
            "namespace": pvc.metadata.namespace,
            "name": pvc.metadata.name,
            "size": pvc.spec.resources.requests['storage'],
            "status": pvc.status.phase
        })
    return result


def get_all_pvc_usages(token: str):
    """
    Uses the common logic to get PVC usage and merges with size info.
    """
    usages = k8s.fetch_all_pvc_usages_from_cluster()
    results = []
    for u in usages:
        size = k8s.get_pvc_size(u["namespace"], u["pvc"])
        used_gib = round(u["usage_percent"] * k8s.parse_size(size) / 100 / 1024, 1)
        results.append({
            "namespace": u["namespace"],
            "name": u["pvc"],
            "size": size,
            "used": f"{used_gib}Gi",
            "usage_percent": round(u["usage_percent"], 1)
        })
    return results


def manual_resize(token: str, namespace: str, pvc_name: str, new_size: str):
    """
    Calls the patch function to resize the PVC.
    """
    k8s.patch_pvc_size(namespace, pvc_name, new_size)
    return True


def list_autoscalers(token: str):
    api = k8s.client.CustomObjectsApi()
    all_autoscalers = []

    namespaces = [ns.metadata.name for ns in k8s.client.CoreV1Api().list_namespace().items]

    for ns in namespaces:
        items = api.list_namespaced_custom_object(
            group="scaling.volumania.io",
            version="v1",
            namespace=ns,
            plural="pvcautoscalers"
        ).get("items", [])

        for item in items:
            spec = item.get("spec", {})
            status = item.get("status", {})
            all_autoscalers.append({
                "name": item["metadata"]["name"],
                "namespace": ns,
                "pvcName": spec.get("pvcName"),
                "minSize": spec.get("minSize"),
                "maxSize": spec.get("maxSize"),
                "stepSize": spec.get("stepSize"),
                "triggerAbovePercent": spec.get("triggerAbovePercent"),
                "checkIntervalSeconds": spec.get("checkIntervalSeconds"),
                "cooldownSeconds": spec.get("cooldownSeconds"),
                "enabled": spec.get("enabled"),
                "currentSize": status.get("currentSize"),
                "lastScaleTime": status.get("lastScaleTime"),
                "reason": status.get("reason")
            })

    return all_autoscalers



def create_autoscaler(token: str, namespace: str, pvcName: str, stepSize: str,
                      maxSize: str, threshold: int, cooldown: int):
    """
    Creates a new pvcautoscaler CR.
    """
    api = k8s.client.CustomObjectsApi()
    body = {
        "apiVersion": "scaling.volumania.io/v1",
        "kind": "PVCAutoScaler",
        "metadata": {
            "name": f"{pvcName}-autoscaler"
        },
        "spec": {
            "pvcName": pvcName,
            "stepSize": stepSize,
            "maxSize": maxSize,
            "triggerAbovePercent": threshold,
            "cooldownSeconds": cooldown,
            "enabled": True
        }
    }

    created = api.create_namespaced_custom_object(
        group="scaling.volumania.io",
        version="v1",
        namespace=namespace,
        plural="pvcautoscalers",
        body=body
    )

    return {"status": "created", "name": created["metadata"]["name"]}


def update_autoscaler(token: str, name: str, namespace: str, stepSize: str,
                      maxSize: str, threshold: int, cooldown: int):
    """
    Patches an existing pvcautoscaler.
    """
    api = k8s.client.CustomObjectsApi()
    body = {
        "spec": {
            "stepSize": stepSize,
            "maxSize": maxSize,
            "triggerAbovePercent": threshold,
            "cooldownSeconds": cooldown
        }
    }

    updated = api.patch_namespaced_custom_object(
        group="scaling.volumania.io",
        version="v1",
        namespace=namespace,
        plural="pvcautoscalers",
        name=name,
        body=body
    )

    return {"status": "updated", "name": updated["metadata"]["name"]}


def delete_autoscaler(token: str, name: str, namespace: str):
    """
    Deletes a pvcautoscaler CR.
    """
    api = k8s.client.CustomObjectsApi()
    api.delete_namespaced_custom_object(
        group="scaling.volumania.io",
        version="v1",
        namespace=namespace,
        plural="pvcautoscalers",
        name=name
    )
    return {"status": "deleted", "name": name}
