# controllers/handlers/pvc_autoscaler_from_annotation.py
import kopf
import kubernetes
from kubernetes.client import ApiException
from utils.k8s import resolve_min_size, is_smaller_or_equal, is_valid_quantity

# ---- Config ----
ANNOT_PREFIX = "volumania.io/autoscaler."
ANNOT_ENABLED = ANNOT_PREFIX + "enabled"
ANNOT_STEP    = ANNOT_PREFIX + "stepSize"
ANNOT_MAX     = ANNOT_PREFIX + "maxSize"
ANNOT_MIN     = ANNOT_PREFIX + "minSize"
ANNOT_QUERY   = ANNOT_PREFIX + "promQuery"

GROUP   = "scaling.volumania.io"
VERSION = "v1"
PLURAL  = "pvcautoscalers"
KIND    = "PVCAutoScaler"
FIELD_MANAGER = "volumania-annotation-controller"

def autoscaler_name(namespace: str, pvc_name: str) -> str:
    return f"autoscaler-{namespace}-{pvc_name}".lower()

def build_pvc_autoscaler_body(namespace: str, pvc_name: str, cfg: dict, name: str) -> dict:
    """Build the PVCAutoScaler custom resource body (CR spec)."""
    spec = {"pvcName": pvc_name, "namespace": namespace}
    spec.update({k: v for k, v in cfg.items() if v is not None})
    return {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": KIND,
        "metadata": {"name": name, "namespace": namespace},
        "spec": spec,
    }

def _warn(pvc_obj, logger, msg: str):
    try:
        kopf.event(pvc_obj, type="Warning", reason="AutoscalerConfigError", message=msg)
    finally:
        logger.error(msg)

def _build_cfg_from_annotations(pvc_obj, logger):
    meta = pvc_obj.get("metadata") or {}
    ns   = meta.get("namespace")
    pvc  = meta.get("name")
    ann  = meta.get("annotations") or {}

    if not ann or ann.get(ANNOT_ENABLED) != "true":
        return None

    step_size = (ann.get(ANNOT_STEP) or "").strip()
    if not step_size:
        _warn(pvc_obj, logger, f"'{ANNOT_STEP}' is required and missing/empty.")
        return "ERROR"

    max_size = (ann.get(ANNOT_MAX) or "").strip()
    if not max_size:
        _warn(pvc_obj, logger, f"'{ANNOT_MAX}' is required and missing/empty.")
        return "ERROR"

    min_size = resolve_min_size(ns, pvc, ann.get(ANNOT_MIN))
    if not min_size:
        _warn(pvc_obj, logger, "PVC size could not be determined for minSize.")
        return "ERROR"

    if not is_valid_quantity(step_size):
        _warn(pvc_obj, logger, f"'{ANNOT_STEP}' has invalid format: '{step_size}'")
        return "ERROR"
    if not is_valid_quantity(max_size):
        _warn(pvc_obj, logger, f"'{ANNOT_MAX}' has invalid format: '{max_size}'")
        return "ERROR"
    if not is_valid_quantity(min_size):
        _warn(pvc_obj, logger, f"'{ANNOT_MIN}' has invalid format: '{min_size}'")
        return "ERROR"

    try:
        if not is_smaller_or_equal(min_size, max_size):
            _warn(pvc_obj, logger, f"'{ANNOT_MIN}' ({min_size}) must be ≤ '{ANNOT_MAX}' ({max_size}).")
            return "ERROR"
    except Exception as e:
        _warn(pvc_obj, logger, f"Size comparison failed: {e}")
        return "ERROR"

    cfg = {"stepSize": step_size, "maxSize": max_size, "minSize": min_size}
    prom = (ann.get(ANNOT_QUERY) or "").strip()
    if prom:
        cfg["metrics"] = {"promQuery": prom}
    return cfg

def apply_autoscaler_for_pvc(pvc_obj, logger):
    meta = pvc_obj.get("metadata") or {}
    ns   = meta.get("namespace")
    pvc  = meta.get("name")

    cfg = _build_cfg_from_annotations(pvc_obj, logger)
    name = autoscaler_name(ns, pvc)
    api = kubernetes.client.CustomObjectsApi()

    if cfg is None:
        try:
            api.delete_namespaced_custom_object(GROUP, VERSION, ns, PLURAL, name)
            logger.info(f"Deleted {KIND} {ns}/{name} (disabled)")
        except ApiException as e:
            if e.status != 404:
                raise
        return

    if cfg == "ERROR":
        return

    body = build_pvc_autoscaler_body(ns, pvc, cfg, name)

    try:
        api.patch_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=ns,
            plural=PLURAL,
            name=name,
            body=body,  
        )
        logger.info(f"Applied {KIND} {ns}/{name}")
    except ApiException as e:
        if e.status == 404:
            api.create_namespaced_custom_object(
                group=GROUP, version=VERSION, namespace=ns, plural=PLURAL, body=body
            )
            logger.info(f"Created {KIND} {ns}/{name}")
        else:
            raise


@kopf.on.event("", "v1", "persistentvolumeclaims")
def pvc_event(event, logger, **_):
    etype = event.get("type")
    obj   = event.get("object") or {}
    if etype in ("ADDED", "MODIFIED"):
        apply_autoscaler_for_pvc(obj, logger)
