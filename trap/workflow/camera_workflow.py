import logging
import time
import asyncio
from queue import Queue

import cv2
import numpy as np

from datetime import datetime
import picamera2
from picamera2 import CompletedRequest, Picamera2, MappedArray
from ultralytics import YOLO

from trap.cameras.camera_factory import CameraFactory
from trap.sessions.detection_metadata import DetectionMetadata
from trap.sessions.detection_metadata_with_image import DetectionMetaDataWithImage
from trap.sessions.sessions_cache import SessionState
from trap.websocket.protocol_component import ProtocolComponent
from trap.workflow.proto import control_pb2

NCNN_MODEL = "./models/insects_320_ncnn_model"
MAIN_SIZE = (2028, 1520)
LORES_SIZE = (320, 320)



class CameraWorkflow(ProtocolComponent):
    name = ""

    def __init__(self, configuration, channels, settings, websocket):
        super().__init__(channels)

        self.logger = logging.getLogger(__name__)

        self.configuration = configuration
        self.settings = settings
        self.websocket = websocket
        self.camera = CameraFactory().instantiate_camera(
                name=configuration.camera_type,
                channels=channels,
                websocket=websocket
        )
        #self.streaming_queue = self.channels.get_queue("streaming_queue")
        self.connection_state = self.channels.get_channel("connection_state")

        self.command_queue = Queue()

        self.model = YOLO(NCNN_MODEL, task="detect")

        self.current_session = None
        self.min_score = 0

        self.picam2 = None
        self.loop = asyncio.get_running_loop()
        self.preview_state = False
        self.detection_state = False

        self.picam2 = Picamera2()

        camera_config = self.picam2.create_preview_configuration(
            main={'format': 'RGB888', 'size': MAIN_SIZE},
            lores={'format': 'RGB888', 'size': LORES_SIZE}
        )
        self.camera.setup(self.picam2, camera_config)

    async def run_workflow_task(self) :
        self.logger.debug("Starting workflow task....")
        await asyncio.gather(
            self.websocket_listener_task(),
            self.connection_state_listener_task(),
            self.workflow_task(),
            self.camera.run_tasks()
        )

    async def websocket_listener_task(self):
        in_channel = self.websocket.subscribe_many_messages(
            "camera.get",
            "detection.state.get",
            "detection.state.set",
            "preview.state.get",
            "preview.state.set"
        )
        await in_channel.subscribe(self.handle_message)

    async def connection_state_listener_task(self):
        await self.connection_state.subscribe(self.handle_state)

    async def handle_state(self, state):
        self.logger.debug(f"Received connection state {state}")
        if state == False and self.preview_state == True :
            logging.debug("No connection, turning off preview")
            self.preview_state = state

    async def handle_message(self, message):
        self.logger.debug(f"WORKFLOW Received message {message.identifier}")
        if message.identifier == "camera.get":
            try:
                msg = control_pb2.CameraType()
                msg.type = self.configuration.camera_type
                await self.publish_proto("camera", msg)
            except Exception as ex :
                x=1;

        elif message.identifier == "detection.state.get":

            state_msg = control_pb2.StateWithSession()
            state_msg.state = self.detection_state
            if self.current_session is not None :
                state_msg.session = self.current_session
            await self.publish_proto("detection.state", state_msg)


        elif message.identifier == "detection.state.set":
            msg = control_pb2.State()
            msg.ParseFromString(message.protobuf)
            if msg.state:
                now = datetime.now()
                self.current_session = now.strftime("%Y%m%d%H%M%S")
                await self.channels.get_channel("session_channel").publish(
                    SessionState(state=True, session=self.current_session))
                state_msg = control_pb2.StateWithSession()
                state_msg.state =True
                state_msg.session = self.current_session
                await self.publish_proto("detection.state", state_msg)
                self.detection_state = True
            else :
                self.detection_state = False
                self.current_session = None
                state_msg = control_pb2.StateWithSession()
                state_msg.state = False
                await self.publish_proto("detection.state", state_msg)


        elif message.identifier == "preview.state.get":
            msg = control_pb2.State()
            msg.state = self.preview_state
            await self.publish_proto("preview.state", msg)

        elif message.identifier == "preview.state.set":
            msg = control_pb2.State()
            msg.ParseFromString(message.protobuf)
            self.preview_state = msg.state
            await self.publish_proto("preview.state", msg)



    def do_track(self, array):
        start_model = time.perf_counter()
        #results = self.model.track(array, persist=True, conf=0.1, tracker='bytetrack.yaml')
        results = self.model.track(array)
        end_model = time.perf_counter()
        print("model = ", (end_model - start_model) * 1000)
        return results

    async def get_image(self) -> CompletedRequest:
        logging.debug("Get image")
        future = self.loop.create_future()

        def job_done_callback(job: "picamera2.job.Job"):
            try:
                result = job.get_result()
            except Exception as e:
                self.loop.call_soon_threadsafe(future.set_exception, e)
            else:
                self.loop.call_soon_threadsafe(future.set_result, result)

        self.camera.picam2.capture_request(signal_function=job_done_callback)
        return await future

    async def close_camera(self):
        self.picam2.stop()
        self.picam2.close()

    async def workflow_task(self):
        logging.debug("Starting cameras workflow task...")
        while True:
          await self.process_image()

    async def process_image(self):

        await self.camera.control_camera()

        request = await self.get_image()
        metadata = request.get_metadata()

        with MappedArray(request, 'lores') as l:
            with MappedArray(request, 'main') as m:

                min_score = self.settings.settings.min_score

                if self.detection_state:

                    # run the tracking in a thread
                    results = await self.loop.run_in_executor(None, self.do_track, l.array)

                    try :
                        if results[0].boxes is not None :
                            img = results[0].orig_img

                            boxes = results[0].boxes.xyxy.cpu().numpy().astype(np.int32)
                            track_ids = [tid.item() for tid in results[0].boxes.id.int().cpu().numpy()]
                            scores = [s.item() for s in results[0].boxes.conf.numpy()]
                            classes = [c.item() for c in results[0].boxes.cls.numpy().astype(np.int32)]
                            detections = list(zip(boxes, track_ids, scores, classes))

                            if self.preview_state :
                                for box, track_id, score, clazz in detections :
                                    x1, y1, x2, y2 = map(int, box)  # Convert coordinates to integers
                                    if score > min_score :
                                        cv2.rectangle(img, (x1, y1), (x2, y2),  (24, 130, 24), 2)  # high score
                                        cv2.putText(img, f"{track_id}/{score:.2f}", (x1, y1 -5),
                                                         cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
                                    else :
                                        cv2.rectangle(img, (x1, y1), (x2, y2),  (84, 84, 84), 1)  # low score
                                        cv2.putText(img, f"{track_id}/{score:.2f}", (x1, y1 - 5),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
                                jpeg = self.to_jpeg(img)
                                logging.debug("STREAMING FRAME WITH BOXES")
                                await self.camera.process_frame(metadata, jpeg)

                            await self.save_detections(m, detections, min_score)
                    except Exception as e :
                        logging.warn(f"Discarding results on error {e}")

                else :
                    # close the open session
                    if self.current_session is not None:
                        await self.channels.get_channel("session_channel").publish(
                            SessionState(state=False, session=self.current_session))
                        self.current_session = None

                    if self.preview_state:
                        jpeg = self.to_jpeg(l.array)
                        logging.debug("STREAMING FRAME")
                        await self.camera.process_frame(metadata, jpeg)

        logging.debug("RELEASE REQUEST")
        request.release()

    async def save_detections(self, frame, detections, min_score):
        try :
            #if self.current_session is None:
            #    now = datetime.now()
            #    self.current_session = now.strftime("%Y%m%d%H%M%S")
            #    await self.channels.get_channel("session_channel").publish(SessionState(state=True, session=self.current_session))

            for box, track_id, score, clazz in detections:
                logging.debug(f"score = {score} min-score = {min_score}")

                if score >= min_score:
                    scaled_box = self.scale(box)
                    logging.debug(f"scaled-box {scaled_box}")
                    x0, y0, x1, y1 = scaled_box
                    img_width = x1 - x0
                    img_height = y1 - y0

                    current_datetime = datetime.now()
                    current_timestamp_ms = int(current_datetime.timestamp() * 1000)

                    metadata = DetectionMetadata(
                        session=self.current_session,
                        detection=track_id,
                        created=current_timestamp_ms,
                        updated=current_timestamp_ms,
                        score=score,
                        clazz=clazz,
                        width=img_width,
                        height=img_height
                    )

                    image = self.to_jpeg(frame.array[y0:y1, x0:x1])

                    await self.channels.get_channel("detection_channel").publish(DetectionMetaDataWithImage(metadata, image))
            x=0
        except Exception as e:
            logging.error(f"Failed to save detections {e}")

    def scale(self, rect):
        s_w, s_h = LORES_SIZE
        d_w, d_h = MAIN_SIZE
        x0, y0, x1, y1 = rect
        x_scale = d_w / s_w
        y_scale = d_h / s_h
        return int(x0 * x_scale), int(y0 * y_scale), int(x1 * x_scale), int(y1 * y_scale)

    def to_jpeg(self, img):
        is_success, im_buf = cv2.imencode(".jpg", img)
        if is_success:
            return im_buf.tobytes()
        else:
            logging.error("Failed to convert image to jpeg")
            return None
