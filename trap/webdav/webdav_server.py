import asyncio
import logging
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from pywebdav.server.fileauth import DAVAuthHandler
from pywebdav.server.fshandler import FilesystemHandler

class NullAuthHandler(DAVAuthHandler):
    def get_userinfo(self,user,pw,command):
        return 1


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class WebDavServer :
    def __init__(self):
        self.port = 8008
        self.host ='127.0.0.1'
        self.directory='/home/steve/ai-trap-py/sessions'
        self.verbose = False
        self.noauth = True
        self.handler = NullAuthHandler
        self.server = ThreadedHTTPServer
        self.logger = logging.getLogger(__name__)

        self.handler.IFACE_CLASS = FilesystemHandler(
            self.directory,
            'http://%s:%s/' % (self.host, self.port), self.verbose
        )

    async def run_webdav_task(self) :
        self.logger.debug("Starting webdav")
        svr = self.server( (self.host, self.port), self.handler )
        await asyncio.gather(asyncio.to_thread(svr.serve_forever()))
        self.logger.debug("webdav complete")

