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
hubmsg_t = 'pethublocal/messages'
pet_t = 'homeassistant/sensor/pethub/pet_'
device_sensor_t = 'homeassistant/sensor/pethub/device_'
device_switch_t = 'homeassistant/switch/pethub/device_'

# Feeder
def on_hub_message(client, obj, msg):
    print("Hub  " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))

# Pet Door
def on_petdoor_message(client, obj, msg):
    print("Door " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))
    pethub = phlp.decodehubmqtt(msg.topic,msg.payload.decode("utf-8"))
    for values in pethub['message'][-1:][0].values():
        if "PetMovement" in values: #Pet Movement 
            mv = next((fm for fm in pethub['message'] if fm['OP'] == "PetMovement"), None)
            ret=mc.publish(pet_t + mv['Animal'].lower() + '/state',mv['Direction'])
        if "LockState" in values: #Lock state
            mv = next((fm for fm in pethub['message'] if fm['OP'] == "LockState"), None)
            if mv['Lock'] in ["LOCKED_IN","LOCKED_ALL"]:
                outlock = "ON"
            else:
                outlock = "OFF"
            if mv['Lock'] in ["LOCKED_OUT","LOCKED_ALL"]:
                inlock = "ON"
            else:
                inlock = "OFF"
            ret=mc.publish(device_switch_t+devl+"_lock_outbound/state",outlock)
            ret=mc.publish(device_switch_t+devl+"_lock_inbound/state",inlock)
            topicsplit = msg.topic.split("/")
            print(topicsplit[-1])
            lockmsg = phlp.updatedb('doors',topicsplit[-1],'lockingmode', mv['Lock'])
            print(lockmsg)

# Pet Door Lock Update State
def on_petdoor_lock_message(client, obj, msg):
    print("Door Lock " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))
    topicsplit = msg.topic.split("/")
    #print(topicsplit[3])
    devname=topicsplit[3].split("_")
    #print(devname[1])
    lockmsg = phlp.generatemessage("petdoor", devname[1], devname[3], str(msg.payload,"utf-8"))
    #print(lockmsg)
    ret=mc.publish(lockmsg['topic'],lockmsg['msg'],qos=1)

# Pet Door Curfew
def on_petdoor_curfew_message(client, obj, msg):
    print("Door Curfew " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))
#    print(p.generatemessage("hub", "flashleds"))
#    ret=mc.publish('pethublocal/messages',p.generatemessage("hub", "flashleds"),qos=1)
#    print(ret)
    print(pethubinit)

# Feeder
def on_feeder_message(client, obj, msg):
    print("Feeder " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))
    pethub = phlp.decodehubmqtt(msg.topic,msg.payload.decode("utf-8"))
#    print(pethub)
    for values in pethub['message'][-1:][0].values():
        if "Feed" in values:
            mv = next((fm for fm in pethub['message'] if fm['OP'] == "Feed"), None)
            print("Feeder Message",mv)
            if 'Animal_Closed' in mv['FA']:
                #Update feeder current weight
                bowl = {"state":mv['FA'], "left":mv['SLT'],"right":mv['SRT']}
                #print(bowl)
                ret=mc.publish(device_sensor_t+pethub['device'].lower()+'_bowl/state',json.dumps(bowl))

                #Update amount animal ate
                petbowl = {"time":mv['FOS'], "left":str(round(float(mv['SLT'])-float(mv['SLF']),2)),"right":str(round(float(mv['SRT'])-float(mv['SRF']),2))}
                print(petbowl)
                for key in petbowl:
                    configmessage={"name": mv['Animal']+" "+key.replace('_', ' '), "icon": "mdi:bowl", "unique_id": "pet_"+mv['Animal'].lower()+"_"+key, "state_topic": pet_t+mv['Animal'].lower()+"_bowl/state", "value_template": "{{value_json."+key+" | round(2)}}"}
                    ret=mc.publish(pet_t+mv['Animal'].lower()+'_'+key+'/config',json.dumps(configmessage))
                ret=mc.publish(pet_t+mv['Animal'].lower()+'_bowl/state',json.dumps(petbowl))
            else:
                #print("Non animal close")
                bowl = {"state":mv['FA'], "left":mv['SLT'],"right":mv['SRT']}
                #ret=mc.publish(device_sensor_t+devl+'_bowl/state',json.dumps(bowl))
                ret=mc.publish(device_sensor_t+pethub['device'].lower()+'_bowl/state',json.dumps(bowl))

