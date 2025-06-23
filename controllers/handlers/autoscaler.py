import kopf
import logging
import time
from utils.k8s import patch_pvc_size, get_pvc_size, compute_new_size, is_smaller_or_equal
from utils.prom import get_pvc_usage_percent

@kopf.timer('pvcautoscalers.scaling.volumania.io', interval=60.0)  # ersetzt checkIntervalSeconds
def autoscale_pvc(spec, status, namespace, name, logger, **kwargs):
    pvc_name = spec.get('pvcName')
    step_size = spec.get('stepSize')
    max_size = spec.get('maxSize')
    threshold = spec.get('triggerAbovePercent', 80)
    cooldown = spec.get('cooldownSeconds', 600)
    enabled = spec.get('enabled', True)

    if not enabled:
        logger.info(f"[AutoScaler] Skipped: autoscaling disabled for {pvc_name}.")
        return

    # Prevent rapid repeats
    last_scaled = status.get("lastScaleTime")
    if last_scaled:
        last_ts = time.strptime(last_scaled, "%Y-%m-%dT%H:%M:%SZ")
        now_ts = time.gmtime()
        if time.mktime(now_ts) - time.mktime(last_ts) < cooldown:
            logger.info(f"[AutoScaler] Cooldown in effect for {pvc_name}.")
            return

    usage = get_pvc_usage_percent(namespace, pvc_name)
    if usage is None:
        logger.warning(f"[AutoScaler] Could not determine usage for {pvc_name}.")
        return

    logger.info(f"[AutoScaler] PVC '{pvc_name}' usage is at {usage:.1f}%.")

    if usage < threshold:
        logger.info(f"[AutoScaler] No action needed.")
        return

    current_size = get_pvc_size(namespace, pvc_name)
    next_size = compute_new_size(current_size, step_size)

    if not is_smaller_or_equal(next_size, max_size):
        logger.info(f"[AutoScaler] Max size reached for {pvc_name}. No resize.")
        return

    patch_pvc_size(namespace, pvc_name, next_size)

    return {
        "lastScaleTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "currentSize": next_size,
        "reason": f"Resized after reaching {usage:.1f}% usage"
    }

