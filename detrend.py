from numpy import *
import glob
import pyfits
import matplotlib.pylab as plt
import atpy
import sys
from scipy import weave
from scipy.weave import converters
import os
from numpy.polynomial import Legendre

from keptoy import * 

# Load up multiquarter data.

cad = 30./60./24.
dmi = 1.    # remove strips of data that are less than 1 day long.
gmi = 1/24. # Let's not worry about gaps that are 1 hour long
nq = 8

# 8669806
def mqload(keplerid):
    g = glob.glob(os.environ['HOME']+'/Marcy/Kepler/kepdat/archive/data3/privkep/EX/Q*/*%09i*.fits' % keplerid)
    tset = atpy.TableSet()
    
    for f in g:
        hdu = pyfits.open(f)
        t = atpy.Table(f,type='fits')
        t.table_name = 'Q%i' % hdu[0].header['QUARTER']
        tset.append(t)

    return tset 

def tf(tset):
    time,flux = ma.masked_array([]),ma.masked_array([])

    for i in range(nq):
        tq = ma.masked_array( tset[i].TIME )
        fq = ma.masked_array( tset[i].SAP_FLUX )

        time = ma.concatenate((time,tq))
        flux = ma.concatenate((flux,fq))

    return time,flux

def nQ(tset):    
    ntab = 0
    for t in tset:
        ntab +=1

    return ntab

def gaps(tset):
    """
    This function identifies gaps in the data signified either by:
    - nan values for time
    - inter quarter separtions

    returns two arrays with the start and end times of each gap.
    """
    g0,g1 = array([]),array([])


    ntab = nQ(tset)

    for i in range(ntab):
        tq = ma.masked_array( tset[i].TIME )
        fq = ma.masked_array( tset[i].SAP_FLUX )
        tq = ma.masked_invalid( tq ) 
        sl = ma.notmasked_contiguous(tq)

        for s in sl:
            g0 = append(g0, tq[s.stop] )
            g1 = append(g1, tq[s.start] )
    # Merge gaps that are not separated by very much data.

    id = where(g0-g1 > dmi)[0]
    g0,g1 = g0[id],g1[id]

    # Since the earliest gap marker, is an end, our idicies are off by one
    g0,g1 = g0[:-1],g1[1:]

    # Ignore gaps that are very short (several cadences).
    id = where(g1-g0 > gmi)[0]   
    g0,g1 = g0[id],g1[id]
    return g0,g1



def overlap(t0,t1,g0,g1):
    """
    Given a list of prospective transit times, we can see whether they
    overlap with the gaps.  If they do, we reject that point.  

    In the case of 3 or 4 gaps we would want to see every single one.
    If there were more transits ~10 we could get away with missing a few.
    """

    fid = open('ccode/tgap.c')
    code = fid.read()
    fid.close()

    nt = len(t0)
    ng = len(g0)

    ov = weave.inline(code,['t0','t1','g0','g1','nt','ng'],
                 type_converters=converters.blitz)
    return ov

def igeg(ig1,P,nt,tdur):
    """
    Return arrays specifying ingress and egress times for a specified
    epoch, period, number of transits, and transit duration.
    """

    ig = ig1 + arange(nt)*P
    eg = ig + tdur
    return ig,eg

def complete():
    tma  = max(time)
    tmi  = min(time)
    tbase = tma - tmi
    
    # This is the maximum period we could have and still possibly see
    # three transits

    Pma  = tbase / 2.  
    nP = 500.
    Parr = logspace( log10(100),log10(Pma),nP )     
    eff = zeros(nP)

    for i in range(nP):
        P = Parr[i]
        tdur = a2tdur(P2a(P))
        nph = P / tdur
        ig1arr = tmi + linspace(0,P,nph)

        # The maximum number of transits that can occur with a specified period
        nt = ceil( tbase / P )
        ocount = 0 

        for ig1 in ig1arr:
            ig,eg  = igeg(ig1,P,nt,tdur)
            ocount += overlap(ig,eg,g0,g1)
            
        eff[i] = 1 - ocount/nph

    return Parr,eff


def plotov(g0,g1,ig,eg):
    fig = plt.gcf()
    fig.clf()
    ax = fig.add_subplot(111)
    ax.hlines(ones(len(g0)),g0,g1,'r',lw=10)
    ax.hlines(ones(len(ig)),ig,eg,'g',lw=10)


def plotcomp():
    """

    """
    fig = plt.gcf()
    fig.clf()
    ax = fig.add_subplot(111)
    ax.plot(time,flux)



def dtrunmed(timel,fluxl):
    """
        
    """
    fluxl,timel = stitch(fluxl,timel)
    ftot,ttot = array([]),array([])

    nseg = len(timel)
    assert len(timel) == len(fluxl)

    for i in range(nseg):
        ftot = append(ftot,fluxl[i] )
        ttot = append(ttot,timel[i] )

    tdt,fdt,fint = array([]),array([]),array([])

    for i in range(nseg):
        time,flux = timel[i],fluxl[i]
        fl,tl = splitq(flux,time)
        nseg = len(fl)

        for j in range(nseg):       
            x,y = runmed(fl[j],tl[j])
            yint = interp1d(x,y,bounds_error=False)
            
            tdt = append(tdt,time)
            fdt = append(fdt,flux-yint(time))
            fint = append(fint,yint(time) )

    tdt = ma.masked_invalid(tdt).astype(float32)
    fdt = ma.masked_invalid(fdt).astype(float32)
    fint = ma.masked_invalid(fint).astype(float32)


    mask = tdt.mask | fdt.mask
    tdt.mask = mask
    fdt.mask = mask
    fint.mask = mask


    tdt = tdt.compressed()
    fdt = fdt.compressed()
    fint = fint.compressed()

    return tdt,fdt,fint


