from dataclasses import dataclass

from trap.sessions_cache import sessions_pb2
from trap.sessions_cache.detection_metadata import DetectionMetadata


@dataclass
class DetectionMetaDataWithImage :
    metadata : DetectionMetadata
    image : bytes

    def to_proto(self) :
        msg = sessions_pb2.DetectionMsg
        msg.session = self.metadata.session
        msg.detection = self.metadata.detection,
        msg.created = self.metadata.created,
        msg.updated = self.metadata.updated,
        msg.score = self.metadata.score,
        msg.clazz = self.metadata.clazz,
        msg.width = self.metadata.width,
        msg.height = self.metadata.height,
        msg.image = self.image