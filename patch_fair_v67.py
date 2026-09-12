#!/usr/bin/env python3
"""Patch the pinned V62.2 FaIR matched-forcing runner for V67."""
from __future__ import annotations
import argparse,re
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("output"); a=ap.parse_args(); text=Path(a.input).read_text(encoding="utf-8")
    if "END_YEAR = 2183" not in text: raise SystemExit("Patch END_YEAR to 2183 before V67 patch")
    anchor="    on, off, cdr = {}, {}, {}\n"
    if text.count(anchor)!=1: raise SystemExit("FaIR carbon_paths anchor not found")
    text=text.replace(anchor,anchor+"    off_reversal_zero = os.environ.get('V67_OFF_STORED_REVERSAL_ZERO', '0') == '1'\n",1)
    patt=re.compile(r"off\[y\]\s*=\s*float\(\s*r\.gross_co2_gtco2\s*\+\s*r\.permafrost_co2_gtco2\s*\+\s*r\.stored_carbon_reversal_gtco2\s*\)",re.DOTALL)
    repl="off[y] = float(\n            r.gross_co2_gtco2 + r.permafrost_co2_gtco2\n            + (0.0 if off_reversal_zero else r.stored_carbon_reversal_gtco2)\n        )"
    text,n=patt.subn(repl,text,count=1)
    if n!=1: raise SystemExit(f"FaIR OFF-path expression count={n}")
    text=text.replace("for yy in [2040, 2100, 2156, 2184, 2200, 2300]:","for yy in [2040, 2100, 2156, 2183]:")
    anchor2="    t_on, t_off = temp(fon), temp(foff)\n"
    if text.count(anchor2)!=1: raise SystemExit("FaIR state-array anchor not found")
    code="""    # V67 member-level ranking metrics.\n    eval_mask = (years >= 2027) & (years <= 2183)\n    eval_years = years[eval_mask]\n    delta_member = co_off - co_on\n    forcing_member = 5.35 * np.log(co_off / co_on)\n    warming_member = t_off - t_on\n    fair_members = pd.DataFrame({\n        'member_id': ids.astype(str),\n        'terminal_delta_co2_ppm': delta_member[years == 2183, :].reshape(-1),\n        'integrated_delta_co2_ppm_year': np.trapz(delta_member[eval_mask, :], eval_years, axis=0),\n        'terminal_co2_forcing_benefit_wm2': forcing_member[years == 2183, :].reshape(-1),\n        'integrated_co2_forcing_benefit_wm2_year': np.trapz(forcing_member[eval_mask, :], eval_years, axis=0),\n        'terminal_avoided_warming_c': warming_member[years == 2183, :].reshape(-1),\n        'integrated_avoided_warming_c_year': np.trapz(warming_member[eval_mask, :], eval_years, axis=0),\n    })\n    if len(fair_members) != 841 or not np.isfinite(fair_members.drop(columns=['member_id']).to_numpy(float)).all():\n        raise RuntimeError('Invalid V67 FaIR member metrics')\n    fair_members.to_csv('fair_member_metrics.csv', index=False)\n"""
    text=text.replace(anchor2,anchor2+code,1); Path(a.output).write_text(text,encoding="utf-8"); print(f"Patched V67 FaIR runner written to {a.output}")
if __name__=="__main__": main()
