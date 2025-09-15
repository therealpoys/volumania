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

import kopf
import kubernetes
from kubernetes.client import ApiException
from utils.k8s import resolve_min_size, is_smaller_or_equal, is_valid_quantity

# ---- Annotation keys ----
ANNOT_PREFIX = "volumania.io/autoscaler."
ANNOT_ENABLED = ANNOT_PREFIX + "enabled"
ANNOT_STEP    = ANNOT_PREFIX + "stepSize"
ANNOT_MAX     = ANNOT_PREFIX + "maxSize"
ANNOT_MIN     = ANNOT_PREFIX + "minSize"
ANNOT_QUERY   = ANNOT_PREFIX + "promQuery"

# ---- CRD config ----
GROUP   = "scaling.volumania.io"
VERSION = "v1"
PLURAL  = "pvcautoscalers"
KIND    = "PVCAutoScaler"
FIELD_MANAGER = "volumania-annotation-controller"


def autoscaler_name(namespace: str, pvc_name: str) -> str:
    """
    Generate a deterministic PVCAutoScaler name for a PVC.

    Args:
        namespace (str): The namespace where the PVC resides.
        pvc_name (str): The name of the PVC.

    Returns:
        str: Lowercased deterministic PVCAutoScaler resource name.
    """
    return f"autoscaler-{namespace}-{pvc_name}".lower()


def build_pvc_autoscaler_body(namespace: str, pvc_name: str, cfg: dict, name: str) -> dict:
    """
    Build the PVCAutoScaler custom resource body (CR spec).

    Args:
        namespace (str): Namespace of the PVC and PVCAutoScaler.
        pvc_name (str): Name of the PVC.
        cfg (dict): Validated autoscaler configuration.
        name (str): Name of the PVCAutoScaler resource.

    Returns:
        dict: A dictionary representing the PVCAutoScaler manifest.
    """
    spec = {"pvcName": pvc_name, "namespace": namespace}
    spec.update({k: v for k, v in cfg.items() if v is not None})
    return {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": KIND,
        "metadata": {"name": name, "namespace": namespace},
        "spec": spec,
    }


def _warn(pvc_obj, logger, msg: str):
    """
    Emit a Kubernetes warning event and log an error message.

    Args:
        pvc_obj (dict): The PVC object where the event should be attached.
        logger (kopf.Logger): Kopf logger instance.
        msg (str): Warning/error message to log and attach as an event.
    """
    try:
        kopf.event(pvc_obj, type="Warning", reason="AutoscalerConfigError", message=msg)
    finally:
        logger.error(f"[PVC-Autoscaling]{msg}")


def _build_cfg_from_annotations(pvc_obj, logger):
    """
    Extract and validate autoscaler configuration from PVC annotations.

    Args:
        pvc_obj (dict): The PVC object with metadata and annotations.
        logger (kopf.Logger): Kopf logger instance.

    Returns:
        dict | str | None:
            - dict: Valid configuration with stepSize, maxSize, minSize, and optional metrics.
            - "ERROR": If annotations are invalid or missing required fields.
            - None: If autoscaler is disabled.
    """
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
    """
    Create, patch, or delete a PVCAutoScaler CR for a given PVC
    based on its autoscaler annotations.

    Args:
        pvc_obj (dict): The PVC object including metadata and annotations.
        logger (kopf.Logger): Kopf logger instance.
    """
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
    """
    Kopf event handler for PVCs.
    Reacts to creation and modification events to reconcile PVCAutoScaler resources.

    Args:
        event (dict): Kubernetes event containing the PVC object.
        logger (kopf.Logger): Kopf logger instance.
        **_: Additional args provided by Kopf (ignored).
    """
    etype = event.get("type")
    obj   = event.get("object") or {}
    if etype in ("ADDED", "MODIFIED"):
        apply_autoscaler_for_pvc(obj, logger)