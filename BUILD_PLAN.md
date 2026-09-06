# FlightGuard build plan

Project 2 of 6. Public repositories authorized. ResearchRadar shipped September 5, 2026.

- [x] Audit BTS source, coverage, timestamps, and synthetic-outcome definition.
- [x] Download and hash January–March 2025 BTS archives; clean selected flights.
- [x] Construct same-carrier ATL connections using schedule fields only.
- [x] Train January models, calibrate February, evaluate March with boundary embargoes.
- [x] Build historical comparison UI, explanations, saved shortlist and export.
- [x] Test timezones, overnight dates, cancellation, leakage, calibration and portable inference.
- [x] Document limitations; package reproducible CLI, Docker and CI.
- [x] Publish prasanaydoshi/FlightGuard and read back files and CI evidence.

Do not start InspectIQ until FlightGuard is verified shipped, and never ship two projects on one Toronto calendar day. Remaining order: InspectIQ, ScentCompass, DiveKit, PilotDeck. Each needs source audit, data/schema, engine, app, meaningful tests/evaluation, reproducibility/docs/CI, and separate public GitHub publication/read-back. Preserve the scope and safety requirements in the daily task.

Shipped PUBLIC September 6, 2026: https://github.com/prasanaydoshi/FlightGuard . All 32 remote files byte-matched the local verified build at commit `1d90e8a9b11d0367f87b4ccaff6e41778c167b92`. GitHub Actions run `34023888141` passed Python tests, portable inference, DOM UI checks, and deterministic retraining. InspectIQ is next, no earlier than September 7, 2026 Toronto time. Browser visual QA and Docker runtime remain unverified and are explicitly documented.
