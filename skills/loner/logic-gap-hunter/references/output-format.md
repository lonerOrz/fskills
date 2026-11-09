# Output Format

Emit the report in the following order. Use `assets/finding-template.md` for each
individual finding.

## 1. Scope

State the exact files, functions, or call chains examined. State what was
excluded and why.

## 2. Coverage map

Table with columns: Dimension | Status (`applicable` / `not-applicable`) | Line
range or exclusion reason.

## 3. Reachable candidates

Findings whose counterexample has a plausible entry path. Use the finding
template. Order by severity descending.

## 4. Assumption-dependent candidates

Findings valid only if a stated implicit assumption fails. Each entry must name
the assumption and the consequence of its violation.

## 5. Theoretical-only candidates

Counterexamples with no reachable entry point. Include them for completeness but
do not list them among primary candidates.

## 6. Dimensions covered with no finding

List the dimensions examined where no reachable counterexample was constructed.
This section is mandatory; omitting it constitutes a false completeness claim.

## 7. Residual risk

State which dimensions could not be examined due to insufficient context, and
what additional context or tooling would be required.
