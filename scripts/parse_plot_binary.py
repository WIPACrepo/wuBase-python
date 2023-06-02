#!/usr/bin/env python 


import matplotlib.pyplot as plt


import numpy as np
import struct

import pywub.parser as wuparser 

    
def main(filename, ntoread):

    f = open(filename, "rb")

    frame_number = 0
    nbytes_read = 0
    
    fig, axes = plt.subplots(figsize=[8,6])
    axes.set_xlabel("sample") 
    axes.set_ylabel("adc (LSB)")
    while True:
        
        if frame_number >= ntoread and not ntoread == -1:
            break
        hdr = f.read(wuparser.HEADER_SIZE)
        
        if len(hdr) != wuparser.HEADER_SIZE:
            if len(hdr) == 0:
                print("Reached EOF!")
            else:
                print(f"Possible incomplete frame at header read: request: {wuparser.HEADER_SIZE} deliver: {len(hdr)}")
                print([f"{i:2X}" for i in hdr])
            break

        nbytes_read += len(hdr)

        nsamples, frame_id, fpga_ts, fpga_tdc = wuparser.unpack_header(hdr)
        
        frame_size = wuparser.calc_frame_size(nsamples)
        payload_size = wuparser.calc_payload_size(nsamples)
        
        payload = f.read(payload_size)
        nbytes_read += len(payload)


        print(f"Frame number {frame_number:X}")
        print(f"Header bytes:")
        bt = [f"{i:02X}" for i in hdr]
        print(f"{bt}")
        print(f"--> Unpacked info:\n\tnsamples: 0x{nsamples:4X}\tdecoded frame_id: 0x{frame_id:4X} fpga_ts: 0x{fpga_ts:16X} fpga_tdc: 0x{fpga_tdc:016X}")



        print(f"--> Payload size: {payload_size}")
        # bt = [f"{i:2X}" for i in payload]
        # print(f"{bt}") 

        if len(payload) != payload_size:
            print(f"Possible data corruption or EOF: request: {payload_size} deliver: {len(payload)}")
            break

        
        adc_data = wuparser.unpack_payload(payload)        
        
        plt.plot(adc_data[0:nsamples], label="Ch0")
        plt.plot(adc_data[nsamples::], label="Ch1")
        print(f"{adc_data}")
        frame_number+=1
        print(f"------------------------------------")
        
    print(f"nfames parsed: {frame_number}; nbytes parsed: {nbytes_read}")
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
