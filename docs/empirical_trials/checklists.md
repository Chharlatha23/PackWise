# Operational Empirical-Trial Checklists

## 1. Pre-Trial Readiness Checklist (Requires Approval)
- [ ] **Endpoint Definition Approved:** Exact operational endpoint definition (e.g., specific microbial limit, moisture limit) is defined and justified for the selected commodity. NO arbitrary/universal endpoints.
- [ ] **Protocol ID Assigned:** The protocol is registered and a unique ID is assigned.
- [ ] **Instrumentation Validated:** Environmental loggers for continuous T/RH trajectories are calibrated and installed. 
- [ ] **Data Status Acknowledged:** Experimenters acknowledge that data will be tagged strictly as `REAL_EMPIRICAL`. No physics-generated records or AI predictions will be treated as empirical observations.

## 2. In-Trial Recording Checklist
- [ ] **Food Batch & Specification:** Record commodity, variety, product form, initial mass, water activity, and batch ID.
- [ ] **Packaging Specification:** Record material, measured thickness (do not use nominal thickness if measured is available), surface area, headspace volume, and film batch ID.
- [ ] **Storage Conditions:** Log continuous temperature and relative humidity trajectories. Do NOT silently replace actual conditions with target setpoints. Do NOT convert into Mean Kinetic Temperature.
- [ ] **Observations:** Record each time-series observation with a timestamp, measurement type, value, unit, replicate ID, and measurement uncertainty where applicable.
- [ ] **Provenance:** Record operator/lab ID, instrument IDs, and calibration provenance.

## 3. Post-Trial Validation Checklist (Before Ingestion)
- [ ] **Gate A (Identity):** `trial_id` and `protocol_id` are present.
- [ ] **Gate B (Units):** All time-series observations have physical units.
- [ ] **Gate C (Physical Validity):** Water activity is between 0.0 and 1.0; target RH is between 0.0 and 100.0.
- [ ] **Gate D (Temporal Consistency):** Time-series observations are in chronological order without negative elapsed times.
- [ ] **Gate E (Environmental Completeness):** Storage environment contains either continuous measured trajectories or documented target setpoints for both Temperature and RH.
- [ ] **Gate F (Replicate Integrity):** Time-series observations possess replicate identifiers.
- [ ] **Gate G (Provenance Completeness):** `operator_or_lab_id` and `creation_timestamp` are documented.
- [ ] **Gate H (Endpoint Definition):** A strict protocol-specific endpoint definition is provided for the observed shelf-life outcome. No null endpoints.
