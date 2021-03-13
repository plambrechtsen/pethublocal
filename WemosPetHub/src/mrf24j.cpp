/**
 * mrf24j.cpp, Karl Palsson, 2011, karlp@tweak.net.au
 * modified bsd license / apache license
 */

#include "mrf24j.h"

// aMaxPHYPacketSize = 127, from the 802.15.4-2006 standard.
static uint8_t rx_buf[127];

// essential for obtaining the data frame only
// bytes_MHR = 2 Frame control + 1 sequence number + 2 panid + 8 longAddr Destination + 8 longAddr Source
static int bytes_MHR = 21;

static int ignoreBytes = 0; // bytes to ignore, some modules behaviour.

static boolean bufPHY = false; // flag to buffer all bytes in PHY Payload, or not

volatile uint8_t flag_got_rx;
volatile uint8_t flag_got_tx;

//static rx_info_t rx_info;
static rx_info_t rx_info;
static tx_info_t tx_info;
static init_params_t init_params;

// Frame Control Addressing Mode Length Mapping: Not Present, Reserved, Short (2 Bytes) , Long (8 Bytes) 
static uint8_t fcsamlength[4] = { 0x00, 0x00, 0x02, 0x08 };

SPISettings mySettings = SPISettings(10000000, MSBFIRST, SPI_MODE0);

/**
 * Constructor MRF24J Object.
 * @param pin_reset, @param pin_chip_select, @param pin_interrupt
 */
Mrf24j::Mrf24j(int pin_reset, int pin_chip_select, int pin_interrupt) {
    _pin_reset = pin_reset;
    _pin_cs = pin_chip_select;
    _pin_int = pin_interrupt;
    _RXMCR.b = 0;
    _TXMCR.b = 0;
    _TXMCR.csmabf = 4;
    _TXMCR.macminbe = 3;
    _ORDER.b = 0xFF;
    _TXSEQNO = 0;

    _CapacityInfo = 0;

    pinMode(_pin_reset, OUTPUT);
    pinMode(_pin_cs, OUTPUT);
    pinMode(_pin_int, INPUT);

//    SPI.setBitOrder(MSBFIRST) ;
//    SPI.setDataMode(SPI_MODE0);
    SPI.begin();
}

void Mrf24j::reset(void) {
    SPI.beginTransaction(mySettings);
    digitalWrite(_pin_reset, LOW);
    delayMicroseconds(300*1000);  // adjusted to be the same value
    digitalWrite(_pin_reset, HIGH);
    delayMicroseconds(300*1000);  // from manual
    SPI.endTransaction();

}

byte Mrf24j::read_short(byte address) {
    SPI.beginTransaction(mySettings);
    digitalWrite(_pin_cs, LOW);
    // 0 top for short addressing, 0 bottom for read
    SPI.transfer(address<<1 & 0b01111110);
    byte ret = SPI.transfer(0x00);
    digitalWrite(_pin_cs, HIGH);
    SPI.endTransaction();
    return ret;
}

byte Mrf24j::read_long(word address) {
    SPI.beginTransaction(mySettings);
    digitalWrite(_pin_cs, LOW);
    byte ahigh = address >> 3;
    byte alow = address << 5;
    SPI.transfer(0x80 | ahigh);  // high bit for long
    SPI.transfer(alow);
    byte ret = SPI.transfer(0);
    digitalWrite(_pin_cs, HIGH);
    SPI.endTransaction();
    return ret;
}

void Mrf24j::write_short(byte address, byte data) {
    SPI.beginTransaction(mySettings);
    digitalWrite(_pin_cs, LOW);
    // 0 for top short address, 1 bottom for write
    SPI.transfer((address<<1 & 0b01111110) | 0x01);
    SPI.transfer(data);
    digitalWrite(_pin_cs, HIGH);
    SPI.endTransaction();
}

void Mrf24j::write_long(word address, byte data) {
    SPI.beginTransaction(mySettings);
    digitalWrite(_pin_cs, LOW);
    byte ahigh = address >> 3;
    byte alow = address << 5;
    SPI.transfer(0x80 | ahigh);  // high bit for long
    SPI.transfer(alow | 0x10);  // last bit for write
    SPI.transfer(data);
    digitalWrite(_pin_cs, HIGH);
    SPI.endTransaction();
}

word Mrf24j::get_pan(void) {
    byte panh = read_short(MRF_PANIDH);
    return panh << 8 | read_short(MRF_PANIDL);
}

word Mrf24j::get_framecontrol(void) {
    byte fc = read_long(0x302);
    return fc << 8 | read_long(0x301);
}

void Mrf24j::set_pan(word panid) {
    write_short(MRF_PANIDH, panid >> 8);
    write_short(MRF_PANIDL, panid & 0xff);
}

