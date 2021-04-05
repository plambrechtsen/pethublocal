#import logging
import json, ast
import pethubpacket as phlp
import paho.mqtt.client as mqtt
from pethubconst import *

#logger = logging.getLogger(__file__)
#logging.basicConfig(level=logging.INFO)

#MQTT for pethublocal/hub and home assistant where the hub messages go, the broker sends the messages from the docker hub mqtt instance to your home assistant instance in the mosquitto.conf broker setting
mqtthost = '192.168.1.250'
mqttport = 1883
hubmsg_t = 'pethublocal/hub/messages'
pet_t = 'homeassistant/sensor/pethub/pet_'
device_sensor_t = 'homeassistant/sensor/pethub/device_'
device_switch_t = 'homeassistant/switch/pethub/device_'

# Feeder
def on_hub_message(client, obj, msg):
    print("Hub")

# Pet Door
def on_petdoor_message(client, obj, msg):
    print("Door " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))
    pethub = phlp.decodehubmqtt(msg.topic,msg.payload.decode("utf-8"))
    for values in pethub['message'][-1:][0].values():
        if "PetMovement" in values: #Pet Movement 
            msg = next((fm for fm in pethub['message'] if fm['OP'] == "PetMovement"), None)
            ret=mc.publish(pet_t + msg['Animal'].lower() + '/state',msg['Direction'])
        if "LockState" in values: #Lock state
            msg = next((fm for fm in pethub['message'] if fm['OP'] == "LockState"), None)
            if msg['Lock'] in ["LOCKED_IN","LOCKED_ALL"]:
                outlock = "ON"
            else:
                outlock = "OFF"
            if msg['Lock'] in ["LOCKED_OUT","LOCKED_ALL"]:
                inlock = "ON"
            else:
                inlock = "OFF"
            ret=mc.publish(device_switch_t+device[0].lower()+"_lock_outbound/state",outlock)
            ret=mc.publish(device_switch_t+device[0].lower()+"_lock_inbound/state",inlock)
    print(pethub)

# Feeder
def on_feeder_message(client, obj, msg):
    print("Feeder " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))
    pethub = phlp.decodehubmqtt(msg.topic,msg.payload.decode("utf-8"))
    msg = next((fm for fm in pethub['message'] if fm['OP'] == "Feed"), None)
    print("Feeder Message",msg)
    print("FA ",msg['FA'])
    if 'Animal_Closed' in msg['FA']:
        #Update feeder current weight
        bowl = {"state":msg['FA'], "left":msg['SLT'],"right":msg['SRT']}
        #print(bowl)
        ret=mc.publish(device_sensor_t+pethub['device'].lower()+'_bowl/state',json.dumps(bowl))

        #Update amount animal ate
        petbowl = {"time":msg['FOS'], "left":str(round(float(msg['SLT'])-float(msg['SLF']),2)),"right":str(round(float(msg['SRT'])-float(msg['SRF']),2))}
        print(petbowl)
        for key in petbowl:
            configmessage={"name": msg['Animal']+" "+key.replace('_', ' '), "icon": "mdi:bowl", "unique_id": "pet_"+msg['Animal'].lower()+"_"+key, "state_topic": pet_t+msg['Animal'].lower()+"_bowl/state", "value_template": "{{value_json."+key+" | round(2)}}"}
            ret=mc.publish(pet_t+msg['Animal'].lower()+'_'+key+'/config',json.dumps(configmessage))
        ret=mc.publish(pet_t+msg['Animal'].lower()+'_bowl/state',json.dumps(petbowl))
    else:
        print("Non animal close")
        bowl = {"state":msg['FA'], "left":msg['SLT'],"right":msg['SRT']}
        #ret=mc.publish(device_sensor_t+device[0].lower()+'_bowl/state',json.dumps(bowl))
        ret=mc.publish(device_sensor_t+pethub['device'].lower()+'_bowl/state',json.dumps(bowl))