def stitch(fl,tl):
    """
    Stitch together the boundaries of the quarters.
    """
    
    swd =  0.5 # How long a timeseries on either end to use days 
    nQ = len(fl)

    for i in range(nQ-1):
        fleft,tleft = fl[i],tl[i]
        fright,tright = fl[i+1],tl[i+1]

        lid = where(tleft > tleft[-1] - swd)[0]
        rid = where(tright < tright[0] + swd)[0]

        medleft = median(fleft[lid])
        medright = median(fright[rid])
        
        factor = medleft / medright
        fright *= factor

    return fl,tl

def runmed(flux,time):
    mbpts = isnan(flux) 

    flux = ma.masked_array( flux)
    time = ma.masked_array( time,mask=isnan(flux) )
    
    twid = 2
    cad = 30./60./24.
    npts = len(time)

    x = []
    y = []

    tmid = time.min() + twid / 2.
    tmidlast = time.max() - twid / 2.

    while tmid < tmidlast:
        tm = ma.getmask( ma.masked_outside(time,tmid-twid/2.,tmid + twid/2.) )
        reg = ma.masked_array(flux,mask=ma.mask_or(mbpts,tm) )

        x.append( tmid )
        y.append( ma.median( reg ) )
        tmid += cad

    x = array(x)
    y = array(y)
    
    return x,y


# TODO: Use Masked arrays so that tout and fout are the same shape as the input tables
def splitq(flux,time):
    # split quarters if the distance between good points is too big.
    mgap = 0.5 * 48

    mbpts = isnan(flux) 
    bflux = ma.masked_array(flux,mask=~mbpts)
    sl = array( ma.notmasked_contiguous(bflux) )
    if len(sl) == 0:
        return [flux],[time]

    gapl = array([s.stop - s.start for s in sl])

    fl = []
    tl = []

    left = 0

    splitid = where( gapl > mgap )[0]
    nseg = len(splitid) + 1
    if nseg > 1:
        for id in splitid:
            right = sl[id].start - 1
            fl.append(flux[left:right])
            tl.append(time[left:right])

            # increment left edge
            left = sl[id].stop + 1

        fl.append(flux[left:])
        tl.append(time[left:])

        return fl,tl
    else:
        return [flux],[time]

from scipy.interpolate import interp1d

def qdt(time,flux):
    """
    Detrend a Quarter 
    """
    fl,tl = splitq(flux,time)
    nseg = len(fl)

    fout,tout = array([]),array([])

    for j in range(nseg):        
        x,y = runmed(fl[j],tl[j])
        yint = interp1d(x,y,bounds_error=False)
        
        fout = append(fout, fl[j] - yint( tl[j] ) )
        tout = append(tout, tl[j])
    return tout,fout 


# Construct the design matrix

def designL(x,order=3,domain=[-1,1]):
    """
    
    """
    nData  = len(x)
    nParam = order + 1
    X = zeros((nData,nParam))

    for i in range(nParam):
        coeff = zeros(nParam)
        coeff[i] = 1
        L = Legendre(coeff,domain=domain)
        X[::,i] = L(x)
    return X



def designLS(t,f,p,order=3,domain=[-1,1]):
    """
    A lightcurve is fit to the following function:
    f = [b] * Legendre( [coeff] )(t)
    
    Since the parameters are not linear, we'll linearize the problem.

    df/d[p] * delta [p] =  y_data - y_0

    We use linear least squares fitting to solve for the differences.  This
    function computes the design matrix df/d[p].

    Inputs:

    t - Times where these points were taken.
    f - Array of fluxes shape = (nLightCurves, nDataPoints)   
    p - Array of parameters.  Must be in the following order:
        [ b_0 ... b_{nLC - 1} , a_1 ... a_{order} ]

        bs are the multiplicative weights given to each LC
        as are the Legendre coeff we do not fit for the constant term.
    """
    
    nLC   = f.shape[0]
    nData = f.shape[1]
    # Require that arrays are 1-D
    p = p.reshape(p.size)

    nb = nLC - 1
    assert len(p) == order + nb

    # nLC*nData by nLC+order+1
    X = zeros( (nb*nData,nb+order) )

    a = p[nb:]
    b = p[:nb]
    coef = hstack( (0,a) )

    shapeFunc = Legendre(coef,domain=domain)(t)
    for iLC in range(nb):
        sL = iLC*nData     # Low slice.  Index of the first row of D-matrix.
        sH = (iLC+1)*nData # High slice. Index of the last row of D-matrix + 1.

        X[sL:sH,iLC] =  shapeFunc

        for j in range(order):
            iOrder = j+1
            dCol = nb+j
            bcoef = zeros(order+1) # Coefficient for the Legendre basis functions

            bcoef[iOrder] = coef[iOrder]
            print bcoef

            X[sL:sH,dCol] = b[iLC]*Legendre(bcoef,domain=domain)(t)
        
    return X

    
def fModel(p,t,f,domain=[-1,1],order=3):
    """
    p - Array of parameters.  Must be in the following order:
    """

    # Require that arrays are 1-D
    p = p.reshape(p.size)
    nLC   = f.shape[0]
    nData = f.shape[1]

    nb = nLC - 1
    assert len(p) == order  + nb

    b = p[:nb]
    a = p[nb:]
    coef = hstack( (0,a) )

    fM = zeros(f.shape)
    fM[0,::] = Legendre(coef,domain=domain)(t)
    for i in range(nb):
        iLC = i + 1
        fM[iLC,::] = b[i]*Legendre(coef,domain=domain)(t)
        
    return fM