'''
    print("FA ",msg['FA'])
'''

# Cat Door
def on_catdoor_message(client, obj, msg):
    print("Cat Door " + msg.topic+" "+str(msg.qos)+" "+msg.payload.decode("utf-8"))


# Missed Message.. this shouldn't happen so log it.
def on_message(client, obj, msg):
    print("**Not Matched** "  + msg.topic+" "+str(msg.qos)+" "+str(msg.payload))

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
    dev=device[0]
    devl=device[0].lower()

    if device[1] == 1: #Hub
        print("Loading Hub: ", device)
        mc.message_callback_add(hubmsg_t, on_hub_message)

    if device[1] == 3: #Pet Door (3) or Cat Door (7)
        print("Loading Pet Door: ", device)
        mc.message_callback_add(hubmsg_t + '/' + device[2], on_petdoor_message)
        mc.message_callback_add(device_switch_t+devl+"_lock_inbound/set", on_petdoor_lock_message)
        mc.message_callback_add(device_switch_t+devl+"_lock_outbound/set", on_petdoor_lock_message)
        mc.message_callback_add(device_switch_t+devl+"_curfew/set", on_petdoor_curfew_message)

        #Not setting the state as a sensor anymore
#        configmessage={"name": device[0], "icon": "mdi:door", "unique_id": "device_"+devl, "state_topic": device_sensor_t + devl + "/state"}
#        ret=mc.publish(device_sensor_t+devl+'/config',json.dumps(configmessage))
#        ret=mc.publish(device_sensor_t+devl+'/state',LockState(device[8]).name)
        #Curfew
        if device[5] != "None" and device[6] != "None" and device[7] != "None":
            #Curfew State Switch
            configmessage={"name": dev+" Curfew", "icon": "mdi:door", "unique_id": "device_"+devl+"_curfew", "command_topic": device_switch_t+devl+"_curfew/set", "state_topic": device_switch_t+devl+"_curfew/state" }
            ret=mc.publish(device_switch_t+devl+"_"+key+'/config',json.dumps(configmessage))
            ret=mc.publish(device_switch_t+devl+'_curfew/state',json.dumps(CurfewState(device[5]).name))

            #Curfew State Times
            curfewstate = {"lock_time":str(device[6]),"unlock_time":str(device[7])}
            for key in curfewstate:
                configmessage={"name": dev+" "+key.replace('_', ' '), "icon": "mdi:door", "unique_id": "device_"+devl+"_"+key, "state_topic": device_sensor_t+devl+"_curfew/state", "value_template": "{{value_json."+key+"}}"}
                ret=mc.publish(device_sensor_t+devl+'_'+key+'/config',json.dumps(configmessage))
        #Lock state as a switch
        if device[8] != "None":
            print("Door state ", device[8])
            lockstate = ["lock_outbound","lock_inbound"]
            #print(curfewstate)
            for key in lockstate:
                #print(key)
                configmessage={"name": dev+" "+key.replace('_', ' '), "icon": "mdi:door", "unique_id": "device_"+devl+"_"+key, "command_topic": device_switch_t+devl+"_"+key+"/set", "state_topic": device_switch_t+devl+"_"+key+"/state" }
                ret=mc.publish(device_switch_t+devl+"_"+key+'/config',json.dumps(configmessage))
            if device[8] in [1,3]:
                outlock = "ON"
            else:
                outlock = "OFF"
            if device[8] in [2,3]:
                inlock = "ON"
            else:
                inlock = "OFF"
            ret=mc.publish(device_switch_t+devl+"_lock_outbound/state",outlock)
            ret=mc.publish(device_switch_t+devl+"_lock_inbound/state",inlock)

    if device[1] == 4: #Feeder
        print("Loading Feeder: ", device)
        mc.message_callback_add(hubmsg_t + '/' + device[2], on_feeder_message)
        if device[9] != "None":
            if device[10] != "None":
                bowltargetstate = {"left_target": str(device[9]),"right_target":str(device[10])}
                for key in bowltargetstate:
                    configmessage={"name": dev+" "+key.replace('_', ' '), "icon": "mdi:bowl", "unique_id": "device_"+devl+"_"+key, "state_topic": device_sensor_t+devl+"_bowl_target/state", "value_template": "{{value_json."+key+"}}"}
                    ret=mc.publish(device_sensor_t+devl+'_'+key+'/config',json.dumps(configmessage))
                ret=mc.publish(device_sensor_t+devl+'_bowl_target/state',json.dumps(bowltargetstate))
                bowl = {"state":"TBC", "left":"0","right":"0"}
                for key in bowl:
                    configmessage={"name": dev+" "+key.replace('_', ' '), "icon": "mdi:bowl", "unique_id": "device_"+devl+"_"+key, "state_topic": device_sensor_t+devl+"_bowl/state", "value_template": "{{value_json."+key+"}}"}
                    ret=mc.publish(device_sensor_t+devl+'_'+key+'/config',json.dumps(configmessage))
                ret=mc.publish(device_sensor_t+devl+'_bowl/state',json.dumps(bowl))
            else:
                configmessage={"name": dev+" bowl target", "icon": "mdi:bowl", "unique_id": "device_"+devl+"_bowl_target", "state_topic": device_sensor_t+devl+"_bowl_target/state"}
                ret=mc.publish(device_sensor_t+devl+'_bowl_target/config',json.dumps(configmessage))
                ret=mc.publish(device_sensor_t+devl+'_bowl_target/state',str(device[9]))

