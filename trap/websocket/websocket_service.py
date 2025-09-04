import asyncio
import logging
from abc import ABC

from aioreactive import AsyncAnonymousObserver
from websockets import ConnectionClosedOK
from websockets.asyncio.server import serve

from trap.websocket import protocol_pb2
from trap.websocket.protobuf_message import ProtobufMessage

class ProtocolComponent(ABC) :
    def __init__(self, channels) :
        self.channels = channels
        self.protocol_in_channel = channels.get_channel(__class__.__name__)
        self.protocol_out_channel = channels.get_channel('protocol_send')


    async def publish_proto(self, identifier, proto):
        msg = ProtobufMessage(identifier, proto)
        await self.protocol_out_channel.publish(msg)

class WebsocketServer :
    def __init__(self, config, channels ) :
        self.subscriptions = {}
        self.port = config.websocket_port
        self.channels = channels
        self.tasks = []
        self.websocket = None
        self.logger = logging.getLogger(__name__)

    async def run_websocket_task(self) :
        self.logger.debug("Starting websocket server task....")

        self.tasks = [
            asyncio.create_task(self.outgoing_task()),
        ]

        async with serve(self.handler, "", self.port) as server:
            await server.serve_forever()

    async def handler(self, websocket):
        self.websocket = websocket

        self.logger.debug(f"creating websocket task")
        incom_task = asyncio.create_task(self.incoming_task())
        await incom_task  # exits when socket gone
        self.websocket = None

    async def outgoing_task(self) :
        async def handle_message(m):
            pm = protocol_pb2.ProtocolMsg()
            pm.identifier = m.identifier
            pm.protobuf = m.protobuf
            if self.websocket is not None:
                self.websocket.send(pm.SerializeToString())
        await self.channels.get_channel("WebsocketServer :: publish_message").subscribe(handle_message)

    async def incoming_task(self):
        self.logger.debug("Incoming task started")

        try:
            while True:
                self.logger.debug("Waiting for message...")
                proto = await self.websocket.recv(decode = False)
                pm = protocol_pb2.ProtocolMsg()
                pm.ParseFromString(proto)

                msg = ProtobufMessage(pm.identifier, pm.protobuf)
                channel = self.subscriptions[msg.identifier]
                if channel is not None:
                    channel.asend(msg)

        except ConnectionClosedOK :
            self.logger.debug("Connection closed")
        except Exception as e:
            self.logger.warn(f"Error in incoming_task {e}")

    def subscribe_message(self, identifier, channel):
        self.subscriptions[identifier] = self.channels.get_channel(channel)


