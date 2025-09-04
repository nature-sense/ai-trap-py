from abc import ABC, abstractmethod

from trap.websocket.websocket_service import ProtocolComponent


class Camera(ABC, ProtocolComponent) :
    def __init__(self):
        self.picam2 = None

    @abstractmethod
    def setup(self, picam2, camera_config) :
        pass

    @abstractmethod
    async def websocket_listener_task(self):
        pass

    @abstractmethod
    def handle_control_cmds(self, control_cmds) :
        pass

    @abstractmethod
    def control_camera(self) :
        pass

    @abstractmethod
    def process_metadata(self, metadata):
        pass
