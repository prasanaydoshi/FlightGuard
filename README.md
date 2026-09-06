# FlightGuard

**Historical connection-risk research using real US DOT flight records.** Compare plausible Delta-operated connections through Atlanta, inspect calibrated risk scores, reveal recorded synthetic outcomes, and reproduce every evaluation locally.

This is a portfolio research application, not a booking engine or personal travel-risk guarantee. It has no live schedules, fares, seat inventory, passenger itineraries or alerts. It does not represent Delta, airports, or BTS.

## Try it in one command

Python 3.11+ is enough to run the included app; no model dependencies or API key are needed to explore the bundled replay.

```sh
git clone https://github.com/prasanaydoshi/FlightGuard.git
cd FlightGuard
python -m http.server 8000 --directory web
```

Open `http://localhost:8000`. Start with **BOS → SEA, March 10, 2025**, then compare shorter journeys against lower estimated connection risk. All times display in each airport's local timezone, with dates and timezone labels in the detail panel. Outcomes are hidden until explicitly revealed.

## What is included

- Historical itinerary explorer with origin, destination, date and risk/duration sorting.
- Separate sigmoid-calibrated connection-failure and disruption models, with portable browser inference.
- Same-inbound alternative comparisons and signed model-term explanations.
- Hypothetical layover sensitivity, clearly separated from available flights or causal predictions.
- Device-local shortlist and CSV export; outcome columns export only when reveal is enabled.
- Real BTS source subset, download provenance and SHA-256 hashes, deterministic extraction/training CLI.
- Chronological holdout, simple baselines, reliability bins, Brier/log-loss/AUC/AP metrics, daily clustered uncertainty and policy comparisons.
- Python tests, JavaScript parity checks, DOM-level UI tests, GitHub Actions, static Docker packaging.

## Data and honest target definitions

