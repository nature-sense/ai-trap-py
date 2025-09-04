import asyncio
import logging
from bless import BlessServer

SERVICE_UUID  = "213e313b-d0df-4350-8e5d-ae657962bb56"

class BluetoothService():

    def __init__(self, config):

        self.node_name = config.node_name
        self.bluetooth_server = None
        self.logger = logging.getLogger(name=__name__)

    async def run_bluetooth_task(self):
        self.logger.debug("BluetoothService :: Starting bluetooth server task....")

        # Instantiate the server
        loop = asyncio.get_running_loop()
        self.bluetooth_server = BlessServer(name=self.node_name, loop=loop)
        await self.bluetooth_server.add_new_service(SERVICE_UUID)
        await self.bluetooth_server.start()
        self.logger.debug("BluetoothService :: Bluetooth advertising")
        await asyncio.Future()