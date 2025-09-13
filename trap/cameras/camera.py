from abc import ABC, abstractmethod

from trap.websocket.protocol_component import ProtocolComponent


class Camera(ProtocolComponent) :
    def __init__(self, channels, websocket):
        super().__init__(channels)
        self.websocket = websocket
        self.picam2 = None

    @abstractmethod
    async def run_tasks(self):
        pass

    @abstractmethod
    def setup(self, picam2, camera_config) :
        pass

    @abstractmethod
    async def websocket_listener_task(self):
        pass


    @abstractmethod
    def control_camera(self) :
        pass

    @abstractmethod
    def process_frame(self, metadata, frame):
        pass
