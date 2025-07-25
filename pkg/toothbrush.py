"""Toothbrush adapter for Candle Controller / WebThings Gateway."""

import os
from os import path
import sys
sys.path.append(path.join(path.dirname(path.abspath(__file__)), 'lib'))

import json
import time
import math

from gateway_addon import Adapter, Device, Property, Action, Database


import asyncio
import hashlib
import logging

import bleak
from bleak_retry_connector import BleakClient, BLEDevice, establish_connection


_TIMEOUT = 3

_CONFIG_PATHS = [
    os.path.join(os.path.expanduser('~'), '.webthings', 'config'),
]

if 'WEBTHINGS_HOME' in os.environ:
    _CONFIG_PATHS.insert(0, os.path.join(os.environ['WEBTHINGS_HOME'], 'config'))


_LOGGER = logging.getLogger(__name__)



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

        

        self.DEBUG = True
        
        self.continuous_scanning = True
        self.brushing = False
        
        self.oralb_toothbrushes = {} # holds the Bleak BLE objects
        
        self.devices = {} # holds Webthings things
        
        self.persistent_data = {'toothbrushes':{}} # mainly stores the mac address of known toothbrushes
        
        self.last_time_scanned = 0
        
        first_run = False
        
        # Paths
        
        self.addon_path = os.path.join(self.user_profile['addonsDir'], self.addon_name)
        self.data_dir_path = os.path.join(self.user_profile['dataDir'], self.addon_name)
        self.persistence_file_path = os.path.join(self.data_dir_path, 'persistence.json')

        try:
            #print("self.persistence_file_path: ", self.persistence_file_path)
            if not os.path.isdir(self.data_dir_path):
                os.mkdir(self.data_dir_path)
        except Exception as ex:
            if self.DEBUG:
                print("failed to create data dir: ", ex)
        
        
        try:
            #print("self.persistence_file_path: " + str(self.persistence_file_path))
            with open(self.persistence_file_path) as f:
                self.persistent_data = json.load(f)
                if self.DEBUG:
                    print("Persistence data was loaded succesfully.")
                
        except Exception as ex:
            first_run = True
            print("Could not load persistent data (if you just installed the add-on then this is normal). " + str(ex))
            self.persistent_data = {'toothbrushes':{}}
        
        
        #if not 'token' in self.persistent_data:
        #    self.persistent_data['token'] = None
        
        
        try:
            self.add_from_config()
        except Exception as ex:
            print("Error loading config: " + str(ex))



        for toothbrush_thing_id, details in self.persistent_data['toothbrushes'].items():
            try:
                print("creating Toothbrush thing with id: ", toothbrush_thing_id)
                
                toothbrush_title = 'Toothbrush'
                try:
                    if 'name' in details.keys():
                        toothbrush_title = details['name']
                except:
                    print("no name in toothbrush persistant data: ", details)
                
                self.devices[toothbrush_thing_id] = ToothbrushDevice(self, toothbrush_thing_id, toothbrush_title)
                self.handle_device_added(self.devices[toothbrush_thing_id])
                self.devices[toothbrush_thing_id].connected = True
                self.devices[toothbrush_thing_id].connected_notify(True)
                if self.DEBUG:
                    print("created toothbrush thing with id: ", toothbrush_thing_id)
                    
            except Exception as ex:
                if self.DEBUG:
                    print("Error creating toothbrush thing: " + str(ex))
            
        
        
        
        
        self.running = True
        asyncio.run(self.asyncio_main())
        
        
        
        """
        try:
            toothbrush_device = ToothbrushDevice(self)
            self.handle_device_added(toothbrush_device)
            self.devices['toothbrush_thing'].connected = True
            self.devices['toothbrush_thing'].connected_notify(True)
            #self.thing = self.get_device("toothbrush_thing")
            if self.DEBUG:
                print("created toothbrush thing")
        except Exception as ex:
            print("Error creating thing: " + str(ex))
        """

        
        #while self.running == True:
            #targetProperty = self.thing.find_property('current_description')
            #time.sleep(1)

        #print("creating Snore Sense thread")
        #t = threading.Thread(target=self.oralb)
        #t.daemon = True
        #t.start()
        
        
        
        


        


        
            
            
       


        # {'brush_time': 2, 'battery': 97, 'status': 'IDLE', 'mode': 'OFF', 'sector': 'SECTOR_1', 'sector_time': 6}
        

        if self.DEBUG:
            print("End of ToothbrushAdapter init process")


    #print("starting asyncio")
    #asyncio.run(oralb_main())
    
    async def oralb_main(self):
        #print("self.running: ", self.running)
        while self.running:
            
            await asyncio.sleep(1)
            
            try:
                oralb_keys = self.oralb_toothbrushes.keys()
                
                #for short_hash, oralb_device in self.oralb_toothbrushes.items():
                for toothbrush_thing_id in oralb_keys:
                
                
                    try:
                        if toothbrush_thing_id in self.oralb_toothbrushes.keys():
                            
                            oralb_device = self.oralb_toothbrushes[toothbrush_thing_id]
                            oralb_data = await oralb_device.gatherdata()
                            if self.DEBUG:
                                print("got Oral-B toothbrush data: ", oralb_data)
                
                            if oralb_data and "battery" in oralb_data.keys() and "brush_time" in oralb_data.keys():
                
                                try:
                            
                                    if not toothbrush_thing_id in self.devices.keys():
                                        if self.DEBUG:
                                            print("this toothbrush does not have a thing yet. Creating it now.")
                                
                                        self.devices[toothbrush_thing_id] = ToothbrushDevice(self, toothbrush_thing_id, 'toothbrush')
                                        self.handle_device_added(self.devices[toothbrush_thing_id])
                                        self.devices[toothbrush_thing_id].connected = True
                                        self.devices[toothbrush_thing_id].connected_notify(True)
                                
                                    if not toothbrush_thing_id in self.devices.keys():
                                        if self.DEBUG:
                                            print("Error, thing still does not exist!")
                                        break
                                    
                                    
                                    privacy = False
                                    brush_time_goal = None

                                    if 'privacy' in self.persistent_data['toothbrushes'][toothbrush_thing_id].keys() and self.persistent_data['toothbrushes'][toothbrush_thing_id]['privacy'] == True:
                                        privacy = True
                                        if self.DEBUG:
                                            print("privacy preference found in persistent data: ", privacy)
                                        
                                    if 'brush_time_goal' in self.persistent_data['toothbrushes'][toothbrush_thing_id].keys() and str(type(self.persistent_data['toothbrushes'][toothbrush_thing_id]['brush_time_goal'])) == "<class 'int'>":
                                        if self.persistent_data['toothbrushes'][toothbrush_thing_id]['brush_time_goal'] > 3:
                                            brush_time_goal = self.persistent_data['toothbrushes'][toothbrush_thing_id]['brush_time_goal']
                                            if self.DEBUG:
                                                print("brush_time_goal has been set: ", brush_time_goal)
                                    
                                          
                                    
                                    
                                    if privacy == True:
                                        if int(oralb_data["battery"]) > 80:
                                            self.devices[toothbrush_thing_id].properties['battery'].update( 100 )
                                        #elif int(oralb_data["battery"]) < 60:
                                        #    self.devices[toothbrush_thing_id].properties['battery'].update( math.floor(int(oralb_data["battery"])/10) * 10 )
                                        else:
                                            #self.devices[toothbrush_thing_id].properties['battery'].update( math.floor(int(oralb_data["battery"])/20) * 20 )
                                            self.devices[toothbrush_thing_id].properties['battery'].update( math.floor(int(oralb_data["battery"])/10) * 10 )
                                    else:
                                        self.devices[toothbrush_thing_id].properties['battery'].update( int(oralb_data["battery"]) )
                                    
                                    
                                    self.devices[toothbrush_thing_id].properties['mode'].update( str(oralb_data["mode"]) )
                                    
                                    
                                    if privacy == True:
                                        self.devices[toothbrush_thing_id].properties['brush_time'].update( None )
                                    #elif str(oralb_data["mode"]) == "OFF":
                                    #    self.devices[toothbrush_thing_id].properties['brush_time'].update( None )
                                    elif oralb_data["brush_time"] != None:
                                        if self.DEBUG:
                                            print("brush time: ", int(oralb_data["brush_time"]))
                                        self.devices[toothbrush_thing_id].properties['brush_time'].update( int(oralb_data["brush_time"]) )
                                    
                                    
                                    if str(type(brush_time_goal)) == "<class 'int'>" and brush_time_goal <= 2:
                                        if self.DEBUG:
                                            print("brush goal too small: ", brush_time_goal)
                                        self.devices[toothbrush_thing_id].properties['goal_reached'].update( None )
                                    elif int(oralb_data["brush_time"]) >= 3 and int(oralb_data["brush_time"]) < brush_time_goal: 
                                        if self.DEBUG:
                                            print("brush time is bigger than  and smaller than the goal, setting goal_reached to false: ", brush_time_goal)
                                        self.devices[toothbrush_thing_id].properties['goal_reached'].update( False )
                                    elif int(oralb_data["brush_time"]) > 4:
                                        if brush_time_goal and int(oralb_data["brush_time"]) >= brush_time_goal:
                                            if self.DEBUG:
                                                print("brush goal reached: ", brush_time_goal)
                                            self.devices[toothbrush_thing_id].properties['goal_reached'].update( True )
                                            
                                    
                                    if privacy == True:
                                        self.devices[toothbrush_thing_id].properties['brushing'].update( None )
                                    elif oralb_data["status"] == "IDLE":
                                        self.devices[toothbrush_thing_id].properties['brushing'].update( False )
                                    elif oralb_data["status"] == "RUN":
                                        self.devices[toothbrush_thing_id].properties['brushing'].update( True )
                                    else:
                                        self.devices[toothbrush_thing_id].properties['brushing'].update( None )
                        
                                    try:
                                        if privacy == True:
                                            self.devices[toothbrush_thing_id].properties['sector'].update( None )
                                        elif "_" in oralb_data["sector"]:
                                            sector = int(oralb_data["sector"].split("_",1)[1])
                                            self.devices[toothbrush_thing_id].properties['sector'].update( sector )
                                    except Exception as ex:
                                        if self.DEBUG:
                                            print("caught error updating Oral-B thing's sector: ", ex)
                                            
                                    try:
                                        if privacy == True:
                                            self.devices[toothbrush_thing_id].properties['sector_time'].update( None )
                                        else:
                                            self.devices[toothbrush_thing_id].properties['sector_time'].update( int(oralb_data["sector_time"]) )
                                    except Exception as ex:
                                        if self.DEBUG:
                                            print("caught error updating Oral-B thing's sector time: ", ex)
                
                                    try:
                                        print("----oralb_data[pressure]:", oralb_data["pressure"])
                                        if privacy == False and oralb_data["pressure"] != None:
                                            self.devices[toothbrush_thing_id].properties['pressure'].update( int(oralb_data["pressure"]) )
                                    except Exception as ex:
                                        if self.DEBUG:
                                            print("caught error updating Oral-B thing's pressure: ", ex)
                
                                except Exception as ex:
                                    if self.DEBUG:
                                        print("caught general error updating Oral-B thing: ", ex)
                                        
                            else:
                                if self.DEBUG:
                                    print("invalid Oral-B data")
                                    
                    except Exception as ex:
                        if self.DEBUG:
                            print("caught error handling gatherData: ", ex)
            except Exception as ex:
                if self.DEBUG:
                    print("caught error during gatherData loop: ", ex)        
            
            
        if self.DEBUG:
            print("Asyncio Oral-B main loop ended")
    
    
    
    
    
    async def toothbrush_scanner(self):
        
        if self.DEBUG:
            print("in toothbrush_scanner. self.running: ", self.running)
        
        async def oralb_discover():
            """Start looking for an OralB toothbrush."""
    
            found_oralb_toothbrushes = []
            try:
                #discovered_devices = await bleak.BleakScanner.discover(return_adv=True)
                discovered_devices = await bleak.BleakScanner.discover()
    
                #if self.DEBUG:
                #    print('discovered devices: ', len(discovered_devices))
                
                for discovered_device in discovered_devices:
                    if discovered_device.name and discovered_device.name == "Oral-B Toothbrush":
                        if self.DEBUG:
                            print("found Oral B toothbrush: ", discovered_device)
                        #return device
                        found_oralb_toothbrushes.append(discovered_device)
                #print("No Oral-B toothbrush detected")
        
        
            except Exception as ex:
                if self.DEBUG:
                    print("caught error while doing bluetooth scan: ", ex)
    
            return found_oralb_toothbrushes
            
            
            
        # MAIN SCANNER LOOP
        #print("self.running: ", self.running)
        while self.running:
            
            await asyncio.sleep(1)
            
            if self.pairing or self.continuous_scanning:
                if self.pairing and self.DEBUG:
                    print("toothbrush_scanner: currently in pairing mode")
                
                found_oralb_devices = await oralb_discover()
        
                if found_oralb_devices:
                    if self.DEBUG:
                        print("found Oral-B BLE devices: ", found_oralb_devices)
            
                    h = hashlib.new('sha256')
            
                    for oralb_device in found_oralb_devices:
                        #print("- name: ", oralb_device.name)
                        #print("oralb_device: ", oralb_device)
                        #print("dir oralb_device: ", dir(oralb_device))
                        #print("- address: ", oralb_device.address)
                        #print("- details: ", oralb_device.details)
                        #print("- metadata: ", oralb_device.metadata)
                        #print("- AdvertisementData: ", oralb_device.AdvertisementData)
                        #print("- AdvertisementData.rssi: ", oralb_device.AdvertisementData.rssi)
                
                        h.update(str(oralb_device.address).encode())
                
                        unique_hash = str(h.hexdigest())
                        short_hash = 'toothbrush_' + unique_hash[-6:]
                
                        #print(" - address hash: ", unique_hash)
                        #print(" - short hash: ", short_hash)
                
                
                        # Save Oral-B object for later use
                        if not short_hash in self.oralb_toothbrushes:
                            self.oralb_toothbrushes[short_hash] = OralB(oralb_device)
                
                
                        # Store data about this found toothbrush in persistent data
                        if not short_hash in self.persistent_data['toothbrushes']:
                            self.persistent_data['toothbrushes'][short_hash] = {
                                        'name':oralb_device.name,
                                        'address':oralb_device.address,
                                        'hash':unique_hash,
                                        'short_hash':short_hash,
                                        'brand':'oralb',
                                        'first_seen':time.time(),
                                        'last_seen':time.time(),
                                        'privacy':False,
                                        'brush_time_goal':0
                                    }
                    
                            self.save_persistent_data()
                
            
        if self.DEBUG:
            print("Asyncio Oral-B scanner loop ended")
    
    
    async def asyncio_main(self):
        await asyncio.gather(asyncio.create_task(self.oralb_main()), asyncio.create_task(self.toothbrush_scanner()))
        if self.DEBUG:
            print("Asyncio done")
    



    def start_pairing(self, timeout):
        self.pairing = True
        #asyncio.run(self.scan_for_oralb())

    def cancel_pairing(self):
        self.pairing = False
                    
        

    def unload(self):
        if self.DEBUG:
            print("Shutting down Toothbrush addon")
        #self.devices['toothbrush_thing'].connected = False
        #self.devices['toothbrush_thing'].connected_notify(False)
        self.running = False
        
        
        for toothbrush_thing_id, thingy in self.devices.items():
            try:
                if self.DEBUG:
                    print("disconnection-notifying Toothbrush thing with id: ", toothbrush_thing_id)
                self.devices[toothbrush_thing_id].connected = False
                self.devices[toothbrush_thing_id].connected_notify(False)
            except Exception as ex:
                if self.DEBUG:
                    print("unload: could not cleanly disconnect-notify toothbrush thing: ", ex)

    def remove_thing(self, device_id):
        if self.DEBUG:
            print("\n-----REMOVING thing with ID: " + str(device_id))
        
        obj = None
        try:
            obj = self.get_device(device_id)        
            if self.DEBUG:
                print("found device object via self.get_device")
        except Exception as ex:
            if self.DEBUG:
                print("Could not find thing via self.get_device: " + str(ex))
            obj = None
        
        
                
        if device_id in self.oralb_toothbrushes.keys():
            del self.oralb_toothbrushes[device_id]
            if self.DEBUG:
                print("Removed device from self.oralb_toothbrushes: ", device_id)
            
        if device_id in self.persistent_data['toothbrushes'].keys():
            del self.persistent_data['toothbrushes'][device_id]
            self.save_persistent_data()
            if self.DEBUG:
                print("Removed device from self.persistent_data: ", device_id)
        
        
        
        try:
            if obj:    
                self.handle_device_removed(obj)  # Remove from device dictionary
                if self.DEBUG:
                    print("Removed device via handle_device_removed")
        except Exception as ex:
            if self.DEBUG:
                print("Could not remove thing(s) from devices: " + str(ex))
        
        if device_id in self.devices.keys():
            del self.devices[device_id]
            if self.DEBUG:
                print("Removed device from self.devices: ", device_id)
        
        
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
    #  SAVE TO PERSISTENCE
    #

    def save_persistent_data(self):
        if self.DEBUG:
            print("Toothbrush: Saving to persistence data store at path: " + str(self.persistence_file_path))
        
        try:
            if not os.path.isfile(self.persistence_file_path):
                open(self.persistence_file_path, 'a').close()
                if self.DEBUG:
                    print("Created an empty persistence file")

            with open(self.persistence_file_path) as f:
                if self.DEBUG:
                    print("saving persistent data: " + str(self.persistent_data))
                json.dump( self.persistent_data, open( self.persistence_file_path, 'w+' ), indent=4 )
                return True

        except Exception as ex:
            if self.DEBUG:
                print("Error: could not store data in persistent store: " + str(ex) )
            return False
       


