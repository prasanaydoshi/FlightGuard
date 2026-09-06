"""Auditable BTS extraction and UTC-normalized schedule construction."""
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ZONES = {'ATL':'America/New_York','BOS':'America/New_York','ORD':'America/Chicago',
         'DEN':'America/Denver','LAX':'America/Los_Angeles','SEA':'America/Los_Angeles'}
SPOKES = sorted(set(ZONES) - {'ATL'})
FIELDS = ['FlightDate','Reporting_Airline','Flight_Number_Reporting_Airline','Origin','Dest',
          'CRSDepTime','CRSArrTime','CRSElapsedTime','DepDelay','ArrDelay','Cancelled','Diverted']
URL = 'https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_{}.zip'

def clock(value):
    n = int(value)
    if n == 2400:
        return 1440
    if n < 0 or n // 100 > 23 or n % 100 > 59:
        raise ValueError('Invalid HHMM')
    return n // 100 * 60 + n % 100

def local_utc(day, hhmm, zone):
    """Reject nonexistent and ambiguous local times rather than guessing a DST fold."""
    naive = datetime.fromisoformat(day) + timedelta(minutes=clock(hhmm))
    z = ZoneInfo(zone)
    choices = set()
    for fold in (0,1):
        aware = naive.replace(tzinfo=z, fold=fold).astimezone(timezone.utc)
        if aware.astimezone(z).replace(tzinfo=None) == naive:
            choices.add(aware)
    if len(choices) != 1:
        raise ValueError('Ambiguous or nonexistent local departure')
    return choices.pop()

def normalize(row):
    dep = local_utc(row['FlightDate'], row['CRSDepTime'], ZONES[row['Origin']])
    elapsed = float(row['CRSElapsedTime'])
    if not 20 <= elapsed <= 720:
        raise ValueError('Invalid scheduled elapsed time')
    arr = dep + timedelta(minutes=elapsed)
    wall = arr.astimezone(ZoneInfo(ZONES[row['Dest']]))
    if wall.hour*60 + wall.minute != clock(row['CRSArrTime']) % 1440:
        raise ValueError('Schedule clock/elapsed/timezone mismatch')
    cancelled = int(float(row['Cancelled']))
    diverted = int(float(row['Diverted']))
    if cancelled not in (0,1) or diverted not in (0,1):
        raise ValueError('Invalid outcome flag')
    def delay(key):
        return None if row[key] == '' else float(row[key])
    ad, dd = delay('ArrDelay'), delay('DepDelay')
    if not (cancelled or diverted) and (ad is None or dd is None):
        raise ValueError('Missing completed-flight delays')
    return {'id':'/'.join(row[k] for k in ['FlightDate','Reporting_Airline','Flight_Number_Reporting_Airline','Origin','Dest']),
            'date':row['FlightDate'],'origin':row['Origin'],'dest':row['Dest'],
            'number':row['Flight_Number_Reporting_Airline'], 'dep':dep.timestamp()/60,
            'arr':arr.timestamp()/60,'cancelled':cancelled,'diverted':diverted,
            'dep_delay':dd,'arr_delay':ad}

def ingest():
    raw = ROOT/'data/raw';raw.mkdir(parents=True,exist_ok=True)
    manifest = {'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
                'source':'US DOT Bureau of Transportation Statistics, Reporting Carrier On-Time Performance',
                'selection':{'carrier':'DL','hub':'ATL','spokes':SPOKES,'months':[1,2,3],'year':2025},
                'archives':[], 'excluded':{},'fields':FIELDS}
    selected=[];seen=set();counts=Counter()
    for month in (1,2,3):
        p=raw/f'2025_{month}.zip'
        if not p.exists():
            with urllib.request.urlopen(URL.format(month),timeout=120) as response:
                p.write_bytes(response.read())
        meta={'url':URL.format(month),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'source_rows':0,'selected_rows':0}
        with zipfile.ZipFile(p) as z:
            name=next(n for n in z.namelist() if n.endswith('.csv'))
            for row in csv.DictReader(io.TextIOWrapper(z.open(name),encoding='utf-8-sig')):
                meta['source_rows']+=1
                if row['Reporting_Airline']!='DL' or not ((row['Origin']=='ATL' and row['Dest'] in SPOKES) or (row['Dest']=='ATL' and row['Origin'] in SPOKES)):
                    continue
                try:
                    f=normalize(row)
                except (ValueError,KeyError) as e:
                    counts[str(e)]+=1;continue
                if f['id'] in seen:
                    counts['duplicate flight identity']+=1;continue
                seen.add(f['id']);selected.append({k:row[k] for k in FIELDS});meta['selected_rows']+=1
        manifest['archives'].append(meta)
    selected.sort(key=lambda r:tuple(r[k] for k in ['FlightDate','Origin','CRSDepTime','Dest','Flight_Number_Reporting_Airline']))
    out=ROOT/'data/flights.csv'
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(selected)
    manifest.update(excluded=dict(counts),selected_rows=len(selected),clean_csv_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
    (ROOT/'data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

def load_flights():
    with (ROOT/'data/flights.csv').open() as f:
        return [normalize(r) for r in csv.DictReader(f)]

if __name__ == '__main__':
    ingest()
