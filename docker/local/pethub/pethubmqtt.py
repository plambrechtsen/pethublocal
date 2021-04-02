#import logging
import asyncio, json, ast
import pethubpacket as phlp
from enum import IntEnum

from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_0, QOS_1, QOS_2

#logger = logging.getLogger(__file__)
#logging.basicConfig(level=logging.WARN)

#MQTT for pethublocal/hub where the hub messages go
mqtt_hub = 'mqtt://192.168.1.251/'
#mqtt_hub = 'mqtt://mqtt/'
mqtt_hubtopic = 'pethublocal/hub/#'

#MQTT for Home Assistant
mqtt_local = 'mqtt://192.168.1.250/'
mqtt_local_t = 'homeassistant/'


class SureEnum(IntEnum):
    """Sure base enum."""
    def __str__(self) -> str:
        return self.name.title()

    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_ 

class Animal(SureEnum): # Animal mdi mapping
    alien        = 0
    cat          = 1
    dog          = 2

class AnimalState(SureEnum): # Animal State
    Outside          = 0
    Inside           = 1

class LockState(SureEnum): # Lock State IDs.
    UNLOCKED        = 0
    LOCKED_IN       = 1
    LOCKED_OUT      = 2
    LOCKED_ALL      = 3
    CURFEW          = 4

class CurfewState(SureEnum): # Sure Petcare API State IDs.
    DISABLED        = 0
    ENABLED         = 1
    STATE2          = 2
    STATE3          = 3

async def hubtolocal(hub_url, local_url, loop):
    print("Pethublocal MQTT HubToLocal Listner starting")
    hub = MQTTClient(loop=loop, config={'keep_alive': 60})
    local = MQTTClient(loop=loop, config={'keep_alive': 60})
    processingmessage = False
    try:
        await hub.connect(hub_url)
        await local.connect(local_url)
        await hub.subscribe([ (mqtt_hubtopic, QOS_1) ])
        pethubinit = phlp.inithubmqtt()
        print(pethubinit)
        for pet in pethubinit['pets']:
            print(pet)
            if pet[3] == 3: #Pet Door
                configmessage={"name": pet[0], "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower(), "state_topic": mqtt_local_t + "sensor/pethub/pet_"+pet[0].lower()+"/state"}
                asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'/config', message=json.dumps(configmessage).encode('utf-8'), qos=QOS_0))
                asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'/state', message=AnimalState(pet[4]).name.encode('utf-8'), qos=QOS_0))
            if pet[3] == 4: #Feeder
                feederarray = ast.literal_eval(pet[4])
                if len(feederarray)==2:
                    bowlstate = {"left":str(feederarray[0]),"right":str(feederarray[1])}
                    print(bowlstate)
                    leftconfigmessage={"name": pet[0]+" left", "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower()+"_left", "state_topic": mqtt_local_t + "sensor/pethub/pet_"+pet[0].lower()+"_bowl/state", "unit_of_measurement": "g", "value_template": "{{value_json.left}}"}
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'_left/config', message=json.dumps(leftconfigmessage).encode('utf-8'), qos=QOS_0))
                    rightconfigmessage={"name": pet[0]+" right", "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower()+"_right", "state_topic": mqtt_local_t + "sensor/pethub/pet_"+pet[0].lower()+"_bowl/state", "unit_of_measurement": "g", "value_template": "{{value_json.right}}"}
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'_right/config', message=json.dumps(rightconfigmessage).encode('utf-8'), qos=QOS_0))
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'_bowl/state', message=json.dumps(bowlstate).encode('utf-8'), qos=QOS_0))
                else:
                    bowlconfigmessage={"name": pet[0]+" bowl", "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower()+"_bowl", "state_topic": mqtt_local_t + "binary_sensor/pethub/pet_"+pet[0].lower()+"_bowl/state"}
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'_bowl/config', message=json.dumps(bowlconfigmessage).encode('utf-8'), qos=QOS_0))
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'_bowl/state', message=pet[4].encode('utf-8'), qos=QOS_0))
        for device in pethubinit['devices']:
            print(device)
            if device[1] == 3: #Pet Door
                print(device[7])
                configmessage={"name": device[0], "icon": "mdi:door", "unique_id": "device_"+device[0].lower(), "state_topic": mqtt_local_t + "sensor/pethub/device_"+device[0].lower()+"/state"}
                asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/device_'+device[0].lower()+'/config', message=json.dumps(configmessage).encode('utf-8'), qos=QOS_0))
                asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/device_'+device[0].lower()+'/state', message=LockState(device[7]).name.encode('utf-8'), qos=QOS_0))
                if device[4] != "None" and device[5] != "None" and device[6] != "None":
                    curfewstate = {"state": CurfewState(device[4]).name, "lock":str(device[5]),"unlock":str(device[6])}
                    print(curfewstate)
                    configmessage={"name": device[0]+" curfew", "icon": "mdi:door", "unique_id": "device_"+device[0].lower()+"_curfew", "state_topic": mqtt_local_t + "sensor/pethub/device_"+device[0].lower()+"_curfew/state", "value_template": "{{value_json.state}}"}
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/device_'+device[0].lower()+'_curfew/config', message=json.dumps(configmessage).encode('utf-8'), qos=QOS_0))
                    configmessage={"name": device[0]+" lock time", "icon": "mdi:door", "unique_id": "device_"+device[0].lower()+"_lock_time", "state_topic": mqtt_local_t + "sensor/pethub/device_"+device[0].lower()+"_curfew/state", "value_template": "{{value_json.lock}}"}
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/device_'+device[0].lower()+'_lock/config', message=json.dumps(configmessage).encode('utf-8'), qos=QOS_0))
                    configmessage={"name": device[0]+" unlock time", "icon": "mdi:door", "unique_id": "device_"+device[0].lower()+"_unlock_time", "state_topic": mqtt_local_t + "sensor/pethub/device_"+device[0].lower()+"_curfew/state", "value_template": "{{value_json.unlock}}"}
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/device_'+device[0].lower()+'_unlock/config', message=json.dumps(configmessage).encode('utf-8'), qos=QOS_0))
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/device_'+device[0].lower()+'_curfew/state', message=json.dumps(curfewstate).encode('utf-8'), qos=QOS_0))
                
        while True:
            if processingmessage == False:
                message = await hub.deliver_message()
            processingmessage = True
            packet = message.publish_packet
            topic_name = packet.variable_header.topic_name
            data = packet.payload.data
            qos = packet.qos
            print(f"TOPIC: {topic_name} QOS: {qos} MESSAGE: {data}")
            pethub = phlp.decodehubmqtt(topic_name,data.decode())
            #The cloud service replays the message back to the hub for some reason, so we should do that. Disabling as it causes loops because of asyncio operations.
            #if processingmessage == True:
            #    asyncio.create_task(hub.publish(topic=topic_name, message=data, qos=QOS_1))

            #Grab the last value which contains an array of all operations
            for values in pethub['message'][-1:][0].values():
