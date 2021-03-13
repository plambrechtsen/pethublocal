/*
 * File:   mrf24j.h
 * copyright Karl Palsson, karlp@tweak.net.au, 2011
 * modified BSD License / apache license
 */

#ifndef LIB_MRF24J_H
#define LIB_MRF24J_H

#include "Arduino.h"
#include "SPI.h"

#define SUREPET_ID 0x7E

#define MRF_RXMCR 0x00
#define MRF_PANIDL 0x01
#define MRF_PANIDH 0x02
#define MRF_SADRL 0x03
#define MRF_SADRH 0x04
#define MRF_EADR0 0x05
#define MRF_EADR1 0x06
#define MRF_EADR2 0x07
#define MRF_EADR3 0x08
#define MRF_EADR4 0x09
#define MRF_EADR5 0x0A
#define MRF_EADR6 0x0B
#define MRF_EADR7 0x0C
#define MRF_RXFLUSH 0x0D
//#define MRF_Reserved 0x0E
//#define MRF_Reserved 0x0F
#define MRF_ORDER 0x10
#define MRF_TXMCR 0x11
#define MRF_ACKTMOUT 0x12
#define MRF_ESLOTG1 0x13
#define MRF_SYMTICKL 0x14
#define MRF_SYMTICKH 0x15
#define MRF_PACON0 0x16
#define MRF_PACON1 0x17
#define MRF_PACON2 0x18
//#define MRF_Reserved 0x19
#define MRF_TXBCON0 0x1A

// TXNCON: TRANSMIT NORMAL FIFO CONTROL REGISTER (ADDRESS: 0x1B)
#define MRF_TXNCON      0x1B
#define MRF_TXNTRIG     0
#define MRF_TXNSECEN    1
#define MRF_TXNACKREQ   2
#define MRF_INDIRECT    3
#define MRF_FPSTAT      4

#define MRF_TXG1CON 0x1C
#define MRF_TXG2CON 0x1D
#define MRF_ESLOTG23 0x1E
#define MRF_ESLOTG45 0x1F
#define MRF_ESLOTG67 0x20
#define MRF_TXPEND 0x21
#define MRF_WAKECON 0x22
#define MRF_FRMOFFSET 0x23
// TXSTAT: TX MAC STATUS REGISTER (ADDRESS: 0x24)
#define MRF_TXSTAT 0x24
#define TXNRETRY1       7
#define TXNRETRY0       6
#define CCAFAIL         5
#define TXG2FNT         4
#define TXG1FNT         3
#define TXG2STAT        2
#define TXG1STAT        1
#define TXNSTAT         0

#define MRF_TXBCON1 0x25
#define MRF_GATECLK 0x26
#define MRF_TXTIME 0x27
#define MRF_HSYMTMRL 0x28
#define MRF_HSYMTMRH 0x29
#define MRF_SOFTRST 0x2A
//#define MRF_Reserved 0x2B
#define MRF_SECCON0 0x2C
#define MRF_SECCON1 0x2D
#define MRF_TXSTBL 0x2E
//#define MRF_Reserved 0x2F
#define MRF_RXSR 0x30
#define MRF_INTSTAT 0x31
#define MRF_INTCON 0x32
#define MRF_GPIO 0x33
#define MRF_TRISGPIO 0x34
#define MRF_SLPACK 0x35
#define MRF_RFCTL 0x36
#define MRF_SECCR2 0x37
#define MRF_BBREG0 0x38
#define MRF_BBREG1 0x39
#define MRF_BBREG2 0x3A
#define MRF_BBREG3 0x3B
#define MRF_BBREG4 0x3C
//#define MRF_Reserved 0x3D
#define MRF_BBREG6 0x3E
#define MRF_CCAEDTH 0x3F

//Hardware MAC Address
#define MRF_HWMAC_ADDR 0xFA
//Hardware mac address length
#define MRF_HWMAC_ADDR_LENGTH 0x08

