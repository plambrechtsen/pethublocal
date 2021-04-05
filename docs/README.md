# Documentation

Below is the standard and Pet Hub Local altered boot process to help explain how the local instance works.

## Standard Hub boot process

As per the below standard flow it is:
- Query DNS for hub.api.surehub.io
- Connect to HTTPS Cloud service to retrieve credentials and client certificate
- Connect to AWS IoT MQTT with client certificate 

```plantuml
@startuml
    skinparam monochrome reverse
    Hub <-> NTP : Get the time
    group DNS
    Hub -> DNS : Lookup hub.api.surehub.io
    DNS -> Hub : Response
    end group
    group Cloud Service Credentials API endpoint
    Hub -> Web : POST to HTTPS /api/credentials with Serial Number & MAC Address
    Web -> Hub : Credentials response with MQTT topic, AWS IoT endpoint and Client Certificate
    end group
    group AWS IoT MQTT TLS Endpoint
    Hub -> MQTT : Connect to AWS with Client Certificate
    MQTT -> Hub : MQTT TLS Session established
    end group
@enduml
```

## Pet Hub Local Hub altered boot process

As per the below the altered flow is:
- Query DNS but get the response for hub.api.surehub.io to point to the local docker container or webserver
- Local Web on first connection proxies the request to the Cloud Web to retrieve the Credentials file
- Alters credentials file to point to local MQTT endpoint and have a consistent topic name rather than UUID value and saves original and new credentials file locally
- Responds to Hub with altered credentials file
- Connect to local MQTT with client certificate but it doesn't validate the certificate

```plantuml
@startuml
    skinparam monochrome reverse
    Hub <-> NTP : Get the time
    group DNS
    Hub -> DNS : Lookup hub.api.surehub.io
    DNS -> Hub : Altered DNS response to return local instance
    end group
    group Cloud Service Credentials API endpoint
    Hub -> "Local Web" : POST to HTTPS /api/credentials\nwith Serial Number & MAC Address
    "Local Web" -> "Cloud Web" : POST to HTTPS /api/credentials\nwith Serial Number & MAC Address
    "Cloud Web" -> "Local Web" : Credentials response with MQTT topicn\nAWS IoT endpoint and Client Certificate
    "Local Web" -> "Local Web" : Alter credential file and save locally
    "Local Web" ->  Hub : Altered credentials response with local MQTT topic,\nlocal MQTT endpoint to also be hub.api.surehub.io
    end group
    group Local MQTT TLS Endpoint
    Hub -> "Local MQTT" : Connect to Local with Client Certificate
    "Local MQTT" -> Hub : MQTT TLS Session established
    end group

@enduml
```
