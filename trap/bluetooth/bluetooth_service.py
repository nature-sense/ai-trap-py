import asyncio
import logging

from bless import BlessServer

class BluetoothService():

    def __init__(self, config, channels):

        self.node_name = config.node_name
        self.service = config.bluetooth_service
        self.bluetooth_server = None
        self.channels = channels
        self.logger = logging.getLogger(name=__name__)

    async def run_bluetooth_task(self):
        self.logger.debug("BluetoothService :: Starting bluetooth server task....")

        # Instantiate the server
        loop = asyncio.get_running_loop()
        self.bluetooth_server = BlessServer(name=self.node_name, loop=loop)
        await self.bluetooth_server.add_new_service(self.service)

        self.logger.debug("BluetoothService :: Bluetooth advertising")
        await asyncio.Future()