#define MRF_RFCON0 0x200
#define MRF_RFCON1 0x201
#define MRF_RFCON2 0x202
#define MRF_RFCON3 0x203
#define MRF_RFCON5 0x205
#define MRF_RFCON6 0x206
#define MRF_RFCON7 0x207
#define MRF_RFCON8 0x208
#define MRF_SLPCAL0 0x209
#define MRF_SLPCAL1 0x20A
#define MRF_SLPCAL2 0x20B
#define MRF_RFSTATE 0x20F
#define MRF_RSSI 0x210
#define MRF_SLPCON0 0x211
#define MRF_SLPCON1 0x220
#define MRF_WAKETIMEL 0x222
#define MRF_WAKETIMEH 0x223
#define MRF_REMCNTL 0x224
#define MRF_REMCNTH 0x225
#define MRF_MAINCNT0 0x226
#define MRF_MAINCNT1 0x227
#define MRF_MAINCNT2 0x228
#define MRF_MAINCNT3 0x229
#define MRF_TESTMODE 0x22F
#define MRF_ASSOEADR1 0x231
#define MRF_ASSOEADR2 0x232
#define MRF_ASSOEADR3 0x233
#define MRF_ASSOEADR4 0x234
#define MRF_ASSOEADR5 0x235
#define MRF_ASSOEADR6 0x236
#define MRF_ASSOEADR7 0x237
#define MRF_ASSOSADR0 0x238
#define MRF_ASSOSADR1 0x239
#define MRF_UPNONCE0 0x240
#define MRF_UPNONCE1 0x241
#define MRF_UPNONCE2 0x242
#define MRF_UPNONCE3 0x243
#define MRF_UPNONCE4 0x244
#define MRF_UPNONCE5 0x245
#define MRF_UPNONCE6 0x246
#define MRF_UPNONCE7 0x247
#define MRF_UPNONCE8 0x248
#define MRF_UPNONCE9 0x249
#define MRF_UPNONCE10 0x24A
#define MRF_UPNONCE11 0x24B
#define MRF_UPNONCE12 0x24C

#define MRF_RXFIFO 0x300 // Received packets start at RXFIFO with first byte being received packet length.

#define MRF_I_RXIF  0b00001000
#define MRF_I_TXNIF 0b00000001

// Frame control field union to map the bits to a word.
typedef union _framecontrolfield {  
    struct {
        // Second byte of fcf
        uint8_t type: 3; // Frame Type
        bool sec: 1; // Security Enabled
        bool fp: 1; // Frame Pending
        bool ack: 1; // Acknowledge Request
        bool panc: 1; // PAN ID Compression
        bool r: 1; // Reserved
        // First byte of fcf
        bool seqq: 1; // Sequence Number Suppression
        bool ie: 1; // Information Elements Present
        uint8_t dam: 2; // Destination Addressing Mode
        uint8_t v: 2; // Frame Version
        uint8_t sam: 2; // Source Addressing Mode
    };
    word w; // FCF word.
} fcf_u;

/*          _CapacityInfo;
            BYTE    Sleep           :1;
            BYTE    Role            :2;
            BYTE    Security        :1;
            BYTE    ConnMode        :2;
            BYTE    CoordCap        :1;
*/

// REGISTER 2-1: RXMCR: RECEIVE MAC CONTROL REGISTER (ADDRESS: 0x00)
typedef union _rxmcr {
    struct {
        bool promi: 1; // PROMI: Promiscuous Mode bit - 1=Receive all good packets, 0=Disabled (D)
        bool errpkt: 1; // ERRPKT: Packet Error Mode - 1=Accept including bad CRC packets, 0=Accpet only good CRC (D)
        bool coord: 1; // COORD: Coordinator - 1=Enabled, 0=Disabled (D)
        bool pancoord: 1; // PANCOORD: PAN Coordinator - 1=Enabled, 0=Disabled (D)
        bool r4: 1; // Reserved - 0 (D)
        bool noackrsp: 1; // NOACKRSP: Automatic Acknowledgement Response - 1 = Disabled, 0=Acknowledgements are returned when they are requested (D).
        bool r6: 1; // Reserved - 0 (D)
        bool r7: 1; // Reserved - 0 (D)
    };
    int b; // RCMCR byte.
} rxmcr_u;

// REGISTER 2-15: ORDER: BEACON AND SUPERFRAME ORDER REGISTER (ADDRESS: 0x10)
typedef union _order {
    struct {
        uint8_t so: 4; // Superframe Order - Specifies the length of the active portion of the superframe, including the beacon frame
        uint8_t bo: 4; // Beacon Order bits - Specifies how often the coordinator will transmit a beacon.
    };
    int b; // ORDER byte.
} order_u;

