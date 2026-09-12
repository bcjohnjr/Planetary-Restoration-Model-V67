# Planetary Restoration Model V67
## Permanence, counterfactual-reversal, permafrost and ensemble robustness test

V67 is a targeted robustness experiment for the carbon-removal timing result reported
from V65/V66. It does not replace the successful V65 workflow. It asks whether the
endpoint-versus-cumulative-benefit timing reversal survives when the stored-carbon
reversal bookkeeping is made physically consistent with the timing of the CDR
programme and when the exogenous permafrost source is stressed.

### Stored-carbon protocols

1. `fixed_source` — exact V65-style control. The canonical stored-carbon-reversal
   source is held fixed and appears in both removal-ON and removal-OFF branches.
2. `ideal_permanent` — stored-carbon reversal is zero in both branches.
3. `coupled_program` — the canonical cumulative reversal burden is redistributed
   in direct proportion to the actual CDR schedule. It appears only in the
   removal-ON world; the removal-OFF counterfactual receives no programme-contingent
   reversal from a programme that did not occur.

The schedule-coupled treatment is a transparent robustness sensitivity, not a
mechanistic storage-failure model. It preserves the canonical cumulative
reversal/CDR ratio while changing timing and counterfactual attribution.

### Permafrost sensitivity

The main matrix retains the canonical exported permafrost source. A focused
sensitivity reruns the coupled early and late schedules with the exogenous
permafrost source set to zero and doubled. This brackets dependence on the fixed
exported source; it is not a substitute for a fully endogenous permafrost model.

### Twelve cases

- fixed_source: early, late
- ideal_permanent: early, late
- coupled_program: early, canonical, uniform, late
- coupled_program + zero permafrost: early, late
- coupled_program + double permafrost: early, late

All timing cases retain the same deliberate cumulative CDR of
2,013.8807318595145 GtCO2. The early/late cases use the same <=20 GtCO2/yr pulse
design as V65.

### Primary predeclared tests

For each stored-carbon treatment under canonical permafrost:

- H1: early removal has greater integrated atmospheric CO2 benefit and integrated
  CO2-forcing benefit through 2183 than late removal.
- H2: late removal has greater terminal atmospheric CO2 benefit in 2183 than early
  removal.
- H3: FaIR and Hector show greater integrated avoided warming for early than late
  removal.

For `coupled_program`, H1/H2 are also tested under zero, canonical and doubled
exogenous permafrost.

FaIR (841 constrained configurations) and OSCAR (200 Monte Carlo members) export
member-level metrics. V67 reports the fraction of paired ensemble members satisfying
H1, H2 and both jointly. Hypothesis support is a scientific result and never controls
whether the workflow itself is green.

### Claim boundary

A positive V67 result would support the statement that the ranking reversal is robust
to three explicit stored-carbon treatments and to a wide exogenous-permafrost
sensitivity. It would not establish a globally optimal CDR schedule, universal
permanence, or fully endogenous permafrost physics.

### Flat-package installation

Upload every file in this ZIP to the repository root except the workflow YAML.
Place `v67-permanence-feedback-robustness.yml` at:

    .github/workflows/v67-permanence-feedback-robustness.yml

Then run GitHub Actions -> `V67 Permanence and Feedback Robustness`.
