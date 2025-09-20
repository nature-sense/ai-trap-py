import subprocess
from enum import Enum


# nmcli d wifi connect my_wifi password <password>
#sudo nmcli r wifi on
#nmcli -t radio wifi -< enabled/disabled

#nmcli connection show
#preconfigured:60d6692b-caef-4531-ae7a-236aeef97435:802-11-wireless:wlan0
#nmcli connection up uuid cd79a7a1-1cf4-49c3-ad58-21ab17d1ba05

#sudo nmi connection add type wifi con-name "HomeWiFi2" ifname "wlan0" ssid "Fastnet2.5" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "your_password"
#Connection 'HomeWiFi2' (60fe863b-0ce0-4287-b09e-de1d43891089) successfully added.

#nmcli net con
# none / portal / limited / full / unknown
class ConectionState(Enum) :
    none = "none",
    portal = "portal",
    limited = "limited"
    full = "full"
    unknown = "unknown"

class NetworkApi :
    # =====================================================
    # Add a wifi network defined by name, ssid and password
    # returns a uuid for the network
    # =====================================================
    @staticmethod
    def add_wifi_network_config(name, ssid, password) :
        try:
            process = subprocess.run([
                'nmcli',
                '-t',
                'connection',
                'add',
                'type',
                'wifi',
                'con-name',
                f'\'{name}\'',
                'ifname',
                '\'wlan0\'',
                'ssid',
                f'\'{ssid}\'',
                'wifi-sec.key-mgmt',
                'wpa-psk',
                'wifi-sec.psk',
                f'\'{password}\''
                ],
                capture_output=True, text=True, check=True
            )
            output_lines = process.stdout.strip().split('\n')
            for line in output_lines:
                if 'successfully added' in line :
                    return line[line.find('(')+1:line.find(')')]
            return None

        except subprocess.CalledProcessError as e:
            print(f"Error executing nmcli: {e}")
            return None

    @staticmethod
    def add_hotspot_config(name, ssid, password) :
        #nmcli d wifi hotspot ifname wlan0 ssid testspot password 12345678
        #sudo nmcli connection add type wifi ifname wlan0 con-name testhotspot ssid testhotspot
        # 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
        #wifi-sec.key-mgmt wpa-psk
        #
        try :
            process = subprocess.run([
                'nmcli',
                '-t',
                'connection',
                'add',
                'type',
                'wifi',
                'con-name',
                f'\'{name}\'',
                'ifname',
                '\'wlan0\'',
                'ssid',
                f'\'{ssid}\'',
                '802-11-wireless.mode',
                'ap',
                '802-11-wireless.band',
                'bg'
                'ipv4.method',
                'shared',
                'wifi-sec.key-mgmt',
                'wpa-psk',
                'wifi-sec.psk',
                f'\'{password}\''
            ], capture_output=True, text=True, check=True)
            output_lines = process.stdout.strip().split('\n')
            for line in output_lines:
                if 'successfully added' in line :
                    return line[line.find('(')+1:line.find(')')]
            return None

        except subprocess.CalledProcessError as e:
            print(f"Error executing nmcli: {e}")
            return None

    # ================================================
    # List wifi configurations
    # ================================================
    @staticmethod
    def list_wifi_configurations() :
        process = subprocess.run(['nmcli', '-t', 'connection', 'show'],
                                 capture_output=True, text=True, check=True)
        output_lines = process.stdout.strip().split('\n')
        networks = []
        for line in output_lines:
            parts = line.split(':')
            if len(parts) == 4 and parts[3] == '802-11-wireless':
                networks.append(parts[0])

    # ================================================
    # get the internet connection state one of:
    # - none
    # - portal = hotspot
    # - limited = wifi (no internet)
    # - full = wifi (with internet
    # - unknown
    # ================================================
    @staticmethod
    def get_connection_state() :
        process = subprocess.run(['nmcli', '-t', 'connection', 'show'],
                                 capture_output=True, text=True, check=True)
        state = process.stdout.strip()
        return ConectionState[state].name

    # ======================================================
    # get details of the current wifi connectiom comprising
    # - connection name
    # - ssid
    # - uuid
    # =======================================================
    @staticmethod
    def get_current_connection() :
        try:
            # Find the acrive wifi connection
            process = subprocess.run(['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'],
                                     capture_output=True, text=True, check=True)
            output_lines = process.stdout.strip().split('\n')
            for line in output_lines:
                if line.startswith('yes:'):
                    ssid = line.split(':', 1)[1]

                    process = subprocess.run(['nmcli', '-t', 'connection', 'show', '-active'],
                                     capture_output=True, text=True, check=True)
                    output_lines = process.stdout.strip().split('\n')
                    for line in output_lines:
                        parts = line.split(':')
                        if len(parts) == 4 and parts[3] == 'wlan0' :
                            name = parts[0]
                            uuid = parts[1]

                            return name, ssid, uuid,
            return None

        except subprocess.CalledProcessError as e:
            print(f"Error executing nmcli: {e}")
            return None

    @staticmethod
    def configuration_up(uuid) :
        process = subprocess.run(['nmcli', 'con', 'up', f'\'{uuid}'],
                                 capture_output=True, text=True, check=True)
        line = process.stdout.strip()
        return  "Connection successfully activated" in line


    @staticmethod
    def configuratiom_down(uuid) :
        process = subprocess.run(['nmcli', 'con', 'down', f'\'{uuid}'],
                                 capture_output=True, text=True, check=True)
        line = process.stdout.strip()
        return  "Connection successfully deactivated" in line

    ##############
    # Turn wifo\i on or off
    #
    @staticmethod
    def set_wifi_state(state) :
        try:
            if state :
                subprocess.run(['sudo', 'nmcli', 'r', 'wifi', 'on'],
                                     capture_output=True, text=True, check=True)
            else :
                subprocess.run(['sudo', 'nmcli', 'r', 'wifi', 'off'],
                                         capture_output=True, text=True, check=True)

        except subprocess.CalledProcessError as e:
            print(f"Error executing nmcli: {e}")
            return None

    @staticmethod
    def get_wifi_state() :
        try:
            process = subprocess.run(['nmcli', '-t', 'radio', 'wifi'],
                                     capture_output=True, text=True, check=True)
            output_lines = process.stdout.strip().split('\n')
            for line in output_lines:
                if line.startswith('enabled'):
                    return True
                else :
                    return False
        except subprocess.CalledProcessError as e:
            print(f"Error executing nmcli: {e}")
            return None

    @staticmethod
    def is_wifi_connected() :
        #nmcli -t connection show --active
        #preconfigured:60d6692b-caef-4531-ae7a-236aeef97435:802-11-wireless:wlan0
        #lo:60e8a9c1-baaf-4297-87fe-b2a3c8df49f6:loopback:lo

        try:
            process = subprocess.run(['nmcli', '-t', 'connection', 'show', '--active'],
                                     capture_output=True, text=True, check=True)
            output_lines = process.stdout.strip().split('\n')
            for line in output_lines:
                parts = line.split(':')
                if parts[2] == "wlan0":
                    return True
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error executing nmcli: {e}")
            return None