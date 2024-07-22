from __future__ import annotations  # Reminder: May be removed after Python 3.9 is EOL.

import struct
from typing import Any

#FIXME: Applies only to MPEs as it stands... 

START_BYTE = 0x21

START_BYTE_WIDTH = 1
NSAMPLES_WIDTH = 2
HIT_NUMBER_WIDTH = 2
FPGA_TS_WIDTH = 6
FPGA_TDC_WIDTH = 8

NSAMPLES_OFFSET   = 0
HIT_NUMBER_OFFSET = NSAMPLES_OFFSET   + NSAMPLES_WIDTH
FPGA_TS_OFFSET    = HIT_NUMBER_OFFSET + HIT_NUMBER_WIDTH
FPGA_TDC_OFFSET   = FPGA_TS_OFFSET    + FPGA_TS_WIDTH
ADC_DATA_OFFSET   = FPGA_TDC_OFFSET   + FPGA_TDC_WIDTH

HEADER_SIZE = NSAMPLES_WIDTH + HIT_NUMBER_WIDTH + FPGA_TS_WIDTH + FPGA_TDC_WIDTH

def unpack_nsamples(d: bytes) -> int:

    if NSAMPLES_WIDTH == 2:
        return struct.unpack("<H", d)[0]
    else:
        return struct.unpack("<B", d)[0]

def unpack_header(header: bytes) -> tuple[Any, ...]:
    
    header = bytearray(header)
    
    header.insert(FPGA_TS_OFFSET + FPGA_TS_WIDTH, 0) #Undo the C close-packing
    header.insert(FPGA_TS_OFFSET + FPGA_TS_WIDTH+1, 0) #Undo the C close-packing
    

    fmt = "<" #endianness + start byte
    if NSAMPLES_WIDTH == 2:
        fmt += "H"
    else:
        fmt += "B"
    
    fmt += "HQQ"
    
    return struct.unpack(fmt, header)
    
def unpack_payload(payload: bytes) -> tuple[Any, ...]:
    unpack_fmt = "<" + "".join(["H" for s in range(int(len(payload)/2))])
    return struct.unpack(unpack_fmt, payload)

def calc_payload_size(nsamples: int) -> int:
    return 2*2*nsamples

def calc_frame_size(nsamples: int) -> int:
    return NSAMPLES_WIDTH + HIT_NUMBER_WIDTH + FPGA_TS_WIDTH + FPGA_TDC_WIDTH + calc_payload_size(nsamples)


def parse_single_raw_hit(hit_data:bytearray) -> bool:
        '''
        Take a bytearray object and try to extract a hit from it.
        '''
        nbytes_read = 0    
        sw = hit_data[0:START_BYTE_WIDTH]
    
        sw = sw.hex()
        sw = int(sw, 16)
        if sw != START_BYTE:
            print(f"Error getting start byte: {sw:x} vs {START_BYTE:x}")
            return False
        
        nbytes_read += START_BYTE_WIDTH
        
        hdr = hit_data[nbytes_read:nbytes_read+HEADER_SIZE]
        
        nbytes_read += len(hdr)

        nsamples, frame_id, fpga_ts, fpga_tdc = unpack_header(hdr)
        
        frame_size = calc_frame_size(nsamples)
        payload_size = calc_payload_size(nsamples)
        
        payload = hit_data[nbytes_read:nbytes_read+payload_size]

        nbytes_read += len(payload)

        # print(f"Header bytes:")
        bt = [f"{i:02X}" for i in hdr]
        # print(f"{bt}")
        print(f"--> Unpacked info:\n\tnsamples: 0x{nsamples:4X}\tdecoded frame_id: 0x{frame_id:4X} fpga_ts: 0x{fpga_ts:16X} fpga_tdc: 0x{fpga_tdc:016X}")

        print(f"--> Payload size: {payload_size}")

        if len(payload) != payload_size:
            print(f"Possible data corruption or EOF: request: {payload_size} deliver: {len(payload)}")
            return 0
                
        adc_data = unpack_payload(payload)        
        
        print(f"{adc_data}")

        print(f"------------------------------------")

        return True