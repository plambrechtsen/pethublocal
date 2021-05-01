#!/usr/bin/env python3

"""
    Pet Hub Constants

    Constants used by Pet Hub Local

    Copyright (c) 2021, Peter Lambrechtsen (peter@crypt.nz)

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

from enum import IntEnum

class SureEnum(IntEnum):
    """Sure base enum."""
    def __str__(self) -> str:
        return self.name.title()

    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_ 

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

class FeederCloseDelay(SureEnum): # Feeder Close Delay speed
    Fast        = 0     # Fast delay
    Normal      = 4000  # Normal delay
    Felaqua     = 5000  # Normal delay
    Slow        = 20000 # Slow delay

class FeederBowls(SureEnum): # Feeder Close Delay speed
    Single        = 1   # RSinFast close delay
    Double        = 2   # Normal delay
    Felaqua       = 4   # Felaquay

class LockState(SureEnum): # Lock State IDs.
    Unlocked        = 0
    KeepIn          = 1
    KeepOut         = 2
    Locked          = 3
    Curfew          = 4
    CURFEW_LOCKED   = -1
    CURFEW_UNLOCKED = -2
    CURFEW_UNKNOWN  = -3

class CatFlapLockState(SureEnum): # Lock State IDs.
    Unlocked        = 6
    KeepIn          = 3
    KeepOut         = 5
    Locked          = 4

class LockedOutState(SureEnum): # Locked Out State for preventing animals coming in
    NORMAL          = 2  # Allow pets in
    LOCKED_IN       = 3  # Keep pets out

class PetDoorDirection(SureEnum): # Pet Movement on Pet Door coming in or out or looked in or unknown animal left
    LookedIn_Outside_40 = 0x40 #This happens if the pet comes up to the door from outside, puts head in and unlocks the door but doesn't come in.
    Inside_61           = 0x61 #Normal ingress
    Outside_62          = 0x62 #Normal egress
    Inside_81           = 0x81 #Ingress if the pet door thought the pet was already inside
    UnknownPet          = 0xd3 #This along with pet 621 is when the pet leaves too quickly for the pet door to read it leaving

class CurfewState(SureEnum): # Curfew State
    OFF             = 1
    ON              = 2
    STATUS          = 3

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

class ProvChipFrom(SureEnum): # Chip Provisioned State
    Existing        = 0  #Already provisioned on device
    Button          = 1  #Provisioned chip from learn button on the back
    NewCloud        = 2  #Provisioned chip from cloud
    Disabled        = 3  #Provisioned chip from cloud

class ProvChipState(SureEnum): # Chip Provisioned State
    Enabled         = 0
    Disabled        = 1
    LOCK            = 2

class CatFlapDirection(SureEnum): # Pet Movement on Cat Flap coming in or going out.
    Out             = 0x0000
    In              = 0x0101
    LookedIn        = 0x0201
    LookedOut       = 0x0200
    Status1         = 0x0102
    Status2         = 0x0202

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
