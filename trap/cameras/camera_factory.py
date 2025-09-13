from trap.cameras.picam3.camera_picam3 import CameraPicam3


class CameraFactory():

    @staticmethod
    def instantiate_camera(name, channels, websocket):
        if name is "picamera3" :
            return CameraPicam3(channels, websocket)
        return None