void Mrf24j::address16_write(word address16) {
    write_short(MRF_SADRH, address16 >> 8);
    write_short(MRF_SADRL, address16 & 0xff);
}

word Mrf24j::address16_read(void) {
    byte a16h = read_short(MRF_SADRH);
    return a16h << 8 | read_short(MRF_SADRL);
}

/**
 * Simple send 16, with acks, not much of anything.. assumes src16 and local pan only.
 * @param data
 */
void Mrf24j::send16(word dest16, char * data) {
    byte len = strlen(data); // get the length of the char* array
    int i = 0;
    write_long(i++, bytes_MHR); // header length
    // +ignoreBytes is because some module seems to ignore 2 bytes after the header?!.
    // default: ignoreBytes = 0;
    write_long(i++, bytes_MHR+ignoreBytes+len);

    // 0 | pan compression | ack | no security | no data pending | data frame[3 bits]
    write_long(i++, 0b01100001); // first byte of Frame Control
    // 16 bit source, 802.15.4 (2003), 16 bit dest,
    write_long(i++, 0b10001000); // second byte of frame control
    write_long(i++, 1);  // sequence number 1

    word panid = get_pan();

    write_long(i++, panid & 0xff);  // dest panid
    write_long(i++, panid >> 8);
    write_long(i++, dest16 & 0xff);  // dest16 low
    write_long(i++, dest16 >> 8); // dest16 high

    word src16 = address16_read();
    write_long(i++, src16 & 0xff); // src16 low
    write_long(i++, src16 >> 8); // src16 high

    // All testing seems to indicate that the next two bytes are ignored.
    //2 bytes on FCS appended by TXMAC
    i+=ignoreBytes;
    for (int q = 0; q < len; q++) {
        write_long(i++, data[q]);
    }
    // ack on, and go!
    write_short(MRF_TXNCON, (1<<MRF_TXNACKREQ | 1<<MRF_TXNTRIG));
}

void Mrf24j::sendframe(tx_info_t tx_info) {

    noInterrupts();
    //Header FCF + SEQ + PAN = 5
    uint8_t len = 5;
    uint8_t dstlen = fcsamlength[tx_info.fcf.dam];
    uint8_t srclen = fcsamlength[tx_info.fcf.sam];
    uint8_t header_length = len + dstlen + srclen;

    uint8_t payload_length = tx_info.data_length;

    int i = 0;
    write_long(i++, header_length ); // header length
    write_long(i++, header_length + payload_length); // Packet length 

    // Frame Control Field
    word txfcf = tx_info.fcf.w;
    write_long(i++, txfcf & 0xff);
    write_long(i++, txfcf >> 8);
    
    // Sequence Number
    write_long(i++, _TXSEQNO++);

    // PAN
    word panid = get_pan();
    write_long(i++, panid & 0xff);  // panid
    write_long(i++, panid >> 8);

    if ( dstlen > 0 ) {
        for (int j = 0; j < dstlen; j++) {
            write_long(i++, rx_info.src[j]);
        }
    }
    if ( srclen == 8 ) {
        for (int j = 0; j < srclen; j++) {
            write_long(i++, init_params.hwmac[j]);
        }
    }

    for(uint8_t j=0;j< tx_info.data_length;j++){
        write_long(i++, tx_info.data[j]);
    }
    // ack on, and go!
    write_short(MRF_TXNCON, 1<<MRF_TXNTRIG);
    interrupts();
//    write_short(MRF_TXNCON, (1<<MRF_TXNACKREQ | 1<<MRF_TXNTRIG));
}

//Setup init params
init_params_t * Mrf24j::get_initparams(void) {
    // Check Hardware Mac 
    int arrval = 0;
    for (int i = 0; i < MRF_HWMAC_ADDR_LENGTH; i++) {
        arrval += init_params.hwmac[i];
    }
    // Set Hardware Mac Address - If the hwmac array is empty then we need to grab the hardware MAC Address.
    if (arrval == 0 ) {
        for (int i = 0; i < MRF_HWMAC_ADDR_LENGTH; i++) {
            init_params.hwmac[i] = read_short(MRF_HWMAC_ADDR + i);
        }
    }
    return &init_params;
}

//Setup init params - Hardware Mac Address
void Mrf24j::set_initparams(byte * macaddress) {
    //Set Hardware Mac Address
    for (int i = 0; i < MRF_HWMAC_ADDR_LENGTH; i++) {
        init_params.hwmac[i] = macaddress[i];
    }
    init_params.hwmacset = true;
}

void Mrf24j::set_interrupts(void) {
    // interrupts for rx and tx normal complete
}

/** use the 802.15.4 channel numbers..
 */
