"""Schedule-only candidate generation and explicit synthetic labels."""
import math
from bisect import bisect_left,bisect_right
from collections import defaultdict
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from .data import SPOKES,ZONES

TRANSFER = 30
DOOR = 15

def outcome(a,b,transfer=TRANSFER,door=DOOR):
    if not 0 <= transfer <= 180 or not 0 <= door <= 60:
        raise ValueError('Invalid transfer or boarding cutoff')
    if a['cancelled'] or b['cancelled']:
        return 1,1,'cancellation'
    if a['diverted'] or b['diverted']:
        return 1,1,'diversion'
    if a['arr_delay'] is None or b['dep_delay'] is None or b['arr_delay'] is None:
        raise ValueError('Missing outcome')
    missed = a['arr'] + a['arr_delay'] + transfer > b['dep'] + b['dep_delay'] - door
    disrupted = missed or b['arr_delay'] > 60
    return int(missed),int(disrupted),'transfer shortfall' if missed else ('arrival >60m late' if disrupted else 'completed within threshold')

FEATURE_NAMES = ['layover / 60','inverse layover','departure hour sin','departure hour cos','weekend'] + ['origin '+x for x in SPOKES] + ['destination '+x for x in SPOKES]
def features(r):
    # Strict whitelist: NEVER access delays, outcomes or actual timestamps here.
    h = r['hour'];lay=r['layover']
    if not 45<=lay<=240 or not 0<=h<24 or r['weekday'] not in range(7) or r['origin'] not in SPOKES or r['dest'] not in SPOKES or r['origin']==r['dest']:
        raise ValueError('Outside model scope')
    return [lay/60,60/lay,math.sin(2*math.pi*h/24),math.cos(2*math.pi*h/24),int(r['weekday']>=5)] + [int(r['origin']==x) for x in SPOKES] + [int(r['dest']==x) for x in SPOKES]

def connections(flights):
    outbound=defaultdict(list)
    for f in flights:
        if f['origin']=='ATL':outbound[f['dest']].append(f)
    for arr in outbound.values():arr.sort(key=lambda x:(x['dep'],x['id']))
    times={k:[f['dep'] for f in arr] for k,arr in outbound.items()}
    rows=[]
    for a in sorted(flights,key=lambda x:(x['dep'],x['id'])):
        if a['dest']!='ATL':continue
        day=datetime.fromtimestamp(a['dep']*60,timezone.utc).astimezone(ZoneInfo(ZONES[a['origin']]))
        for dest,arr in sorted(outbound.items()):
            if dest==a['origin']:continue
            lo=bisect_left(times[dest],a['arr']+45);hi=bisect_right(times[dest],a['arr']+240)
            # Entirely schedule-based deterministic sampling: earliest/latest available onward flight.
            chosen=sorted(set([lo,hi-1])) if hi>lo else []
            for j in chosen:
                b=arr[j];fail,disruption,reason=outcome(a,b)
                local=datetime.fromtimestamp(b['dep']*60,timezone.utc).astimezone(ZoneInfo('America/New_York'))
                rows.append({'id':a['id']+'>'+b['id'],'group':a['id']+'>'+dest,'date':a['date'],
                  'origin':a['origin'],'dest':dest,'inbound':'DL'+a['number'],'outbound':'DL'+b['number'],
                  'departure_utc':datetime.fromtimestamp(a['dep']*60,timezone.utc).isoformat(),
                  'hub_arrival_utc':datetime.fromtimestamp(a['arr']*60,timezone.utc).isoformat(),
                  'hub_departure_utc':datetime.fromtimestamp(b['dep']*60,timezone.utc).isoformat(),
                  'arrival_utc':datetime.fromtimestamp(b['arr']*60,timezone.utc).isoformat(),
                  'layover':b['dep']-a['arr'],'hour':local.hour+local.minute/60,'weekday':day.weekday(),
                  'duration':b['arr']-a['dep'],'failure':fail,'disruption':disruption,'reason':reason,
                  'inbound_arr_delay':a['arr_delay'],'outbound_dep_delay':b['dep_delay'],'outbound_arr_delay':b['arr_delay']})
    return rows

def split(r):
    date=r['date']
    # Two-day leading embargo prevents any single flight appearing in adjacent partitions.
    if '2025-01-01'<=date<='2025-01-31':return 'train'
    if '2025-02-03'<=date<='2025-02-28':return 'calibration'
    if '2025-03-03'<=date<='2025-03-31':return 'test'
    return 'embargo'

def sigmoid(v):
    return 1/(1+math.exp(-max(-700,min(700,v))))

def predict(r,model):
    z=model['intercept']+sum(a*b for a,b in zip(features(r),model['coef']))
    return sigmoid(model['cal_intercept']+model['cal_coef']*z)
