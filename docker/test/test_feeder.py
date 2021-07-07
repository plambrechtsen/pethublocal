# Test Cat Flap
import pytest
import json
import logging
import sys
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter

sys.path.append('../source')
import pethubpacket as p

log = logging.getLogger(__name__)

def setup_module():
    log.info('setup')

def teardown_module():
    log.info('teardown')

@pytest.mark.pethubstatus
def test_feeder_battery(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 0050 126 18 0c 00 05 00 b8 c8 42 54 ae 17 00 00 d3 0c 00 00 25 01 00 00 0e 00 42 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.message[-1].Operation[0] == 'Battery'
    assert result.message[0].data.msg == '0c'
    assert result.message[0].data.counter == '5'
    assert result.message[0].Operation == 'Battery'
    assert result.message[0].Battery == "6.062"

@pytest.mark.pethubstatus
def test_feeder_status_tag1(request): #Zero feeder using button on the back
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 0010 126 12 11 00 0a 00 b8 c8 42 54 14 cd 5b 07 00 e1 01 02 01 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.message[-1].Operation[0] == 'TagProvision'
    assert result.message[0].data.msg == '11'
    assert result.message[0].data.counter == '10'
    assert result.message[0].Operation == 'TagProvision'
    assert result.message[0].LockState == "Normal"
    assert result.message[0].Offset == 1
    assert result.message[0].Animal == "Cat"
    assert result.message[0].ChipState == 'Enabled'

@pytest.mark.pethubstatus
def test_feeder_animal_open(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 0010 126 29 18 00 c9 00 b8 c8 42 54 14 cd 5b 07 00 e1 01 00 00 00 02 79 fb ff ff 00 00 00 00 d0 00 00 00 00 00 00 00 06 00 25 01 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.message[-1].Operation[0] == 'Feed'
    assert result.message[0].data.msg == '18'
    assert result.message[0].data.counter == '201'
    assert result.message[0].Operation == 'Feed'
    assert result.message[0].Action == "Animal_Open"
    assert result.message[0].Time == "0"
    assert result.message[0].LeftFrom == "-11.59"
    assert result.message[0].LeftTo == "0.0"
    assert result.message[0].LeftDelta == "11.59"
    assert result.message[0].RightFrom == "2.08"
    assert result.message[0].RightTo == "0.0"
    assert result.message[0].RightDelta == "-2.08"
    assert result.message[0].Animal == "Cat"
    assert result.message[0].BowlCount == 2

@pytest.mark.pethubstatus
def test_feeder_animal_close(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 0020 126 29 18 00 ca 00 b8 c8 42 54 14 cd 5b 07 00 e1 01 01 0b 00 02 79 fb ff ff 8c fb ff ff d0 00 00 00 d1 00 00 00 07 00 25 01 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.message[-1].Operation[0] == 'Feed'
    assert result.message[0].data.msg == '18'
    assert result.message[0].data.counter == '202'
    assert result.message[0].Operation == 'Feed'
    assert result.message[0].Action == "Animal_Closed"
    assert result.message[0].Time == "11"
    assert result.message[0].LeftFrom == "-11.59"
    assert result.message[0].LeftTo == "-11.4"
    assert result.message[0].LeftDelta == "0.19"
    assert result.message[0].RightFrom == "2.08"
    assert result.message[0].RightTo == "2.09"
    assert result.message[0].RightDelta == "0.01"
    assert result.message[0].Animal == "Cat"
    assert result.message[0].BowlCount == 2

@pytest.mark.pethubstatus
def test_feeder_manual_open(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 0030 126 29 18 00 04 00 b8 c8 42 54 01 02 03 04 05 06 07 04 00 00 02 b9 0e 00 00 bd 0e 00 00 60 00 00 00 53 00 00 00 ee 00 24 01 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.message[-1].Operation[0] == 'Feed'
    assert result.message[0].data.msg == '18'
    assert result.message[0].data.counter == '4'
    assert result.message[0].Operation == 'Feed'
    assert result.message[0].Action == "Manual_Open"
    assert result.message[0].Time == "0"
    assert result.message[0].LeftFrom == "37.69"
    assert result.message[0].LeftTo == "37.73"
    assert result.message[0].LeftDelta == "0.04"
    assert result.message[0].RightFrom == "0.96"
    assert result.message[0].RightTo == "0.83"
    assert result.message[0].RightDelta == "-0.13"
    assert result.message[0].Animal == "Manual"
    assert result.message[0].BowlCount == 2

@pytest.mark.pethubstatus
def test_feeder_manual_close(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 0040 126 29 18 00 04 00 b8 c8 42 54 01 02 03 04 05 06 07 05 52 00 02 b9 0e 00 00 3a 00 00 00 60 00 00 00 d3 1a 00 00 ef 00 25 01 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.message[-1].Operation[0] == 'Feed'
    assert result.message[0].data.msg == '18'
    assert result.message[0].data.counter == '4'
    assert result.message[0].Operation == 'Feed'
    assert result.message[0].Action == "Manual_Closed"
    assert result.message[0].Time == "82"
    assert result.message[0].LeftFrom == "37.69"
    assert result.message[0].LeftTo == "0.58"
    assert result.message[0].LeftDelta == "-37.11"
    assert result.message[0].RightFrom == "0.96"
    assert result.message[0].RightTo == "68.67"
    assert result.message[0].RightDelta == "67.71"
    assert result.message[0].Animal == "Manual"
    assert result.message[0].BowlCount == 2

@pytest.mark.pethubstatus
def test_feeder_zero_button(request): #Zero feeder using button on the back
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 0260 126 29 18 00 08 00 b8 c8 42 54 01 02 03 04 05 06 07 06 00 00 02 00 00 00 00 d0 fa ff ff 00 00 00 00 51 ff ff ff 07 00 24 01 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.message[-1].Operation[0] == 'Feed'
    assert result.message[0].data.msg == '18'
    assert result.message[0].data.counter == '8'
    assert result.message[0].Operation == 'Feed'
    assert result.message[0].Action == "Zero_Both"
    assert result.message[0].LeftFrom == "0.0"
    assert result.message[0].LeftTo == "-13.28"
    assert result.message[0].LeftDelta == "-13.28"
    assert result.message[0].RightFrom == "0.0"
    assert result.message[0].RightTo == "-1.75"
    assert result.message[0].RightDelta == "-1.75"
    assert result.message[0].Animal == "Manual"



#Test Command Messages

@pytest.mark.parametrize("test_acks", [
    ("09"), # Boot message 09
    ("0b"), # Unknown 0b message
    ("0c"), # Battery state change
    ("10"), # Boot message 10
    ("11"), # Tag provisioning
    ("16"), # Status 16 message
    ("17"), # Boot message 17
    ("18"), # Feeder state change
])
@pytest.mark.pethubcommand
def test_feeder_command_acknowledge(request,test_acks):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 1000 127 00 00 0c 00 b8 c8 42 54 " + test_acks + " 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'Ack'
    assert result.message[0].data.msg == '00'
    assert result.message[0].data.counter == '12'
    assert result.message[0].Operation == 'Ack'
    assert result.message[0].Message == test_acks

@pytest.mark.parametrize("test_query,type,subdata", [
    ("09 00 ff","09","00ff"),    # Boot message 09
    ("10 00", "10", "00"),       # Boot message 10
    ("11 00 ff", "11", "00ff"),  # Tag provisioned
    ("17 00 00", "17", "0000"),  # Boot message  17
    ("0b 00", "0b", "00"),       # Unknown 0b
    ("0c 00", "0c", "00"),       # Battery state
])
@pytest.mark.pethubcommand
def test_feeder_command_query(request,test_query,type,subdata):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 1000 127 01 00 01 01 b8 c8 42 54 " + test_query)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'Query'
    assert result.message[0].data.msg == '01'
    assert result.message[0].data.counter == '257'
    assert result.message[0].Operation == 'Query'
    assert result.message[0].Type == type
    assert result.message[0].SubData == subdata

@pytest.mark.pethubcommand
def test_feeder_command_set_time(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 1000 127 07 00 01 00 b8 c8 42 54 00 00 00 00 07")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'Settime'
    assert result.message[0].data.msg == '07'
    assert result.message[0].data.counter == '1'
    assert result.message[0].Operation == 'Settime'
    assert result.message[0].Type == "0000000007"

@pytest.mark.parametrize("test_generate,genvalue,genresponse", [
    ("SetLeftScale", "10", " 0a e8 03 00 00"),      # Set Left Target Weight
    ("SetRightScale", "25", " 0b c4 09 00 00"),     # Set Right Target Weight
    ("SetBowlCount", "One", " 0c 01 00 00 00"),     # Set Bowl Count
    ("SetBowlCount", "Two", " 0c 02 00 00 00"),     # Set Bowl Count
    ("SetCloseDelay", "Fast", " 0d 00 00 00 00"),   # 0 Seconds
    ("SetCloseDelay", "Normal", " 0d a0 0f 00 00"), # 4 Seconds "0fa0" = 4000
    ("SetCloseDelay", "Slow", " 0d 20 4e 00 00"),   # 20 Seconds "4e20" = 20000
    ("Set12", "500", " 12 f4 01 00 00"),            # Set Message 12
    ("Custom-Intruder", "", " 14 00 01 00 00"),      # Set Custom Mode - Intruder
    ("Custom-GeniusCat", "", " 14 80 00 00 00"),     # Set Custom Mode - GeniusCat
])
@pytest.mark.pethubcommand
def test_feeder_command_updatestate(request,test_generate,genvalue,genresponse):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 1000 127 09 00 12 01 b8 c8 42 54" + genresponse)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'UpdateState'
    assert result.message[0].data.msg == '09'
    assert result.message[0].data.counter == '274'
    assert result.message[0].Operation == 'UpdateState'
    assert result.message[0].SubOperation == test_generate
    if test_generate in ['SetLeftScale','SetRightScale']:
        assert result.message[0].Weight == genvalue
    if test_generate == 'SetBowlCount':
        assert result.message[0].Bowls == genvalue
    if test_generate == 'SetCloseDelay':
        assert result.message[0].Delay == genvalue
    if test_generate == 'Set12':
        assert result.message[0].Value == genvalue
    if test_generate == 'Set12':
        assert result.message[0].Value == genvalue

@pytest.mark.parametrize("test_zeroscale,zerovalue", [
    ("ZeroLeft", "01"),      # Zero Left
    ("ZeroRight", "02"),     # Zero Right
    ("ZeroBoth", "03"),      # Zero Both
])
@pytest.mark.pethubcommand
def test_feeder_command_zeroscale(request,test_zeroscale,zerovalue):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 1000 127 0d 00 12 00 b8 c8 42 54 00 19 00 00 00 03 00 00 00 00 01 " + zerovalue)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'ZeroScales'
    assert result.message[0].Operation == 'ZeroScales'
    assert result.message[0].Scale == test_zeroscale

@pytest.mark.pethubcommand
def test_feeder_command_provision_hdxtag_enable(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 1000 127 11 00 11 00 b8 c8 42 54 01 23 45 67 89 00 03 02 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'TagProvision'
    assert result.message[0].data.msg == '11'
    assert result.message[0].data.counter == '17'
    assert result.message[0].Operation == 'TagProvision'
    assert result.message[0].Animal == 'HDX_Tag'
    assert result.message[0].LockState == 'Normal'
    assert result.message[0].Offset == 0
    assert result.message[0].ChipState == 'Enabled'

@pytest.mark.pethubcommand
def test_feeder_command_provision_fdxbcattag_enable(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/4444444444444444","5fef6320 1000 127 11 00 02 00 b8 c8 42 54 14 cd 5b 07 00 e1 01 02 01 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'Feeder'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'TagProvision'
    assert result.message[0].data.msg == '11'
    assert result.message[0].data.counter == '2'
    assert result.message[0].Operation == 'TagProvision'
    assert result.message[0].Animal == 'Cat'
    assert result.message[0].LockState == 'Normal'
    assert result.message[0].Offset == 1
    assert result.message[0].ChipState == 'Enabled'

#Generate Messages

@pytest.mark.pethubgenerate
def test_feeder_generate_settime(request):
    log.info('TEST: ' + request.node.name)
    result = p.generatemessage("4444444444444444", "SetTime", "")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.topic == 'pethublocal/messages/4444444444444444'
    assert ' 1000 127 07 00 ' in result.msg
    assert ' 00 00 00 00 07' in result.msg

@pytest.mark.parametrize("test_generate,genvalue,genresponse", [
    ("SetLeftScale", "10", " 0a e8 03 00 00"),      # Set Left Target Weight
    ("SetRightScale", "25", " 0b c4 09 00 00"),     # Set Right Target Weight
    ("SetBowlCount", "One", " 0c 01 00 00 00"),     # Set Bowl Count
    ("SetBowlCount", "Two", " 0c 02 00 00 00"),     # Set Bowl Count
    ("SetCloseDelay", "Fast", " 0d 00 00 00 00"),   # 0 Seconds
    ("SetCloseDelay", "Normal", " 0d a0 0f 00 00"), # 4 Seconds "0fa0" = 4000
    ("SetCloseDelay", "Slow", " 0d 20 4e 00 00"),   # 20 Seconds "4e20" = 20000
    ("Set12", "500", " 12 f4 01 00 00"),            # Set Message 12
    ("Custom-Intruder", "", " 14 00 01 00 00"),     # Set Custom Mode - Intruder
    ("Custom", "Intruder", " 14 00 01 00 00"),      # Set Custom Mode - Intruder
    ("Custom-GeniusCat", "", " 14 80 00 00 00"),    # Set Custom Mode - Genius Cat Mode
    ("Custom", "GeniusCat", " 14 80 00 00 00"),     # Set Custom Mode - Genius Cat Mode
])
@pytest.mark.pethubgenerate
def test_feeder_generate_setvalues(request,test_generate,genvalue,genresponse):
    log.info('TEST: ' + request.node.name)
    result = p.generatemessage("4444444444444444", test_generate, genvalue)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.topic == 'pethublocal/messages/4444444444444444'
    assert ' 1000 127 09 00 ' in result.msg
    assert genresponse in result.msg

@pytest.mark.parametrize("test_zeroscale,zerovalue,zeroresponse", [
    ("ZeroScale", "Left", "01"),  # Zero Left Scale
    ("ZeroScale", "Right", "02"), # Zero Right Scale
    ("ZeroScale", "Both", "03"),  # Zero Both Scales
])
@pytest.mark.pethubgenerate
def test_feeder_generate_zeroscales(request,test_zeroscale,zerovalue,zeroresponse):
    log.info('TEST: ' + request.node.name)
    result = p.generatemessage("4444444444444444", test_zeroscale, zerovalue)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.topic == 'pethublocal/messages/4444444444444444'
    assert ' 1000 127 0d 00 ' in result.msg
    assert "00 19 00 00 00 03 00 00 00 00 01 " + zeroresponse in result.msg

@pytest.mark.parametrize("test_tagprovision,tagvalue,tagresponse", [
    ("TagProvision", "enable-0-0123456789", " 01 23 45 67 89 00 03 02 00 01"),
    ("TagProvision", "enable-1-900.000001234567", " 87 d6 12 00 00 e1 01 02 01 01"),
    ("TagProvision", "disable-2-900.000123456788", " 14 cd 5b 07 00 e1 01 02 02 00"),
])
@pytest.mark.pethubgenerate
def test_feeder_generate_tagprovision(request,test_tagprovision,tagvalue,tagresponse):
    log.info('TEST: ' + request.node.name)
    result = p.generatemessage("4444444444444444", test_tagprovision, tagvalue)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.topic == 'pethublocal/messages/4444444444444444'
    assert ' 1000 127 11 00 ' in result.msg
    assert tagresponse in result.msg
