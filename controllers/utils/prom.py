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

from prometheus_api_client import PrometheusConnect
import os

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus.default.svc:9090")
prom = PrometheusConnect(url=os.getenv("PROM_URL", PROMETHEUS_URL), disable_ssl=True)

def get_pvc_usage_percent(namespace: str, pvc_name: str) -> float | None:
    try:
        query = f"""
        (kubelet_volume_stats_used_bytes{{persistentvolumeclaim="{pvc_name}", namespace="{namespace}"}} /
         kubelet_volume_stats_capacity_bytes{{persistentvolumeclaim="{pvc_name}", namespace="{namespace}"}}) * 100
        """
        result = prom.custom_query(query=query.strip())
        return float(result[0]["value"][1])
    except Exception:
        return None