#                if "Ack" in values:
#                    print
                if "Feed" in values: #Feeder Message
                    feedermsg = next((fm for fm in pethub['message'] if fm['OP'] == "Feed"), None)
                    print("Feeder Message",feedermsg)
                    localtopic = mqtt_local_t + pethub['device'] + '/' + feedermsg['Animal'] + '/'
                    asyncio.create_task(local.publish(topic=localtopic + 'action', message=feedermsg['FA'].encode('utf-8') , qos=QOS_0))
                    asyncio.create_task(local.publish(topic=localtopic + 'feedtime', message=feedermsg['FOS'].encode('utf-8') , qos=QOS_0))
                    asyncio.create_task(local.publish(topic=localtopic + 'leftfrom', message=feedermsg['SLF'].encode('utf-8') , qos=QOS_0))
                    asyncio.create_task(local.publish(topic=localtopic + 'leftto', message=feedermsg['SLT'].encode('utf-8') , qos=QOS_0))
                    if feedermsg['BC'] > 1:
                        asyncio.create_task(local.publish(topic=localtopic + 'rightfrom', message=feedermsg['SRF'].encode('utf-8') , qos=QOS_0))
                        asyncio.create_task(local.publish(topic=localtopic + 'rightto', message=feedermsg['SRT'].encode('utf-8') , qos=QOS_0))
                if "PetMovement" in values: #Pet Movement 
                    msg = next((fm for fm in pethub['message'] if fm['OP'] == "PetMovement"), None)
                    localtopic = mqtt_local_t + pethub['device'] + '/' + msg['Animal'] + '/'
                    asyncio.create_task(local.publish(topic=mqtt_local_t + 'binary_sensor/pethub/pet_'+pet[0].lower()+'/state', message=msg['State'].encode('utf-8') , qos=QOS_0))
#                    asyncio.create_task(local.publish(topic=localtopic + 'offset', message=msg['PetOffset'].encode('utf-8') , qos=QOS_0))
            processingmessage = False
            print(pethub)
    except asyncio.CancelledError:
        await hub.unsubscribe(['pethublocal/hub/#'])
        await hub.disconnect()
        #logger.debug("DISCONNECTED======================")
        print("DISCONNECTED======================")
    except ClientException as ce:
        #logger.exception("Client exception: %s" % ce)
        print("Client exception: %s" % ce)

async def stop(self):
    print('Stopping mqttrpc...')
    #logger.info('Stopping mqttrpc...')
    # Check subscriptions
    if self._connected_state.is_set():        
        await self.unsubscribe(self.subscriptions)
        await self.disconnect()
    tasks = [task for task in asyncio.Task.all_tasks() if task is not
                asyncio.tasks.Task.current_task()]
    list(map(lambda task: task.cancel(), tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    print('Finished cancelling tasks, result: {}'.format(results))
    #logger.debug('Finished cancelling tasks, result: {}'.format(results))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    reader = loop.create_task(hubtolocal(mqtt_hub, mqtt_local, loop))
    try:
        loop.run_until_complete(reader)
    except KeyboardInterrupt:
        print("KEYBOARD INTERRUPT==================")
        #logger.info("KEYBOARD INTERRUPT==================")
        reader.cancel()
        #logger.info("READER CANCELLED==================")
        loop.run_until_complete(reader)
        #logger.info("FINISHED LOOP==================")
    finally:
        loop.close()