#
#  DEVICES
#

class ToothbrushDevice(Device):
    """Toothbrush device type."""

    def __init__(self, adapter, id='toothbrush_thing', title='Toothbrush'):
        """
        Initialize the object.
        adapter -- the Adapter managing this device
        """

        
        Device.__init__(self, adapter, id)
        #print("Creating Toothbrush thing.  id,title: ", id, title)
        
        self._id = id
        self.id = id
        self.adapter = adapter
        self._type.append('BinarySensor')

        self.name = id
        self.title = title
        self.description = 'Toothbrush thing'

        if self.adapter.DEBUG: 
            print("Toothbrush thing has been created.  ID, title: ", self.id, self.title)

        self.properties = {}
        # BooleanProperty
        
        """
        self.properties["state"] = ToothbrushProperty(
                        self,
                        "state",
                        {
                            "label": "State",
                            'type': 'boolean',
                            'readOnly': True,
                            '@type': 'BooleanProperty',
                        },
                        False)
        """
        
        self.properties["mode"] = ToothbrushProperty(
                        self,
                        "mode",
                        {
                            "label": "Mode",
                            'type': 'string',
                            'readOnly': True,
                        },
                        "")
        
        
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
                        
        self.properties["brush_time"] = ToothbrushProperty(
                        self,
                        "brush_time",
                        {
                            "label": "Brush time",
                            'type': 'integer',
                            'readOnly': True,
                        },
                        None)
                        
        brush_time_goal = 0
        try:
            if self.adapter.persistent_data['toothbrushes'][self.id]:
                if 'brush_time_goal' in self.adapter.persistent_data['toothbrushes'][self.id].keys() and str(type(self.adapter.persistent_data['toothbrushes'][self.id]['brush_time_goal'])) == "<class 'int'>":
                    brush_time_goal = int(self.adapter.persistent_data['toothbrushes'][self.id]['brush_time_goal'])
                    if self.adapter.DEBUG: 
                        print("found brush_time_goal preference in persistent data: ", brush_time_goal)
                        
        except Exception as ex:
            if self.adapter.DEBUG:
                print("no brush_time_goal preference found in persistant data for toothbrush: ", self.id, ", error was: ", ex)
        
        
        
        self.properties["brush_time_goal"] = ToothbrushProperty(
                        self,
                        "brush_time_goal",
                        {
                            "label": "Brush time goal",
                            'type': 'integer',
                            'readOnly': False,
                            'minimum':0,
                            'maximum':3600,
                        },
                        brush_time_goal)
        
        
        
        self.properties["goal_reached"] = ToothbrushProperty(
                        self,
                        "goal_reached",
                        {
                            "label": "Goal reached",
                            'type': 'boolean',
                            'readOnly': True,
                            #'@type': 'BooleanProperty',
                        },
                        None)
        
                        
                        
        self.properties["pressure"] = ToothbrushProperty(
                        self,
                        "pressure",
                        {
                            "label": "Pressure",
                            'type': 'integer',
                            'readOnly': True,
                        },
                        None)
        
        self.properties["sector"] = ToothbrushProperty(
                        self,
                        "sector",
                        {
                            "label": "Sector",
                            'type': 'integer',
                            'readOnly': True,
                        },
                        None)
                        
        self.properties["sector_time"] = ToothbrushProperty(
                        self,
                        "sector_time",
                        {
                            "label": "Sector time",
                            'type': 'integer',
                            'readOnly': True,
                        },
                        None)
        
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
        
        privacy_state = False
        try:
            if self.adapter.persistent_data['toothbrushes'][self.id]:
                if 'privacy' in self.adapter.persistent_data['toothbrushes'][self.id].keys():
                    if self.adapter.persistent_data['toothbrushes'][self.id]['privacy'] != None:
                        privacy_state = bool(self.adapter.persistent_data['toothbrushes'][self.id]['privacy'])
                        if self.adapter.DEBUG: 
                            print("found privacy preference in persistent data: ", privacy_state)
                        
        except Exception as ex:
            if self.adapter.DEBUG:
                print("no privacy preference found in persistant data for toothbrush: ", self.id, ", error was: ", ex)
        
        if self.adapter.DEBUG:
            print("initial privacy state of toothbrush: ", privacy_state)
        
        self.properties["privacy"] = ToothbrushProperty(
                        self,
                        "privacy",
                        {
                            "label": "Privacy",
                            'type': 'boolean',
                            'readOnly': False,
                        },
                        privacy_state)
        
        
        
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
        #print("in set_value for property: ", self.title)
        #print("set_value is called on a Toothbrush property by the UI. This should not be possible in this case?")
        
        if self.title == 'privacy':
            try:
                if value == None:
                    value = False
                if self.device.adapter.DEBUG: 
                    print("toothbrush privacy state is changing to: ", value)
                if self.device.adapter.persistent_data['toothbrushes'] and self.device.adapter.persistent_data['toothbrushes'][self.device.id]:
                    if self.device.adapter.persistent_data['toothbrushes'][self.device.id]['privacy'] and self.device.adapter.persistent_data['toothbrushes'][self.device.id]['privacy'] != None:
                        self.device.adapter.persistent_data['toothbrushes'][self.device.id]['privacy'] = bool(value)
                    else:
                        self.device.adapter.persistent_data['toothbrushes'][self.device.id]['privacy'] = bool(value)
                    self.device.adapter.save_persistent_data()
                        #print("saved privacy preference to persistent data")
                else:
                    if self.device.adapter.DEBUG: 
                        print("Error, device not found in persistent data?")
                
            except Exception as ex:
                if self.device.adapter.DEBUG: 
                    print("set_value: caught error: could not find toothbrush_thing_id?: ", self.device.id, ex)
        
        if self.title == 'brush_time_goal':
            try:
                if value == None:
                    value = 9
                    
                if self.device.adapter.persistent_data['toothbrushes'] and self.device.adapter.persistent_data['toothbrushes'][self.device.id]:
                    self.device.adapter.persistent_data['toothbrushes'][self.device.id]['brush_time_goal'] = int(value)
                    self.device.adapter.save_persistent_data()
                    #print("saved brush_time_goal preference to persistent data")
                
            except Exception as ex:
                if self.device.adapter.DEBUG: 
                    print("set_value: caught error: could not find toothbrush_thing_id?: ", self.device.id, ex)



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
            "pressure": None,
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
        except Exception as ex:
            _LOGGER.debug(f"{self.name}: Error connecting to device: ", ex)

    def _disconnected(self, client: BleakClient) -> None:
        """Disconnected callback."""
        print(
            f"{self.name}: Disconnected from device; RSSI: {self.ble_device.rssi}"
        )
        self.client = None

    async def gatherdata(self):
        """Connect to the OralB to get data."""
        if self.ble_device is None:
            #print("gatherdata: self.ble_device is None, aborting")
            return self.result
        if time.time() - self.prev_time < 1:
            #print("gatherdata: already scanned less than a second ago, aborting")
            return self.result
        self.prev_time = time.time()
        #print("gatherdata: trying to connect...")
        await self.connect()
        #print("gatherdata: connected!")
        chars = {
            # a0f0fff0-5047-4d53-8208-4f72616c2d42
            "a0f0ff08-5047-4d53-8208-4f72616c2d42": "time",
            "a0f0ff05-5047-4d53-8208-4f72616c2d42": "battery",
            "a0f0ff04-5047-4d53-8208-4f72616c2d42": "status",
            "a0f0ff07-5047-4d53-8208-4f72616c2d42": "mode",
            "a0f0ff09-5047-4d53-8208-4f72616c2d42": "sector",
            "a0f0ff0b-5047-4d53-8208-4f72616c2d42": "pressure",
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
        passive_pressures = {
            0: "normal",
            16: "normal",
            32: "normal",
            48: "normal",
            50: "normal",
            56: "power button pressed",
            80: "normal",
            82: "normal",
            86: "button pressed",
            90: "power button pressed",
            114: "normal",
            118: "button pressed",
            122: "power button pressed",
            144: "high",
            146: "high",
            150: "button pressed",
            154: "power button pressed",
            178: "high",
            182: "button pressed",
            186: "power button pressed",
            192: "high",
            240: "high",
            242: "high",
        }
        pressures = {
            0: -1, #"low", 
            1: 0, #"normal", 
            2: 1, #"high"
        }
       
        try:
            tasks = []
            if self.client:
                for char, _ in chars.items():
                    tasks.append(asyncio.create_task(self.client.read_gatt_char(char)))
                    #print("gatherdata: appended read task")
                results = await asyncio.gather(*tasks)
                #print("gatherdata: all tasks complete!")
                res_dict = dict(zip(chars.values(), results))
                print("res_dict: ", res_dict)


                self.result["brush_time"] = 60 * res_dict["time"][0] + res_dict["time"][1]
                self.result["battery"] = res_dict["battery"][0]
                self.result["status"] = statuses.get(res_dict["status"][0], "UNKNOWN")
                self.result["mode"] = modes.get(res_dict["mode"][0], "UNKNOWN")
                self.result["sector"] = sectors.get(res_dict["sector"][0], "UNKNOWN")
                self.result["sector_time"] = res_dict["sector"][1]
            
                try:
                    self.result["pressure"] = res_dict["pressure"][0] #int(res_dict["pressure"][0]) - 1 #pressures.get(, "UNKNOWN")
                    #self.result["pressure"] = pressures.get(res_dict["pressure"][0], None)
                except Exception as ex:
                    print(f"{self.name}: caught error getting pressure data: ", ex)
                    self.result["pressure"] = None
            
        except Exception as ex:
           print(f"{self.name}: Not connected to device: ", ex)
        
        #print("result: ", self.result)

        return self.result