// REGISTER 2-16: TXMCR: CSMA-CA MODE CONTROL REGISTER (ADDRESS: 0x11)
typedef union _txmcr {
    struct {
        int csmabf: 3; // CSMABF<2:0>: CSMA Backoff - 0-5 (6&7 Undef) and 4(D)
        int macminbe: 2; // MACMINBE<1:0>: MAC Minimum Backoff Exponent in the CSMA-CA algorithm - 0=Disabled, 3(D)
        bool slotted: 1; // SLOTTED: Slotted CSMA-CA Mode bit - 1=Enable, 0=Disable(D)
        bool batlife: 1; // BATLIFEXT: Battery Life Extension Mode - 1=Enable, 0=Disable(D)
        bool nocsma: 1; // NOCSMA: No Carrier Sense Multiple Access Algorithm - 1=Disable, 0=Enable(D)
    };
    int b; // TCMCR Byte
} txmcr_u;


/**
 * Single structure for messages used for RX and TX
 */
typedef struct _message_t {
    uint8_t frame_length;
    uint8_t header_length;
    uint8_t payload_length;
    uint8_t data_length;
    fcf_u fcf; // Field Control Field
    uint8_t seq; // Sequence number
    word panid;
    uint8_t src[8];
    uint8_t dst[8];
    uint8_t payload[116]; // max payload length = (127 aMaxPHYPacketSize - 2 Frame control - 1 sequence number - 2 panid - 2 shortAddr Destination - 2 shortAddr Source - 2 FCS)
    uint8_t lqi;
    uint8_t rssi;
} message_t;

typedef struct _rx_info_t {
    uint8_t frame_length;
    uint8_t header_length;
    uint8_t data_length;
    uint8_t data[116]; //max data length = (127 aMaxPHYPacketSize - 2 Frame control - 1 sequence number - 2 panid - 2 shortAddr Destination - 2 shortAddr Source - 2 FCS)
    uint8_t lqi;
    uint8_t rssi;
    fcf_u fcf;
    word panid;
    uint8_t src[8];
    uint8_t dst[8];
} rx_info_t;

/**
 * Based on the TXSTAT register, but "better"
 */
typedef struct _tx_info_t{
    uint8_t tx_ok:1;
    uint8_t retries:2;
    uint8_t channel_busy:1;
    fcf_u fcf;
    uint8_t dst[8];
    uint8_t data[116]; //max data length = (127 aMaxPHYPacketSize - 2 Frame control - 1 sequence number - 2 panid - 2 shortAddr Destination - 2 shortAddr Source - 2 FCS)
    uint8_t data_length;
    uint8_t frame_length;
    uint8_t header_length;
    uint8_t srclen;
    uint8_t dstlen;
} tx_info_t;

// Init paramers for setting a custom source MAC Address
typedef struct _init_params_t {
    uint8_t hwmac_length:MRF_HWMAC_ADDR_LENGTH;
    uint8_t hwmac[MRF_HWMAC_ADDR_LENGTH];
    bool hwmacset;
} init_params_t;

class Mrf24j
{
    public:
        Mrf24j(int pin_reset, int pin_chip_select, int pin_interrupt);
        void reset(void);
        void init(void);

        byte read_short(byte address);
        byte read_long(word address);

        void write_short(byte address, byte data);
        void write_long(word address, byte data);

        word get_pan(void);
        void set_pan(word panid);

        word get_framecontrol(void);

        void address16_write(word address16);
        word address16_read(void);

        void set_interrupts(void);

        void set_promiscuous(boolean enabled);
        void set_pancontroller(boolean enabled);
        void set_coordinator(void);
        void sendframe(tx_info_t tx_info);

        /**
         * Set the channel, using 802.15.4 channel numbers (11..26)
         */
        void set_channel(byte channel);

        void rx_enable(void);
        void rx_disable(void);

        /** If you want to throw away rx data */
        void rx_flush(void);

        rx_info_t * get_rxinfo(void);

        tx_info_t * get_txinfo(void);

        uint8_t * get_rxbuf(void);

        void set_ignoreBytes(int ib);

        /**
         * Set bufPHY flag to buffer all bytes in PHY Payload, or not
         */
        void set_bufferPHY(boolean bp);

        boolean get_bufferPHY(void);

        //Setup init params
        init_params_t * get_initparams(void);
        void set_initparams(byte * data);

        /**
         * Set PA/LNA external control
         */
        void set_palna(boolean enabled);

        void send16(word dest16, char * data);
        //void beaconack(byte type);
        tx_info_t * beaconack(byte type);

        void interrupt_handler(void);

        void check_flags(void (*rx_handler)(void), void (*tx_handler)(void));

    private:
        int _pin_reset;
        int _pin_cs;
        int _pin_int;
        rxmcr_u _RXMCR;
        txmcr_u _TXMCR;
        order_u _ORDER;
        byte _TXSEQNO;
        byte _CapacityInfo;
};

#endif  /* LIB_MRF24J_H */
