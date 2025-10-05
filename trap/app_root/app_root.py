#!/usr/bin/env python
import asyncio
import configparser
import logging
import os
from datetime import datetime

from trap.channels.channels_service import ChannelsService
from trap.network.network_manager import NetworkManager
from trap.sessions.sessions_cache import SessionsCache
from trap.bluetooth.bluetooth_service import BluetoothService
from trap.settings.settings_database import SettingsDatabase
from trap.webdav.webdav_server import WebDavServer
from trap.websocket.websocket_service import WebsocketServer
from trap.workflow.camera_workflow import CameraWorkflow

SESSIONS_DIRECTORY = "./sessions"
CONFIG_FILE = "configuration/config.ini"

session_format = "%Y%m%d$H%M%S"
def session_to_datetime(session) :
    return datetime.strptime(session,session_format)

class Configuration :
    def __init__(self, node_name, camera_type, settings_path, sessions_path, websocket_port, bluetooth_service ):
        self.node_name = node_name
        self.camera_type = camera_type
        self.settings_path = settings_path
        self.sessions_path = sessions_path
        self.websocket_port = websocket_port
        self.bluetooth_service = bluetooth_service

class ConfigFile :

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.file_exists = False
        if os.path.exists('CONFIG_FILE'):
            self.config.read('CONFIG_FILE')
            self.file_exists = True

    def read_value(self, name, default):
        if self.file_exists:
            value = self.config["trap"][name]
            if value is not None:
                return value
        return default

    def read_int_value(self, name, default):
        if self.file_exists:
            value = self.config.getint("trap", name)
            if value is None:
                return value
        return default

class AppRoot:
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(name=__name__)

        self.config_file = ConfigFile()
        self.configuration = Configuration(
            os.uname().nodename.upper(),
            self.config_file.read_value("cameras", "picamera3"),
            self.config_file.read_value("settingsPath", "./configuration"),
            self.config_file.read_value("sessionsPath", "./sessions"),
            self.config_file.read_int_value("websocket", 8096),
            self.config_file.read_value("bluetoothService", "213e313b-d0df-4350-8e5d-ae657962bb56"),
        )

        self.channels  = ChannelsService()
        self.webdav = WebDavServer()
        self.bluetooth = BluetoothService(self.configuration, self.channels) #config
        #self.network   = NetworkManager(self.configuration, self.channels)
        self.websocket = WebsocketServer(self.configuration, self.channels) #config, channels
        self.settings  = SettingsDatabase(self.configuration, self.channels, self.websocket) #channel,websocket,config
        self.sessions  = SessionsCache(self.configuration, self.channels, self.settings, self.websocket) #config settings websocket
        self.workflow  = CameraWorkflow(self.configuration, self.channels, self.settings, self.websocket)

        self.network = NetworkManager(self.configuration, self.channels)

    async def run_trap(self):
        logging.debug("AppRoot :: Run trap...")
        await asyncio.gather(
            self.bluetooth.run_bluetooth_task(),
            self.websocket.run_websocket_task(),
            self.workflow.run_workflow_task(),
            self.sessions.run_cache_task(),
            self.settings.run_settings_task(),
            #self.webdav.run_webdav_task()
        )








