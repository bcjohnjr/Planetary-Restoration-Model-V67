#!/usr/bin/env python3
"""Generate the predeclared V67 trajectory robustness matrix."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED = ["year","gross_co2_gtco2","permafrost_co2_gtco2","stored_carbon_reversal_gtco2","cdr_gtco2","net_co2_gtco2"]
CANONICAL_TOTAL = 2013.8807318595145
CANONICAL_PEAK = 15.2

def validate(df):
    miss=[c for c in REQUIRED if c not in df.columns]
    if miss: raise RuntimeError(f"Missing columns: {miss}")
    x=df.sort_values("year").reset_index(drop=True).copy()
    if not np.array_equal(x.year.to_numpy(int), np.arange(2026,2184)):
        raise RuntimeError("Expected exact annual years 2026-2183")
    ident=x.gross_co2_gtco2+x.permafrost_co2_gtco2+x.stored_carbon_reversal_gtco2-x.cdr_gtco2
    err=float(np.max(np.abs(ident-x.net_co2_gtco2)))
    if err>1e-9: raise RuntimeError(f"Mass-balance error {err}")
    if not np.isfinite(x[REQUIRED].to_numpy(float)).all(): raise RuntimeError("Non-finite trajectory value")
    return x

def pulse_schedule(years,total,peak,late):
    out=np.zeros(len(years),float); eligible=np.where(years>=2027)[0]
    n_full=int(total//peak); rem=float(total-n_full*peak); n_needed=n_full+(1 if rem>1e-12 else 0)
    chosen=eligible[-n_needed:] if late else eligible[:n_needed]
    if late:
        if rem>1e-12: out[chosen[0]]=rem; out[chosen[1:]]=peak
        else: out[chosen]=peak
    else:
        out[chosen[:n_full]]=peak
        if rem>1e-12: out[chosen[n_full]]=rem
    return out

def make_schedule(base,name):
    years=base.year.to_numpy(int); canonical=base.cdr_gtco2.to_numpy(float)
    if name=="canonical": return canonical.copy()
    if name=="uniform":
        out=np.zeros(len(years),float); out[years>=2027]=CANONICAL_TOTAL/int(np.sum(years>=2027)); return out
    if name=="early": return pulse_schedule(years,CANONICAL_TOTAL,20.0,False)
    if name=="late": return pulse_schedule(years,CANONICAL_TOTAL,20.0,True)
    raise ValueError(name)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",default="external_validation_net_co2_trajectory.csv"); ap.add_argument("--outdir",default="trajectories"); a=ap.parse_args()
    base=validate(pd.read_csv(a.input)); outdir=Path(a.outdir); outdir.mkdir(parents=True,exist_ok=True)
    if abs(float(base.cdr_gtco2.sum())-CANONICAL_TOTAL)>1e-6: raise RuntimeError("Unexpected canonical CDR total")
    if abs(float(base.cdr_gtco2.max())-CANONICAL_PEAK)>1e-9: raise RuntimeError("Unexpected canonical CDR peak")
    if abs(float(base.loc[base.year==2026,"cdr_gtco2"].iloc[0]))>1e-12: raise RuntimeError("2026 CDR must be zero")
    rev_total=float(base.stored_carbon_reversal_gtco2.sum()); ratio=rev_total/CANONICAL_TOTAL; pf_total=float(base.permafrost_co2_gtco2.sum())
    specs=[
      ("fixed__early","fixed_source","early","canonical",0),("fixed__late","fixed_source","late","canonical",0),
      ("permanent__early","ideal_permanent","early","canonical",1),("permanent__late","ideal_permanent","late","canonical",1),
      ("coupled__early","coupled_program","early","canonical",1),("coupled__canonical","coupled_program","canonical","canonical",1),
      ("coupled__uniform","coupled_program","uniform","canonical",1),("coupled__late","coupled_program","late","canonical",1),
      ("coupled_pfzero__early","coupled_program","early","zero",1),("coupled_pfzero__late","coupled_program","late","zero",1),
      ("coupled_pfdouble__early","coupled_program","early","double",1),("coupled_pfdouble__late","coupled_program","late","double",1)]
    rows=[]
    for cid,rp,sched,pfp,offzero in specs:
        x=base[REQUIRED].copy(); cdr=make_schedule(base,sched); x["cdr_gtco2"]=cdr
        if rp=="fixed_source": rev=base.stored_carbon_reversal_gtco2.to_numpy(float)
        elif rp=="ideal_permanent": rev=np.zeros(len(base))
        else: rev=ratio*cdr
        x["stored_carbon_reversal_gtco2"]=rev
        if pfp=="canonical": pf=base.permafrost_co2_gtco2.to_numpy(float)
        elif pfp=="zero": pf=np.zeros(len(base))
        else: pf=2.0*base.permafrost_co2_gtco2.to_numpy(float)
        x["permafrost_co2_gtco2"]=pf
        x["net_co2_gtco2"]=x.gross_co2_gtco2+x.permafrost_co2_gtco2+x.stored_carbon_reversal_gtco2-x.cdr_gtco2
        validate(x)
        if abs(float(x.cdr_gtco2.sum())-CANONICAL_TOTAL)>1e-6: raise RuntimeError(f"{cid}: CDR total changed")
        if rp=="coupled_program" and abs(float(x.stored_carbon_reversal_gtco2.sum())-rev_total)>1e-8: raise RuntimeError(f"{cid}: reversal total changed")
        pos=x.loc[x.cdr_gtco2>1e-12,"year"]; centroid=float(np.sum(x.year.to_numpy(float)*x.cdr_gtco2.to_numpy(float))/CANONICAL_TOTAL)
        fn=f"{cid}.csv"; x.to_csv(outdir/fn,index=False)
        rows.append({"case_id":cid,"reversal_protocol":rp,"schedule":sched,"permafrost_protocol":pfp,"off_stored_reversal_zero":offzero,"file":fn,
                     "cumulative_cdr_gtco2":float(x.cdr_gtco2.sum()),"stored_reversal_gtco2":float(x.stored_carbon_reversal_gtco2.sum()),
                     "permafrost_gtco2":float(x.permafrost_co2_gtco2.sum()),"peak_cdr_gtco2_per_year":float(x.cdr_gtco2.max()),
                     "first_positive_cdr_year":int(pos.min()),"last_positive_cdr_year":int(pos.max()),"cdr_timing_centroid_year":centroid})
    manifest={"experiment":"V67 permanence/counterfactual/permafrost robustness","years":[2026,2183],"canonical_cdr_total_gtco2":CANONICAL_TOTAL,
              "canonical_reversal_total_gtco2":rev_total,"canonical_reversal_to_cdr_ratio":ratio,"canonical_permafrost_total_gtco2":pf_total,
              "case_count":len(rows),"cases":rows,
              "coupled_reversal_definition":"annual stored-carbon reversal = canonical cumulative reversal/CDR ratio x annual CDR; removal-OFF excludes this programme-contingent source"}
    pd.DataFrame(rows).to_csv(outdir/"manifest.csv",index=False); (outdir/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8"); print(json.dumps(manifest,indent=2))
if __name__=="__main__": main()
