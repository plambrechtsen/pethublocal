#!/usr/bin/env python3

"""
    Pet Hub Constants

    Constants used by Pet Hub Local

    Copyright (c) 2021, Peter Lambrechtsen (peter@crypt.nz)

    Used and abused surepy constants from Ben's amazing work: https://github.com/benleb/surepy

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software Foundation,
    Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
"""

from enum import IntEnum, IntFlag

class SureEnum(IntEnum):
    #Sure Int enum for integer based enums
    def __str__(self) -> str:
        return self.name.title()

    def as_hex(self):
        bytestring=self.to_bytes(4, 'little').hex()
        return " ".join(bytestring[i:i + 2] for i in range(0, len(bytestring), 2))

    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_ 

    @classmethod
    def has_member(self, value):
        return value in self._member_names_

    @classmethod #Handle weird values, as it really shouldn't crash
    def _missing_(self, value):
        new_member = int.__new__(self, value)
        new_member._name_ = str(value)
        new_member._value_ = value
        return self._value2member_map_.setdefault(value, new_member)

class SureFlag(IntFlag):
    """Sure Flag enum."""
    def as_hex(cls):
        bytestring=cls.to_bytes(4, 'little').hex()
        return " ".join(bytestring[i:i + 2] for i in range(0, len(bytestring), 2))

    def string_array(cls):
        return [member for member in cls._member_names_ if member in str(cls)]

    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_

    @classmethod
    def has_member(self, value):
        return value in self._member_names_

class EntityType(SureEnum):
    """Sure Entity Types."""
    PET           = 0   # artificial ID, not used by the Sure Petcare API
    HUB           = 1   # Hub
    REPEATER      = 2   # Repeater
    PETDOOR       = 3   # Pet Door Connect
    FEEDER        = 4   # Microchip Pet Feeder Connect
    PROGRAMMER    = 5   # Programmer
    CATFLAP       = 6   # Cat Flap Connect
    FEEDER_LITE   = 7   # Feeder Lite
    FELAQUA       = 8   # Felaqua Connect
    DEVICES       = 13  # artificial ID, Pet Flap + Cat Flap + Feeder = 3 + 6 + 4 = 13  ¯\_(ツ)_/¯

class FeederState(SureEnum): # Feeder states
    Animal_Open   = 0   # Animal Open Feeder
    Animal_Closed = 1   # Animal Closed Feeder
    Manual_Open   = 4   # Manually Opened Feeder
    Manual_Closed = 5   # Manually Closed Feeder
    Zero_Both     = 6   # Zero Feeder both scales
    Zero_Left     = 7   # Zero Feeder left scale
    Zero_Right    = 8   # Zero Feeder right scale

class FeederZeroScales(SureEnum): # Feeder states
    ZeroLeft     = 1    # Zero Feeder left scale
    ZeroRight    = 2    # Zero Feeder right scale
    ZeroBoth     = 3    # Zero Feeder both scales

class FeederCloseDelay(SureEnum): # Feeder Close Delay speed
    Fast        = 0     # Fast delay
    Normal      = 4000  # Normal delay
    Felaqua     = 5000  # Normal delay
    Slow        = 20000 # Slow delay

class FeederBowls(SureEnum): # Feeder Close Delay speed
    One           = 1   # Single Bowl
    Two           = 2   # Double Bowl
    Felaqua       = 4   # Felaqua

class PetDoorLockState(SureEnum): # Lock State IDs.
    Unlocked        = 0
    KeepIn          = 1
    KeepOut         = 2
    Locked          = 3
    Curfew          = 4
    CURFEW_LOCKED   = -1
    CURFEW_UNLOCKED = -2
    CURFEW_UNKNOWN  = -3

class PetDoorLockedOutState(SureEnum): # Locked Out State for preventing animals coming in
    Normal          = 2  # Allow pets in
    Locked_Out      = 3  # Keep pets out

