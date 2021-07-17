# Test Pet Hub Local
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


# Test Status Messages
@pytest.mark.pethubstatus
def test_feeder_battery(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/6666666666666666","5fef6320 0050 126 18 0c 00 05 00 b8 c8 42 54 04 17 00 00 d3 0c 00 00 25 01 00 00 0e 00 42 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'CatFlap'
    assert result.message[-1].Operation[0] == 'Battery'
    assert result.message[0].data.msg == '0c'
    assert result.message[0].data.counter == '5'
    assert result.message[0].Operation == 'Battery'
    assert result.message[0].Battery == "5.892"


@pytest.mark.parametrize("provhex, lockstate", [
    ("03", "KeepIn"),    # Lock State - KeepIn
    ("06", "Unlocked"),  # Lock State - Unlocked
])
@pytest.mark.pethubstatus
def test_catflap_status_curfewlockstate(request,provhex,lockstate):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/6666666666666666", "5fef6320 1000 126 1e 0d 00 01 00 b8 c8 42 54 ff ff ff ff 00 00 00 00 00 00 00 00 00 00 00 00 fc 00 02 00 06 "+provhex)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    log.info(' State ' + str(result.message[0].LockState))
    assert result.operation == 'Command'
    assert result.device == 'CatFlap'
    assert result.message[-1].Operation[0] == 'CurfewLockState'
    assert result.message[0].frametimestamp == "2021-01-01 12:34:56"  # Timestamp
    assert result.message[0].data.msg == '0d'  # Message type
    assert result.message[0].data.counter == '1'  # Counter
    assert result.message[0].LockState == lockstate  # State


@pytest.mark.parametrize("operation,provhex,animal,lockstate, offset, tagstate", [
    ("LockState", "00 00 00 00 00 00 07 03 00 02", "Empty", "KeepIn", 0, ""),    # Lock State - KeepIn
    ("LockState", "00 00 00 00 00 00 07 04 00 02", "Empty", "Locked", 0, ""),    # Lock State - Locked
    ("LockState", "00 00 00 00 00 00 07 05 00 02", "Empty", "KeepOut", 0, ""),   # Lock State - KeepOut
    ("LockState", "00 00 00 00 00 00 07 06 00 02", "Empty", "Unlocked", 0, ""),  # Lock State - Unlocked
    ("Tag", "14 cd 5b 07 00 e1 01 02 00 00", "Cat", "Normal", 0, "Enabled"),  # Tag 1
    ("Tag", "16 cd 5b 07 00 e1 01 03 01 00", "900.000123456790", "KeepIn", 1, "Enabled"),  # Tag 1
    ("Tag", "17 cd 5b 07 00 e1 01 02 02 01", "900.000123456791", "Normal", 2, "Disabled"),  # Tag 1
    ("Tag", "18 cd 5b 07 00 e1 01 03 03 01", "900.000123456792", "KeepIn", 3, "Disabled"),  # Tag 1
    ("Tag", "00 00 00 00 00 00 07 06 04 00", "Empty", "Unlocked", 4, "Enabled"),  # Tag 1
    ("Tag", "00 00 00 00 00 00 07 06 0a 00", "Empty", "Unlocked", 10, "Enabled"),  # Tag 1
    ("Tag", "00 00 00 00 00 00 07 06 1e 00", "Empty", "Unlocked", 30, "Enabled"),  # Tag 1
])
@pytest.mark.pethubstatus
def test_catflap_status_tagprovisioning_and_doorlocking(request, operation, provhex, animal, lockstate, offset, tagstate):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/6666666666666666", "5fef6320 0000 126 12 11 00 01 00 b8 c8 42 54 " + provhex)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'CatFlap'
    assert result.operation == 'Status'
    assert result.message[-1].Operation[0] == operation
    assert result.message[0].Operation == operation
    assert result.message[0].Offset == offset
    assert result.message[0].LockState == lockstate
    if result.message[-1].Operation[0] == 'Tag':
        assert result.message[0].Animal == animal


@pytest.mark.parametrize("taghex,directionhex,animal,direction", [
    ("14 cd 5b 07 00 e1 01", "00 00", "Cat", "Out"),                     # Animal went out
    ("16 cd 5b 07 00 e1 01", "01 01", "900.000123456790", "In"),         # Animal came in
    ("17 cd 5b 07 00 e1 01", "02 00", "900.000123456791", "LookedOut"),  # Animal Looked out but didn't go out
    ("18 cd 5b 07 00 e1 01", "02 01", "900.000123456792", "LookedIn"),   # Animal Looked in but didn't come in
    ("00 00 00 00 00 00 00", "02 02", "Empty", "Status2"),               # Status 2, this happens a lot with above messages
    ("00 00 00 00 00 00 00", "01 02", "Empty", "Status1"),               # Random Status message I don't know if this happens but added for completeness
])
@pytest.mark.pethubstatus
def test_catflap_status_petmovement(request, taghex, directionhex, animal, direction):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/6666666666666666", "5fef6320 0110 126 1e 13 00 01 01 b8 c8 42 54 00 00 00 00 02 16 00 00 "+directionhex+" "+taghex+" 01 00 00 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.operation == 'Status'
    assert result.device == 'CatFlap'
    assert result.message[-1].Operation[0] == 'PetMovement'
    assert result.message[0].frametimestamp == "2021-01-01 12:34:56"  # Timestamp
    assert result.message[0].data.msg == '13'  # Message type
    assert result.message[0].Animal == animal
    assert result.message[0].Direction == direction


# Test Command Messages
@pytest.mark.parametrize("test_acks", [
    ("09"), # Boot message 09
    ("0b"), # Unknown 0b message
    ("0c"), # Battery state change
    ("10"), # Boot message 10
    ("11"), # Tag provisioning
    ("13"), # Pet Movement
    ("16"), # Status 16 message
    ("17")  # Boot message 17
])
@pytest.mark.pethubcommand
def test_catflap_command_acknowledge(request,test_acks):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/6666666666666666","5fef6320 1000 127 00 00 0c 00 b8 c8 42 54 " + test_acks + " 00 00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'CatFlap'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'Ack'
    assert result.message[0].data.msg == '00'
    assert result.message[0].data.counter == '12'
    assert result.message[0].Operation == 'Ack'
    assert result.message[0].Message == test_acks


@pytest.mark.parametrize("test_query,type,subdata", [
    ("09 00 ff", "09", "00ff"),  # Boot message 09
    ("10 00", "10", "00"),  # Boot message 10
    ("11 00 ff", "11", "00ff"),  # Tag provisioned
    ("17 00 00", "17", "0000"),  # Boot message  17
    ("0b 00", "0b", "00"),  # Unknown 0b
    ("0c 00", "0c", "00"),  # Battery state
])
@pytest.mark.pethubcommand
def test_catflap_command_query(request, test_query, type, subdata):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/6666666666666666", "5fef6320 1000 127 01 00 01 01 b8 c8 42 54 " + test_query)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.device == 'CatFlap'
    assert result.operation == 'Command'
    assert result.message[-1].Operation[0] == 'Query'
    assert result.message[0].data.msg == '01'
    assert result.message[0].data.counter == '257'
    assert result.message[0].Operation == 'Query'
    assert result.message[0].Type == type
    assert result.message[0].SubData == subdata


@pytest.mark.pethubcommand
def test_catflap_command_curfewset(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/6666666666666666", "5fef6320 1000 127 12 00 01 00 b8 c8 42 54 00 00 00 00 00 00 07 00 80 07 42 54 80 17 42 54 03 c0 43 42 54 80 50 42 54 03 00 00 42 00 00 00 42 00 06 00 00 42 00 00 00 42 00 06")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.operation == 'Command'
    assert result.device == 'CatFlap'
    assert result.message[-1].Operation[0] == 'Curfew'
    assert result.message[0].frametimestamp == "2021-01-01 12:34:56"  # Timestamp
    assert result.message[0].data.msg == '12'  # Message type
    assert result.message[0].data.counter == '1'  # Counter
    assert len(result.message[0].Curfew) == 2  # Number of curfew entries
    assert result.message[0].Curfew[0].State == 3  # Curfew Enabled
    assert result.message[0].Curfew[0].Start == "2021-01-01 00:30:00"  # Curfew Start in UTC
    assert result.message[0].Curfew[0].End == "2021-01-01 01:30:00"  # Curfew End in UTC
    assert result.message[0].Curfew[1].State == 3  # Curfew Enabled
    assert result.message[0].Curfew[1].Start == "2021-01-01 04:15:00"  # Curfew Start in UTC
    assert result.message[0].Curfew[1].End == "2021-01-01 05:02:00"  # Curfew End in UTC

@pytest.mark.pethubcommand
def test_catflap_command_curfewclear(request):
    log.info('TEST: ' + request.node.name)
    result = p.decodehubmqtt("pethublocal/messages/6666666666666666", "5fef6320 1000 127 12 00 01 00 b8 c8 42 54 00 00 00 00 00 00 07 00 00 00 42 00 00 00 42 00 06 00 00 42 00 00 00 42 00 06 00 00 42 00 00 00 42 00 06 00 00 42 00 00 00 42 00 06")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.operation == 'Command'
    assert result.device == 'CatFlap'
    assert result.message[-1].Operation[0] == 'Curfew'
    assert result.message[0].frametimestamp == "2021-01-01 12:34:56"  # Timestamp
    assert result.message[0].data.msg == '12'  # Message type
    assert result.message[0].data.counter == '1'  # Counter
    assert len(result.message[0].Curfew) == 0  # Number of curfew entries


@pytest.mark.pethubgenerate
def test_catflap_generate_settime(request):
    log.info('TEST: ' + request.node.name)
    result = p.generatemessage("6666666666666666", "SetTime", "")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.topic == 'pethublocal/messages/6666666666666666'
    assert ' 1000 127 07 00 ' in result.msg
    assert ' 00 00 00 00 07' in result.msg

def test_catflap_generate_catflapcurfew(request):
    log.info('TEST: ' + request.node.name)
    result = p.generatemessage("6666666666666666", "Curfew", "08:30-10:00,11:30-20:00,12:30-21:00,14:30-22:00")
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    # now = p.datetime.now()  # Current timestamp in local time
    # val = Box({'test':1})
    # log.info(' info'+json.dumps(val))
    #    times = timestamp(result.msg)
    #    pytest.warn("Message " + hextimestampfromnow())
    #    print(times)
    assert result.topic == 'pethublocal/messages/6666666666666666'
    # assert ' 1000 2 34 2 {} {}'.format(p.hb(now.hour), p.hb(now.minute)) in result.msg


@pytest.mark.parametrize("test_generate,genvalue,genresponse", [
    ("LockKeepIn", "",  " 00 00 00 00 00 00 07 03 00 02"),
    ("Locked", "",      " 00 00 00 00 00 00 07 04 00 02"),
    ("LockKeepOut", "", " 00 00 00 00 00 00 07 05 00 02"),
    ("Unlocked", "",    " 00 00 00 00 00 00 07 06 00 02"),
    ("TagProvision", "1-900.000123456790-Normal-Enabled", " 16 cd 5b 07 00 e1 01 02 01 00"),
    ("TagProvision", "2-900.000123456791-KeepIn-Enabled", " 17 cd 5b 07 00 e1 01 03 02 00"),
    ("TagProvision", "3-900.000123456792-Normal-Disabled", " 18 cd 5b 07 00 e1 01 02 03 01"),
    ("TagProvision", "4-900.000123456793-KeepIn-Disabled", " 19 cd 5b 07 00 e1 01 03 04 01"),
])
@pytest.mark.pethubgenerate
def test_catflap_generate_setvalues(request,test_generate,genvalue,genresponse):
    log.info('TEST: ' + request.node.name)
    result = p.generatemessage("6666666666666666", test_generate, genvalue)
    jsonresult = json.dumps(result, indent=4)
    log.info("Result:\n" + highlight(jsonresult, JsonLexer(), TerminalFormatter()))
    assert result.topic == 'pethublocal/messages/6666666666666666'
    assert ' 1000 127 11 00 ' in result.msg
    assert genresponse in result.msg