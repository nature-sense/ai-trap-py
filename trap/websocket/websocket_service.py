import asyncio
import logging
from abc import ABC

from websockets import ConnectionClosedOK
from websockets.asyncio.server import serve

from trap.channels.channel import Channel
from trap.websocket.proto import protocol_pb2
from trap.websocket.protobuf_message import ProtobufMsg

class WebsocketServer :
    def __init__(self, config, channels ) :
        self.subscriptions = {}
        self.port = config.websocket_port
        self.channels = channels
        self.tasks = []
        self.websocket = None
        self.logger = logging.getLogger(__name__)
        self.connection_state = self.channels.get_channel("connection_state")

    async def run_websocket_task(self) :
        self.logger.debug("Starting websocket server task....")

        self.tasks = [
            asyncio.create_task(self.outgoing_task()),
        ]

        async with serve(self.handler, "", self.port) as server:
            await server.serve_forever()

    async def handler(self, websocket):
        self.websocket = websocket

        self.logger.debug(f"creating websocket incoming task")
        incom_task = asyncio.create_task(self.incoming_task())
        await incom_task  # exits when socket gone
        self.websocket = None

    async def outgoing_task(self) :
        logging.debug("Starting websocket outgoing task....")

        async def handle_message(m):
            pm = protocol_pb2.ProtobufMessage()
            try :
                logging.debug(f"Sending message {pm.identifier}")
                pm.identifier = m.identifier
                pm.protobuf = m.protobuf
                if self.websocket is not None:
                    await self.websocket.send(pm.SerializeToString())
            except Exception as e :
                self.logger.error(f"Failed to send message {pm.identifier}: {e}")

        await self.channels.get_channel("publish_message").subscribe(handle_message)

    async def incoming_task(self):
        self.logger.debug("Incoming task started")
        try:
            while True:
                self.logger.debug("Waiting for message...")
                proto = await self.websocket.recv(decode = False)
                pm = protocol_pb2.ProtobufMessage()
                pm.ParseFromString(proto)

                self.logger.debug(f"Received {pm.identifier}")

                msg = ProtobufMsg(pm.identifier, pm.protobuf)
                channel = self.subscriptions.get(msg.identifier)
                if channel is not None:
                    self.logger.debug(f"Forwarding message {msg.identifier}")
                    await channel.publish(msg)
                else :
                    self.logger.warn(f"No subscription for {pm.identifier}")


        except ConnectionClosedOK :
            self.logger.debug("Connection closed")
            await self.connection_state.publish(False)

        except Exception as e:
            self.logger.debug("Connection closed")
            await self.connection_state.publish(False)
            self.logger.warn(f"Error in incoming_task {e}")

    def subscribe_one_message(self, identifier):
        self.logger.debug(f"Subscribed to {identifier}")
        channel = Channel()
        self.subscriptions[identifier] = channel
        return channel

    def subscribe_many_messages(self, *args):
        channel = Channel()
        for ident in args :
            self.logger.debug(f"Subscribed to {ident}")
            self.subscriptions[ident] = channel
        return channel

