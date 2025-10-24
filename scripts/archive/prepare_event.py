import sys
sys.path.append('/Users/gongjian/Documents/Research/MTJ/step4_picks_check/WaveView/src')
from mytrace import events
from func import read_JSON
import datetime
import pandas as pd
import numpy as np
import pdb
parameters = read_JSON('input.json')
time0 = datetime.datetime.strptime(parameters['time0'], '%Y-%m-%d')
evobj = events(catalog_type=parameters['catalog_type'], 
                time0=time0,
                filename1=parameters['new_location'])
#### subset events
mask = np.ones((len(evobj.catalog_evid), )).astype(bool)
good_events = []
for i in range(1, 5):
    df1 = pd.read_csv('../HypoDD-Y{}/input_event.dat'.format(i), sep='\s+', header=None, usecols=[9,10], names=['e1', 'e2'])
    df2 = pd.read_csv('../HypoDD-Y{}/hypoDD.reloc'.format(i), sep='\s+', header=None, usecols=[0], names=['e3'])
    for j in range(0, df2.shape[0]):
        index = np.where(df1['e1']==df2['e3'][j])[0][0]
        good_events.append(df1['e2'][index])
for i in range(0, len(evobj.catalog_evid)):
    if evobj.catalog_evid[i] in good_events:
        continue
    else:
        mask[i] = False

#### event info     
elat, elon, edep = evobj.catalog_elat[mask], evobj.catalog_elon[mask], evobj.catalog_edep[mask]
evid = evobj.catalog_evid[mask]
etime = evobj.catalog_etime[mask]
nevent = len(evid)

#### picks
pick_df = pd.read_csv(parameters['new_arrival'])
pick_df['datetime'] =  pd.to_datetime(pick_df['time']) 


fid = open('input_event.dat', 'w')
for i in range(0, nevent):
    date = '{:04d}{:02d}{:02d}'.format(etime[i].year, etime[i].month, etime[i].day)
    time = '{}{:02d}{:02d}{:02d}'.format(etime[i].hour, etime[i].minute, etime[i].second, int(etime[i].microsecond/1e4))
    fid.write('{}  {:>8s}  {:>8.4f}  {:>9.4f}  {:>9.3f} {:>4.1f} {:>7.2f} {:>7.2f} {:>6.2f}  {:>9d} {:d}\n'.format(\
        date, time, elat[i], elon[i], edep[i], 0.0, 0.0, 0.0, 0.0, i, evid[i]))
fid.close()


fid = open('input_phase.pha', 'w')
for i in range(0, nevent):
    if np.mod(i, 5000) == 0:
        print('{}/{}'.format(i, nevent))   
    # 1997 6 13 13 44 37.33 49.2424 -123.6192 3.42 3.43 0.0 0.0 0.03 1
    #, YR, MO, DY, HR, MN, SC, LAT, LON, DEP, MAG, EH, EZ, RMS, ID
    fid.write('# {} {} {} {} {} {:.2f} {:.4f} {:.4f} {:.3f} {:.1f} {:.2f} {:.2f} {:.2f} {:d}\n'.format(\
        etime[i].year, etime[i].month, etime[i].day, etime[i].hour, etime[i].minute,\
        etime[i].second+etime[i].microsecond/1e6, \
        elat[i], elon[i], edep[i], 0.0, 0.0, 0.0, 0.0, i))

    temp_df = pick_df[pick_df['event']==evid[i]]
    temp_df = temp_df.reset_index(drop=True)
    for j in range(0, temp_df.shape[0]):
        dt = (temp_df['datetime'][j] -  etime[i]).total_seconds()
        fid.write('{:<5s}      {:>6.3f}  {:>6.3f}   {}\n'.format(\
            temp_df['station'][j], dt, 1.0, temp_df['phase'][j]))
fid.close()
