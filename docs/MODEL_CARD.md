# FlightGuard model card

## Intended use
Historical research, demonstrations of temporal ML evaluation, and explaining buffer/risk trade-offs. Not operational booking advice, an airline minimum-connection checker, live disruption alerts, or passenger-outcome prediction.

## Population and source audit
6,601 DL-operated flights, Jan–Mar 2025, ATL plus BOS/DEN/LAX/ORD/SEA. Direct US DOT/BTS monthly archives; retrieval September 6, 2026. URL, hash and row counts are committed. One clock/elapsed/timezone inconsistency excluded. No synthetic flight measurements or fabricated benchmark data. Only the constructed itinerary identities and passenger-feasibility labels are synthetic.

## Target
Failure if either leg cancels/diverts, or actual inbound gate arrival + 30m is later than actual outbound gate departure − 15m. Disruption additionally counts onward arrival delay >60m. This conflates missed connections with canceled/diverted itinerary failures intentionally; the UI calls it failure, not a pure missed-connection event. No observed passenger labels exist. Boarding cutoff and transfer allowance are hypothetical, fixed across airports/passengers; do not treat them as airline policy.

## Leakage controls
Schedule-only deterministic candidate sampling. Predictor whitelist excludes actual times, delays and outcomes. Independent month-based train/calibrate/test with two-day leading embargo; tests verify disjoint flight IDs and outcome maturity at partition boundaries. Features contain no target statistics or weather. Final BTS schedules may be revised and differ from what was available when passengers booked; archived point-in-time features are unavailable. Origin-local weekday bug was corrected after the initial evaluation run and disclosed; no test-guided feature search or hyperparameter optimization occurred.

## Fit and evaluation
Two L2 logistic models (C=1) with independent sigmoid calibration (C=1e6); no class weighting or test optimization. Full results, reliability bins and a daily clustered Brier-difference bootstrap are in `web/evaluation.json`. Full failure model AUC 0.78695 / Brier 0.04492; layover-only baseline AUC 0.80192 / Brier 0.04451. More complexity did not win. Calibration drifts across months. Outcome rate: failure 5.11%, disruption 10.33%. Small high-score bins have substantial uncertainty.

## Decision comparison
Compare the earliest/latest eligible onward options with identical inbound/destination. Low-risk selection trades roughly 111 more scheduled minutes for lower recorded synthetic failure. This is retrospective feasibility under fixed flight outcomes, not causal uplift, passenger benefit, seat availability or economic utility. Shared legs/days mean observations are dependent. The bootstrap clusters dates but does not establish uncertainty for other seasons, hubs or networks.

## Deployment and privacy
Static browser inference using JSON coefficients, no pickle deserialization, no secrets, no tracking, no remote prediction API. Shortlists stay in local browser storage. Browser code labels historical and hypothetical results; unsupported inputs are rejected. Third-party GitHub/BTS links open only through user action. No online prices or purchases.

## Verification gaps
Python/data/model tests and DOM-level emulation passed; Python/JS prediction parity and exact local offline retraining passed. Rendered-browser visual/mobile and download tests were unavailable because the static local preview was blocked. nginx Dockerfile has not been runtime-tested. GitHub CI and publication state are recorded separately in SHIP_STATUS.json after read-back, never inferred from scheduling.

## Responsible next iteration
Expand independent time coverage and hubs, obtain archived schedule snapshots and airline/gate-specific transfer inputs with appropriate licensing, validate calibration on a new month, and compare against the simple longer-buffer rule. Actual passenger labels would require a legitimate partner and explicit privacy controls. Do not silently repurpose this score for current travelers or accessibility needs.