class CatFlapLockState(SureEnum): # Cat Flap Lock State from message type 11.
    Normal          = 2  #This is when a cat is provisioned in normal in / out mode
    KeepIn          = 3  #This applies to the cat when they are individually being kept in, and if the device is 07, then it is applying to the door
    Locked          = 4
    KeepOut         = 5
    Unlocked        = 6

class PetDoorDirection(SureEnum): # Pet Movement on Pet Door coming in or out or looked in or unknown animal left
    Outside_LookedIn    = 0x40 #This happens if the pet comes up to the door from outside, puts head in and unlocks the door but doesn't come in.
    Inside              = 0x61 #Normal ingress
    Outside             = 0x62 #Normal egress
    Inside_Already      = 0x81 #Ingress if the pet door thought the pet was already inside
    Outside_UnknownPet  = 0xd3 #This along with pet 621 is when the pet leaves too quickly for the pet door to read it leaving

class CurfewState(SureEnum): # Curfew State
    Disabled        = 0
    Off             = 1
    On              = 2
    Status          = 3

class CatFlapCurfewState(SureEnum): # Curfew State
    Off             = 6
    On              = 3

class HubLeds(SureEnum):     # Sure Petcare API LED State offset 0x18
    Off             = 0      #Ears Off
    Bright          = 1      #Bright Ears
    Dimmed          = 4      #Dimmed
    FlashOff        = 0x80   #Flash Leds 3 times when off
    FlashBright     = 0x81   #Flash Leds 3 times when bright
    FlashDimmed     = 0x84   #Flash Leds 3 times when dimmed

class HubAdoption(SureEnum): #Sure Petcare adoption / pairing_mode mode 0x15
    Disabled        = 0      #Not attempting to pair a new device
    Enabled         = 2      #In pairing / adoption mode
    Button          = 0x82   #Pairing mode enabled by pressing "reset" button underneath

class ProvChipFrom(SureEnum): # Chip Provisioned State
    Existing        = 0  #Already provisioned on device
    Button          = 1  #Provisioned chip from learn button on the back
    NewCloud        = 2  #Provisioned chip from cloud
    Disabled        = 3  #Provisioned chip from cloud

class TagState(SureEnum): # Tag State on Non Pet-Door Device
    Enabled         = 0
    Disabled        = 1
    LockState       = 2

class CatFlapDirection(SureEnum): # Pet Movement on Cat Flap coming in or going out.
    Out             = 0x0000  # Animal went out
    In              = 0x0101  # Animal came in
    LookedIn        = 0x0201  # Animal Looked in but didn't come in
    LookedOut       = 0x0200  # Animal Looked out but didn't go out
    Status2         = 0x0202  # Status 2, this happens a lot with above messages
    Status1         = 0x0102  # Random Status message I don't know if this happens but added for completeness

class Animal(SureEnum): # Animal mdi mapping
    alien        = 0
    cat          = 1
    dog          = 2

class AnimalState(SureEnum): # Animal State
    Outside          = 0
    Inside           = 1
    Unknown          = 2

class Online(SureEnum): # Online offline
    Offline          = 0
    Online           = 1

class Enabled(SureEnum): # Enabled disabled
    Disabled         = 0
    Enabled          = 1

class OnOff(SureEnum): # Enabled disabled
    Off              = 0
    On               = 1
    Status           = 2

class FeederCustomMode(SureFlag): #Custom Modes on the Feeder
    Intruder = 0x100   # Bit9 - Intruder Mode - Close lid when another non-provisioned tag turns up
    GeniusCat = 0x80   # Bit8 - Genius Cat Mode - Disable open/close button as Genius Cat has figured out how to open the feeder by pressing button.
    Bit7 = 0x40
    Bit6 = 0x20
    Bit5 = 0x10
    Bit4 = 0x8
    Bit3 = 0x4
    Bit2 = 0x2
    Bit1 = 0x1
    Normal = 0

