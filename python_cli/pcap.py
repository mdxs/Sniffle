"""
Quick'n'dirty Pcap module

This module only provides a specific class able to write
PCAP files with Bluetooth Low Energy Link Layer.
"""

"""
SQK: taken from virtuallabs btlejack code (rev d7e6555)
Originally licensed under the MIT license
https://github.com/virtualabs/btlejack/blob/master/btlejack/pcap.py

Copyright (c) 2018 virtualabs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from io import BytesIO
from struct import pack

class PcapBleWriter(object):
    """
    PCAP BLE Link-layer writer.
    """

    DLT =  251  # DLT_BLUETOOTH_LE_LL

    def __init__(self, output=None):
        # open stream
        if output is None:
            self.output = BytesIO()
        else:
            self.output = open(output,'wb')

        # write headers
        self.write_header()

    def write_header(self):
        """
        Write PCAP header.
        """
        header = pack(
            '<IHHIIII',
            0xa1b2c3d4,
            2,
            4,
            0,
            0,
            65535,
            self.DLT
        )
        self.output.write(header)

    def write_packet_header(self, ts_sec, ts_usec, packet_size):
        """
        Write packet header
        """
        pkt_header = pack(
            '<IIII',
            ts_sec,
            ts_usec,
            packet_size,
            packet_size
        )
        self.output.write(pkt_header)

    def payload(self, aa, packet, chan, rssi):
        """
        Generates Bluetooth LE LL packet format.
        You must override this method for every inherited
        writer classes.
        """
        return pack('<I', aa) + packet[10:]+ pack('<BBB',0,0,0) # fake CRC for now

    def write_packet(self, ts_usec, aa, chan, rssi, packet):
        """
        Add packet to PCAP output.

        Basically, generates payload and encapsulates in a header.
        """
        ts_s = ts_usec // 10000000
        ts_u = int(ts_usec - ts_s*1000000)
        payload = self.payload(aa, packet, chan, rssi)
        self.write_packet_header(ts_s, ts_u, len(payload))
        self.output.write(payload)

    def close(self):
        """
        Close PCAP.
        """
        if not isinstance(self.output, BytesIO):
            self.output.close()

class PcapBlePHDRWriter(PcapBleWriter):
    """
    PCAP BLE Link-layer with PHDR.
    """
    DLT = 256 # DLT_BLUETOOTH_LE_LL_WITH_PHDR

    def __init__(self, output=None):
        super().__init__(output=output)

    def payload(self, aa, packet, chan, rssi):
        """
        Generate payload with specific header.
        """
        payload_header = pack(
            '<BbbBIH',
            chan,
            rssi,
            -100,
            0,
            aa,
            0x813
        )
        payload_data = pack('<I', aa) + packet[10:] + pack('<BBB', 0, 0, 0)
        return payload_header + payload_data


class PcapNordicTapWriter(PcapBleWriter):
    """
    PCAP BLE Link-layer writer.
    """

    DLT = 272 # DLT_NORDIC_BLE
    BTLEJACK_ID = 0xDC

    def __init__(self, output=None):
        super().__init__(output=output)
        self.pkt_counter = 0

    def payload(self, aa, packet, chan, rssi):
        """
        Create payload with Nordic Tap header.
        """
        payload_data = packet[:10] + pack('<I', aa) + packet[10:]
        payload_data += pack('<BBB', 0, 0, 0)
        pkt_size = len(payload_data)
        if pkt_size > 256:
            pkt_size = 256

        payload_header = pack(
            '<BBBBHB',
            self.BTLEJACK_ID,
            6,
            pkt_size,
            1,
            self.pkt_counter,
            0x06 # EVENT_PACKET
        )

        return payload_header + payload_data[:pkt_size]
