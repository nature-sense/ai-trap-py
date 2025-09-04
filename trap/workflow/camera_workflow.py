import logging
import time
import asyncio
from queue import Queue

import cv2
import numpy as np

from datetime import datetime

from picamera2 import CompletedRequest, Picamera2, MappedArray
from ultralytics import YOLO
from trap.sessions_cache.detection_metadata import DetectionMetadata
from trap.sessions_cache.detection_metadata_with_image import DetectionMetaDataWithImage

NCNN_MODEL = "./models/insects_320_ncnn_model"
MAIN_SIZE = (2028, 1520)
LORES_SIZE = (320, 320)



class CameraWorkflow():
    name = ""

    def __init__(self,app):
        self.settings = app.settings
        self.channels = app.channels
        self.streaming_queue = self.channels.get_queue("streaming_queue")
        self.command_queue = Queue()
        self.camera = camera
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

    async def set_detection_state(self, state):
        logging.debug(f"set_detection_state - {state}")
        self.detection_state = state
        await self.channels.get_channel("detection_state_channel").asend(state)

    async def get_detection_state(self):
        await self.channels.get_channel("detection_state_channel").asend(self.detection_state)

    async def set_preview_state(self, state):
        logging.debug(f"set_preview_state - {state}")
        self.preview_state = state
        await self.channels.get_channel("preview_state_channel").asend(state)

    async def get_preview_state(self):
        await self.channels.get_channel("preview_state_channel").asend(self.preview_state)

    def do_track(self, array):
        start_model = time.perf_counter()
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

    async def run_workflow_task(self):
        logging.debug("Starting cameras workflow task...")
        while True:
            await self.process_image()

    async def process_image(self):

        await self.camera.control_camera()

        request = await self.get_image()
        metadata = request.get_metadata()
        await self.camera.process_metadata(metadata)

        with MappedArray(request, 'lores') as l:
            with MappedArray(request, 'main') as m:
                if self.detection_state:

                    # run the tracking in a thread
                    results = await self.loop.run_in_executor(None, self.do_track, l.array)
                    if self.preview_state :
                        img = results[0].orig_img
                        for box in results[0].boxes.xyxy:  # xyxy format: [x1, y1, x2, y2]
                            x1, y1, x2, y2 = map(int, box)  # Convert coordinates to integers
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Green color, 2px thick
                        jpeg = self.to_jpeg(img)
                        logging.debug("STREAMING FRAME WITH BOXES")
                        await self.streaming_queue.put(jpeg)

                    try:
                        boxes = results[0].boxes.xyxy.cpu().numpy().astype(np.int32)
                        track_ids = [tid.item() for tid in results[0].boxes.id.int().cpu().numpy()]
                        scores = [s.item() for s in results[0].boxes.conf.numpy()]
                        classes = [c.item() for c in results[0].boxes.cls.numpy().astype(np.int32)]

                        await self.save_detections(m, zip(boxes, track_ids, scores, classes))
                    except AttributeError:
                        logging.debug("NO DATA")
                        await asyncio.sleep(0.1)
                else :
                    if self.current_session is not None:
                        await self.channels.get_channel("session_channel").asend(
                            SessionState(state=False, session=self.current_session))
                        self.current_session = None

                    if self.preview_state:
                        jpeg = self.to_jpeg(l.array)
                        logging.debug("STREAMING FRAME")
                        await self.streaming_queue.put(jpeg)

        logging.debug("RELEASE REQUEST")
        request.release()

    async def save_detections(self, frame, detections):
        if self.current_session is None:
            now = datetime.now()
            self.current_session = now.strftime("%Y%m%d%H%M%S")
            await self.channels.get_channel("session_channel").asend(SessionState(state=True, session=self.current_session))

        for box, track_id, score, clazz in detections:
            min_score = self.settings.get_settings().min_score
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

                await self.channels.get_channel("detection_channel").asend(DetectionMetaDataWithImage(metadata, image))

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
