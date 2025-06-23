from prometheus_api_client import PrometheusConnect
import os

prom = PrometheusConnect(url=os.getenv("PROM_URL", "http://localhost:9090"), disable_ssl=True)

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
