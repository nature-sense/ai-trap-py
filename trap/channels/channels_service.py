import logging
from asyncio import Queue
from trap.channels.channel import Channel


class ChannelsService :
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.channels = {}
        self.queues = {}

    def get_channel(self, channel_name):
        self.logger.debug(f"get_channel {channel_name}" )
        if channel_name in self.channels:
            return self.channels[channel_name]
        else:
            channel = Channel()
            self.channels[channel_name] = channel
            return channel

    def get_queue(self, queue_name):
        if queue_name in self.queues:
            return self.queues[queue_name]
        else:
            queues = Queue()
            self.queues[queue_name] = queues
            return queues