void Mrf24j::set_channel(byte channel) {
    write_long(MRF_RFCON0, (((channel - 11) << 4) | 0x03));
    write_short(MRF_RFCTL, 0x04); // Reset RF state machine.
    write_short(MRF_RFCTL, 0x00); // part 2
}

void Mrf24j::init(void) {
//    SPI.usingInterrupt(digitalPinToInterrupt(pin_interrupt));

    // Seems a bit ridiculous when I use reset pin anyway
    write_short(MRF_SOFTRST, 0x7); // from manual
    while ((read_short(MRF_SOFTRST) & 0x7) != 0) {
        ; // wait for soft reset to finish
    }
    

    /* flush the RX fifo */
    write_short(MRF_RXFLUSH,0x01);
    
    /* Program the short MAC Address, 0xffff */
    write_short(MRF_SADRL,0xFF);
    write_short(MRF_SADRH,0xFF);
    write_short(MRF_PANIDL,0xFF);
    write_short(MRF_PANIDH,0xFF);

    // Hardcode long mac address
    for(int i=0;i<8;i++)
    {
        write_short(MRF_EADR0+i,init_params.hwmac[i]);
    }

    //Start init following what Microchip does
    /* setup */
    write_long(MRF_RFCON2, 0x80); // – Enable PLL (PLLEN = 1).
    write_long(MRF_RFCON3, 0x00); // power level to be 0dBm

    /* program RSSI ADC with 2.5 MHz clock */
    write_long(MRF_RFCON6, 0x90); // – Initialize TXFIL = 1 and 20MRECVR = 1.
    write_long(MRF_RFCON7, 0x80); // – Initialize SLPCLKSEL = 0x2 (100 kHz Internal oscillator).
    write_long(MRF_RFCON8, 0x10); // – Initialize RFVCO = 1.
    write_long(MRF_SLPCON1, 0x21); // – Initialize CLKOUTEN = 1 and SLPCLKDIV = 0x01.

    //  Configuration for nonbeacon-enabled devices (see Section 3.8 “Beacon-Enabled and Nonbeacon-Enabled Networks”):
    write_short(MRF_BBREG2, 0x80); // Set CCA mode to ED - Program CCA mode using RSSI */
    write_short(MRF_BBREG6, 0x40); // – Set appended RSSI value to RXFIFO. - Enable the packet RSSI */
    write_short(MRF_CCAEDTH, 0x60); // – Set CCA ED threshold. - Program CCA, RSSI threshold values */

    write_short(MRF_PACON2, 0x98); // – Initialize FIFOEN = 1 and TXONTS = 0x6.
    write_short(MRF_TXSTBL, 0x95); // – Initialize RFSTBL = 0x9.

    while ((read_long(MRF_RFSTATE) & 0xA0) != 0xA0) {
        // wait until the MRF24J40 is in receive mode
    }

    //Set Interupts - Disable Sleep Alert, Wake-up Alert, Half Symbol Timer, Security Key, Enables RX FIFO, Disable TX GTS2 FIFO, Disable TX GTS1 FIFO, Enable TX Normal FIFO
    write_short(MRF_INTCON, 0b11110111);

    // Make RF communication stable under extreme temperatures
    write_long(MRF_RFCON0, 0x03); // – Initialize RFOPT = 0x03.
    write_long(MRF_RFCON1, 0x02); // – Initialize VCOOPT = 0x02.

    //Set Channel
    set_channel(15);
//    delay(1); // delay at least 192usec
}


/**
 * Call this from within an interrupt handler connected to the MRFs output
 * interrupt pin.  It handles reading in any data from the module, and letting it
 * continue working.
 * Only the most recent data is ever kept.
 */
