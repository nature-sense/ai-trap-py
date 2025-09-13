from abc import ABC
import logging

from trap.websocket.protobuf_message import ProtobufMsg

class ProtocolComponent(ABC) :
    def __init__(self, channels) :
        self.logger = logging.getLogger(__name__)

        self.channels = channels
        self.protocol_in_channel = channels.get_channel(__class__.__name__)
        self.protocol_out_channel = channels.get_channel('publish_message')


    async def publish_proto(self, identifier, msg):
        logging.debug(f"publish_proto: {identifier}")
        msg = ProtobufMsg(identifier, msg.SerializeToString())
        await self.protocol_out_channel.publish(msg)