# Cat Door
def on_catdoor_message(client, obj, msg):
    print("Cat Door " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))

# Missed Message.. this shouldn't happen so log it.
def on_message(client, obj, msg):
    print("OnMessage "  + msg.topic+" "+str(msg.qos)+" "+str(msg.payload))

def on_publish(cl,data,res):
    #print("data published ", res)
    pass

print("Starting Pet Hub")
mc = mqtt.Client()
mc.on_message = on_message
mc.on_publish = on_publish
print("Connecting to Home Assistant MQTT endpoint at " + mqtthost + " port " + str(mqttport))
mc.connect(mqtthost, mqttport, 30)

#Gather init data from pethublocal.db
pethubinit = phlp.inithubmqtt()
print(pethubinit)
print("Load Devices from pethublocal.db and init Home Assistant MQTT discovery configuration")
for device in pethubinit['devices']:

    if device[1] == 1: #Hub
        print("Loading Hub: ", device)
        mc.message_callback_add(hubmsg_t, on_hub_message)

    if device[1] == 3 or device[1] == 7: #Pet Door (3) or Cat Door (7)
        print("Loading Pet Door: ", device)
        mc.message_callback_add(hubmsg_t + '/' + device[2], on_petdoor_message)
        #Not setting the state as a sensor anymore
#        configmessage={"name": device[0], "icon": "mdi:door", "unique_id": "device_"+device[0].lower(), "state_topic": device_sensor_t + device[0].lower() + "/state"}
#        ret=mc.publish(device_sensor_t+device[0].lower()+'/config',json.dumps(configmessage))
#        ret=mc.publish(device_sensor_t+device[0].lower()+'/state',LockState(device[8]).name)
        #Curfew
        if device[5] != "None" and device[6] != "None" and device[7] != "None":
            curfewstate_t = "_curfew/state"
            curfewstate = {"curfew": CurfewState(device[5]).name, "lock_time":str(device[6]),"unlock_time":str(device[7])}
            #print(curfewstate)
            for key in curfewstate:
                #print(key)
                configmessage={"name": device[0]+" "+key.replace('_', ' '), "icon": "mdi:door", "unique_id": "device_"+device[0].lower()+"_"+key, "state_topic": device_sensor_t+device[0].lower()+"_curfew/state", "value_template": "{{value_json."+key+"}}"}
                ret=mc.publish(device_sensor_t+device[0].lower()+'_'+key+'/config',json.dumps(configmessage))
            ret=mc.publish(device_sensor_t+device[0].lower()+'_curfew/state',json.dumps(curfewstate))
        #Lock state as a switch
        if device[8] != "None":
            print("Door state ", device[8])
            lockstate = ["lock_outbound","lock_inbound"]
            #print(curfewstate)
            for key in lockstate:
                #print(key)
                configmessage={"name": device[0]+" "+key.replace('_', ' '), "icon": "mdi:door", "unique_id": "device_"+device[0].lower()+"_"+key, "command_topic": device_switch_t+device[0].lower()+"_"+key+"/set", "state_topic": device_switch_t+device[0].lower()+"_"+key+"/state" }
                ret=mc.publish(device_switch_t+device[0].lower()+"_"+key+'/config',json.dumps(configmessage))
            if device[8] in [1,3]:
                outlock = "ON"
            else:
                outlock = "OFF"
            if device[8] in [2,3]:
                inlock = "ON"
            else:
                inlock = "OFF"
            ret=mc.publish(device_switch_t+device[0].lower()+"_lock_outbound/state",outlock)
            ret=mc.publish(device_switch_t+device[0].lower()+"_lock_inbound/state",inlock)

    if device[1] == 4: #Feeder
        print("Loading Feeder: ", device)
        mc.message_callback_add(hubmsg_t + '/' + device[2], on_feeder_message)
        if device[9] != "None":
            if device[10] != "None":
                bowltargetstate = {"left_target": str(device[9]),"right_target":str(device[10])}
                for key in bowltargetstate:
                    configmessage={"name": device[0]+" "+key.replace('_', ' '), "icon": "mdi:bowl", "unique_id": "device_"+device[0].lower()+"_"+key, "state_topic": device_sensor_t+device[0].lower()+"_bowl_target/state", "value_template": "{{value_json."+key+"}}"}
                    ret=mc.publish(device_sensor_t+device[0].lower()+'_'+key+'/config',json.dumps(configmessage))
                ret=mc.publish(device_sensor_t+device[0].lower()+'_bowl_target/state',json.dumps(bowltargetstate))
                bowl = {"state":"TBC", "left":"0","right":"0"}
                for key in bowl:
                    configmessage={"name": device[0]+" "+key.replace('_', ' '), "icon": "mdi:bowl", "unique_id": "device_"+device[0].lower()+"_"+key, "state_topic": device_sensor_t+device[0].lower()+"_bowl/state", "value_template": "{{value_json."+key+"}}"}
                    ret=mc.publish(device_sensor_t+device[0].lower()+'_'+key+'/config',json.dumps(configmessage))
                ret=mc.publish(device_sensor_t+device[0].lower()+'_bowl/state',json.dumps(bowl))
            else:
                configmessage={"name": device[0]+" bowl target", "icon": "mdi:bowl", "unique_id": "device_"+device[0].lower()+"_bowl_target", "state_topic": device_sensor_t+device[0].lower()+"_bowl_target/state"}
                ret=mc.publish(device_sensor_t+device[0].lower()+'_bowl_target/config',json.dumps(configmessage))
                ret=mc.publish(device_sensor_t+device[0].lower()+'_bowl_target/state',str(device[9]))

