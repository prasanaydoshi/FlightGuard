import copy
import hashlib
import json
from datetime import datetime,timedelta,timezone
import math
import pytest
from flightguard.data import ROOT,clock,local_utc,normalize,load_flights
from flightguard.engine import connections,features,outcome,predict,split
from flightguard.train import metrics

def record(**overrides):
    row={'FlightDate':'2025-01-01','Reporting_Airline':'DL','Flight_Number_Reporting_Airline':'1',
         'Origin':'LAX','Dest':'ATL','CRSDepTime':'2300','CRSArrTime':'0630','CRSElapsedTime':'270',
         'DepDelay':'0','ArrDelay':'0','Cancelled':'0','Diverted':'0'}
    row.update(overrides);return row

def test_clock():
    assert clock('2400')==1440
    assert clock('0030')==30
    for v in ['1260','2500','-1']:
        with pytest.raises(ValueError):clock(v)

def test_overnight_date_and_timezone():
    f=normalize(record())
    assert datetime.fromtimestamp(f['arr']*60,timezone.utc).isoformat()=='2025-01-02T11:30:00+00:00'
    assert f['arr']-f['dep']==270

def test_dst_rejects_gaps_and_folds():
    for d,t in [('2025-03-09','0230'),('2025-11-02','0130')]:
        with pytest.raises(ValueError):local_utc(d,t,'America/New_York')
    assert local_utc('2025-03-09','0330','America/New_York').hour==7

def test_2400_rollover():
    assert local_utc('2025-01-01','2400','America/New_York')==datetime(2025,1,2,5,tzinfo=timezone.utc)

def test_inconsistent_schedule_rejected():
    with pytest.raises(ValueError):normalize(record(CRSArrTime='0730'))
    with pytest.raises(ValueError):normalize(record(CRSElapsedTime='-1'))

def test_cancelled_missing_times_preserved():
    assert normalize(record(Cancelled='1',ArrDelay='',DepDelay=''))['cancelled']==1
    with pytest.raises(ValueError):normalize(record(ArrDelay=''))

def test_outcome_boundaries_cancellation_diversion():
    a=normalize(record());b=copy.deepcopy(a);b['dep']=a['arr']+45
    assert outcome(a,b)==(0,0,'completed within threshold')
    a['arr_delay']=.01;assert outcome(a,b)[0]==1
    b['dep_delay']=1;assert outcome(a,b)[0]==0
    b['cancelled']=1;assert outcome(a,b)[2]=='cancellation'
    b['cancelled']=0;b['diverted']=1;assert outcome(a,b)[2]=='diversion'
    with pytest.raises(ValueError):outcome(a,b,transfer=-1)

def test_disruption_threshold():
    a=normalize(record());b=copy.deepcopy(a);b['dep']=a['arr']+120
    b['arr_delay']=60;assert outcome(a,b)[1]==0
    b['arr_delay']=61;assert outcome(a,b)[1]==1

@pytest.fixture(scope='module')
def rows():return connections(load_flights())

def test_real_source_hash_and_counts():
    m=json.loads((ROOT/'data/manifest.json').read_text())
    assert hashlib.sha256((ROOT/'data/flights.csv').read_bytes()).hexdigest()==m['clean_csv_sha256']
    assert len(load_flights())==m['selected_rows']==6601
    assert sum(a['source_rows'] for a in m['archives'])==1645503

def test_candidate_integrity(rows):
    assert len(rows)==len(set(r['id'] for r in rows))
    for r in rows:
        assert r['origin']!=r['dest']
        assert 45<=r['layover']<=240
        assert datetime.fromisoformat(r['arrival_utc'])>datetime.fromisoformat(r['departure_utc'])

def test_temporal_partitions_have_no_shared_flights(rows):
    legs={s:{leg for r in rows if split(r)==s for leg in r['id'].split('>')} for s in ['train','calibration','test']}
    assert not legs['train']&legs['calibration']
    assert not legs['calibration']&legs['test']
    assert not legs['train']&legs['test']
    assert split({'date':'2025-02-01'})=='embargo'
    assert split({'date':'2025-03-02'})=='embargo'
    for s,boundary in [('train','2025-02-03T00:00:00+00:00'),('calibration','2025-03-03T00:00:00+00:00')]:
        for r in rows:
            if split(r)==s and r['outbound_arr_delay'] is not None:
                assert datetime.fromisoformat(r['arrival_utc'])+timedelta(minutes=r['outbound_arr_delay'])<datetime.fromisoformat(boundary)

def test_no_outcome_features(rows):
    r=rows[0];changed={**r,'failure':999,'disruption':999,'inbound_arr_delay':999999,'outbound_dep_delay':-999,'outbound_arr_delay':999,'reason':'poison'}
    assert features(r)==features(changed)
    minimal={k:r[k] for k in ['layover','hour','weekday','origin','dest']}
    assert features(r)==features(minimal)

def test_schedule_sampling_not_outcome_selected():
    flights=load_flights()[:500];altered=copy.deepcopy(flights)
    for f in altered:f['cancelled']=1;f['diverted']=1
    assert [r['id'] for r in connections(flights)]==[r['id'] for r in connections(altered)]

def test_prediction_validation(rows):
    m=json.loads((ROOT/'web/model.json').read_text())['models']['failure']
    assert 0<predict(rows[0],m)<1
    for change in [{'layover':float('nan')},{'layover':44},{'hour':24},{'weekday':7},{'origin':'XXX'},{'dest':rows[0]['origin']}]:
        with pytest.raises(ValueError):predict({**rows[0],**change},m)

def test_evaluation_recomputed():
    rs=json.loads((ROOT/'web/replay.json').read_text());m=json.loads((ROOT/'web/model.json').read_text());e=json.loads((ROOT/'web/evaluation.json').read_text())
    p=[predict(r,m['models']['failure']) for r in rs]
    assert all(abs(a-r['risk'])<1e-12 for a,r in zip(p,rs))
    got=metrics([r['failure'] for r in rs],p)
    assert abs(got['brier']-e['failure']['brier'])<1e-12
    assert all('2025-03-03'<=r['date']<='2025-03-31' for r in rs)
