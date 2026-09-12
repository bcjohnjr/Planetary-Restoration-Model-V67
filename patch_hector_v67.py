#!/usr/bin/env python3
"""Patch an already horizon-patched V65 Hector runner for V67.

V67 changes the removal-OFF counterfactual for programme-contingent stored-carbon
reversals.  Late schedules also need one numerical safeguard: ON and OFF have an
identical carbon/forcing history before the first CDR year, so their matched-
forcing constraints are locked to the same converged prefix.  This prevents two
independent fixed-point solves from ending on slightly different, but individually
acceptable, pre-intervention constraints when one branch needs one extra iteration.
The scientific 1e-5 W/m2 forcing gate and the 1e-8 ppm CO2 monotonicity gate are
left unchanged.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def sub_once(text: str, pattern: str | re.Pattern[str], repl: str, label: str, *, flags: int = 0) -> str:
    out, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if n != 1:
        raise SystemExit(f"{label} count={n}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    a = ap.parse_args()
    text = Path(a.input).read_text(encoding="utf-8")

    # V67 counterfactual: stored-carbon reversal is programme-contingent in the
    # coupled/permanent cases, so the OFF branch can exclude it.
    gross_pattern = re.compile(
        r"gross_source_gtco2\s*<-\s*x\$gross_co2_gtco2\s*\+\s*"
        r"x\$permafrost_co2_gtco2\s*\+\s*x\$stored_carbon_reversal_gtco2\s*\n\s*"
        r"gross_c\s*<-\s*gross_source_gtco2\s*\*\s*co2_to_c",
        re.DOTALL,
    )
    gross_repl = '''off_reversal_zero <- identical(Sys.getenv("V67_OFF_STORED_REVERSAL_ZERO", "0"), "1")

gross_source_on_gtco2 <-
  x$gross_co2_gtco2 +
  x$permafrost_co2_gtco2 +
  x$stored_carbon_reversal_gtco2

gross_source_off_gtco2 <-
  x$gross_co2_gtco2 +
  x$permafrost_co2_gtco2 +
  if (off_reversal_zero) 0 else x$stored_carbon_reversal_gtco2

gross_c_on <- gross_source_on_gtco2 * co2_to_c
gross_c_off <- gross_source_off_gtco2 * co2_to_c'''
    text = sub_once(text, gross_pattern, gross_repl, "Hector gross-source block")

    ffi_pattern = re.compile(
        r'(FFI_EMISSIONS\(\),\s*\n\s*)gross_c(,\s*\n\s*unit_ffi,\s*\n\s*"FFI gross source")',
        re.DOTALL,
    )
    text = sub_once(
        text,
        ffi_pattern,
        r'\1if (removal_on) gross_c_on else gross_c_off\2',
        "Hector FFI assignment",
    )

    # Extend the accepted-state solver with an optional locked common prefix.
    fit_signature = re.compile(
        r"fit_case\s*<-\s*function\(\s*"
        r"label,\s*removal_on,\s*tol\s*=\s*1e-5,\s*max_iter\s*=\s*400L,\s*"
        r"alpha_initial\s*=\s*0\.10,\s*alpha_min\s*=\s*0\.001,\s*"
        r"alpha_max\s*=\s*0\.25\s*\)\s*\{",
        re.DOTALL,
    )
    fit_repl = '''fit_case <- function(
  label,
  removal_on,
  tol = 1e-5,
  max_iter = 400L,
  alpha_initial = 0.10,
  alpha_min = 0.001,
  alpha_max = 0.25,
  locked_mask = NULL,
  locked_constraint = NULL
) {'''
    text = sub_once(text, fit_signature, fit_repl, "Hector fit_case signature")

    lock_validation = '''

  # Optional V67 common-prefix lock.  The lock is numerical only: it is used
  # solely for years before ON and OFF diverge, when both branches represent
  # exactly the same experiment and therefore must have the same constraint.
  if (is.null(locked_mask)) {
    locked_mask <- rep(FALSE, length(match_years))
  } else {
    locked_mask <- as.logical(locked_mask)
    if (length(locked_mask) != length(match_years) || any(is.na(locked_mask))) {
      fail("Invalid locked-prefix mask in %s", label)
    }
  }

  if (any(locked_mask)) {
    if (
      is.null(locked_constraint) ||
      length(locked_constraint) != length(match_years) ||
      any(!is.finite(locked_constraint[locked_mask]))
    ) {
      fail("Invalid locked-prefix constraint in %s", label)
    }
  }
'''
    seed_comment = re.compile(
        r'(\n\s*#\s*\n\s*# Run the branch once without future total-forcing\s*\n\s*# constraints\. Hector supplies its own CO2 forcing\.)'
    )
    m = seed_comment.search(text)
    if not m:
        raise SystemExit("Hector pre-seed anchor count=0")
    if len(seed_comment.findall(text)) != 1:
        raise SystemExit(f"Hector pre-seed anchor count={len(seed_comment.findall(text))}")
    text = text[:m.start()] + lock_validation + text[m.start():]

    constraint_pattern = re.compile(
        r'(constraint\s*<-\s*\n\s*rf_seed\s*\+\s*\n\s*target\s*\n)'
    )
    constraint_repl = r'''\1
  if (any(locked_mask)) {
    constraint[locked_mask] <- locked_constraint[locked_mask]
  }
'''
    text = sub_once(text, constraint_pattern, constraint_repl, "Hector initial locked constraint")

    direction_pattern = re.compile(
        r'(direction\s*<-\s*\n\s*fixed_point_target\s*-\s*\n\s*current\$constraint\s*\n)'
    )
    direction_repl = r'''\1
    if (any(locked_mask)) {
      direction[locked_mask] <- 0
    }
'''
    text = sub_once(text, direction_pattern, direction_repl, "Hector locked update direction")

    trial_pattern = re.compile(
        r'(trial_constraint\s*<-\s*\n\s*current\$constraint\s*\+\s*\n\s*trial_alpha\s*\*\s*\n\s*direction\s*\n)'
    )
    trial_repl = r'''\1
      if (any(locked_mask)) {
        trial_constraint[locked_mask] <- locked_constraint[locked_mask]
      }
'''
    text = sub_once(text, trial_pattern, trial_repl, "Hector locked trial constraint")

    return_pattern = re.compile(
        r'(list\(\s*run\s*=\s*current\$run,\s*)(history\s*=\s*history,)',
        re.DOTALL,
    )
    return_repl = r'''\1constraint =
      current$constraint,

    \2'''
    text = sub_once(text, return_pattern, return_repl, "Hector fit_case constraint return")

    # Solve ON normally.  For OFF, lock only the years strictly before the
    # first positive CDR year to ON's already-converged forcing constraint.
    # All late-schedule pre-intervention states are then bitwise comparable,
    # while the post-intervention suffix is still independently solved.
    branch_pattern = re.compile(
        r'on_case\s*<-\s*fit_case\(\s*"removal-ON matched",\s*TRUE\s*\)\s*'
        r'off_case\s*<-\s*fit_case\(\s*"removal-OFF matched",\s*FALSE\s*\)',
        re.DOTALL,
    )
    branch_repl = '''on_case <- fit_case(
  "removal-ON matched",
  TRUE
)

intervention_years <- x$year[x$cdr_gtco2 > 1e-12]
if (!length(intervention_years)) {
  fail("V67 trajectory contains no positive CDR year")
}
first_intervention_year <- min(intervention_years)
common_prefix_mask <- match_years < first_intervention_year

if (any(common_prefix_mask)) {
  say(
    "V67: locking %d common-prefix forcing years through %d to the converged ON constraint",
    sum(common_prefix_mask),
    first_intervention_year - 1
  )
}

off_case <- fit_case(
  "removal-OFF matched",
  FALSE,
  locked_mask = common_prefix_mask,
  locked_constraint = on_case$constraint
)'''
    text = sub_once(text, branch_pattern, branch_repl, "Hector synchronized ON/OFF branch block")

    # Add a symmetric pre-intervention equality gate.  This is stricter than
    # merely requiring removal ON not to exceed OFF and ensures the lock did
    # what it was designed to do.  The original post/full-horizon monotonicity
    # gate below remains untouched at 1e-8 ppm.
    delta_pattern = re.compile(
        r'(pair\$delta_co2_ppm\s*<-\s*\n\s*pair\$co2_off_ppm\s*-\s*\n\s*pair\$co2_on_ppm\s*\n)'
    )
    delta_repl = r'''\1
common_prefix_rows <- pair$year < first_intervention_year
common_prefix_co2_maxabs_ppm <- max(
  abs(pair$delta_co2_ppm[common_prefix_rows])
)

if (!is.finite(common_prefix_co2_maxabs_ppm) || common_prefix_co2_maxabs_ppm > 1e-8) {
  fail(
    "Hector V67 common-prefix CO2 equality failed: %.12g ppm",
    common_prefix_co2_maxabs_ppm
  )
}
'''
    text = sub_once(text, delta_pattern, delta_repl, "Hector common-prefix equality gate")

    # Keep the original 1e-8 ppm monotonicity threshold, but make any future
    # failure self-diagnosing instead of emitting a context-free message.
    monotonicity_pattern = re.compile(
        r'if\s*\(\s*any\(\s*pair\$delta_co2_ppm\s*<\s*-1e-8\s*\)\s*\)\s*\{\s*'
        r'fail\(\s*"Removal ON raises CO2 above OFF beyond tolerance"\s*\)\s*\}',
        re.DOTALL,
    )
    monotonicity_repl = '''min_delta_co2_ppm <- min(pair$delta_co2_ppm)
min_delta_index <- which.min(pair$delta_co2_ppm)

if (min_delta_co2_ppm < -1e-8) {
  fail(
    paste0(
      "Removal ON raises CO2 above OFF beyond tolerance: ",
      "min OFF-ON=%.12g ppm at year %d; ON=%.12g ppm; OFF=%.12g ppm"
    ),
    min_delta_co2_ppm,
    pair$year[min_delta_index],
    pair$co2_on_ppm[min_delta_index],
    pair$co2_off_ppm[min_delta_index]
  )
}'''
    text = sub_once(text, monotonicity_pattern, monotonicity_repl, "Hector monotonicity diagnostic gate")

    Path(a.output).write_text(text, encoding="utf-8")
    print(f"Patched V67 Hector runner written to {a.output}")


if __name__ == "__main__":
    main()