print("Load Pets from pethublocal.db and init Home Assistant MQTT discovery configuration")
for pet in pethubinit['pets']:
    if pet[3] == 3: #Pet Door
        print("Loading Pet: " + pet[0] + " for feeder " + pet[2] )
        configmessage={"name": pet[0], "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower(), "state_topic": pet_t+pet[0].lower()+"/state"}
        ret=mc.publish(pet_t+pet[0].lower()+'/config',json.dumps(configmessage))
        ret=mc.publish(pet_t+pet[0].lower()+'/state',str(AnimalState(pet[4]).name))

    if pet[3] == 4: #Feeder
        print("Loading Pet: " + pet[0] + " for pet door " + pet[2] )
        feederarray = ast.literal_eval(pet[4])
        if len(feederarray)==2:
            bowlstate = {"left":str(feederarray[0]),"right":str(feederarray[1])}
            print(bowlstate)
            for key in bowl:
                configmessage={"name": pet[0]+" "+key, "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower()+"_"+key, "state_topic": pet_t+pet[0].lower()+"_bowl/state", "unit_of_measurement": "g", "value_template": "{{value_json."+key+"}}"}
                ret=mc.publish(pet_t+pet[0].lower()+'_'+key+'/config',json.dumps(configmessage))
            ret=mc.publish(pet_t+pet[0].lower()+'_bowl/state',json.dumps(bowlstate))
        else:
            configmessage={"name": device[0]+" bowl target", "icon": "mdi:bowl", "unique_id": "device_"+device[0].lower()+"_bowl_target", "state_topic": device_sensor_t+device[0].lower()+"_bowl_target/state"}
            ret=mc.publish(pet_t+pet[0].lower()+'_bowl/config',json.dumps(configmessage))
            ret=mc.publish(pet_t+pet[0].lower()+'_bowl/state',str(pet[4]))

#Publish callback
print("Subscribe to pethublocal and home assistant topics")
mc.subscribe([("pethublocal/#",1), ("homeassistant/+/pethub/+/state", 0), ("homeassistant/+/pethub/+/set", 0)])
mc.loop_forever()
