import logging
import asyncio
import pethubpacket as phlp

from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_0, QOS_1, QOS_2

logger = logging.getLogger(__file__)
logging.basicConfig(level=logging.WARN)

#MQTT for pethublocal/hub where the hub messages go
mqtt_hub = 'mqtt://mqtt/'
#MQTT for Home Assistant
mqtt_local = 'mqtt://192.168.1.251/'
mqtt_local_t = 'pethublocal/local/'


async def hubtolocal(hub_url, local_url, loop):
    hub = MQTTClient(loop=loop, config={'keep_alive': 60})
    local = MQTTClient(loop=loop, config={'keep_alive': 60})
    try:
        await hub.connect(hub_url)
        await local.connect(local_url)
        await hub.subscribe([ ('pethublocal/hub/#', QOS_1) ])
        while True:
            message = await hub.deliver_message()
            packet = message.publish_packet
            topic_name = packet.variable_header.topic_name
            data = packet.payload.data
            qos = packet.qos
            print(f"TOPIC: {topic_name} QOS: {qos} MESSAGE: {data}")
            pethub = phlp.decodehubmqtt(topic_name,data.decode())
            for values in pethub['message'][-1:][0].values():
                if "Feed" in values:
                    localtopic = mqtt_local_t + pethub['device'] + '/' + pethub['message'][0][0]['Animal'] + '/'
                    asyncio.create_task(local.publish(topic=localtopic + 'action', message=pethub['message'][0][0]['FA'].encode('utf-8') , qos=QOS_0))
                    asyncio.create_task(local.publish(topic=localtopic + 'feedtime', message=pethub['message'][0][0]['FOS'].encode('utf-8') , qos=QOS_0))
                    asyncio.create_task(local.publish(topic=localtopic + 'leftfrom', message=pethub['message'][0][0]['SLF'].encode('utf-8') , qos=QOS_0))
                    asyncio.create_task(local.publish(topic=localtopic + 'leftto', message=pethub['message'][0][0]['SLT'].encode('utf-8') , qos=QOS_0))
                    if pethub['message'][0][0]['BC'] > 1:
                        asyncio.create_task(local.publish(topic=localtopic + 'rightfrom', message=pethub['message'][0][0]['SRF'].encode('utf-8') , qos=QOS_0))
                        asyncio.create_task(local.publish(topic=localtopic + 'rightto', message=pethub['message'][0][0]['SRT'].encode('utf-8') , qos=QOS_0))
#                if "PetMovement" in values:
#                    print(pethub)
#                   print(pethub['message'][0])
#                    localtopic = mqtt_local_t + pethub['device'] 
                    #+ '/' + pethub['message'][0][0]['Animal'] + "/"
                    #asyncio.create_task(local.publish(topic=localtopic + 'direction', message=pethub['message'][0][0]['Direction'].encode('utf-8') , qos=QOS_0))
            print(pethub)
    except asyncio.CancelledError:
        await hub.unsubscribe(['pethublocal/hub/#'])
        await hub.disconnect()
        logger.debug("DISCONNECTED======================")
    except ClientException as ce:
        logger.exception("Client exception: %s" % ce)

async def stop(self):
    logger.info('Stopping mqttrpc...')
    # Check subscriptions
    if self._connected_state.is_set():        
        await self.unsubscribe(self.subscriptions)
        await self.disconnect()
    tasks = [task for task in asyncio.Task.all_tasks() if task is not
                asyncio.tasks.Task.current_task()]
    list(map(lambda task: task.cancel(), tasks))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    logger.debug('Finished cancelling tasks, result: {}'.format(results))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    reader = loop.create_task(hubtolocal(mqtt_hub, mqtt_local, loop))
    try:
        loop.run_until_complete(reader)
    except KeyboardInterrupt:
        logger.info("KEYBOARD INTERRUPT==================")
        reader.cancel()
        logger.info("READER CANCELLED==================")
        loop.run_until_complete(reader)
        logger.info("FINISHED LOOP==================")
    finally:
        loop.close()
