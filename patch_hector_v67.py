#!/usr/bin/env python3
"""Patch an already horizon-patched V65 Hector runner for V67."""
from __future__ import annotations
import argparse,re
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input"); ap.add_argument("output"); a=ap.parse_args(); text=Path(a.input).read_text(encoding="utf-8")
    patt=re.compile(r"gross_source_gtco2\s*<-\s*x\$gross_co2_gtco2\s*\+\s*x\$permafrost_co2_gtco2\s*\+\s*x\$stored_carbon_reversal_gtco2\s*\n\s*gross_c\s*<-\s*gross_source_gtco2\s*\*\s*co2_to_c",re.DOTALL)
    repl='''off_reversal_zero <- identical(Sys.getenv("V67_OFF_STORED_REVERSAL_ZERO", "0"), "1")\n\ngross_source_on_gtco2 <-\n  x$gross_co2_gtco2 +\n  x$permafrost_co2_gtco2 +\n  x$stored_carbon_reversal_gtco2\n\ngross_source_off_gtco2 <-\n  x$gross_co2_gtco2 +\n  x$permafrost_co2_gtco2 +\n  if (off_reversal_zero) 0 else x$stored_carbon_reversal_gtco2\n\ngross_c_on <- gross_source_on_gtco2 * co2_to_c\ngross_c_off <- gross_source_off_gtco2 * co2_to_c'''
    text,n=patt.subn(repl,text,count=1)
    if n!=1: raise SystemExit(f"Hector gross-source block count={n}")
    ffi=re.compile(r'(FFI_EMISSIONS\(\),\s*\n\s*)gross_c(,\s*\n\s*unit_ffi,\s*\n\s*"FFI gross source")',re.DOTALL)
    text,n2=ffi.subn(r'\1if (removal_on) gross_c_on else gross_c_off\2',text,count=1)
    if n2!=1: raise SystemExit(f"Hector FFI assignment count={n2}")
    Path(a.output).write_text(text,encoding="utf-8"); print(f"Patched V67 Hector runner written to {a.output}")
if __name__=="__main__": main()
