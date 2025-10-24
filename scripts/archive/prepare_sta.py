import pandas as pd
import sys
sys.path.append('/Users/gongjian/Documents/Research/MTJ/step3_COMPLOC/HypoDD-small-cluster')
from src import read_JSON
import numpy as np

parameters = read_JSON('input.json')
df = pd.read_csv(parameters['gmap'], sep='|')
stas = np.unique(df['Station'])
fid = open('input_sta.txt', 'w')
for i in range(0, len(stas)):
    staname = stas[i]
    temp_df = df[df['Station']==staname]
    temp_df = temp_df.reset_index(drop=True)
    if temp_df['Network'][0] == '7D' or temp_df['Network'][0] == 'Z5':
        continue
    fid.write('{} {} {}\n'.format(staname, temp_df['Latitude'][0], temp_df['Longitude'][0]))
fid.close()