void Mrf24j::interrupt_handler(void) {
    uint8_t last_interrupt = read_short(MRF_INTSTAT);
    if (last_interrupt & MRF_I_RXIF) {
        flag_got_rx++;
        // read out the packet data...
        noInterrupts();
        rx_disable();
        // read start of rxfifo for, has 2 bytes more added by FCF. frame_length = m + n + 2
        uint8_t frame_length = read_long(MRF_RXFIFO);
        rx_info.frame_length = frame_length;

        // Frame Control Field into fcf word.
        rx_info.fcf.w = read_long(MRF_RXFIFO + 2) << 8 | read_long(MRF_RXFIFO + 1);

        // Update rx_info src and dest mac and header_length based on Source and Destination Addressing Mode length.
        uint8_t len = 5;
        uint8_t dstlen = fcsamlength[rx_info.fcf.dam];
        uint8_t srclen = fcsamlength[rx_info.fcf.sam];
        if ( dstlen > 0 ) {
            for (int d = 0; d < dstlen; d++) {
                rx_info.dst[d] = read_long(MRF_RXFIFO + 1 + len + d );
            }
        }
        if ( srclen > 0 ) {
            for (int s = 0; s < srclen; s++) {
                rx_info.src[s] = read_long(MRF_RXFIFO + 1 + len + dstlen + s );
            }
        }
        rx_info.header_length = len + dstlen + srclen;
        rx_info.data_length = rx_info.frame_length - rx_info.header_length;

        // Copy payload
        if ( rx_info.frame_length > rx_info.header_length ) {
            for (int i = 0 ; i < rx_info.frame_length - rx_info.header_length ; i++) {
                // MRF_RXFIFO + Remove Length Byte + Header Length = Payload
                rx_info.data[i] = read_long(MRF_RXFIFO + 1 + rx_info.header_length + i);
            }
        }

        // LQI first byte after frame as per datasheet
        rx_info.lqi = read_long(MRF_RXFIFO + frame_length + 1 );

        // RSSI second byte after frame as per datasheet
        rx_info.rssi = read_long(MRF_RXFIFO + frame_length + 2 );
        rx_enable();
        interrupts();
    }
    if (last_interrupt & MRF_I_TXNIF) {
        flag_got_tx++;
        uint8_t tmp = read_short(MRF_TXSTAT);
        // 1 means it failed, we want 1 to mean it worked.
        tx_info.tx_ok = !(tmp & ~(1 << TXNSTAT));
        tx_info.retries = tmp >> 6;
        tx_info.channel_busy = (tmp & (1 << CCAFAIL));
    }
}


/**
 * Call this function periodically, it will invoke your nominated handlers
 */
void Mrf24j::check_flags(void (*rx_handler)(void), void (*tx_handler)(void)){
    // TODO - we could check whether the flags are > 1 here, indicating data was lost?
    if (flag_got_rx) {
        flag_got_rx = 0;
        rx_handler();
    }
    if (flag_got_tx) {
        flag_got_tx = 0;
        tx_handler();
    }
}

/**
 * Set RX mode to promiscuous, or normal
 */
void Mrf24j::set_promiscuous(boolean enabled) {
    if (enabled) {
        _RXMCR.promi = true;
    } else {
        _RXMCR.promi = false;
    }
    write_short(MRF_RXMCR, _RXMCR.b);
}

/**
 * Set Pan controller
 * Configuring Nonbeacon-Enabled PAN Coordinator
The following steps configure the MRF24J40 as a coordinator in a nonbeacon-enabled network:
1. Set the PANCOORD (RXMCR 0x00<3>) bit = 1 to configure as the PAN coordinator.
2. Clear the SLOTTED (TXMCR 0x11<5>) bit = 0 to configure Unslotted CSMA-CA mode.
3. Configure BO (ORDER 0x10<7:4>) value = 0xF.
4. Configure SO (ORDER 0x10<3:0>) value = 0xF.
 * 
 */
void Mrf24j::set_pancontroller(boolean enabled) {
    if (enabled) {
        _RXMCR.pancoord = true;
    } else {
        _RXMCR.pancoord = false;
    }    
    write_short(MRF_RXMCR, _RXMCR.b);
    if (enabled) {
        _TXMCR.slotted = false;
    } else {
        _TXMCR.slotted = true;
    }
    write_short(MRF_TXMCR, _TXMCR.b);
    write_short(MRF_ORDER, _ORDER.b);
}

/**
 * Set coordinator
 */
void Mrf24j::set_coordinator() {
    bitSet(_CapacityInfo,3);
}

rx_info_t * Mrf24j::get_rxinfo(void) {
    return &rx_info;
}

tx_info_t * Mrf24j::get_txinfo(void) {
    return &tx_info;
}

uint8_t * Mrf24j::get_rxbuf(void) {
    return rx_buf;
}

void Mrf24j::set_ignoreBytes(int ib) {
    // some modules behaviour
    ignoreBytes = ib;
}

/**
 * Set bufPHY flag to buffer all bytes in PHY Payload, or not
 */
void Mrf24j::set_bufferPHY(boolean bp) {
    bufPHY = bp;
}

boolean Mrf24j::get_bufferPHY(void) {
    return bufPHY;
}

/**
 * Set PA/LNA external control
 */
void Mrf24j::set_palna(boolean enabled) {
    if (enabled) {
        write_long(MRF_TESTMODE, 0x07); // Enable PA/LNA on MRF24J40MB module.
    }else{
        write_long(MRF_TESTMODE, 0x00); // Disable PA/LNA on MRF24J40MB module.
    }
}

void Mrf24j::rx_flush(void) {
    write_short(MRF_RXFLUSH, 0x00);
}

void Mrf24j::rx_disable(void) {
    write_short(MRF_BBREG1, 0x04);  // RXDECINV - disable receiver
}

void Mrf24j::rx_enable(void) {
    write_short(MRF_BBREG1, 0x00);  // RXDECINV - enable receiver
}
