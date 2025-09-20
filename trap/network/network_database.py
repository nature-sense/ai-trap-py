import json
import os
from dataclasses import dataclass

from fsspec.utils import atomic_write
from strong_typing.serialization import json_to_object
from strong_typing.serializer import object_to_json


@dataclass
class NetworkSettings :
    hotspot_name : str
    hotspot_ssid : str
    hotspot_uuid : str
    network_name : str
    network_ssid : str
    network_uuid : str

class NetworkDatabase :
    def __init__(self, config) :
        self.config = config
        self.path = f"{config.settings_path}/network.db"
        self.trap_name = config.node_name.lower()
        self.settings = self.read_settings()

    def write_settings(self, settings):
        with atomic_write(self.path, "w") as f:
            f.write(json.dumps(object_to_json(settings)))
            #if self.on_changed is not None:
            #    self.on_changed(settings)

    def read_settings(self) :
        try :
            with os.open(self.path, os.O_RDONLY) as f :
                json_str = os.read(f, os.path.getsize(self.path)).decode("utf-8")
                return json_to_object(NetworkSettings, json.loads(json_str))
        except Exception as e:
            return None

