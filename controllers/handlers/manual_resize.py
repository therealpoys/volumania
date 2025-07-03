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
from utils.k8s import patch_pvc_size

# Kopf handler that reacts to both "create" and "update" events
# for the custom resource pvcmanualresizes.scaling.volumania.io
@kopf.on.create('pvcmanualresizes.scaling.volumania.io')
@kopf.on.update('pvcmanualresizes.scaling.volumania.io')
def handle_manual_resize(spec, patch, namespace, logger, **kwargs):
    """
    Handles manual PVC resize requests.

    This handler is triggered whenever a pvcmanualresizes.scaling.volumania.io
    custom resource is created or updated. It reads the target PVC name
    and the new requested size from the spec, performs the resize,
    and updates the status field of the custom resource to reflect
    the outcome.

    Args:
        spec (dict): The spec section of the custom resource,
            expected to contain 'pvcName' and 'newSize'.
        patch (dict): The patch object to update the resource's status.
        namespace (str): The namespace where the custom resource lives.
        logger (kopf.Logger): Logger instance provided by Kopf for structured logging.
        **kwargs: Additional Kopf context parameters (ignored here).
    """
    # Extract target PVC name and the new desired size from the CR spec
    pvc_name = spec.get('pvcName')
    new_size = spec.get('newSize')
    
    logger.info(f"[ManualResize] Requested resize of PVC '{pvc_name}' to {new_size}.")

    try:
        # Perform the actual PVC resize operation
        patch_pvc_size(namespace, pvc_name, new_size)

        # Set the status to indicate success
        patch['status'] = {
            'applied': True,
            'message': f"PVC resized to {new_size}"
        }
    except Exception as e:
        # On error, update the status to indicate failure
        patch['status'] = {
            'applied': False,
            'message': str(e)
        }
        # Raise a TemporaryError to retry after a delay
        raise kopf.TemporaryError(f"Resize failed: {e}", delay=60)


