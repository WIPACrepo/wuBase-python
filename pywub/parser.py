import struct

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

def unpack_nsamples(d):

    if NSAMPLES_WIDTH == 2:
        return struct.unpack("<H", d)[0]
    else:
        return struct.unpack("<B", d)[0]

def unpack_header(header):
    
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
    
def unpack_payload(payload):
    unpack_fmt = "<" + "".join(["H" for s in range(int(len(payload)/2))])
    return struct.unpack(unpack_fmt, payload)

def calc_frame_size(nsamples):
    return NSAMPLES_WIDTH + HIT_NUMBER_WIDTH + FPGA_TS_WIDTH + FPGA_TDC_WIDTH + 2*2*nsamples

def calc_payload_size(nsamples):
    return 2*2*nsamples

