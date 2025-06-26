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