Downloaded **September 6, 2026**, directly from the [BTS Reporting Carrier archive directory](https://transtats.bts.gov/PREZIP/). We inspected **1,645,503 source rows** across January, February and March 2025 and retained **6,601 DL-operated flights** between ATL and BOS, DEN, LAX, ORD, SEA. One selected record was excluded because its scheduled arrival clock disagreed with departure time, timezone and elapsed duration. No records were excluded merely for cancellation or diversion. Exact archive URLs, hashes and counts are in [data/manifest.json](data/manifest.json).

The [BTS dataset description](https://transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EFD) documents scheduled/actual flight times, cancellations and diversions; its [on-time portal](https://www.transtats.bts.gov/ontime/) specifies local-time reporting. Airport timezone mappings are explicit in `flightguard/data.py` and resolved using Python's IANA ZoneInfo database. UTC timestamps are reconstructed from local scheduled departure plus scheduled elapsed minutes. Invalid clocks, ambiguous/nonexistent DST times and clock mismatches are rejected rather than guessed. Actual gate times are derived by adding reported delays to the corresponding scheduled UTC instant; this handles overnight and multiday delays without wrapping them into the wrong date.

For each inbound flight and different destination, consider scheduled onward DL departures **45–240 minutes** after ATL arrival. Retain the earliest and latest eligible departure (one if identical). Sampling uses schedule fields only, before inspecting outcomes. We do not claim these combinations were sold, booked, available, compliant with airline minimum-connection rules, or taken by real passengers.

**Synthetic connection failure:** either leg canceled/diverted, OR actual inbound arrival + **30 minutes** transfer is later than actual outbound gate departure − **15 minutes** boarding cutoff. Equality is considered feasible. These times are research assumptions, not airline rules. A diversion is conservatively counted as failure, including diversions that eventually reach their destination.

**Synthetic disruption:** connection failure OR onward flight arrival more than **60 minutes late**. The same flight may occur in several itineraries, so itinerary records are not independent passenger observations. Outcomes do not model rebooking, baggage, missed meetings, downstream trips, or financial losses.

## Reproducibility

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm ci
python -m pytest -q
npm test
OPENBLAS_NUM_THREADS=1 python -m flightguard.train --output /tmp/flightguard-retrained
python tests/reproduce.py /tmp/flightguard-retrained
```

The clean CSV, frozen models, evaluation and full held-out replay are committed. Training needs no network. Python 3.11+ and Node 22 are used in CI. Direct dependencies are pinned, and the JS test dependency tree is locked. Numerical comparison allows tiny cross-platform floating-point differences; the local rerun exactly matched JSON artifacts.

To recollect official source data and rebuild:

```sh
python -m flightguard.data
OPENBLAS_NUM_THREADS=1 python -m flightguard.train
```

The collector reuses cached monthly ZIPs under `data/raw/`; otherwise it downloads around 83 MB total. Source ZIPs are not committed. To intentionally refresh an existing cache, move the old ZIPs elsewhere first. Compare new hashes against the committed manifest before treating revised data as the same benchmark. The clean CSV is the benchmark of record. The CLI may fail on network interruption or malformed downloads; it never substitutes invented data.

## Temporal evaluation

| Partition | Inbound local dates | Synthetic itineraries |
| --- | --- | ---: |
| Train | Jan 1–31, 2025 | 4,675 |
| Independent calibration | Feb 3–28, 2025 | 3,983 |
| Held-out evaluation | Mar 3–31, 2025 | 5,052 |
| Excluded boundary days | Feb 1–2 and Mar 1–2 | 598 |

Feature set: scheduled layover and inverse layover; sine/cosine of onward ATL departure hour; inbound origin-local weekend indicator; one-hot origin/destination. Two L2 logistic models fit January; separate February logistic calibrators fit each raw score. No actual delays, labels, cancellation flags, realized weather, flight IDs or final arrival outcomes enter features. Tests verify that changing outcome fields cannot affect features or candidate identities, and no flight identity crosses partitions. Actual completed outcome times from the earlier partition precede the next partition's start.

The feature set and regularization were fixed before evaluation. A timezone implementation correction changed the weekend definition from ATL-local to inbound-origin-local after an initial run; this was a semantic bug fix, not hyperparameter tuning. Both models were rerun with the corrected definition. Historical BTS records are revised reports, not point-in-time archived booking schedules, so this is retrospective replay rather than a certified booking-time backtest.

### Held-out results

| Failure model | Brier ↓ | Log loss ↓ | ROC AUC ↑ | Average precision ↑ |
| --- | ---: | ---: | ---: | ---: |
| Full schedule model + calibration | 0.04492 | 0.17615 | 0.78695 | 0.17983 |
| Layover-only model + calibration | **0.04451** | **0.17436** | **0.80192** | **0.20453** |
| Constant February prevalence | 0.04867 | 0.20349 | 0.50000 | 0.05107 |

March synthetic failure prevalence is **5.11%**. The full model's 10-bin ECE is **2.06 percentage points**. Separate disruption-model AUC is **0.65269**, Brier **0.09024**, prevalence **10.33%**, ECE **4.07 points**. Calibration is not perfect and risks generally overestimate March outcomes.

**The fuller model does not outperform the simpler layover baseline.** This is documented in the app, not hidden. Equal-weight daily Brier difference (full minus baseline) is +0.000466; a 1,000-replicate paired daily bootstrap gives approximately [0.000002, 0.000933]. With only 29 test days and shared flights, this is narrow-sample uncertainty, not proof of general superiority. Do not tune on this same test set in future iterations; add new time periods.

Among **1,503 same-inbound/destination groups** with two sampled options, choosing the shortest had 7.65% synthetic failure and a 509-minute mean total journey. Choosing lower modeled failure risk had 1.33% failure and a 620-minute mean journey. Both risk selection rules chose the same onward alternatives in this sample. This is largely a **111-minute buffer trade-off**, not free risk reduction, not a causal treatment estimate, and not evidence that a sophisticated model beats simply waiting longer.

## Verification and limitations

15 Python tests cover real-data hashes/counts, midnight, timezones, DST ambiguity/gaps, overnight arrival, missing outcomes, cancellation/diversion handling, transfer and disruption boundaries, candidate integrity, partition separation, feature leakage and evaluation recomputation. JavaScript matches **10,104 predictions** (both targets for every test itinerary), maximum absolute difference **2.22×10⁻¹⁶**. DOM-level tests exercise app rendering, filters, selection, shortlist persistence, outcome reveal, sensitivity and evidence panels. These are DOM emulation tests, not rendered-browser QA. The cloud preview could not open this static local server, so visual/responsive rendering and real-browser download behavior are **not verified**. Docker packaging is supplied but not run in this environment.

The app is static and self-contained after serving; Python's development HTTP server is only for local exploration. For production static hosting, deploy `web/` using your preferred static host or the included nginx container:

```sh
docker build -t flightguard .
docker run --rm -p 8080:80 flightguard
```

No public live app URL is claimed by this repository shipment. The published deliverable is runnable code, data, models, tests and documentation. The app intentionally rejects unsupported routes/hours/buffer ranges. It does not score today's airline schedules. Source coverage ends March 31, which truncates any onward candidate outside the source window. The narrow carrier/hub/season and schedule-only selection limit generalization.

## Repository guide

- `flightguard/data.py`: official-source ingestion, hashes, validation, UTC reconstruction.
- `flightguard/engine.py`: candidate sampling, target definitions, feature whitelist, portable inference.
- `flightguard/train.py`: train/calibrate/test, baselines, metrics and export.
- `web/`: complete static app and frozen artifacts.
- `tests/`: unit/data/leakage, parity, DOM and reproduction checks.
- `docs/MODEL_CARD.md`: intended use, risks, controls and next steps.
- `BUILD_PLAN.md`, `SHIP_STATUS.json`: sequential portfolio shipment checkpoint.

Original code is MIT licensed. BTS data remain attributed to the US DOT/BTS; the code license does not assert ownership over source records or third-party trademarks. No copied airline assets are used.
