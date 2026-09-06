# FlightGuard build plan

Project 2 of 6. Public repositories authorized. ResearchRadar shipped September 5, 2026.

- [x] Audit BTS source, coverage, timestamps, and synthetic-outcome definition.
- [ ] Download and hash January–March 2025 BTS archives; clean selected flights.
- [ ] Construct same-carrier ATL connections using schedule fields only.
- [ ] Train January models, calibrate February, evaluate March with boundary embargoes.
- [ ] Build historical comparison UI, explanations, saved shortlist and export.
- [ ] Test timezones, overnight dates, cancellation, leakage, calibration and portable inference.
- [ ] Document limitations; package reproducible CLI, Docker and CI.
- [ ] Publish prasanaydoshi/FlightGuard and read back files and CI evidence.

Do not start InspectIQ until FlightGuard is verified shipped, and never ship two projects on one Toronto calendar day. Remaining order: InspectIQ, ScentCompass, DiveKit, PilotDeck. Each needs source audit, data/schema, engine, app, meaningful tests/evaluation, reproducibility/docs/CI, and separate public GitHub publication/read-back. Preserve the scope and safety requirements in the daily task.
