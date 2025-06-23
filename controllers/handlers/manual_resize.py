import kopf
from utils.k8s import patch_pvc_size

@kopf.on.create('pvcmanualresizes.scaling.volumania.io')
@kopf.on.update('pvcmanualresizes.scaling.volumania.io')
def handle_manual_resize(spec, patch, namespace, logger, **kwargs):
    pvc_name = spec.get('pvcName')
    new_size = spec.get('newSize')
    
    logger.info(f"[ManualResize] Requested resize of PVC '{pvc_name}' to {new_size}.")

    try:
        patch_pvc_size(namespace, pvc_name, new_size)

        # ✅ Set the status via patch object
        patch['status'] = {
            'applied': True,
            'message': f"PVC resized to {new_size}"
        }
    except Exception as e:
        patch['status'] = {
            'applied': False,
            'message': str(e)
        }
        raise kopf.TemporaryError(f"Resize failed: {e}", delay=60)

