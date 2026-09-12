#!/usr/bin/env python3
"""Patch the pinned V65 OSCAR matched-forcing runner for V67."""
from __future__ import annotations
import argparse
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("output"); a=ap.parse_args(); text=Path(a.input).read_text(encoding="utf-8")
    old='''    off = np.asarray([\n        float(\n            p.loc[y, "gross_co2_gtco2"]\n            + p.loc[y, "permafrost_co2_gtco2"]\n            + p.loc[y, "stored_carbon_reversal_gtco2"]\n        )\n        for y in years\n    ], dtype=float)\n'''
    new='''    off_reversal_zero = os.environ.get("V67_OFF_STORED_REVERSAL_ZERO", "0") == "1"\n    off = np.asarray([\n        float(\n            p.loc[y, "gross_co2_gtco2"]\n            + p.loc[y, "permafrost_co2_gtco2"]\n            + (0.0 if off_reversal_zero else p.loc[y, "stored_carbon_reversal_gtco2"])\n        )\n        for y in years\n    ], dtype=float)\n'''
    if text.count(old)!=1: raise SystemExit("OSCAR OFF-path block not found")
    text=text.replace(old,new,1)
    anchor="    delta_ppm = co2_off - co2_on\n"
    if text.count(anchor)!=1: raise SystemExit("OSCAR delta anchor not found")
    code='''    forcing_benefit_member = 5.35 * np.log(co2_off / co2_on)\n    oscar_members = pd.DataFrame({\n        "member_id": np.arange(co2_on.shape[1], dtype=int),\n        "terminal_delta_co2_ppm": delta_ppm[-1, :],\n        "integrated_delta_co2_ppm_year": np.trapz(delta_ppm, years, axis=0),\n        "terminal_co2_forcing_benefit_wm2": forcing_benefit_member[-1, :],\n        "integrated_co2_forcing_benefit_wm2_year": np.trapz(forcing_benefit_member, years, axis=0),\n    })\n    if len(oscar_members) != args.nmc or not np.isfinite(oscar_members.drop(columns=["member_id"]).to_numpy(float)).all():\n        raise RuntimeError("Invalid V67 OSCAR member metrics")\n    oscar_members.to_csv(outdir / "oscar_member_metrics.csv", index=False)\n'''
    text=text.replace(anchor,anchor+code,1)
    oldc='''    closure_gtco2 = (\n        cumulative_cdr[:, None]\n        - atmospheric_benefit_gtco2\n        - land_comp_gtco2\n        - ocean_comp_gtco2\n    )\n'''
    newc='''    stored_map = pathway.set_index("year")["stored_carbon_reversal_gtco2"].to_dict()\n    stored_annual = np.asarray([float(stored_map[int(y)]) for y in years], dtype=float)\n    cumulative_program_withdrawal = np.cumsum(cdr_annual - (stored_annual if off_reversal_zero else 0.0))\n    closure_gtco2 = (\n        cumulative_program_withdrawal[:, None]\n        - atmospheric_benefit_gtco2\n        - land_comp_gtco2\n        - ocean_comp_gtco2\n    )\n'''
    if text.count(oldc)!=1: raise SystemExit("OSCAR closure block not found")
    text=text.replace(oldc,newc,1); Path(a.output).write_text(text,encoding="utf-8"); print(f"Patched V67 OSCAR runner written to {a.output}")
if __name__=="__main__": main()
