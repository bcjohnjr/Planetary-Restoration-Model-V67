#!/usr/bin/env python3
"""Compute standardized V67 per-case central metrics."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

TRAPZ = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
ALPHA=5.35; START=2027; END=2183

def window(df,label):
    x=df.copy(); x['year']=np.rint(x.year.to_numpy(float)).astype(int); x=x[(x.year>=START)&(x.year<=END)].sort_values('year').reset_index(drop=True)
    if not np.array_equal(x.year.to_numpy(int),np.arange(START,END+1)): raise RuntimeError(f'{label}: incomplete window')
    return x

def common(df,label,on_col,off_col):
    x=window(df,label); on=x[on_col].to_numpy(float); off=x[off_col].to_numpy(float)
    if not np.isfinite(on).all() or not np.isfinite(off).all() or np.any(on<=0) or np.any(off<=0): raise RuntimeError(f'{label}: invalid CO2')
    d=off-on; rf=ALPHA*np.log(off/on); yrs=x.year.to_numpy(float)
    return {'terminal_delta_co2_ppm':float(d[-1]),'integrated_delta_co2_ppm_year':float(TRAPZ(d,yrs)),
            'terminal_co2_forcing_benefit_wm2':float(rf[-1]),'integrated_co2_forcing_benefit_wm2_year':float(TRAPZ(rf,yrs))}

def temp(df,label,on_col,off_col):
    x=window(df,label); d=x[off_col].to_numpy(float)-x[on_col].to_numpy(float); yrs=x.year.to_numpy(float)
    if not np.isfinite(d).all(): raise RuntimeError(f'{label}: invalid temperature')
    return {'terminal_avoided_warming_c':float(d[-1]),'integrated_avoided_warming_c_year':float(TRAPZ(d,yrs))}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--case-id',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--trajectory',required=True)
    ap.add_argument('--fair-timeseries',required=True); ap.add_argument('--hector-timeseries',required=True); ap.add_argument('--oscar-timeseries',required=True); ap.add_argument('--output',default='v67_case_summary.json'); a=ap.parse_args()
    man=pd.read_csv(a.manifest); hit=man.loc[man.case_id==a.case_id]
    if len(hit)!=1: raise RuntimeError('Manifest case lookup failed')
    meta=hit.iloc[0].to_dict(); tr=pd.read_csv(a.trajectory); cdr=tr.cdr_gtco2.to_numpy(float); total=float(cdr.sum()); centroid=float(np.sum(tr.year.to_numpy(float)*cdr)/total)
    fair=pd.read_csv(a.fair_timeseries); hector=pd.read_csv(a.hector_timeseries); oscar=pd.read_csv(a.oscar_timeseries)
    fm=common(fair,'FaIR','co2_on_p50_ppm','co2_off_p50_ppm'); fm.update(temp(fair,'FaIR','tas_on_p50_c','tas_off_p50_c'))
    hm=common(hector,'Hector','co2_on_ppm','co2_off_ppm'); hm.update(temp(hector,'Hector','tas_on_c','tas_off_c'))
    om=common(oscar,'OSCAR','co2_on_p50_ppm','co2_off_p50_ppm')
    summary={'experiment':'V67 permanence/counterfactual/permafrost robustness','case_id':a.case_id,'reversal_protocol':str(meta['reversal_protocol']),
             'schedule':str(meta['schedule']),'permafrost_protocol':str(meta['permafrost_protocol']),'off_stored_reversal_zero':int(meta['off_stored_reversal_zero']),
             'cumulative_cdr_gtco2':total,'stored_reversal_gtco2':float(tr.stored_carbon_reversal_gtco2.sum()),'permafrost_gtco2':float(tr.permafrost_co2_gtco2.sum()),
             'cdr_timing_centroid_year':centroid,'models':{'FaIR':fm,'Hector':hm,'OSCAR':om},
             'claim_boundary':'Coupled reversal is a robustness sensitivity, not a mechanistic storage-failure model; permafrost zero/double is exogenous amplitude sensitivity, not fully endogenous permafrost physics.'}
    Path(a.output).write_text(json.dumps(summary,indent=2),encoding='utf-8'); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
