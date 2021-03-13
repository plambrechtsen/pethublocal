#include <Arduino.h>
#include <SPI.h>
#include "mrf24j.h"
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include "main.h"

//Time
#include <sys/time.h>                   // struct timeval
#include <time.h>                       // time() ctime()         1)

//MRF Pins
#if defined(ESP8266)
  const int pin_reset = D4;
  const int pin_cs = D0;
  const int pin_interrupt = D3;
#else
  const int pin_reset = 16;
  const int pin_cs = 26;
  const int pin_interrupt = 17;
#endif

//WiFi
#if defined(ESP8266)
  #include <ESP8266WiFi.h>
  #include <ESP8266WebServer.h>
#else
  #include <WiFi.h>
  #include <WebServer.h>
#endif

//MQTT
WiFiClient espClient;
PubSubClient mqttClient(espClient); //lib required for mqtt

//MQTT Callback
void callback(char* topic, byte* payload, unsigned int length);
char MQTTTopic[18] = "pethublocal/local";
#define MQTTClientID "PetHubLocal"


//System LED to flash
int LED = 02;

char hexval[8];

//boolean message_received = false;
boolean mqtt_msg_received = false;

//MRF Buffers
char rx_buffer[127];
uint8_t tx_buffer[127];
uint8_t mqtt_rx_topic[3];
uint8_t mqtt_rx_payload[16];  // TBD

//Received Packet Sequence counter
byte _TXPacketSeqNo;

typedef struct _device {
//  uint8_t mac;
  String mac;
  boolean online;
  uint8_t sequence;
} device_t;

#define DEVICE_COUNT 2
device_t devices[DEVICE_COUNT];

StaticJsonDocument<64> hwdoc; //Deserialised hardware config JSON Document

Mrf24j mrf(pin_reset, pin_cs, pin_interrupt);

char * tohex(uint8_t val){
  sprintf(hexval, "%.2X", val);
  return hexval;
}

String mac2str(byte ar[]){
  String s;
  for (byte i = 0; i < 8; ++i)
  {
    char buf[3];
    sprintf(buf, "%.2X", ar[i]);
    s += buf;
//    if (i < 7) s += ':';
  }
  return s;
}

bool get_device_state(String macaddress) {
  bool result = false;
  for (int q = 0; q < DEVICE_COUNT; q++) {
	device_t *d = &devices[q];
    if (d->mac == macaddress){
      result = d->online;
      if (DEBUGSTATE) {
        Serial.print("Get device state: ");
        Serial.print(macaddress);
        Serial.println(result ? " Online" : " Offline");
      }
    }
  }
  return result;
}

void set_device_state(String macaddress, bool state) {
  for (int q = 0; q < DEVICE_COUNT; q++) {
	device_t *d = &devices[q];
    if (d->mac == macaddress){
      d->online = state;
      if (DEBUGSTATE) {
        Serial.print("Set device state: ");
        Serial.print(macaddress);
        Serial.println(state ? " Online" : " Offline");
      }
    }
  }
}

uint8_t get_device_seq(String macaddress) {
  uint8_t result = 0;
  for (int q = 0; q < DEVICE_COUNT; q++) {
	device_t *d = &devices[q];
    if (d->mac == macaddress){
      result = d->sequence++;
    }
  }
  return result;
}

void set_device_seq(String macaddress, uint8_t seq) {
  for (int q = 0; q < DEVICE_COUNT; q++) {
	device_t *d = &devices[q];
    if (d->mac == macaddress){
      d->sequence = seq;
    }
  }
}

//MQTT Callback
void callback(char* topic, byte* payload, unsigned int length) {

  uint8_t i;
  
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  if(length>15)
  {
    Serial.println("Received message too long");
  }
  else
    {
      for(i=0;i<2;i++)
        mqtt_rx_topic[i] = topic[i];
      mqtt_rx_topic[i] = 0x00;
      
      for (i=0;i<length;i++)
      {
        Serial.print((char)payload[i]);
        mqtt_rx_payload[i] = payload[i];
      }
      mqtt_rx_payload[i] = 0x00;
      mqtt_msg_received = true;
    }
  Serial.println();
}

