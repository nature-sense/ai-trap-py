import logging

from trap.cameras.ahqcam.proto import ahqcam_pb2
from trap.cameras.camera import Camera

class CameraAhq(Camera) :

    def __init__(self, channels, websocket):
        super().__init__(channels, websocket)
        self.logger = logging.getLogger(name=__name__)

    async def run_tasks(self):
        pass

    def control_camera(self):
        pass

    async def websocket_listener_task(self):
        pass

    def setup(self, picam2, camera_config):
        pass

    async def process_frame(self, metadata, frame):
        self.logger.debug(metadata)

        msg = ahqcam_pb2.Frame()
        msg.frame = frame
        await self.publish_proto("ahqcam.frame", msg)



