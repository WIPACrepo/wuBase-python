#!/usr/bin/env python 


import matplotlib.pyplot as plt


import numpy as np
import struct

def calc_frame_size(nsamples):
    return NSAMPLES_WIDTH + FPGA_TS_WIDTH + FPGA_TDC_WIDTH + 2*2*nsamples

def calc_payload_size(nsamples):
    return 2*2*nsamples

NSAMPLES_WIDTH = 2
FPGA_TS_WIDTH = 6
FPGA_TDC_WIDTH = 8

NSAMPLES_OFFSET = 0
FPGA_TS_OFFSET = NSAMPLES_OFFSET + NSAMPLES_WIDTH
FPGA_TDC_OFFSET = FPGA_TS_OFFSET + FPGA_TS_WIDTH
ADC_DATA_OFFSET = FPGA_TDC_OFFSET + FPGA_TDC_WIDTH

HEADER_SIZE = NSAMPLES_WIDTH + FPGA_TS_WIDTH + FPGA_TDC_WIDTH

def unpack_header(header):
    return struct.unpack("<HQQ", header)
    
def unpack_payload(payload):
    unpack_fmt = "<" + "".join(["H" for s in range(int(len(payload)/2))])
    return struct.unpack(unpack_fmt, payload)

    
def main(filename, ntoread):

    f = open(filename, "rb")

    frame_number = 0
    
    fig, axes = plt.subplots(figsize=[8,6])
    axes.set_xlabel("sample") 
    axes.set_ylabel("adc (LSB)")
    while True:
        
        if frame_number >= ntoread and not ntoread == -1:
            break
        hdr = f.read(HEADER_SIZE)
        if len(hdr) != HEADER_SIZE:
            break
        
        header = bytearray(hdr)
        header.insert(FPGA_TS_OFFSET + FPGA_TS_WIDTH, 0) #Undo the C close-packing
        header.insert(FPGA_TS_OFFSET + FPGA_TS_WIDTH+1, 0) #Undo the C close-packing

        nsamples, fpga_ts, fpga_tdc = unpack_header(header)
        
        frame_size = calc_frame_size(nsamples)
        payload_size = calc_payload_size(nsamples)
        payload = f.read(payload_size)

        print(f"Frame number {frame_number}")
        print(f"--> Header info:\n\tnsamples: {nsamples}\t fpga_ts: 0x{fpga_ts:8X}\t fpga_tdc: {bin(fpga_tdc)[2::]:064}")
        print(f"--> Payload size: {payload_size}")
        adc_data = unpack_payload(payload)
        
        plt.plot(adc_data[0:nsamples], label="Ch0")
        plt.plot(adc_data[nsamples::], label="Ch1")
        
        frame_number+=1
        

    fig.savefig("plot.pdf")
    f.close()



if __name__ == "__main__": 
    
    import argparse
    parser = argparse.ArgumentParser(description="Parse wuBase binary data.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--file", type=str, required=True, 
                        help="File to parse")
    parser.add_argument("--ntoparse", type=int, default=-1, 
                            help="Number of traces to parse from file. (-1 means all)")                        

    cli_args = parser.parse_args()  

    main(cli_args.file, cli_args.ntoparse)
