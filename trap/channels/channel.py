import logging

from aioreactive import AsyncSubject, AsyncAnonymousObserver


class Channel :
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.async_subject = AsyncSubject()

    async def publish(self, object):
        await self.async_subject.asend(object)

    async def subscribe(self, on_message):
        logging.debug(f"subscribe() to channel")
        async def del_session_sink(s):
            #logging.debug(f"subscribe() sink received message")
            await on_message(s)
        sink = AsyncAnonymousObserver(del_session_sink)
        await self.async_subject.subscribe_async(sink)

    async def subscribe_with_lambda(self, on_message_lambda):
        async def del_session_sink(s):
            on_message_lambda(s)
        sink = AsyncAnonymousObserver(del_session_sink)
        await self.async_subject.subscribe_async(sink)