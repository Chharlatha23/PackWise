# Operational Empirical-Trial Protocol Template

## 1. Objective and Scope
- **Commodity:** [e.g., Strawberry, Fresh-Cut Apple]
- **Variety:** [e.g., Chandler]
- **Purpose:** Record actual food-packaging shelf-life experimental observations for ingestion into the AI-Food-Packaging-Optimizer.

## 2. Pre-Trial Readiness & Required Decisions (Approval Needed)
- **Endpoint Definition**: What is the strict operational endpoint determining shelf-life failure? [e.g., moisture_limit, microbial_threshold > 6.0 log10 CFU/g, sensory_score < 3]. *Must be justified for the selected commodity and approved by a domain expert before trial.*
- **Storage Conditions**: 
  - Target Temperature (°C): [Value or Ambient]
  - Target Relative Humidity (%): [Value or Ambient]
  - *Note: Continuous environmental trajectories (T, RH) MUST be recorded. Do not rely solely on setpoints.*
- **Packaging Material**: [e.g., LDPE, PET/PE_Laminate]

## 3. Provenance and Lab Identification
- **Laboratory/Operator ID:** 
- **Instrument IDs:**
- **Calibration Info:** 

## 4. Materials and Methodology
- Initial mass (kg):
- Initial moisture content (g H2O / g dry solid):
- Initial water activity (aw):
- Measured film thickness (um):
- Measured OTR/WVTR (if applicable):
- Headspace volume (m3) and Initial Gas %: 

## 5. Sampling and Observation Frequency
- **Measurement intervals:** 
- **Replicate plan:** [e.g., 3 replicates per timepoint]
- **Uncertainty reporting:** [e.g., standard_error, expanded_u95]

## 6. End of Trial
- Ensure strict adherence to the defined endpoint.
- Do NOT convert actual trajectories into Mean Kinetic Temperature.
- Do NOT assume that every recorded outcome is directly comparable with the offline Q10 `SHELF_LIFE_EST` reference.
