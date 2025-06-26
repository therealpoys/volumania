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
from handlers import manual_resize, autoscaler
import logging

# Optional: Global init/logging hooks
@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.persistence.finalizer = 'volumania.scaling/finalizer'
    settings.posting.level = logging.INFO
    settings.watching.server_timeout = 60
    settings.watching.client_timeout = 90

    # Explicit cluster-wide mode to avoid warning
    settings.scanning.disabled = True
    settings.watching.clusterwide = True