void reconnect() {
  while (!mqttClient.connected()) {
    if (DEBUGMESSAGES) {
      Serial.println("Attempting MQTT connection...");
    }
    if (mqttClient.connect(MQTTClientID)) {
      if (DEBUGMESSAGES) {
        Serial.println("connected");
      }

      // Once connected, publish an announcement...
      mqttClient.publish(MQTTTopic, "PetHubLocal connected to MQTT");
      // ... and resubscribe
//      mqttClient.subscribe(MQTTTopic);

    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void connectmqtt()
{
  mqttClient.connect(MQTTClientID);  // ESP will connect to mqtt broker with clientID
  {
    if (DEBUGMESSAGES) {
      Serial.println("connected to MQTT");
    }
    // Once connected, publish an announcement...

    mqttClient.publish(MQTTTopic,  "PetHubLocal connected to MQTT");
    // ... and resubscribe
//    mqttClient.subscribe(MQTTTopic); 

    if (!mqttClient.connected())
    {
      reconnect();
    }
  }
}

void handle_rx() {
  digitalWrite(LED, HIGH);
  uint8_t rxbuffer[128];
  char rxchar[256];

  bool devicestate = get_device_state(mac2str(mrf.get_rxinfo()->src));

  if (DEBUG) {
    Serial.print("Src=");
    Serial.print(mac2str(mrf.get_rxinfo()->src));
    Serial.print(" Dst=");
    Serial.print(mac2str(mrf.get_rxinfo()->dst));
  }
  if (DEBUGLENGTH) {
    Serial.print(" Packet Len=");
    Serial.print(mrf.get_rxinfo()->frame_length, DEC);
    Serial.print(" Header Len=");
    Serial.print(mrf.get_rxinfo()->header_length, DEC);
    Serial.print(" Payload Len=");
    Serial.println(mrf.get_rxinfo()->data_length, DEC);
  }

  //Copy rx data to buffers
  if (mrf.get_rxinfo()->data_length > 0) {
    for (int i = 0; i < mrf.get_rxinfo()->data_length; i++) {
        rxbuffer[i] = mrf.get_rxinfo()->data[i];
        strcat (rxchar,tohex(mrf.get_rxinfo()->data[i]));
    }
    if (DEBUGMESSAGES) {    
      Serial.print(" Payload=");
      Serial.print(rxchar);
    }
  }

  //Always need to create a tx structure
  tx_info_t tx_info;
  // Frame Control Field
  tx_info.fcf.w = 0;
  //Set Source Addressing mode to send the hwmac
  tx_info.fcf.sam = 3;
  bool sendframe = true;
  bool sendmqtt = false;

  //Beacon Message - Device is offline coming online
  if ( rxbuffer[0] == 0x07 ){
    if (DEBUG) {
      Serial.println(" Beacon received");
    }
    set_device_state(mac2str(mrf.get_rxinfo()->src),false); //Device offline

    tx_info.data_length = 7;
    uint8_t data[tx_info.data_length] = { 0xff, 0x45, 0x00, 0x00, 0x7e, 0x02, 0x00 };
    // Pet door ack
    if ( rxbuffer[1] == 0x0f ) {
        data[5] = 0x01;
    }
    // Feeder ack
    if ( rxbuffer[1] == 0x2f ) {
        data[5] = 0x02;
    }
    for(int j=0; j <tx_info.data_length; j++)
    {
        tx_info.data[j] = data[j] ;
    }
  } 

  //Association message - Device is offline coming online
  else if ( devicestate == false && rxbuffer[0] == 0x01 ){
    if (DEBUG) {
      Serial.println(" Assocation Received when device is offline ");
    }    
    set_device_state(mac2str(mrf.get_rxinfo()->src),false); //Device offline

    //Set Dest Addressing mode to send to the device
    tx_info.fcf.dam = 3;
    tx_info.fcf.type = 3;
    tx_info.fcf.panc = true;
    tx_info.fcf.ack = true;

    tx_info.data_length = 4;
    uint8_t data[tx_info.data_length] = { 0x02, 0xfe, 0xff, 0x00 };
    for(int j=0; j <tx_info.data_length; j++)
    {
        tx_info.data[j] = data[j] ;
    }
    sendframe = true;
  }

  //Start Received - Device online
  else if ( rxbuffer[0] == 0x13 ){
    if (DEBUGMESSAGES) {
      Serial.print(" Start Received - Device counter: ");
      Serial.println(tohex(rxbuffer[1]));
    }

    set_device_state(mac2str(mrf.get_rxinfo()->src),true); //Device online

    //Set Dest Addressing mode to send to the device
    tx_info.fcf.dam = 3;
    tx_info.fcf.type = 1;
    tx_info.fcf.panc = true;
    tx_info.fcf.ack = true;
    
    set_device_seq(mac2str(mrf.get_rxinfo()->src),rxbuffer[1]);
    tx_info.data_length = 4;
    uint8_t data[tx_info.data_length] = { 0x14, _TXPacketSeqNo++, rxbuffer[1], 0x00 };
    for(int j=0; j <tx_info.data_length; j++)
    {
        tx_info.data[j] = data[j] ;
    }
  } 

  //Beacon message - Device is online
  else if ( rxbuffer[0] == 0x08 ){
    if (DEBUGMESSAGES) {
      Serial.print(" Online Beacon received - Counter: ");
      Serial.println(tohex(rxbuffer[1]));
    }
    set_device_state(mac2str(mrf.get_rxinfo()->src),true); //Device online
  
    //Set Dest Addressing mode to send to the device
    tx_info.fcf.dam = 3;
    tx_info.fcf.type = 1;
    tx_info.fcf.panc = true;
    tx_info.fcf.ack = false;

    tx_info.data_length = 3;
    uint8_t data[tx_info.data_length] = { 0x0a, _TXPacketSeqNo++, get_device_seq(mac2str(mrf.get_rxinfo()->src)) };
    if (rxbuffer[2] == 0x01) {
        data[0] = 0x09;
    }
    for(int j=0; j <tx_info.data_length; j++)
    {
        tx_info.data[j] = data[j] ;
    }
  } 

  //Data frame
  else if ( devicestate == true && rxbuffer[0] == 0x01 ){
    if (DEBUGMESSAGES) {
      Serial.println(" Online Data frame");
    }
    set_device_state(mac2str(mrf.get_rxinfo()->src),true); //Device online
  
    //Set Dest Addressing mode to send to the device
    tx_info.fcf.dam = 3;
    tx_info.fcf.type = 1;
    tx_info.fcf.panc = true;
    tx_info.fcf.ack = false;
    
    set_device_seq(mac2str(mrf.get_rxinfo()->src),rxbuffer[1]);
    tx_info.data_length = 4;
    uint8_t data[tx_info.data_length] = { 0x02, _TXPacketSeqNo++, rxbuffer[1], 0x00 };
    //More packets to come
    if (rxbuffer[2] == 0x01) {
        data[0] = 0x09;
    }
    for(int j=0; j <tx_info.data_length; j++)
    {
        tx_info.data[j] = data[j] ;
    }

    sendframe = true;
    //Send to MQTT
    sendmqtt = true;
  }

  //Final ack packet
  else if ( rxbuffer[0] == 0x02 ){
    Serial.println(" Online Data Ack frame");

    //We are online
    set_device_state(mac2str(mrf.get_rxinfo()->src),true);
  
    //Set Dest Addressing mode to send to the device
    tx_info.fcf.dam = 3;
    tx_info.fcf.type = 1;
    tx_info.fcf.panc = true;
    
    tx_info.data_length = 4;
    uint8_t data[tx_info.data_length] = { 0x0a, _TXPacketSeqNo++, get_device_seq(mac2str(mrf.get_rxinfo()->src)), 0x00 };
    if (rxbuffer[2] == 0x01) {
        data[0] = 0x09;
    }
    for(int j=0; j <tx_info.data_length; j++)
    {
        tx_info.data[j] = data[j] ;
    }

    //Send to MQTT
    sendmqtt = true;
  } 
  else if ( rxbuffer[0] == 0x0A ){
    Serial.println(" Resyncing counters");
    set_device_seq(mac2str(mrf.get_rxinfo()->src),rxbuffer[1]);
    sendframe = false;
  } 
  else {
    Serial.println("Unknown payload");
    sendmqtt = true;
  }

  //If we are publishing beacons to MQTT
  if (sendmqtt == true or DEBUGMQTT) {
    char MQTTTopicMsg[80];
    strcpy(MQTTTopicMsg, MQTTTopic);
    strcat(MQTTTopicMsg, "/");
    strcat(MQTTTopicMsg,mac2str(mrf.get_rxinfo()->src).c_str());
    noInterrupts();
    mqttClient.publish(MQTTTopicMsg,rxchar);
    interrupts();
  }
  if (sendframe) {
    mrf.sendframe(tx_info);
  }

  digitalWrite(LED, LOW);
}

void handle_tx() {
    if (mrf.get_txinfo()->tx_ok) {
//        Serial.println("TX went ok, got ack");
    } else {
        Serial.print("TX failed after ");
        Serial.print(mrf.get_txinfo()->retries);
        Serial.println(" retries - Chan Busy - ");
        Serial.print(mrf.get_txinfo()->channel_busy);
        Serial.println(" retries");
    }
}

void interrupt_routine() {
  mrf.interrupt_handler(); // mrf24 object interrupt routine
}

void setup() {
  Serial.begin(250000);
  pinMode(LED, OUTPUT);
  digitalWrite(LED, LOW);

  Serial.print("Connecting WiFi Network");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");

  mqttClient.setServer(MQTT_SERVER, 1883);//connecting to mqtt server
  mqttClient.setCallback(callback);
  //delay(5000);
  connectmqtt();
  mqttClient.setCallback(callback);

  Serial.print("Connecting MQTT Server");
  while (!mqttClient.connect(MQTT_CLIENT))
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("MQTT Connected");

  //Set hardware configuration as a json to be configured externally later.
  char hardwareconfig[] = "{'hwmac': '80:1F:12:FF:FE:E8:8D:D9'}";
  DeserializationError error = deserializeJson(hwdoc, hardwareconfig);
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.f_str());
    return;
  }

  //Transmit packet counter
  _TXPacketSeqNo = 0;

  // Hard code devices struct, to move to json payload for config later
  device_t *d0 = &devices[0];
  d0->mac = "52E26AFEFF121F80";
  d0->online = false;
  d0->sequence= 0x00;
  device_t *d1 = &devices[1];
  d1->mac = "162E02C0F9D5B370";
  d1->online = false;
  d1->sequence= 0x00;

  //Update hwmac if it is in the config
  if (hwdoc.containsKey("hwmac")) {
    byte hwmac[8];
    char hwmacstr[64];
    strlcpy(hwmacstr,hwdoc["hwmac"], sizeof(hwmacstr));  
    char* hwmacptr;
    hwmac[0] = strtol( strtok(hwmacstr,":"), &hwmacptr, HEX );
    for( uint8_t i = 1; i < 8; i++ )
    {
      hwmac[i] = strtol( strtok( NULL,":"), &hwmacptr, HEX );
    }
    mrf.set_initparams(hwmac);
    Serial.print("Config  MAC Address : ");
    Serial.println(mac2str(mrf.get_initparams()->hwmac));
  }

  // Initialise the MRF24J40
  mrf.reset();
  mrf.init();

  Serial.print("Current MAC Address : ");
  Serial.println(mac2str(mrf.get_initparams()->hwmac));

  // We are a coordinator 
//  mrf.set_coordinator();
  mrf.set_pancontroller(true);

  //The SurePet PAN to use
  mrf.set_pan(0x3421);

  // uncomment if you want to receive any packet on this channel
//  mrf.set_promiscuous(true);
  mrf.rx_flush();
 
  // uncomment if you want to buffer all PHY Payload
//  mrf.set_bufferPHY(true);

  attachInterrupt(digitalPinToInterrupt(pin_interrupt), interrupt_routine, CHANGE);
  interrupts();
}

void loop() {
  //Check for messages
  mrf.check_flags(&handle_rx, &handle_tx);

  // Keep MQTT Connection alive
  if(!mqttClient.loop())
  {
    Serial.print("Lost connection MQTT Server");
    while (!mqttClient.connect(MQTT_CLIENT))
    {
      delay(500);
      Serial.print(".");
    }
    Serial.println("");
    Serial.println("MQTT Connected");
  }
}
