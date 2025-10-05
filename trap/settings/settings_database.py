import asyncio
import json
import logging
import os
from dataclasses import dataclass

from fsspec.utils import atomic_write
from strong_typing.serialization import object_to_json, json_to_object

from trap.websocket.protobuf_message import ProtobufMsg
from trap.settings.proto import settings_pb2
from trap.websocket.protocol_component import ProtocolComponent

SETTINGS_DATABASE = "configuration/settings.db"

@dataclass
class Settings :
    trap_name : str
    max_sessions : int
    min_score : float

    @staticmethod
    def from_proto(proto):
        s = settings_pb2.Settings()
        s.ParseFromString(proto)
        return Settings(
            s.trap_name,
            s.max_sessions,
            s.min_score
        )
    def to_proto(self):
        s = settings_pb2.Settings()
        s.trap_name = self.trap_name
        s.max_sessions = self.max_sessions
        s.min_score = self.min_score
        return s.SerializeToString()


class SettingsDatabase(ProtocolComponent) :

    def __init__(self, config, channels, websocket ):
        super().__init__(channels)
        self.logger = logging.getLogger(name=__name__)

        self.path = f"{config.settings_path}/settings.db"
        self.websocket = websocket

        self.on_changed = None
        self.settings = self.read_settings()
        if self.settings is None:
            self.settings = Settings("", 5, 0.75)
            self.write_settings(self.settings)

    async def run_settings_task(self):
        self.logger.debug("Starting settings database task....")

        await asyncio.gather(self.websocket_listener_task())

    # ==========================================================================================
    # Handle requests received from the app. There are two request types:
    #  - get.settings : Return the settings object
    #  - set.settings : Set the settings onject
    # ==========================================================================================
    async def websocket_listener_task(self):
        in_channel = self.websocket.subscribe_many_messages("settings.get","settings.set")
        await in_channel.subscribe(self.handle_message)

    async def handle_message(self, message: ProtobufMsg):
        if message.identifier == "settings.get":
            settings_proto = self.settings.to_proto()
            await self.protocol_out_channel.publish(ProtobufMsg("settings", settings_proto))

        elif message.identifier == "settings.set":
            self.settings = Settings.from_proto(message.protobuf)
            self.write_settings(self.settings)
            settings_proto = self.settings.to_proto()
            await self.protocol_out_channel.publish(ProtobufMsg("settings", settings_proto))

    def write_settings(self, settings):
        with atomic_write(self.path, "w") as f:
            f.write(json.dumps(object_to_json(settings)))
            if self.on_changed is not None:
                self.on_changed(settings)

    def read_settings(self) :
        try :
            with os.open(self.path, os.O_RDONLY) as f :
                json_str = os.read(f, os.path.getsize(self.path)).decode("utf-8")
                return json_to_object(Settings, json.loads(json_str))
        except Exception as e:
            return None







