import asyncio
import json
import logging
import os

import cv2
import numpy as np
from strong_typing.serialization import json_to_object, object_to_json

from trap.sessions.proto import sessions_pb2
from trap.sessions.detection_metadata import DetectionMetadata
from trap.sessions.detection_metadata_with_image import DetectionMetaDataWithImage
from trap.websocket.protocol_component import ProtocolComponent


def session_to_proto(session):
    sess = sessions_pb2.Session()
    sess.session = session
    return sess

def session_from_proto(proto) -> str:
    sess = sessions_pb2.Session()
    sess.ParseFromString(proto)
    return sess.session

def session_details_to_proto(session, detections):
    proto = sessions_pb2.SessionDetails()
    proto.session = session
    proto.detections = detections
    return proto

class SessionState() :
    def __init__(self, state, session):
        self.state = state
        self.session = session

class SessionsCache(ProtocolComponent):
    def __init__(self, config, channels, settings, websocket):
        super().__init__(channels)
        self.logger = logging.getLogger(name=__name__)

        self.sessions_directory = config.sessions_path
        self.channels = channels
        self.settings = settings
        self.websocket = websocket

        self.sessions = {}
        self.current_session = None

        # initialise rhe cache asynchronously
        asyncio.create_task(self.init()) # run asynchronously

    # ------------------------------------------------------------------------------------------
    # Initialise the cache from the metadata files in the session directories
    # ------------------------------------------------------------------------------------------
    async def init(self):
        self.logger.debug("Rebuilding sessions cache....")
        sessions = sorted(os.listdir(self.sessions_directory))
        for session in sessions:
            self.logger.debug(f"Found {session}")
            await self._new_session(session)
            detections = self._get_detections_metadata_for_session(session)
            for detection in detections:
                self.logger.debug(f"detection image {detection.detection}")
                await self._init_detection(session, detection)


    async def run_cache_task(self):
        self.logger.debug("Starting sessions cache task....")

        await asyncio.gather(
            self.session_listener_task(),
            self.detection_listener_task(),
            self.websocket_listener_task()
        )

    # ==========================================================================================
    # Handle events received from the Camera Flow component via the following channels :
    #  - session_channel : Creation of sessions
    #  - detection_channel : Creation and updating of detection metadata
    # ==========================================================================================

    async def session_listener_task(self):
        async def handle_session(s) :
            await self.session(s)
        await self.channels.get_channel("session_channel").subscribe(handle_session)

    async def detection_listener_task(self):
        async def handle_detection(d):
            await self.detection(d)
        await self.channels.get_channel("detection_channel").subscribe(handle_detection)

    async def session(self, session_state) :
        # Create the directories and an entry in the cache
        if session_state.state is True :
            session = session_state.session
            self.current_session = session

            session_dir = f"{self.sessions_directory}/{session}"
            image_dir = f"{session_dir}/images"
            metadata_dir = f"{session_dir}/metadata"

            os.mkdir(session_dir)
            os.mkdir(image_dir)
            os.mkdir(metadata_dir)

            self.logger.debug("Created directories")

            await self._new_session(session)
            await self._clean_up_sessions()

    async def detection(self, detection) :
        metadata = detection.metadata
        image = detection.image

        session_dir = f"{self.sessions_directory}/{metadata.session}"
        metadata_file = str(f"{session_dir}/metadata/{metadata.detection}.json")
        image_file = str(f"{session_dir}/images/{metadata.detection}.jpg")

        meta = self._get_detection(metadata.session, metadata.detection)
        if meta is None:
            # If there is no existing detection, simply create the metadata
            # and image files and update the cache
            with open(metadata_file, 'w') as file:
                file.write(json.dumps(object_to_json(metadata)))
            with open(image_file, 'wb') as file:
                file.write(image)

            await self._new_detection(detection)
        else :

            # Otherwise the action will depend on whether this detection has a higher score
            # than the currently stored one
            meta.updated = metadata.updated #

            if metadata.score > meta.score :
                meta.score = metadata.score
                meta.width = metadata.width
                meta.height = metadata.height
                with open(image_file, 'wb') as file:
                    file.write(image)

            self._set_detection(self.current_session, meta)
            with open(metadata_file, 'w') as file:
                file.write(json.dumps(object_to_json(meta)))
            #await self._new_detection(detection)


    # ==========================================================================================
    # Handle requests received from the app. There are two request types:
    #  - sessions : Return the list of sessions
    #  - session.detections : Return the list of detections for a given session
    # ==========================================================================================

    async def websocket_listener_task(self):
        in_channel = self.websocket.subscribe_many_messages(
            "sessions",
            "session.detections"
        )
        await in_channel.subscribe(self.handle_message)


    async def handle_message(self, message):
        if message.identifier == "sessions":
            for sess in self._list_sessions() :
                await self.publish_proto("session.details", session_details_to_proto(sess[0], sess[1]))

        elif message.identifier == "session.detections":
            session = session_from_proto(message.protobuf)
            for det in self._get_detections_for_session(session) :
                await self.publish_proto("detection",DetectionMetaDataWithImage(det[0],det[1]).to_proto())

    def _list_sessions(self):
        return map(lambda session: (session, len(self.sessions[session])), sorted(self.sessions.keys()))

    def _get_detections_for_session(self, session):
        detections = []
        det_list = list(self.sessions.get(session).values())
        det_list.reverse()
        for det in det_list:
            img = self._get_image_data(session, det.detection)
            detections.append((det, img))
        return detections

    # ==========================================================================================
    #  Cache functions
    # ==========================================================================================
    async def _new_session(self, session) :
        self.sessions[session] = {}
        await self.publish_proto("session.new", session_to_proto(session))

    async def _delete_session(self, session) :
        del self.sessions[session]
        await self.publish_proto("session.delete", session_to_proto(session))

    async def _new_detection(self, meta_with_image) :
        metadata = meta_with_image.metadata
        session = metadata.session

        sess = self.sessions[session]
        if sess is not None :
            sess[metadata.detection] = metadata
            await self.publish_proto("detection", meta_with_image.to_proto())
            await self.publish_proto(
                "session.details",
                session_details_to_proto(
                    metadata.session,
                    len(self.sessions.get(session)
                    )
                )
            )

    async def _init_detection(self, session, detection_metadata) :
       sess = self.sessions.get(session)
       if sess is not None :
            sess[detection_metadata.detection] = detection_metadata

    def _count_detections(self, session) :
        return len(self.sessions.get(session))

    def _get_detection(self, session, detection):
        sess = self.sessions.get(session)
        if sess is not None :
            meta = sess.get(detection)
            if meta is not None :
                return meta
        return None

    def _set_detection(self, session, metadata) :
        sess = self.sessions.get(session)
        if sess is not None:
            sess[metadata.detection] = metadata


    async def _clean_up_sessions(self):
        settings = self.settings.settings
        max_sessions = settings.max_sessions
        session_files = os.listdir(self.sessions_directory)
        sessions = sorted(session_files)
        num_sessions = len(sessions)
        self.logger.debug(f"num sessions {num_sessions} max sessions {max_sessions}")
        if num_sessions >= max_sessions:
            #for idx in range(0, num_sessions-self.max_sessions+1):
            for idx in range(0, num_sessions - max_sessions):

                sess_path = f"{self.sessions_directory}/{sessions[idx]}"
                img_path = f"{sess_path}/images"
                self._delete_session_files(img_path)
                meta_path = f"{sess_path}/metadata"
                self._delete_session_files(meta_path)
                os.rmdir(sess_path)
                await self._delete_session(sessions[idx])

                #resp = SessionDeletedResponse(sessions[idx]).to_proto()
                #await self.websocket_server.send_response(resp)

    def _delete_session_files(self, dir_path):
        print(dir_path)
        if not os.path.exists(dir_path):
            self.logger.debug(f"Directory not found: {dir_path}")
            return

        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                self.logger.debug(f"Deleting file {file_path}")
                os.remove(file_path)
            except Exception as e:
                self.logger.debug(f"Error deleting {file_path}: {e}")
        os.rmdir(dir_path)

    def _get_detections_metadata_for_session(self, session) :
        metadata_list = []
        metadata_path = f"{self.sessions_directory}/{session}/metadata"
        files = sorted(os.listdir(metadata_path))
        for file in files:
            file_path = f"{metadata_path}/{file}"
            m_fd = os.open(file_path, os.O_RDONLY)
            try :
                json_str = os.read(m_fd, os.path.getsize(file_path)).decode("utf-8")
                metadata_list.append(json_to_object(DetectionMetadata, json.loads(json_str)))
            except Exception as e :
                self.logger.error(f"Error reading metadate file {file_path}: {e}")

        return metadata_list

    def _get_image_data(self, session, detection):
        image_path =   f"{self.sessions_directory}/{session}/images/{detection}.jpg"
        assert(os.path.exists(image_path))

        i_fd = os.open(image_path, os.O_RDONLY)
        img = os.read(i_fd, os.path.getsize(image_path))
        return img

