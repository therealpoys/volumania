import kopf
from handlers import manual_resize
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
