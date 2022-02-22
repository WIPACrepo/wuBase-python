#!/usr/bin/env python 

import matplotlib.pyplot as plt
import numpy as np
import os, sys

from eventHist import *

# make plots of wuBase hit waveforms, ascii output format V1
# as recorded by take-test-data*.py script
#
# Usage: python plot-test-data.py basename infile1 [infile2] [...]
# 
# Output: {basename}_waveforms.pdf, etc

if len(sys.argv)<3:
	print("\nUsage: python plot-test-data.py basename infile1 [infile2] [...]\n")
	sys.exit(1)

hitData=[]  # will hold (ch1,ch2,discraw,discsync) for each saved hit
maxDisplayWaveforms = 1500
waveformCount = 0

# make a filename root from the first argument
basename=sys.argv[1]
  
# calibration constants to convert from raw adc values into uA & pC
ch1_uA_per_count = 0.2494
ch1_pC_per_count_sample = 0.004157

h_ch1all=eventHist(300.,400.,100,basename,"Ch1 Value (All)","Events")
h_ch1event=eventHist(300.,400.,100,basename,"Ch1 Value (Current event)","Events")
h_ch1ped=eventHist(300.,400.,100,basename,"Ch1 Pedestal","Events")
h_ch1max=eventHist(-20.,200.,110,basename,"Ch1 Maximum (subtracted)","Events")
h_ch1area=eventHist(-100.,1000.,110,basename,"Ch1 Pulse Sum (subtracted)","Events")
h_ch1imax=eventHist(-5.,50.,110,basename,"Ch1 Peak Current (uA)","Events")
h_ch1charge=eventHist(-0.2,2.0,110,basename,"Ch1 Charge (pC)","Events")
h_dt=eventHist(0.,0.1,100,basename,"Time between hits (sec)","Events")
h_log10dt=eventHist(-8.,2.,1000,basename,"Log10(dt/sec) between hits","Events")

# read mode fsm definitions
WAIT_FOR_HIT=0
NSAMPLES_NEXT=1
TIMESTAMP_NEXT=2
TDCWORD_NEXT=3
CH1_NEXT=4
CH1_IN_PROGRESS=5
CH2_IN_PROGRESS=6
readstate=WAIT_FOR_HIT

