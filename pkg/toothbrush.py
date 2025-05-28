"""Toothbrush adapter for Candle Controller / WebThings Gateway."""

import os
from os import path
import sys
sys.path.append(path.join(path.dirname(path.abspath(__file__)), 'lib'))

import json
import time

from gateway_addon import Adapter, Device, Property, Action, Database

import asyncio
import logging

import bleak
from bleak_retry_connector import BleakClient, BLEDevice, establish_connection


_TIMEOUT = 3

_CONFIG_PATHS = [
    os.path.join(os.path.expanduser('~'), '.webthings', 'config'),
]

if 'WEBTHINGS_HOME' in os.environ:
    _CONFIG_PATHS.insert(0, os.path.join(os.environ['WEBTHINGS_HOME'], 'config'))


class ToothbrushAdapter(Adapter):
    """Adapter for Toothbrush"""

    def __init__(self, verbose=True):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """
        #print("Initialising Toothbrush")
        self.pairing = False
        self.name = self.__class__.__name__
        self.addon_name = 'toothbrush'
        Adapter.__init__(self, 'toothbrush', 'toothbrush', verbose=verbose)
        #print("Adapter ID = " + self.get_id())

        self.addon_path = os.path.join(self.user_profile['addonsDir'], self.addon_name)

        self.DEBUG = True
        self.running = True
        
        
        self.brushing = False
        
        
        try:
            self.add_from_config()
        except Exception as ex:
            print("Error loading config: " + str(ex))

        
        try:
            toothbrush_device = ToothbrushDevice(self)
            self.handle_device_added(toothbrush_device)
            self.devices['toothbrush_thing'].connected = True
            self.devices['toothbrush_thing'].connected_notify(True)
            self.thing = self.get_device("toothbrush_thing")
        except Exception as ex:
            print("Error creating thing: " + str(ex))
            

        
        #while self.running == True:
            #targetProperty = self.thing.find_property('current_description')
            #time.sleep(1)

        #print("creating Snore Sense thread")
        #t = threading.Thread(target=self.oralb)
        #t.daemon = True
        #t.start()
        
        
        
        async def oralb_discover():
            """Start looking for a OralB toothbrush."""
            devices = await bleak.BleakScanner.discover()
            print('discovered devices')
            for device in devices:
                if device.name == "Oral-B Toothbrush":
                    print("found Oral B toothbrush")
                    return device
            return None

        async def oralb_main():
            while self.running:
                if self.DEBUG:
                    print("initiating scan for Oral-B toothbrush")
                ble_device = await oralb_discover()
                if ble_device != None:
                    if self.DEBUG:
                        print("got Oral-B BLE device: ", ble_device)
                    orlb = OralB(ble_device)
                    while self.running:
                        time.sleep(1)
                        try:
                            oralb_data = await orlb.gatherdata()
                            if self.DEBUG:
                                print("got Oral-B toothbrush data: ", oralb_data)
                        
                        except Exception as ex:
                            if self.DEBUG:
                                print("caught error gathering data from Oral-B toothbrush: ", ex)
                            break
                else:
                    if self.DEBUG:
                        print("No Oral-B toothbrush detected.. waiting 5 seconds to try again")
                    time.sleep(5)



        asyncio.run(oralb_main())
            


        # {'brush_time': 2, 'battery': 97, 'status': 'IDLE', 'mode': 'OFF', 'sector': 'SECTOR_1', 'sector_time': 6}
        

        if self.DEBUG:
            print("End of ToothbrushAdapter init process")
        
        

        

    def unload(self):
        print("Shutting down Toothbrush")
        self.running = False
        


    def remove_thing(self, device_id):
        if self.DEBUG:
            print("-----REMOVING:" + str(device_id))
        
        try:
            obj = self.get_device(device_id)        
            self.handle_device_removed(obj)  # Remove from device dictionary
            if self.DEBUG:
                print("Removed device")
        except Exception as ex:
            if self.DEBUG:
                print("Could not remove thing(s) from devices: " + str(ex))
        
        return



    def add_from_config(self):
        """Attempt to add all configured devices."""
        try:
            database = Database('toothbrush')
            if not database.open():
                return

            config = database.load_config()
            database.close()
        except:
            print("Error! Failed to open settings database.")
            return

        if not config:
            print("Error loading config from database")
            return
        
        
        # Debugging
        try:
            if 'Debugging' in config:
                self.DEBUG = bool(config['Debugging'])
                if self.DEBUG:
                    print("Debugging is set to: " + str(self.DEBUG))
            else:
                self.DEBUG = False
        except:
            print("Error loading debugging preference")
            
        
        
       


#
#  DEVICES
#

class ToothbrushDevice(Device):
    """Toothbrush device type."""

    def __init__(self, adapter):
        """
        Initialize the object.
        adapter -- the Adapter managing this device
        """

        
        Device.__init__(self, adapter, 'toothbrush_thing')
        #print("Creating Toothbrush thing")
        
        self._id = 'toothbrush_thing'
        self.id = 'toothbrush_thing'
        self.adapter = adapter
        self._type.append('BinarySensor')

        self.name = 'toothbrush_thing'
        self.title = 'Toothbrush'
        self.description = 'Toothbrush thing'


        if self.adapter.DEBUG: 
            print("Empty Toothbrush thing has been created.")

        self.properties = {}
        # BooleanProperty
        
        self.properties["brushing"] = ToothbrushProperty(
                        self,
                        "brushing",
                        {
                            "label": "Brushing",
                            'type': 'boolean',
                            'readOnly': True,
                            '@type': 'BooleanProperty',
                        },
                        False)
        
        self.properties["battery"] = ToothbrushProperty(
                        self,
                        "battery",
                        {
                            "label": "Battery level",
                            'type': 'integer',
                            'readOnly': True,
                            'unit':'percent',
                            'minimum':0,
                            'maximum':100,
                            #'@type': 'BooleanProperty',
                        },
                        None)
        
        self.adapter.handle_device_added(self)


        



#
#  PROPERTY
#


class ToothbrushProperty(Property):
    """Toothbrush property type."""

    def __init__(self, device, name, description, value):
        
        #print("incoming thing device at property init is: " + str(device))
        Property.__init__(self, device, name, description)
        
        
        self.device = device
        self.name = name
        self.title = name
        self.description = description # dictionary
        self.value = value
        self.set_cached_value(value)
        self.device.notify_property_changed(self)


    def set_value(self, value):
        #print("set_value is called on a Toothbrush property by the UI. This should not be possible in this case?")
        pass


    def update(self, value):
        
        if value != self.value:
            if self.device.adapter.DEBUG: 
                print("Toothbrush property: "  + str(self.title) + ", -> update to: " + str(value))
            self.value = value
            self.set_cached_value(value)
            self.device.notify_property_changed(self)
        else:
            if self.device.adapter.DEBUG: 
                print("Toothbrush property: "  + str(self.title) + ", was already this value: " + str(value))
                
                
                
                
_LOGGER = logging.getLogger(__name__)


class OralB:
    """Connects to OralB toothbrush to get information."""

    def __init__(self, ble_device: BLEDevice) -> None:
        """Initialize the class object."""
        self.ble_device = ble_device
        self._cached_services = None
        self.client = None
        self.name = "OralB"
        self.prev_time = 0

        self.result = {
            "brush_time": None,
            "battery": None,
            "status": None,
            "mode": None,
            "sector": None,
            "sector_time": None,
        }

    def set_ble_device(self, ble_device) -> None:
        self.ble_device = ble_device

    def disconnect(self) -> None:
        self.client = None
        self.ble_device = None

    async def connect(self) -> None:
        """Ensure connection to device is established."""
        if self.client and self.client.is_connected:
            return

        # Check again while holding the lock
        if self.client and self.client.is_connected:
            return
        _LOGGER.debug(f"{self.name}: Connecting; RSSI: {self.ble_device.rssi}")
        try:
            self.client = await establish_connection(
                BleakClient,
                self.ble_device,
                self.name,
                self._disconnected,
                cached_services=self._cached_services,
                ble_device_callback=lambda: self.ble_device,
            )
            _LOGGER.debug(f"{self.name}: Connected; RSSI: {self.ble_device.rssi}")
        except Exception:
            _LOGGER.debug(f"{self.name}: Error connecting to device")

    def _disconnected(self, client: BleakClient) -> None:
        """Disconnected callback."""
        _LOGGER.debug(
            f"{self.name}: Disconnected from device; RSSI: {self.ble_device.rssi}"
        )
        self.client = None

    async def gatherdata(self):
        """Connect to the OralB to get data."""
        if self.ble_device is None:
            print("gatherdata: self.ble_device is None, aborting")
            return self.result
        if time.time() - self.prev_time < 1:
            print("gatherdata: already scanned less than a second ago, aborting")
            return self.result
        self.prev_time = time.time()
        print("gatherdata: trying to connect...")
        await self.connect()
        print("gatherdata: connected!")
        chars = {
            # a0f0fff0-5047-4d53-8208-4f72616c2d42
            "a0f0ff08-5047-4d53-8208-4f72616c2d42": "time",
            "a0f0ff05-5047-4d53-8208-4f72616c2d42": "battery",
            "a0f0ff04-5047-4d53-8208-4f72616c2d42": "status",
            "a0f0ff07-5047-4d53-8208-4f72616c2d42": "mode",
            "a0f0ff09-5047-4d53-8208-4f72616c2d42": "sector",
        }
        statuses = {
            2: "IDLE",
            3: "RUN",
        }
        modes = {
            0: "OFF",
            1: "DAILY_CLEAN",
            7: "INTENSE",
            2: "SENSITIVE",
            4: "WHITEN",
            3: "GUM_CARE",
            6: "TONGUE_CLEAN",
        }
        sectors = {
            0: "SECTOR_1",
            1: "SECTOR_2",
            2: "SECTOR_3",
            3: "SECTOR_4",
            4: "SECTOR_5",
            5: "SECTOR_6",
            7: "SECTOR_7",
            8: "SECTOR_8",
            "FE": "LAST_SECTOR",
            "FF": "NO_SECTOR",
        }
        try:
            tasks = []
            for char, _ in chars.items():
                tasks.append(asyncio.create_task(self.client.read_gatt_char(char)))
                print("gatherdata: appended read task")
            results = await asyncio.gather(*tasks)
            print("gatherdata: all tasks complete!")
            res_dict = dict(zip(chars.values(), results))

            self.result["brush_time"] = 60 * res_dict["time"][0] + res_dict["time"][1]
            self.result["battery"] = res_dict["battery"][0]
            self.result["status"] = statuses.get(res_dict["status"][0], "UNKNOWN")
            self.result["mode"] = modes.get(res_dict["mode"][0], "UNKNOWN")
            self.result["sector"] = sectors.get(res_dict["sector"][0], "UNKNOWN")
            self.result["sector_time"] = res_dict["sector"][1]
        except Exception:
            _LOGGER.debug(f"{self.name}: Not connected to device")
        
        print("result: ", self.result)

        return self.result


