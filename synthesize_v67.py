#!/usr/bin/env python3
"""Synthesize V67 robustness and ensemble-member ranking results."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
MODELS=('FaIR','Hector','OSCAR')
PAIR_SETS={'fixed_source':('fixed__early','fixed__late'),'ideal_permanent':('permanent__early','permanent__late'),'coupled_program':('coupled__early','coupled__late')}
PF_PAIRS={'zero':('coupled_pfzero__early','coupled_pfzero__late'),'canonical':('coupled__early','coupled__late'),'double':('coupled_pfdouble__early','coupled_pfdouble__late')}
EXPECTED={'fixed__early','fixed__late','permanent__early','permanent__late','coupled__early','coupled__canonical','coupled__uniform','coupled__late','coupled_pfzero__early','coupled_pfzero__late','coupled_pfdouble__early','coupled_pfdouble__late'}

def member_file(root,model):
    p=root/('fair_work/fair_member_metrics.csv' if model=='FaIR' else 'oscar_results/oscar_member_metrics.csv')
    if not p.exists(): raise RuntimeError(f'Missing member file {p}')
    return p

def paired_member_stats(roots,eid,lid,model):
    e=pd.read_csv(member_file(roots[eid],model)); l=pd.read_csv(member_file(roots[lid],model)); x=e.merge(l,on='member_id',suffixes=('_early','_late'),validate='one_to_one')
    h1=x.integrated_co2_forcing_benefit_wm2_year_early>x.integrated_co2_forcing_benefit_wm2_year_late
    h2=x.terminal_delta_co2_ppm_late>x.terminal_delta_co2_ppm_early
    out={'model':model,'members':int(len(x)),'fraction_early_gt_late_integrated_forcing':float(np.mean(h1)),'fraction_late_gt_early_terminal_co2':float(np.mean(h2)),'fraction_joint_ranking_reversal':float(np.mean(h1 & h2))}
    if model=='FaIR':
        ht=x.integrated_avoided_warming_c_year_early>x.integrated_avoided_warming_c_year_late
        out['fraction_early_gt_late_integrated_avoided_warming']=float(np.mean(ht))
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--outdir',default='v67_results'); a=ap.parse_args(); root=Path(a.root); outdir=Path(a.outdir); outdir.mkdir(parents=True,exist_ok=True)
    summaries={}; roots={}
    for p in root.rglob('v67_case_summary.json'):
        d=json.loads(p.read_text(encoding='utf-8')); cid=d['case_id']
        if cid in summaries: raise RuntimeError(f'Duplicate case {cid}')
        summaries[cid]=d; roots[cid]=p.parents[1]
    if set(summaries)!=EXPECTED: raise RuntimeError(f'Case mismatch missing={sorted(EXPECTED-set(summaries))} extra={sorted(set(summaries)-EXPECTED)}')
    rows=[]
    for cid in sorted(summaries):
        d=summaries[cid]
        for model in MODELS:
            rows.append({'case_id':cid,'reversal_protocol':d['reversal_protocol'],'schedule':d['schedule'],'permafrost_protocol':d['permafrost_protocol'],'model':model,
                         'cumulative_cdr_gtco2':d['cumulative_cdr_gtco2'],'stored_reversal_gtco2':d['stored_reversal_gtco2'],'permafrost_gtco2':d['permafrost_gtco2'],**d['models'][model]})
    df=pd.DataFrame(rows); df.to_csv(outdir/'V67_CASE_METRICS.csv',index=False)
    central_tests={}; member_rows=[]
    for protocol,(eid,lid) in PAIR_SETS.items():
        central_tests[protocol]={}
        for model in MODELS:
            e=df[(df.case_id==eid)&(df.model==model)].iloc[0]; l=df[(df.case_id==lid)&(df.model==model)].iloc[0]
            item={'early_gt_late_integrated_co2':bool(e.integrated_delta_co2_ppm_year>l.integrated_delta_co2_ppm_year),
                  'early_gt_late_integrated_forcing':bool(e.integrated_co2_forcing_benefit_wm2_year>l.integrated_co2_forcing_benefit_wm2_year),
                  'late_gt_early_terminal_co2':bool(l.terminal_delta_co2_ppm>e.terminal_delta_co2_ppm),
                  'integrated_forcing_early_minus_late_wm2_year':float(e.integrated_co2_forcing_benefit_wm2_year-l.integrated_co2_forcing_benefit_wm2_year),
                  'terminal_co2_late_minus_early_ppm':float(l.terminal_delta_co2_ppm-e.terminal_delta_co2_ppm)}
            if model in ('FaIR','Hector'):
                item['early_gt_late_integrated_avoided_warming']=bool(e.integrated_avoided_warming_c_year>l.integrated_avoided_warming_c_year)
                item['integrated_avoided_warming_early_minus_late_c_year']=float(e.integrated_avoided_warming_c_year-l.integrated_avoided_warming_c_year)
            central_tests[protocol][model]=item
        for model in ('FaIR','OSCAR'):
            mr=paired_member_stats(roots,eid,lid,model); mr['reversal_protocol']=protocol; member_rows.append(mr)
    member_df=pd.DataFrame(member_rows); member_df.to_csv(outdir/'V67_MEMBER_RANKING.csv',index=False)
    pf_tests={}
    for pf,(eid,lid) in PF_PAIRS.items():
        pf_tests[pf]={}
        for model in MODELS:
            e=df[(df.case_id==eid)&(df.model==model)].iloc[0]; l=df[(df.case_id==lid)&(df.model==model)].iloc[0]
            pf_tests[pf][model]={'early_gt_late_integrated_forcing':bool(e.integrated_co2_forcing_benefit_wm2_year>l.integrated_co2_forcing_benefit_wm2_year),'late_gt_early_terminal_co2':bool(l.terminal_delta_co2_ppm>e.terminal_delta_co2_ppm)}
    h1h2=all(central_tests[p][m]['early_gt_late_integrated_forcing'] and central_tests[p][m]['late_gt_early_terminal_co2'] for p in PAIR_SETS for m in MODELS)
    h3=all(central_tests[p][m].get('early_gt_late_integrated_avoided_warming',True) for p in PAIR_SETS for m in ('FaIR','Hector'))
    pfall=all(pf_tests[p][m]['early_gt_late_integrated_forcing'] and pf_tests[p][m]['late_gt_early_terminal_co2'] for p in PF_PAIRS for m in MODELS)
    result={'experiment':'V67 permanence/counterfactual/permafrost robustness','status':'PASS_PROTOCOL','case_count':len(EXPECTED),
            'scientific_support':{'ranking_reversal_all_three_stored_carbon_protocols_all_models':h1h2,'avoided_warming_early_advantage_all_FaIR_Hector_protocols':h3,'ranking_reversal_zero_canonical_double_permafrost_all_models':pfall},
            'central_tests':central_tests,'permafrost_tests':pf_tests,'member_level':member_rows,'interpretation_rule':'PASS_PROTOCOL means computation completed and numerical gates passed; scientific-support booleans are results, not CI pass/fail gates.'}
    (outdir/'V67_ROBUSTNESS_SUMMARY.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# V67 permanence, counterfactual and permafrost robustness results','',f'- Ranking reversal across stored-carbon protocols/models: **{h1h2}**',f'- Early avoided-warming advantage across FaIR/Hector: **{h3}**',f'- Ranking reversal across permafrost sensitivity: **{pfall}**','','## Central early-vs-late results','','| Reversal protocol | Model | Early minus late integrated forcing (W m^-2 yr) | Late minus early terminal CO2 (ppm) |','|---|---|---:|---:|']
    for p in PAIR_SETS:
        for m in MODELS:
            z=central_tests[p][m]; lines.append(f"| {p} | {m} | {z['integrated_forcing_early_minus_late_wm2_year']:.4f} | {z['terminal_co2_late_minus_early_ppm']:.4f} |")
    lines += ['','## Ensemble-member support','','| Protocol | Model | Members | Early wins integrated forcing | Late wins terminal CO2 | Joint reversal |','|---|---|---:|---:|---:|---:|']
    for r in member_rows: lines.append(f"| {r['reversal_protocol']} | {r['model']} | {r['members']} | {r['fraction_early_gt_late_integrated_forcing']:.3f} | {r['fraction_late_gt_early_terminal_co2']:.3f} | {r['fraction_joint_ranking_reversal']:.3f} |")
    lines += ['','Coupled reversal is a diagnostic robustness sensitivity, not a mechanistic storage-failure model. Permafrost zero/double is exogenous amplitude sensitivity, not fully endogenous permafrost physics.']
    (outdir/'V67_ROBUSTNESS_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