for infile in sys.argv[2:]:
 lasttime=None

 with open(infile) as f:
  readstate=WAIT_FOR_HIT
  readingCh1=False   # will be True when line is expected to have ch1 data
  readingCh2=False   # similar for ch2
  for line in f:
    linestrip=line.rstrip()
    tokens=linestrip.split()
    if readstate==WAIT_FOR_HIT:
      if len(tokens)!=1: continue
      if tokens[0]!="V1": continue
      readstate=NSAMPLES_NEXT
      continue
    elif readstate==NSAMPLES_NEXT:
      if len(tokens)!=1:
        readstate=WAIT_FOR_HIT #unexpected input
      else:
        nsamples=int(tokens[0],16)
        readstate=TIMESTAMP_NEXT
        if nsamples>256:
          readstate=WAIT_FOR_HIT # unexpected input
      continue
    elif readstate==TIMESTAMP_NEXT:
      if len(tokens)!=1:
        readstate=WAIT_FOR_HIT #unexpected input
      else:
        time=int(tokens[0],16)
        readstate=TDCWORD_NEXT
      continue
    elif readstate==TDCWORD_NEXT:
      if len(tokens)!=1:
        readstate=WAIT_FOR_HIT #unexpected input
      else:
        readstate=CH1_NEXT
      continue
    elif readstate==CH1_NEXT:
      ch1=[]
      ch2=[]
      discraw=[]
      discsync=[]
      for hexvalue in tokens:
        raw=int(hexvalue,16)&0xfff
        if len(ch1)>=nsamples:
          readstate=WAIT_FOR_HIT #more values than expected
          continue
        ch1.append(raw)
      if len(ch1)==nsamples:
        readstate=CH2_IN_PROGRESS
      else:
        readstate=CH1_IN_PROGRESS
      continue
    elif readstate==CH1_IN_PROGRESS:
      for hexvalue in tokens:
        raw=int(hexvalue,16)&0xfff
        if len(ch1)>=nsamples:
          readstate=WAIT_FOR_HIT #more values than expected
          continue
        ch1.append(raw)
      if len(ch1)==nsamples:
        readstate=CH2_IN_PROGRESS
      else:
        readstate=CH1_IN_PROGRESS
      continue
    elif readstate==CH2_IN_PROGRESS:
      for hexvalue in tokens:
        raw=int(hexvalue,16)
        if len(ch2)>=nsamples:
          readstate=WAIT_FOR_HIT #more values than expected
          continue
        ch2.append(raw&0xfff)
        discsync.append((raw>>13)&1)
        discraw.append((raw>>12)&1)
      if len(ch2)==nsamples:
        readstate=WAIT_FOR_HIT # that's next after processing data
        ymax=max(ch1)
        if ymax==0: continue   # empty waveform = not good
        waveformCount += 1
        if len(hitData)<maxDisplayWaveforms:
          hitData.append((ch1,ch2,discraw,discsync))
        ch1_value_counts=numpy.zeros(100)
        h_ch1event.clear()
        for ch1_value in ch1: 
          h_ch1event.increment(ch1_value)
          h_ch1all.increment(ch1_value)
        imax,nmax=h_ch1event.getMaximum()
        # compute sloppily interpolated max in (imax-.5,imax+.5), call that pedestal
        nleft=h_ch1event.getBinValue(imax-1)
        nright=h_ch1event.getBinValue(imax+1)
        pedestal=h_ch1event.xmin+h_ch1event.dx*(imax+(nright-nleft)/(nmax+nleft+nright))
        h_ch1ped.increment(pedestal)
        # subtract pedestal from peak, add to histogram
        h_ch1max.increment(ymax-pedestal)
        h_ch1imax.increment((ymax-pedestal)*ch1_uA_per_count)
        # add up samples in window (-3,+6) around max of waveform
        tmax=ch1.index(ymax)
        tleft=tmax-3
        if tleft<0: tleft=0
        tright=tmax+6+1
        if tright>=len(ch1): tright=len(ch1)-1
        area=sum(ch1[tleft:tright])-(tright-tleft)*pedestal
        h_ch1area.increment(area)
        charge=area*ch1_pC_per_count_sample
        h_ch1charge.increment(charge)
        # compute time separation between this hit and the previous one (assuming time stamps at 60Msps)
        if lasttime:
          if time<=lasttime:
            h_log10dt.increment(-100.) # use underflow bin for unphysical values
            h_dt.increment(-100.)
          else:
            h_log10dt.increment(math.log10((time-lasttime)/60e6))
            h_dt.increment((time-lasttime)/60e6)
        lasttime=time
      else:
        readstate=CH2_IN_PROGRESS
      continue


print(f"Total reported hits = {waveformCount}")

# plot sample waveforms    
plt.clf()
fig,(ax1,ax2,ax3,ax4) = plt.subplots(4)
times=[i*1000./60. for i in range(10000)]
nmax=0
ch1_min=5000.
ch1_max=0.
ch2_min=5000.
ch2_max=0.
for (ch1,ch2,discraw,discsync) in hitData:
  n=len(ch1)-6
  if n>nmax: nmax=n
  ax1.plot(times[:n],discraw[:-6],'-',linewidth=0.5)
  ax2.plot(times[:n],discsync[:-6],'-',linewidth=0.5)
  ax3.plot(times[:n],ch1[6:],'-',linewidth=0.5)
  ax4.plot(times[:n],ch2[6:],'-',linewidth=0.5)
  ch1_min=min(ch1_min,min(ch1))
  ch2_min=min(ch2_min,min(ch2))
  ch1_max=max(ch1_max,max(ch1))
  ch2_max=max(ch2_max,max(ch2))
ax1.set(ylabel='Disc_Raw')
ax2.set(ylabel='Disc_Resync')
ax3.set(ylabel='Channel 1')
ax4.set(ylabel='Channel 2')
ax4.set(xlabel='Time (nsec)')
ax1.set_xlim(0,600)
ax2.set_xlim(0,600)
ax3.set_xlim(0,600)
ax4.set_xlim(0,600)
ch1_delta=max(1.,ch1_max-ch1_min)
ch1_ymin=ch1_min-0.2*ch1_delta
ch1_ymax=ch1_max+0.2*ch1_delta
ch2_delta=max(1.,ch2_max-ch2_min)
ch2_ymin=ch2_min-0.2*ch2_delta
ch2_ymax=ch2_max+0.2*ch2_delta
ax3.set_ylim(ch1_ymin,ch1_ymax)
ax4.set_ylim(ch2_ymin,ch2_ymax)
ax1.label_outer()
ax2.label_outer()
ax3.label_outer()
ax4.label_outer()
plt.savefig(basename+'_waveforms.pdf')

