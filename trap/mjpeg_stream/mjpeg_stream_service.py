import asyncio
import logging

from websockets import serve


class MjpegStreamService :
    def __init__(self, config, channels):

        self.port = config.streaming_port
        self.queue = channels.get_queue("streaming_queue")
        self.websocket = None
        self.tasks = []
        self.logger = logging.getLogger(name=__name__)

    async def run_streaming_task(self):
        self.logger.debug("Starting streaming server task...")
        self.tasks = [
            asyncio.create_task(self.send_frame_task()),
        ]

        async with serve(self.handler, "", self.port) as server:
            await server.serve_forever()

    async def handler(self, websocket):
        if self.websocket is not None :
            return

        self.websocket = websocket

        self.logger.debug(f"creating tasks websocket ")
        incom_task = asyncio.create_task(self.incoming_task())
        await incom_task # exits when socket gone
        self.websocket = None
        #self.channels.get_channel("")

    async def incoming_task(self) :
        try:
            while True:
                await self.websocket.recv(decode=False)
        except Exception as e:
            self.logger.warn(f"Error in incoming_task {e}")

    async def send_frame_task(self):
        self.logger.debug(f"starting send_frame_task")

        while True:
            try:
                frame = await self.queue.get()
                self.logger.debug(f"frame from queue")

                if self.websocket is not None :
                    self.logger.debug(f"ending frame to websocket")
                    await self.websocket.send(frame)
            except Exception as e:
                self.logger.warn(f"Error in send_frame_task {e}")