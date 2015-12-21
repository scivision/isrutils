"""
summed measurements and plots
"""
from __future__ import division,absolute_import
from datetime import datetime
from pandas import Panel4D,DataFrame,Series
from numpy import absolute,nan,linspace,percentile
from matplotlib.pyplot import figure,draw,pause,subplots,show
from matplotlib.cm import jet
#from matplotlib.colors import LogNorm
#import matplotlib.animation as anim
#
from .plasmaline import readplasmaline
from .common import timeticks,findindex2Dsphere,timesync,projectisrhist,writeplots
from .snrpower import readpower_samples
from GeoData.plotting import plotazelscale

vidnorm = None #LogNorm()

#%% joint isr optical plot
def dojointplot(ds,spec,freq,beamazel,optical,optazel,optlla,isrlla,heightkm,utopt,utlim,makeplot,odir):
    """
    f1,a1: radar   figure,axes
    f2,a2: optical figure,axes
    """
    assert isinstance(ds,(Series,DataFrame))

#%% setup master figure
    fig,axs = subplots(2,1,figsize=(8,12))
#%% setup radar plot(s)
    a1 = axs[1]
    plotsumlongpulse(ds,a1)

    h1 = a1.axvline(nan,color='k',linestyle='--')
    t1 = a1.text(0.05,0.95,'time=',transform=a1.transAxes,va='top',ha='left')
#%% setup top optical plot
    a0 = axs[0]
    clim = compclim(optical,lower=10,upper=99.9)
    h0 = a0.imshow(optical[0,...],origin='lower',interpolation='none',cmap='gray',
                   norm=vidnorm,vmin=clim[0],vmax=clim[1])
    a0.set_axis_off()
    t0 = a0.set_title('')

#%% plot magnetic zenith beam
    azimg = optazel[:,1].reshape(optical.shape[1:])
    elimg = optazel[:,2].reshape(optical.shape[1:])

    optisrazel = projectisrhist(isrlla,beamazel,optlla,optazel,heightkm)

    br,bc = findindex2Dsphere(azimg,elimg,optisrazel['az'],optisrazel['el'])

    #hollow beam circle
#    a2.scatter(bc,br,s=500,marker='o',facecolors='none',edgecolor='red', alpha=0.5)

    #beam data, filled circle
    s0 = a0.scatter(bc,br,s=500,alpha=0.5,linewidths=1.5,
                    edgecolors=jet(linspace(ds.min(),ds.max())))

    a0.autoscale(True,tight=True)

#%% time sync
    tisr = ds.index#.to_pydatetime() #Timestamp() is fine, no need to make it datetime(). datetime64() is no good.
    Iisr,Iopt = timesync(tisr,utopt,utlim)
#%% iterate
    first = True
    for iisr,iopt in zip(Iisr,Iopt):
        ctisr = tisr[iisr]
        ctopt = datetime.utcfromtimestamp(utopt[iopt])
#%% update isr plot
        h1.set_xdata(ctisr)
        t1.set_text('isr: {}'.format(ctisr))
#%% update hist plot
        h0.set_data(optical[iopt,...])
        s0.set_array(ds[ctisr]) #FIXME not changing magnetic zenith beam color? NOTE this is isr time index
        t0.set_text('optical: {}'.format(ctopt))
#%% anim
        if 'show' in makeplot:
            if first:
                plotazelscale(optical[iopt,...],azimg,elimg)
                show()
                first=False
#
            draw(); pause(0.01)

        writeplots(fig,ctopt,odir,makeplot,ctxt='joint')
#
#    def update(t):
#        h.set_xdata(t)
#        return h,
#
#    line_ani = anim.FuncAnimation(fig=f1, func=update, frames=T.size,
#                                   interval=50, blit=False)

def compclim(imgs,lower=0.5,upper=99.9,Nsamples=10):
    """
    inputs:
    images: Nframe x ypix x xpix grayscale image stack (have not tried with 4-D color)
    lower,upper: percentage (0,100)% to clip
    Nsamples: number of frames to test across the image stack (don't use too many for memory reasons)
    """
    sampind = linspace(0,imgs.shape[0],Nsamples,endpoint=False,dtype=int)

    return percentile(imgs[sampind,...],[lower,upper])

#%% dt3
def sumlongpulse(fn,beamid,tlim,zlim):
    snrsamp,azel,lla = readpower_samples(fn,beamid,tlim,zlim)
    assert isinstance(snrsamp,DataFrame)

    return snrsamp.sum(axis=0),azel,lla

def plotsumlongpulse(dsum,ax):
    assert isinstance(dsum,Series)
    if not ax:
        fg = figure()
        ax = fg.gca()

    dsum.plot(ax=ax)
    ax.set_ylabel('summed power')
    ax.set_xlabel('time [UTC]')
    ax.set_title('long pulse summed over altitude (200..350)km')

    ax.set_yscale('log')
    ax.grid(True)

    ax.xaxis.set_major_locator(timeticks(dsum.index[-1] - dsum.index[0]))
    return ax

#%% plasma line
def sumplasmaline(fn,beamid,flim,tlim,zlim):
    spec,freq = readplasmaline(fn,beamid,tlim)
    assert isinstance(spec,Panel4D)
    assert isinstance(flim[0],float)

    z = spec.major_axis
    specsum = DataFrame(index=spec.items,columns=spec.labels)

    zind = (zlim[0] <= z) & (z <= zlim[1])

    for s in spec:
        find = (flim[0] <= absolute(freq[s]/1e6)) & (absolute(freq[s]/1e6) < flim[1])
        specsum.loc[:,s] = spec.loc[:,:,zind,find].sum(axis=3).sum(axis=2)

    return specsum

def plotsumplasmaline(plsum):
    assert isinstance(plsum,DataFrame)

    fg = figure()
    ax = fg.gca()
    plsum.plot(ax=ax)
    ax.set_ylabel('summed power')
    ax.set_xlabel('time [UTC]')
    ax.set_title('plasma line summed over altitude (200..350)km and frequency (3.5..5.5)MHz')

    ax.xaxis.set_major_locator(timeticks(plsum.columns[-1]-plsum.columns[0]))