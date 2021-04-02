#import logging
import asyncio, json
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
                #configmessage='{"name": "{0} inside", "unique_id": "pet_{1}_inside", "icon": "mdi:{2}", "state_topic": "homeassistant/sensor/pethub/pet_{1}_fed1/state"}'.format(pet[0],pet[0].lower(),Animal(pet[1]))
                #configmessage={"name": pet[0]+" inside", "device_class": "occupancy", "unique_id": "pet_"+pet[0].lower(), "state_topic": mqtt_local_t + "sensor/pethub/pet_"+pet[0].lower()+"/state"}
                configmessage={"name": pet[0], "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower(), "state_topic": mqtt_local_t + "sensor/pethub/pet_"+pet[0].lower()+"/state"}
                print(configmessage)
                asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'/config', message=json.dumps(configmessage).encode('utf-8'), qos=QOS_0))
                asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'/state', message=AnimalState(pet[4]).name.encode('utf-8'), qos=QOS_0))
                #asyncio.create_task(local.publish(topic=localtopic + 'action', message=feedermsg['FA'].encode('utf-8') , qos=QOS_0))
                #print(pet[3])
                #sensor/pethub/pet_Wicket_fed1/config'
                #asyncio.create_task(local.publish(topic=localtopic + 'action', message=feedermsg['FA'].encode('utf-8') , qos=QOS_0))
#            if pet[3] == 4: #Feeder
                #configmessage='{"name": "{0} inside", "unique_id": "pet_{1}_inside", "icon": "mdi:{2}", "state_topic": "homeassistant/sensor/pethub/pet_{1}_fed1/state"}'.format(pet[0],pet[0].lower(),Animal(pet[1]))
#                configmessage={"name": pet[0]+" feed", "unique_id": "pet_"+pet[0].lower(), "icon": "mdi:{2}", "state_topic": mqtt_local_t + "binary_sensor/pethub/pet_"+pet[0].lower()+"/state"}
#                print(configmessage)
#                asyncio.create_task(local.publish(topic=mqtt_local_t + 'sensor/pethub/pet_'+pet[0].lower()+'_feed/config', message=json.dumps(configmessage).encode('utf-8'), qos=QOS_0))
#                asyncio.create_task(local.publish(topic=mqtt_local_t + 'binary_sensor/pethub/pet_'+pet[0].lower()+'/state', message=AnimalState(pet[4]).name.encode('utf-8'), qos=QOS_0))
                
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
