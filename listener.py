#!/usr/bin/env python
"""
Meshtastic to CalTopo position forwarder.

This script listens for Meshtastic device position updates and forwards them
as GPS coordinates to CalTopo API for tracking purposes.
"""

import sys
import time
import logging
from dataclasses import dataclass
import requests
import yaml
import meshtastic
import meshtastic.serial_interface
from pubsub import pub

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Configuration for the Meshtastic to CalTopo server.

    Attributes:
        rate_limit (int): Time in seconds between API requests to CalTopo
        ignore_list (list[str]): List of device IDs to ignore
        caltopo_url (str): Base URL for CalTopo API
        logging (str): Logging level setting ("INFO" or "WARNING")
        logging_level (int): Numeric logging level for Python's logging module
    """

    rate_limit: int
    ignore_list: list[str]
    caltopo_url: str
    logging: str
    logging_level: int

    def __init__(self, yaml_file: str):
        """Initialize configuration from a YAML file.

        Args:
            yaml_file (str): Path to the YAML configuration file
        """
        with open(yaml_file, "r", encoding="utf-8") as fh:
            yaml_data = yaml.safe_load(fh)

        self.logging = yaml_data["logging"]
        if self.logging == "INFO":
            self.logging_level = logging.INFO
        else:
            self.logging_level = logging.WARNING

        self.caltopo_url = yaml_data["caltopo_url"]
        self.rate_limit = int(yaml_data["rate_limit"])
        self.ignore_list = {}
        for i in yaml_data["ignore"]:
            self.ignore_list[i] = True


@dataclass
class Server:
    """Server for forwarding Meshtastic position updates to CalTopo.

    Attributes:
        url_prefix (str): Base URL for API requests
        last_update (int): Timestamp of last update
        config (ServerConfig): Server configuration
    """

    url_prefix: str
    last_update: int
    config: ServerConfig

    def report(self, loc):
        """Send location data to CalTopo API.

        Args:
            loc (Location): Location object containing device and GPS data
        """
        current_time = time.time()
        delta = current_time - self.last_update
        if delta < self.config.rate_limit:
            print("rate limiting")
            return

        logger.info(
            "TX %s %ddbi %dft %s %s %dkph",
            loc.source,
            loc.rssi,
            loc.altitude,
            loc.longitude,
            loc.latitude,
            loc.speed,
        )
        url = (
            f"{self.url_prefix}?id={loc.source}&lat={loc.latitude}&lng={loc.longitude}"
        )
        requests.get(url, timeout=10)

    def on_receive(self, packet, interface):  # pylint: disable=unused-argument
        """Callback for handling Meshtastic position packets.

        Args:
            packet (dict): Raw Meshtastic packet data
            interface (SerialInterface): Meshtastic interface object
        """
        loc = Location(packet)
        logger.info(
            "RX %s %ddbi %dft %s %s %dkph",
            loc.source,
            loc.rssi,
            loc.altitude,
            loc.longitude,
            loc.latitude,
            loc.speed,
        )

        if loc.source is None:
            return

        if loc.source in self.config.ignore_list:
            return

        self.report(loc)

    def __init__(self, yaml_file: str):
        """Initialize the server with configuration from a YAML file.

        Args:
            yaml_file (str): Path to the YAML configuration file
        """
        self.config = ServerConfig(yaml_file)
        self.url_prefix = self.config.caltopo_url
        self.last_update = time.time() - self.config.rate_limit
        logging.basicConfig(
            level=self.config.logging_level,
            format="{asctime} - {levelname} - {message}",
            style="{",
        )


@dataclass
class Location:
    """Location data extracted from a Meshtastic packet.

    Attributes:
        source (int): Device ID
        altitude (int): Altitude in feet
        longitude (str): GPS longitude
        latitude (str): GPS latitude
        speed (int): Speed in kph
        rssi (int): RSSI in dBi
    """

    source: int
    altitude: int
    longitude: str
    latitude: str
    speed: int
    rssi: int

    def __init__(self, packet):
        self.source = packet["fromId"]
        self.altitude = packet["decoded"]["position"]["altitude"]
        self.longitude = packet["decoded"]["position"]["longitude"]
        self.latitude = packet["decoded"]["position"]["latitude"]
        self.speed = packet["decoded"]["position"]["groundSpeed"]
        self.rssi = packet["rxRssi"]


def main(config: str) -> None:
    """the main event"""

    serv = Server(config)

    pub.subscribe(serv.on_receive, "meshtastic.receive.position")
    interface = meshtastic.serial_interface.SerialInterface()

    sleep_time = 10
    if len(sys.argv) > 1:
        sleep_time = int(sys.argv[1])

    time.sleep(sleep_time)
    interface.close()


if __name__ == "__main__":
    main("config.yaml")
