import logging

from trap.network.network_api import NetworkApi


class NetworkManager() :
    def __init__(self, config, channels):
        self.config = config
        self.channels = channels
        self.wifi_cfg = NetworkApi.list_wifi_configurations()

        wifi_network =  self.wifi_cfg.get("preconfigured")
        if wifi_network is None :
            exit(0)

        if wifi_network.autostart :
            


        # Determine thew current netork state
        # if there is a network called 'preconfigured' with autpstart on this
        # this is the first time the trap has been run


        # Find the initial state
        #self.wifi_status.active = NetworkApi.get_wifi_state()
        #curr_net = NetworkApi.get_current_network()

        #self.settings = self.database.read_settings()
        #if self.settings is None:

        #    if self.settings is None:
        #        if NetworkApi.get_wifi_state() is True :
        #            # ------------------------------------------------------------------
        #            # Get the current network and create an entry for it in the settings
        #            # Create an entru for the hotspot in the settings
        #            # ------------------------------------------------------------------
        #            curr_net = NetworkApi.get_current_connection()
        #            if curr_net is not None:
        #                hotspot_name = 'hotspot'
        #                hotspot_ssid = self.config.node_name
        #                hotspot_password = "naturesense"
        #                hotspot_uuid = NetworkApi.add_hotspot_config(hotspot_name, hotspot_ssid, hotspot_password)

        #                network_name = curr_net[0]
        #                network_ssid = curr_net[1]
        #                network_uuid = curr_net[2]

        #                self.settings = NetworkSettings(
        #                    hotspot_name,
        #                    hotspot_ssid,
        #                    hotspot_uuid,
        #                    network_name,
        #                    network_ssid,
        #                    network_uuid
        #                )
        #                self.database.write_settings(self.settings)
        #            else :
        #                logging.error("No wifi connected. Cannot initialise the network settings")
        #        else :
        #            logging.error("Wifi is off. Cannot initialise the network settings")

    def start_hotspot(self):
        NetworkApi.configuration_up(self.settings.hotspot_uuid)

    def stop_hotspot(self):
        NetworkApi.configuratiom_down(self.settings.hotspot_uuid)

    def start_network(self):
        NetworkApi.configuration_up(self.settings.network_uuid)

    def stop_network(self):
        NetworkApi.configuratiom_down(self.settings.network_uuid)



