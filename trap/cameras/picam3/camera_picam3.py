import asyncio
import logging
from asyncio import Lock
from enum import Enum

from libcamera import controls
from trap.cameras.camera import Camera
from bidict import bidict

from trap.cameras.picam3.proto import picam3_pb2

AUTOFOCUS_MODE = "autofocusMode"
MANUAL_FOCUS = "manualFocus"
TRIGGER_AUTOFOCUS = "triggerAutofocus"


class AutofocusMode(Enum):
    MANUAL = 0
    CONTINUOUS = 1,
    TRIGGERED = 2


class Picam3ControlModel :
    def __init__(self, mode, position):
        self.mode = mode
        self.position = position


class CameraPicam3(Camera) :
    def __init__(self, channels, websocket):
        super().__init__(channels, websocket)
        self.autofocus_mode = AutofocusMode.CONTINUOUS
        self.requested_focus_mode = None
        self.control_model = None
        self.command_queue = []
        self.lock = Lock()
        self.logger = logging.getLogger(name=__name__)

        self.modes = bidict({
            picam3_pb2.AutofocusMode.manual     : controls.AfModeEnum.Manual,
            picam3_pb2.AutofocusMode.continuous : controls.AfModeEnum.Continuous,
            picam3_pb2.AutofocusMode.triggered  : controls.AfModeEnum.Auto
        })

    async def run_tasks(self):
        await asyncio.gather(self.websocket_listener_task())

    def setup(self, picam2, camera_config) :
        self.picam2 = picam2
        self.picam2.start(camera_config)
        self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

    async def websocket_listener_task(self):
        self.websocket.subscribe_message("picam3.mode.set", self.protocol_in_channel)
        self.websocket.subscribe_message("picam3.position.set", self.protocol_in_channel)
        self.websocket.subscribe_message("picam3.focus.trigger", self.protocol_in_channel)
        await self.protocol_in_channel.subscribe(self.handle_message)

    async def handle_message(self, message):
        if message.identifier == "picam3.mode.set":
            msg = picam3_pb2.SetMode()
            msg.ParseFromString(message.protobuf)
            af_mode = self.modes[msg.mode]
            async with self.lock:
                self.command_queue.append((AUTOFOCUS_MODE, af_mode))

        elif message.identifier == "picam3.position.set":
            msg = picam3_pb2.SetPosition()
            msg.ParseFromString(message.protobuf)
            self.logger.debug(f"POSITION {msg.position}")
            async with self.lock:
                self.command_queue.append((MANUAL_FOCUS, msg.position))

        elif message.identifier == "picam3.focus.trigger":
            async with self.lock:
                self.command_queue.append((TRIGGER_AUTOFOCUS, None))

    # =====================================================================
    # control_camera()
    # apply autofocus mode or lens position changes
    # called from within the main camera loop
    # =====================================================================
    async def control_camera(self):
        async with self.lock :
            self.logger.debug(f"Control camera {len(self.command_queue)} commands")
            for cmd in self.command_queue :
                self.logger.debug(f"FOUND COMMAND {cmd[0]} {cmd[1]}")
                if cmd[0] == AUTOFOCUS_MODE:
                    control_mode = cmd[1]
                    self.logger.debug(f"control mode = {control_mode}")
                    self.picam2.set_controls({"AfMode": control_mode})

                elif cmd[0] == MANUAL_FOCUS:
                    position = cmd[1]
                    self.logger.debug(f"Lens position = {position}")
                    self.picam2.set_controls({"LensPosition": position})

                elif cmd[0] == TRIGGER_AUTOFOCUS:
                    self.picam2.autofocus_cycle(wait=False)

            self.command_queue.clear()

    async def process_frame(self, metadata, frame):
        self.logger.debug(metadata)

        af_state = metadata["AfState"]
        lens_position = metadata["LensPosition"]

        msg = picam3_pb2.Frame()
        metadata = picam3_pb2.FrameMetadata()
        metadata.mode = self.modes.inverse[af_state]
        metadata.position = lens_position
        msg.metadata.CopyFrom(metadata)
        msg.frame = frame
        await self.publish_proto("picam3.frame", msg)