# plot average waveforms and also the individual ones
# N.B. reuse some quantities from above
plt.clf()
fig,(ax1,ax2,ax3,ax4) = plt.subplots(4)
# first compute the average waveforms
length_min = 100000
for (ch1,ch2,discraw,discsync) in hitData:
  if len(ch1)<length_min: length_min=len(ch1)
ch1sum=[0.]*length_min
ch2sum=[0.]*length_min
for (ch1,ch2,discraw,discsync) in hitData:
  for i in range(length_min):
    ch1sum[i]+=ch1[i]
    ch2sum[i]+=ch2[i]
ch1avg=[ch1sum[i]/len(hitData) for i in range(length_min)]
ch2avg=[ch2sum[i]/len(hitData) for i in range(length_min)]
limit0=[0]*length_min
limit4095=[4095]*length_min
# now plot the averages in top two panels
n=length_min-6
ax1.plot(times[:n],ch1avg[6:],'-',linewidth=0.5)
ax1.plot(times[:n],limit0[6:],'--')
ax1.plot(times[:n],limit4095[6:],'--')
ax2.plot(times[:n],ch2avg[6:],'-',linewidth=0.5)
ax2.plot(times[:n],limit0[6:],'--')
ax2.plot(times[:n],limit4095[6:],'--')
# plot the individual ones again
for (ch1,ch2,discraw,discsync) in hitData:
  n=len(ch1)-6
  ax3.plot(times[:n],ch1[6:],'-',linewidth=0.5)
  ax4.plot(times[:n],ch2[6:],'-',linewidth=0.5)
# set up labels and limits
ax1.set(ylabel='Ch1 Avg')
ax2.set(ylabel='Ch2 Avg')
ax3.set(ylabel='Ch1 Examples')
ax4.set(ylabel='Ch2 Examples')
ax4.set(xlabel='Time (nsec)')
ax1.set_xlim(0,600)
ax2.set_xlim(0,600)
ax3.set_xlim(0,600)
ax4.set_xlim(0,600)
ax1.set_ylim(ch1_ymin,ch1_ymax)
ax2.set_ylim(ch2_ymin,ch2_ymax)
ax3.set_ylim(ch1_ymin,ch1_ymax)
ax4.set_ylim(ch2_ymin,ch2_ymax)
ax1.label_outer()
ax2.label_outer()
ax3.label_outer()
ax4.label_outer()
plt.savefig(basename+'_averages.pdf')

# plot histograms of raw adc values
plt.clf()
f=plt.figure(figsize=(10.,10.5))
f.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=.3, hspace=.4)
hist_list=[h_ch1all,h_ch1ped,h_ch1max,h_ch1area]
for i in range(len(hist_list)):
    ax=f.add_subplot(3,2,i+1)
    hist_list[i].plot(ax,'b')
    hist_list[i].autoSetLimits(ax,scale='lin')
    ax.set_xlabel(hist_list[i].xlabel)
    ax.set_ylabel(hist_list[i].ylabel)
    ax.set_title(hist_list[i].title)
plt.savefig(basename+'_adc_hist.pdf')

# plot histograms in physical units
plt.clf()
f=plt.figure(figsize=(10.,10.5))
f.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=.3, hspace=.4)
hist_list=[h_ch1imax,h_ch1charge]
for i in range(len(hist_list)):
    ax=f.add_subplot(3,2,i+1)
    hist_list[i].plot(ax,'b')
    hist_list[i].autoSetLimits(ax,scale='lin')
    ax.set_xlabel(hist_list[i].xlabel)
    ax.set_ylabel(hist_list[i].ylabel)
    ax.set_title(hist_list[i].title)
plt.savefig(basename+'_pulse_hist.pdf')

# plot more histograms
plt.clf()
f=plt.figure(figsize=(10.,10.5))
f.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=.3, hspace=.4)
hist_list=[h_log10dt,h_log10dt,h_dt,h_dt]
scale_list=['lin','log','lin','log']  # which plots use lin or log scaling on y axis
for i in range(len(hist_list)):
    ax=f.add_subplot(3,2,i+1)
    hist_list[i].plot(ax,'b')
    hist_list[i].autoSetLimits(ax,scale=scale_list[i])
    ax.set_xlabel(hist_list[i].xlabel)
    ax.set_ylabel(hist_list[i].ylabel)
    ax.set_title(hist_list[i].title)
plt.savefig(basename+'_dt_hist.pdf')
