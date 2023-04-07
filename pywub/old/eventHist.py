#
# eventHist.py
#
# utility module for histograms that can be filled one event at a time
#
import numpy, math

class eventHist:
    """Utility module for histograms that can be filled one event at a time"""
    
    def __init__(self, xmin=0., xmax=1., nbins=100, title="", xlabel="", ylabel=""):
        """initialization of range and bins"""
        if xmax<=xmin: raise Exception("inverted or zero range")
        if nbins<=0: raise Exception("invalid bin count")
        self.xmin=float(xmin)
        self.xmax=float(xmax)
        self.nbins=nbins
        self.counts=numpy.zeros(nbins)
        self.dx=float(xmax-xmin)/nbins
        self.underflow=0.
        self.overflow=0.
        self.title=title
        self.xlabel=xlabel
        self.ylabel=ylabel

    def clear(self):
        """zero the counts"""
        self.counts.fill(0.)
        self.underflow=0.
        self.overflow=0.
        
    def increment(self, x):
        """increment bin containing x by 1"""
        i=int(math.floor((x-self.xmin)/self.dx))
        if i<0:
            self.underflow+=1.
        elif i>=self.nbins:
            self.overflow+=1.
        else:
            self.counts[i]+=1.
            
    def incrementWeighted(self, x, weight):
        """increment bin containing x by weight"""
        i=int(math.floor((x-self.xmin)/self.dx))
        if i<0:
            self.underflow+=weight
        elif i>=self.nbins:
            self.overflow+=weight
        else:
            self.counts[i]+=weight
    
    def add(self, h):
        """add binwise contents of another histogram h to this one"""
        if not h.nbins==self.nbins: raise Exception("binning doesn't match")
        if not h.xmin==self.xmin: raise Exception("binning doesn't match")
        self.counts+=h.counts
        self.underflow+=h.underflow
        self.overflow+=h.overflow
    
    def addScaled(self, h, f):
        """add contents of another histogram h, after multiplying with f"""
        if not h.nbins==self.nbins: raise Exception("binning doesn't match")
        if not h.xmin==self.xmin: raise Exception("binning doesn't match")
        self.counts+=h.counts*f
        self.underflow+=h.underflow*f
        self.overflow+=h.overflow*f
    
    def getCounts(self, i):
        """get contents of specified bin (numbered from 0 to nbins-1)"""
        return self.counts[i]
    
    def getUnderflow(self):
        """get contents of underflow bin"""
        return self.underflow
        
    def getOverflow(self):
        """get contents of overflow bin"""
        return self.overflow
        
    def getSumAll(self):
        """get sum of all counts including underflow and overflow"""
        return sum(self.counts)+self.underflow+self.overflow
    
    def getSumBelow(self, x):
        """get sum below given x, including underflow"""
        if x<self.xmin or x>self.xmax: raise Exception("out of range of bins")
        f=(x-self.xmin)/self.dx    # translate x into bin number (floating pt)
        i=int(math.floor(f))       # determine lower bounding integer
        if i>=self.nbins: i=self.nbins-1  # (possible rounding error issues)
        totalCounts=sum(self.counts[0:i])
        totalCounts+=(f-i)*self.counts[i]
        totalCounts+=self.underflow
        return totalCounts
    
    def getSumAbove(self, x):
        """get sum above given x, including overflow"""
        if x<self.xmin or x>self.xmax: raise Exception("out of range of bins")
        f=(x-self.xmin)/self.dx    # translate x into bin number (floating pt)
        i=int(math.floor(f))       # determine lower bounding integer
        if i>=self.nbins: i=self.nbins-1  # (possible rounding error issues)
        totalCounts=sum(self.counts[i:])
        totalCounts-=(f-i)*self.counts[i]
        totalCounts+=self.overflow
        return totalCounts
    
    def getSumInRange(self, x1, x2):
        """get sum of counts in range, allowing fractional bins as needed"""
        if x1<self.xmin or x2>self.xmax: raise Exception("out of range of bins")
        if x1>x2: raise Exception("inverted range specification")
        f1=(x1-self.xmin)/self.dx    # translate x1 and x2 into bin number, 
        f2=(x2-self.xmin)/self.dx    #    including both integer and frac parts
        i1=int(math.floor(f1))       # determine the lower bounding integer
        i2=int(math.floor(f2))       #
        if i2>=self.nbins: i2=self.nbins-1    # (possible rounding error issues)
        totalCounts=sum(self.counts[i1:i2])
        totalCounts-=(f1-i1)*self.counts[i1]  # correct for fractional bins
        totalCounts+=(f2-i2)*self.counts[i2]  #   at end of range
        return totalCounts

    def getMaximum(self):
        """return index and y value for maximum bin"""
        i=numpy.argmax(self.counts)
        return i,self.counts[i]

    def getBinValue(self, i):
        """return contents of specified bin number"""
        if i<0 or i>=self.nbins: return 0.
        return self.counts[i]
        
    def getEmptyCopy(self):
        """return a copy of this histogram with zero contents"""
        return eventHist(self.xmin,self.xmax,self.nbins)
    
    def getCopy(self):
        """return a copy of this histogram with same contents"""
        hnew=eventHist(self.xmin,self.xmax,self.nbins)
        hnew.counts=self.counts
        hnew.overflow=self.overflow
        hnew.underflow=self.underflow
        return hnew

    def getScaledCopy(self, f):
        """return a copy of this histogram with contents multiplied by f"""
        hnew=eventHist(self.xmin,self.xmax,self.nbins)
        hnew.counts=self.counts*f
        hnew.overflow=self.overflow*f
        hnew.underflow=self.underflow*f
        return hnew

    def getNormalizedCopy(self, handleDivideByZero=False):
        """return a copy of histogram normalized to 1 (incl. over/underflow)"""
        hnew=eventHist(self.xmin,self.xmax,self.nbins)
        sumAll=sum(self.counts)+self.underflow+self.overflow
        if sumAll!=0:
            f=1./sumAll
        else:
            if handleDivideByZero: f=0.
            else: raise Exception("Cannot normalize empty histogram")
        hnew.counts=self.counts*f
        hnew.overflow=self.overflow*f
        hnew.underflow=self.underflow*f
        return hnew

    def dump(self, stream):
        """print contents"""
        print >>stream, "underflow\t%f"%(self.underflow)
        print >>stream, "overflow\t%f"%(self.overflow)
        for i in range(self.nbins):
            x=self.xmin+(i+0.5)*self.dx
            print >>stream, "%f\t%f"%(x,self.counts[i])
            
    def plot(self, ax, *args, **kwargs):
        """plot into given instance of matplotlib.axes.AxesSubplot"""
        # create list of x values needed to make histogram that actually
        #   shows start and end bins in standard fashion at the right place
        xplot=[self.xmin+(i+1)*self.dx for i in range(-1,self.nbins)]
        tinyvalue=1e-50*max(abs(self.counts))
        yplot=[tinyvalue,]+[(y if y!=0 else tinyvalue) for y in self.counts]
        ax.plot(xplot,yplot,*args,drawstyle="steps-pre",**kwargs)
        
    def autoSetLimits(self, ax, scale="linear"):
        """set reasonable limits for plotting, also linear/log/symlog scale"""
        maxcount=max(self.counts)
        if scale=="linear" or scale=="lin":
            ax.set_yscale("linear")
            mincount=min(self.counts)
            if mincount>=0.: 
                ymin, ymax = 0., 1.2*maxcount
                if ymax==0.: ymax=1.
            else: 
                ymin = mincount-.2*(maxcount-mincount)
                ymax = maxcount+.2*(maxcount-mincount)
                if ymax==ymin:
                    ymax+=1
                    ymin-=1
            ax.axis([self.xmin,self.xmax,ymin,ymax])
        elif scale=="log":
            ax.set_yscale("log")
            # set of values seen in counts array, look for nonzero ones
            s=sorted(list(set(numpy.maximum(self.counts,0.))))
            maxcount=s[-1]
            if len(s)>10:  # maybe skip smallest nonzero value as "minimum"
                if s[0]==0: mincount,mincount2=s[1],s[2] 
                else: mincount,mincount2=s[0],s[1]
                if mincount<maxcount/1e4 and mincount<mincount2/10:
                    mincount=mincount2  # skip smallest nonzero val, outlier
            elif len(s)>1:  # take smallest nonzero value as "minimum"
                if s[0]==0: mincount=s[1]
                else: mincount=s[0]
            else:
                if s[0]==0: mincount=0.1
                else: mincount=s[1]
            margin=max([(maxcount/mincount)**0.2,1.5])
            ymin, ymax = mincount/margin, maxcount*margin
            ax.axis([self.xmin, self.xmax, ymin, ymax])
        elif scale=="symlog":
            ax.set_yscale("symlog")
            mincount=min(self.counts)
            if mincount>=0.: # min, max both >=0
                ymin, ymax = 0., (maxcount+.1)**1.2
                if ymax==0.: ymax=1.
            elif maxcount>0.: # min<0, max>0
                ymin = -((-mincount+.1)**1.2)
                ymax = (maxcount+.1)**1.2
            else: # min<0, max<=0
                ymin, ymax = -((-mincount+.1)**1.2), 0.
            ax.axis([self.xmin,self.xmax,ymin,ymax])
        else:
            raise Exception("invalid scale type, need linear/log/symlog")
