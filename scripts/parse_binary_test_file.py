#!/usr/bin/env python 

import numpy as np

import pywub.parser as wuparser 

    
def main(filename, ntoread, nsamples_expected):

    f = open(filename, "rb")

    frame_number = 0
    nbytes_read = 0
    
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
        
        payload_size = wuparser.calc_payload_size(nsamples)
        
        payload = f.read(payload_size)
        nbytes_read += len(payload)

        print(f"Frame number {frame_number:X}")
        print(f"Header bytes:")
        bt = [f"{i:2X}" for i in hdr]
        print(f"{bt}")
        print(f"--> Unpacked info:\n\tnsamples: {nsamples}\tframe_id: {frame_id:4X} fpga_ts: 0x{fpga_ts:8X}")# fpga_tdc: {bin(fpga_tdc)[2::]:064}")



        print(f"--> Payload size: {payload_size}")
        bt = [f"{i:2X}" for i in payload]
        print(f"{bt}")

        if nsamples != nsamples_expected:
            print(f"!!!!!! Test nsamples is incorrect! {nsamples} vs {nsamples_expected}")       
            break             

        if len(payload) != payload_size:
            print(f"Possible incomplete frame at EOL: request: {payload_size} deliver: {len(payload)}")
            break

        
        adc_data = wuparser.unpack_payload(payload)        
        
        print(f"{adc_data}")
        frame_number+=1
        print(f"------------------------------------")
        
    print(f"nfames parsed: {frame_number}; nbytes parsed: {nbytes_read}")

    f.close()



if __name__ == "__main__": 
    
    import argparse
    parser = argparse.ArgumentParser(description="Parse wuBase binary data.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--file", type=str, required=True, 
                        help="File to parse")
    parser.add_argument("--ntoparse", type=int, default=-1, 
                            help="Number of traces to parse from file. (-1 means all)") 
    parser.add_argument("--nsamples", type=int, default=0x8,
                            help="Number of expected samples in the test structure.")                       

    cli_args = parser.parse_args()  

    main(cli_args.file, cli_args.ntoparse, cli_args.nsamples)
