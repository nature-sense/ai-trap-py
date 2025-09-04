from abc import ABC

from trap.cameras.camera import Camera

class CameraAhq(Camera) :
    def __init__(self):
        super().__init__()

    def setup(self, picam2, camera_config) :
        self.picam2 = picam2
        self.picam2.start(camera_config)

    def set_autofocus_mode(self, autofocus_mode):
        pass
    def set_focus_distance(self, distance):
        pass
    async def trigger_focus(self):
        pass