print("Load Pets from pethublocal.db and init Home Assistant MQTT discovery configuration")
for pet in pethubinit['pets']:
    if pet[3] == 3: #Pet Door
        print("Loading Pet: " + pet[0] + " for pet door " + pet[2] )
        configmessage={"name": pet[0], "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower(), "state_topic": pet_t+pet[0].lower()+"/state"}
        ret=mc.publish(pet_t+pet[0].lower()+'/config',json.dumps(configmessage))
        ret=mc.publish(pet_t+pet[0].lower()+'/state',str(AnimalState(pet[4]).name))

    if pet[3] == 4: #Feeder
        print("Loading Pet: " + pet[0] + " for feeder " + pet[2] )
        feederarray = ast.literal_eval(pet[4])
        if len(feederarray)==2:
            bowlstate = {"left":str(feederarray[0]),"right":str(feederarray[1])}
            print(bowlstate)
            for key in bowl:
                configmessage={"name": pet[0]+" "+key, "icon": "mdi:"+Animal(pet[1]).name, "unique_id": "pet_"+pet[0].lower()+"_"+key, "state_topic": pet_t+pet[0].lower()+"_bowl/state", "unit_of_measurement": "g", "value_template": "{{value_json."+key+"}}"}
                ret=mc.publish(pet_t+pet[0].lower()+'_'+key+'/config',json.dumps(configmessage))
            ret=mc.publish(pet_t+pet[0].lower()+'_bowl/state',json.dumps(bowlstate))
#        else:
            #configmessage={"name": device[0]+" bowl target", "icon": "mdi:bowl", "unique_id": "device_"+devl+"_bowl_target", "state_topic": device_sensor_t+devl+"_bowl_target/state"}
            #ret=mc.publish(pet_t+pet[0].lower()+'_bowl/config',json.dumps(configmessage))
            #ret=mc.publish(pet_t+pet[0].lower()+'_bowl/state',str(pet[4]))

#Publish callback
print("Subscribe to pethublocal and home assistant topics")
mc.subscribe([("pethublocal/#",1), ("homeassistant/+/pethub/+/state", 0), ("homeassistant/+/pethub/+/set", 0)])
mc.loop_forever()
