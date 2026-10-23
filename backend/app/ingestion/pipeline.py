import os
import json
import glob
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, List, Any, Optional
import logging

from app.models.evidence import (
    Source, EvidenceRecord, ValidationResult, DataTransformation,
    FoodCommodity, FoodObservation,
    RespirationObservation, PostharvestStorageLimits, PostharvestGasTolerances,
    PackagingMaterial, MaterialBarrierObservation,
    MicrobialOrganism, MicrobialCardinalParameters, MicrobialGrowthKinetics,
    MicrobialGasInhibitionResponse, EvidenceClassification, VerificationStatus,
    GasSpecies, PropertyType, MissingnessStatus, ProcessingState, StructureType
)
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


# ============================================================
# DATASET NAME → cleaning_log / validation_results KEY MAPPING
# ============================================================
DATASET_KEY_MAP = {
    "usda_fdc_sample_foundation": "usda_fdc",
    "india_ifct_2017_composition": "india_ifct",
    "usda_handbook_66_respiration": "usda_handbook_66",
    "uc_davis_produce_facts": "uc_davis",
    "icar_iifpt_indian_postharvest": "indian_postharvest",
    "cirad_wur_packaging_dataset": "cirad_wur",
    "polyid_experimental_vs_predicted": "polyid",
    "manufacturer_tds_datasheets": "manufacturer_tds",
    "combase_microbial_kinetics": "combase",
}

SHORT_KEY_TO_LONG_MAP = {v: k for k, v in DATASET_KEY_MAP.items()}


class DataIngestionPipeline:
    def __init__(self, db: Session, base_dir: str = "../data/processed",
                 reference_dir: str = "../data/reference"):
        self.db = db
        self.base_dir = Path(base_dir)
        self.reference_dir = Path(reference_dir)
        if not self.base_dir.exists():
            root_candidate = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
            if root_candidate.exists():
                self.base_dir = root_candidate
                self.reference_dir = root_candidate.parent / "reference"
        self.stats = {
            "datasets_processed": 0,
            "total_input_records": 0,
            "total_inserted": 0,
            "total_skipped": 0,
            "validation_results_ingested": 0,
            "data_transformations_ingested": 0,
            "dataset_details": {},
            "entity_counts": {},
        }
        # In-memory tracking for linking reference artifacts
        self.dataset_evidence_map: Dict[str, List[EvidenceRecord]] = {}
        self.evidence_by_record_id: Dict[str, EvidenceRecord] = {}

        # Loaded lazily once
        self._cleaning_log: Optional[List[Dict]] = None
        self._validation_results: Optional[Dict] = None

    # ----------------------------------------------------------
    # Reference artifact loaders
    # ----------------------------------------------------------
    def _load_cleaning_log(self) -> List[Dict]:
        if self._cleaning_log is None:
            path = self.reference_dir / "cleaning_log.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._cleaning_log = json.load(f)
            else:
                self._cleaning_log = []
        return self._cleaning_log

    def _load_validation_results(self) -> Dict:
        if self._validation_results is None:
            path = self.reference_dir / "validation_results.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._validation_results = json.load(f)
            else:
                self._validation_results = {}
        return self._validation_results

    # ----------------------------------------------------------
    # Main entry point
    # ----------------------------------------------------------
    def run(self):
        files = glob.glob(str(self.base_dir / "**" / "*.json"), recursive=True)
        for file_path in files:
            self.process_file(file_path)

        # Ingest reference artifacts after evidence records exist
        self._ingest_validation_results()
        self._ingest_data_transformations()

        self.db.commit()

        # Collect entity counts
        self._collect_entity_counts()

        self.generate_report()
        return self.stats

    # ----------------------------------------------------------
    # File-level processing
    # ----------------------------------------------------------
    def process_file(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "source_metadata" not in data:
            logger.warning(f"Skipping {file_path} - Invalid format")
            return

        dataset_name = Path(file_path).stem
        short_key = DATASET_KEY_MAP.get(dataset_name, dataset_name)
        if dataset_name not in self.dataset_evidence_map:
            self.dataset_evidence_map[dataset_name] = []
        if short_key not in self.dataset_evidence_map:
            self.dataset_evidence_map[short_key] = []

        self.stats["dataset_details"][dataset_name] = {
            "source_count": 0,
            "inserted_count": 0,
            "duplicate_count": 0,
            "issues": [],
        }

        meta = data["source_metadata"]

        # 1. UPSERT Source
        source = self.upsert_source(meta)

        # 2. Extract literature_references from source_metadata if present
        lit_refs = meta.get("literature_references")

        # 3. Process Records based on type
        if "records" in data:
            self.process_records(dataset_name, source, data["records"], lit_refs)
        elif "materials" in data:
            self.process_materials(dataset_name, source, data["materials"], lit_refs)
        elif "datasheets" in data:
            self.process_materials(dataset_name, source, data["datasheets"], lit_refs)
        elif "experimental_observations" in data or "predicted_values" in data:
            self.process_polyid(dataset_name, source, data, lit_refs)

        self.stats["datasets_processed"] += 1

    # ----------------------------------------------------------
    # Source upsert
    # ----------------------------------------------------------
    def upsert_source(self, meta: Dict) -> Source:
        source_name = meta.get("source_name", meta.get("dataset_name", "Unknown Source"))
        url = meta.get("url")

        if url:
            source = self.db.query(Source).filter(
                (Source.url == url) | (Source.source_name == source_name)
            ).first()
        else:
            source = self.db.query(Source).filter(
                Source.source_name == source_name
            ).first()

        if not source:
            institution = (
                meta.get("institution")
                or meta.get("organization")
                or (", ".join(meta["institutions"]) if "institutions" in meta else None)
                or (", ".join(meta["institutional_authorities"]) if "institutional_authorities" in meta else None)
                or (", ".join(meta["manufacturers"]) if "manufacturers" in meta else None)
            )
            source = Source(
                source_name=source_name,
                institution=institution,
                url=url,
                dataset_type=meta.get("dataset_type"),
                license=meta.get("license"),
                governance_rule=meta.get("governance_rule"),
            )
            self.db.add(source)
            self.db.flush()
        return source

    # ----------------------------------------------------------
    # Evidence record creation (with idempotency)
    # ----------------------------------------------------------
    def create_evidence(
        self,
        source: Source,
        record_id: str,
        raw_payload: Dict,
        classification: EvidenceClassification,
        status: VerificationStatus,
        lit_refs: Any = None,
        synthetic_warning: Optional[str] = None,
        dataset_name: Optional[str] = None,
    ) -> EvidenceRecord:
        evidence = self.db.query(EvidenceRecord).filter_by(
            source_id=source.id,
            record_identifier_in_source=record_id,
        ).first()

        if not evidence:
            evidence = EvidenceRecord(
                source_id=source.id,
                record_identifier_in_source=record_id,
                evidence_classification=classification,
                verification_status=status,
                raw_json_payload=raw_payload,
                literature_references=lit_refs,
                synthetic_prediction_warning=synthetic_warning,
            )
            self.db.add(evidence)
            self.db.flush()

        # Cache for reference artifact linking
        if dataset_name:
            short_key = DATASET_KEY_MAP.get(dataset_name, dataset_name)
            self.dataset_evidence_map.setdefault(dataset_name, []).append(evidence)
            self.dataset_evidence_map.setdefault(short_key, []).append(evidence)
        self.evidence_by_record_id[record_id] = evidence

        return evidence

    # ----------------------------------------------------------
    # Generic record processing (food, postharvest, microbial)
    # ----------------------------------------------------------
    def process_records(self, dataset_name: str, source: Source,
                        records: List[Dict], lit_refs: Any = None):
        self.stats["dataset_details"][dataset_name]["source_count"] += len(records)
        self.stats["total_input_records"] += len(records)

        for idx, rec in enumerate(records):
            record_id = (
                rec.get("id")
                or rec.get("fdc_id")
                or rec.get("ifct_code")
                or rec.get("combase_id")
                or rec.get("commodity_id")
                or rec.get("commodity_name")
                or str(idx)
            )
            record_id = str(record_id)

            # Idempotency check
            if self.db.query(EvidenceRecord).filter_by(
                source_id=source.id,
                record_identifier_in_source=record_id,
            ).first():
                self.stats["dataset_details"][dataset_name]["duplicate_count"] += 1
                self.stats["total_skipped"] += 1
                continue

            evidence = self.create_evidence(
                source=source,
                record_id=record_id,
                raw_payload=rec,
                classification=EvidenceClassification.EXPERIMENTAL_LITERATURE_DATA,
                status=VerificationStatus.PARTIALLY_VERIFIED,
                lit_refs=lit_refs,
                dataset_name=dataset_name,
            )

            # Commodity Data
            if "commodity_name" in rec:
                commodity = self.upsert_commodity(rec)
                self.process_food_properties(evidence, commodity, rec)
                self.process_postharvest(evidence, commodity, rec)

            # Microbial Data
            if "organism_name" in rec:
                organism = self.upsert_organism(rec)
                self.process_microbial(evidence, organism, rec)

            self.stats["dataset_details"][dataset_name]["inserted_count"] += 1
            self.stats["total_inserted"] += 1

    # ----------------------------------------------------------
    # Material processing (CIRAD, Manufacturer TDS)
    # ----------------------------------------------------------
    def process_materials(self, dataset_name: str, source: Source,
                          materials: List[Dict], lit_refs: Any = None):
        self.stats["dataset_details"][dataset_name]["source_count"] += len(materials)
        self.stats["total_input_records"] += len(materials)

        for idx, mat in enumerate(materials):
            record_id = str(
                mat.get("material_id")
                or mat.get("datasheet_id")
                or mat.get("id")
                or mat.get("material_name")
                or idx
            )
            if self.db.query(EvidenceRecord).filter_by(
                source_id=source.id,
                record_identifier_in_source=record_id,
            ).first():
                self.stats["dataset_details"][dataset_name]["duplicate_count"] += 1
                self.stats["total_skipped"] += 1
                continue

            evidence = self.create_evidence(
                source, record_id, mat,
                EvidenceClassification.EXPERIMENTAL_LITERATURE_DATA,
                VerificationStatus.VERIFIED_EXTRACT,
                lit_refs=lit_refs,
                dataset_name=dataset_name,
            )

            material_db = self.upsert_material(mat)
            self.process_barrier(evidence, material_db, mat)
            self.stats["dataset_details"][dataset_name]["inserted_count"] += 1
            self.stats["total_inserted"] += 1

    # ----------------------------------------------------------
    # PolyID processing (experimental vs predicted separation)
    # ----------------------------------------------------------
    def process_polyid(self, dataset_name: str, source: Source,
                       data: Dict, lit_refs: Any = None):
        for key, cls, stat in [
            ("experimental_observations",
             EvidenceClassification.EXPERIMENTAL_LITERATURE_DATA,
             VerificationStatus.VERIFIED_EXTRACT),
            ("predicted_values",
             EvidenceClassification.MODEL_PREDICTED,
             VerificationStatus.PREDICTIVE_ONLY),
        ]:
            if key in data:
                items = data[key]
                self.stats["dataset_details"][dataset_name]["source_count"] += len(items)
                self.stats["total_input_records"] += len(items)

                for idx, item in enumerate(items):
                    record_id = item.get("polyid_exp_id") or item.get("polyid_pred_id") or f"polyid_{key}_{idx}"
                    if self.db.query(EvidenceRecord).filter_by(
                        source_id=source.id,
                        record_identifier_in_source=record_id,
                    ).first():
                        self.stats["dataset_details"][dataset_name]["duplicate_count"] += 1
                        self.stats["total_skipped"] += 1
                        continue

                    item_lit = lit_refs
                    synthetic_warning = None

                    if cls == EvidenceClassification.MODEL_PREDICTED:
                        synthetic_warning = item.get("warning_flag")
                        item_lit = {
                            "model_doi": item.get("model_doi"),
                            "qsar_algorithm": item.get("qsar_algorithm"),
                            "model_training_r2": item.get("model_training_r2"),
                            "prediction_confidence": item.get("prediction_confidence"),
                        }
                    elif cls == EvidenceClassification.EXPERIMENTAL_LITERATURE_DATA:
                        lab_ref = (
                            item.get("experimental_otr", {}).get("laboratory_reference")
                            or item.get("experimental_wvtr", {}).get("laboratory_reference")
                        )
                        if lab_ref:
                            item_lit = {"laboratory_reference": lab_ref}

                    evidence = self.create_evidence(
                        source, record_id, item, cls, stat,
                        lit_refs=item_lit,
                        synthetic_warning=synthetic_warning,
                        dataset_name=dataset_name,
                    )
                    mat = self.upsert_material(item)
                    self.process_barrier(evidence, mat, item)
                    self.stats["dataset_details"][dataset_name]["inserted_count"] += 1
                    self.stats["total_inserted"] += 1

    # ===========================================================
    # UPSERTS
    # ===========================================================
    def upsert_commodity(self, rec: Dict) -> FoodCommodity:
        name = rec.get("commodity_name", "Unknown")
        commodity = self.db.query(FoodCommodity).filter_by(commodity_name=name).first()
        if not commodity:
            state = None
            ps = rec.get("processing_state", "").upper()
            if ps in ["RAW", "FRESH_CUT", "PROCESSED"]:
                state = ProcessingState(ps)

            commodity = FoodCommodity(
                commodity_name=name,
                scientific_name=rec.get("scientific_name"),
                vernacular_name=rec.get("indian_name") or rec.get("indian_vernacular_name"),
                food_category=rec.get("food_category"),
                origin_region=rec.get("origin_region"),
                processing_state=state,
            )
            self.db.add(commodity)
            self.db.flush()
        return commodity

    def upsert_organism(self, rec: Dict) -> MicrobialOrganism:
        name = rec.get("organism_name", "Unknown")
        organism = self.db.query(MicrobialOrganism).filter_by(organism_name=name).first()
        if not organism:
            organism = MicrobialOrganism(
                organism_name=name,
                organism_type=rec.get("organism_type"),
            )
            self.db.add(organism)
            self.db.flush()
        return organism

    def upsert_material(self, rec: Dict) -> PackagingMaterial:
        name = (
            rec.get("material_name")
            or rec.get("polymer_name")
            or rec.get("polymer_type")
            or "Unknown Material"
        )
        mat = self.db.query(PackagingMaterial).filter_by(material_name=name).first()
        if not mat:
            st = None
            st_raw = (rec.get("structure_type") or "").upper()
            if st_raw in ["MONOLAYER", "MULTILAYER", "COATED"]:
                st = StructureType(st_raw)

            mat = PackagingMaterial(
                material_name=name,
                brand_grade=rec.get("brand_grade"),
                structure_type=st,
                layer_sequence=rec.get("layer_sequence", []),
            )
            self.db.add(mat)
            self.db.flush()
        return mat

    # ===========================================================
    # FOOD PROPERTIES
    # ===========================================================
    def process_food_properties(self, evidence: EvidenceRecord,
                                commodity: FoodCommodity, rec: Dict):
        for section in ["proximate_composition", "physicochemical_properties"]:
            if section in rec:
                for k, v in rec[section].items():
                    if isinstance(v, dict) and "value" in v:
                        ms = None
                        if v.get("missingness_status"):
                            try:
                                ms = MissingnessStatus(v["missingness_status"])
                            except ValueError:
                                pass

                        obs = FoodObservation(
                            evidence_id=evidence.id,
                            commodity_id=commodity.id,
                            property_name=k,
                            original_value=str(v.get("original_value", "")),
                            value=v.get("value"),
                            value_min=v.get("value_min"),
                            value_max=v.get("value_max"),
                            operator=v.get("operator"),
                            is_range=v.get("is_range", False),
                            missingness_status=ms,
                        )
                        self.db.add(obs)

    # ===========================================================
    # POSTHARVEST (respiration, storage limits, EMAP tolerances)
    # ===========================================================
    def process_postharvest(self, evidence: EvidenceRecord,
                            commodity: FoodCommodity, rec: Dict):
        # ----- RESPIRATION -----
        resp_key = None
        for k in ["respiration_profile", "respiration_measurements", "respiration_kinetics"]:
            if k in rec:
                resp_key = k
                break

        if resp_key:
            resp_list = rec[resp_key]
            if isinstance(resp_list, list):
                for rm in resp_list:
                    self._ingest_respiration_measurement(evidence, commodity, rm)

        # ----- POSTHARVEST STORAGE LIMITS -----
        lims_key = None
        for k in ["physiological_limits", "recommended_storage_conditions", "postharvest_storage_limits"]:
            if k in rec:
                lims_key = k
                break
        if lims_key:
            lims = rec[lims_key]
            if isinstance(lims, dict):
                obs = PostharvestStorageLimits(
                    evidence_id=evidence.id,
                    commodity_id=commodity.id,
                    optimum_temperature_c=lims.get("optimum_temperature_c") or lims.get("storage_temperature_min_c"),
                    optimum_rh_percent=lims.get("optimum_rh_percent") or lims.get("relative_humidity_min_percent"),
                    chilling_injury_threshold_c=lims.get("chilling_threshold_c") or lims.get("chilling_injury_threshold_c"),
                    ambient_shelf_life_days=(
                        lims.get("approximate_shelf_life_days")
                        or lims.get("ambient_shelf_life_days")
                        or lims.get("air_refrigerated_shelf_life_days")
                    ),
                    map_shelf_life_days=(
                        lims.get("map_shelf_life_days")
                        or lims.get("map_refrigerated_shelf_life_days")
                    ),
                )
                self.db.add(obs)

        # ----- EMAP GAS TOLERANCES -----
        tol_key = None
        for k in ["emap_gas_tolerances", "emap_tolerances"]:
            if k in rec:
                tol_key = k
                break

        if tol_key:
            tol = rec[tol_key]
            if isinstance(tol, dict):
                obs = PostharvestGasTolerances(
                    evidence_id=evidence.id,
                    commodity_id=commodity.id,
                    target_o2_min_percent=tol.get("target_o2_min_percent"),
                    target_o2_max_percent=tol.get("target_o2_max_percent"),
                    target_co2_min_percent=tol.get("target_co2_min_percent"),
                    target_co2_max_percent=tol.get("target_co2_max_percent"),
                    min_o2_fermentation_limit_percent=tol.get("min_o2_fermentation_limit_percent"),
                    max_co2_injury_limit_percent=tol.get("max_co2_injury_limit_percent"),
                )
                self.db.add(obs)

        # UC Davis physiological_limits also contains EMAP fields
        if lims_key == "physiological_limits":
            lims = rec[lims_key]
            emap_o2_min = lims.get("emap_o2_min_percent")
            if emap_o2_min is not None:
                obs = PostharvestGasTolerances(
                    evidence_id=evidence.id,
                    commodity_id=commodity.id,
                    target_o2_min_percent=emap_o2_min,
                    target_o2_max_percent=lims.get("emap_o2_max_percent"),
                    target_co2_min_percent=lims.get("emap_co2_min_percent"),
                    target_co2_max_percent=lims.get("emap_co2_max_percent"),
                    max_co2_injury_limit_percent=lims.get("co2_injury_threshold_percent"),
                )
                self.db.add(obs)

    def _ingest_respiration_measurement(self, evidence: EvidenceRecord,
                                        commodity: FoodCommodity, rm: Dict):
        temp = rm.get("temperature_c")
        temp_parsed = rm.get("temperature_c_parsed", {})
        temp_value = temp_parsed.get("value") if temp_parsed else temp

        rq = rm.get("respiratory_quotient_rq_typical") or rm.get("respiratory_quotient_rq")

        # ---- O2 ----
        o2_min_raw = rm.get("o2_consumption_rate_min_mg_kg_h")
        o2_max_raw = rm.get("o2_consumption_rate_max_mg_kg_h")
        o2_min_parsed = rm.get("o2_consumption_rate_min_mg_kg_h_parsed", {})
        o2_max_parsed = rm.get("o2_consumption_rate_max_mg_kg_h_parsed", {})

        if o2_min_raw is not None or o2_max_raw is not None or o2_min_parsed or o2_max_parsed:
            rate_min = o2_min_parsed.get("value", o2_min_raw) if o2_min_parsed else o2_min_raw
            rate_max = o2_max_parsed.get("value", o2_max_raw) if o2_max_parsed else o2_max_raw
            has_range = (rate_min is not None and rate_max is not None and rate_min != rate_max)

            obs = RespirationObservation(
                evidence_id=evidence.id,
                commodity_id=commodity.id,
                gas_species=GasSpecies.O2,
                rate_value=rate_min,
                rate_min=rate_min,
                rate_max=rate_max,
                is_range=has_range,
                operator="range" if has_range else "=",
                temperature_c_value=temp_value,
                respiratory_quotient=rq,
                original_unit="mg_kg_h",
                canonical_unit="mg/kg·h",
            )
            self.db.add(obs)

        # ---- CO2 ----
        co2_min_raw = rm.get("co2_production_rate_min_mg_kg_h")
        co2_max_raw = rm.get("co2_production_rate_max_mg_kg_h")
        co2_min_parsed = rm.get("co2_production_rate_min_mg_kg_h_parsed", {})
        co2_max_parsed = rm.get("co2_production_rate_max_mg_kg_h_parsed", {})

        if co2_min_raw is not None or co2_max_raw is not None or co2_min_parsed or co2_max_parsed:
            rate_min = co2_min_parsed.get("value", co2_min_raw) if co2_min_parsed else co2_min_raw
            rate_max = co2_max_parsed.get("value", co2_max_raw) if co2_max_parsed else co2_max_raw
            has_range = (rate_min is not None and rate_max is not None and rate_min != rate_max)

            obs = RespirationObservation(
                evidence_id=evidence.id,
                commodity_id=commodity.id,
                gas_species=GasSpecies.CO2,
                rate_value=rate_min,
                rate_min=rate_min,
                rate_max=rate_max,
                is_range=has_range,
                operator="range" if has_range else "=",
                temperature_c_value=temp_value,
                respiratory_quotient=rq,
                original_unit="mg_kg_h",
                canonical_unit="mg/kg·h",
            )
            self.db.add(obs)

    # ===========================================================
    # MICROBIAL (cardinal, kinetics, gas inhibition)
    # ===========================================================
    def process_microbial(self, evidence: EvidenceRecord,
                          organism: MicrobialOrganism, rec: Dict):
        if "cardinal_parameters" in rec:
            cp = rec["cardinal_parameters"]
            obs = MicrobialCardinalParameters(
                evidence_id=evidence.id,
                organism_id=organism.id,
                temperature_min_c=cp.get("temperature_min_c"),
                temperature_opt_c=cp.get("temperature_opt_c"),
                temperature_max_c=cp.get("temperature_max_c"),
                water_activity_aw_min=cp.get("water_activity_aw_min"),
                ph_min=cp.get("ph_min"),
                ph_opt=cp.get("ph_opt"),
                ph_max=cp.get("ph_max"),
            )
            self.db.add(obs)

        if "growth_kinetics" in rec:
            for gk in rec["growth_kinetics"]:
                obs = MicrobialGrowthKinetics(
                    evidence_id=evidence.id,
                    organism_id=organism.id,
                    temperature_c_value=gk.get("temperature_c"),
                    ph_value=gk.get("ph"),
                    water_activity_aw_value=gk.get("water_activity_aw"),
                    specific_growth_rate_mu_max_1_h=gk.get("specific_growth_rate_mu_max_1_h"),
                    lag_time_lambda_h=gk.get("lag_time_lambda_h"),
                    atmosphere_condition=gk.get("atmosphere"),
                )
                self.db.add(obs)

        if "gas_inhibition_responses" in rec:
            gi = rec["gas_inhibition_responses"]
            if isinstance(gi, dict):
                obs = MicrobialGasInhibitionResponse(
                    evidence_id=evidence.id,
                    organism_id=organism.id,
                    co2_sensitivity=gi.get("co2_sensitivity"),
                    minimum_co2_inhibition_percent=gi.get("minimum_co2_inhibition_percent"),
                    notes=gi.get("notes"),
                )
                self.db.add(obs)

    # ===========================================================
    # MATERIAL BARRIERS
    # ===========================================================
    def process_barrier(self, evidence: EvidenceRecord,
                        material: PackagingMaterial, rec: Dict):
        # 1. CIRAD / TDS style: list of dicts in barrier_measurements or barrier_profiles
        barrier_list = rec.get("barrier_measurements") or rec.get("barrier_profiles") or []
        for b in barrier_list:
            prop_str = b.get("property", "").upper()
            pt_enum = None
            if "OTR" in prop_str:
                pt_enum = PropertyType.OTR
            elif "CO2TR" in prop_str:
                pt_enum = PropertyType.CO2TR
            elif "WVTR" in prop_str:
                pt_enum = PropertyType.WVTR

            if pt_enum:
                v_parsed = b.get("value_parsed", {})
                obs = MaterialBarrierObservation(
                    evidence_id=evidence.id,
                    material_id=material.id,
                    property_type=pt_enum,
                    original_value=str(v_parsed.get("original_value", b.get("value"))),
                    value=v_parsed.get("value", b.get("value")),
                    value_min=v_parsed.get("value_min"),
                    value_max=v_parsed.get("value_max"),
                    operator=v_parsed.get("operator"),
                    is_range=v_parsed.get("is_range", False),
                    original_unit=b.get("unit"),
                    test_temperature_c_value=b.get("test_temperature_c"),
                    test_rh_percent_value=b.get("test_rh_percent"),
                    thickness_value=(
                        rec.get("measured_thickness_um")
                        or rec.get("nominal_thickness_um")
                        or b.get("thickness_microns")
                    ),
                    test_method=b.get("test_standard"),
                )
                self.db.add(obs)

        # 2. PolyID style: experimental distinct dict keys
        for key in [
            "experimental_otr", "experimental_co2tr", "experimental_wvtr",
        ]:
            if key in rec:
                b = rec[key]
                prop_str = key.split("_")[1].upper()
                pt_enum = getattr(PropertyType, prop_str)
                obs = MaterialBarrierObservation(
                    evidence_id=evidence.id,
                    material_id=material.id,
                    property_type=pt_enum,
                    value=b.get("value"),
                    original_unit=b.get("unit"),
                    test_temperature_c_value=b.get("test_temperature_c"),
                    test_rh_percent_value=b.get("test_rh_percent"),
                    thickness_value=rec.get("measured_thickness_um"),
                    test_method=b.get("test_standard"),
                )
                self.db.add(obs)

        # 3. PolyID style: QSAR predicted property
        if "predicted_property" in rec and "predicted_value" in rec:
            prop_str = str(rec.get("predicted_property", "")).upper()
            pt_enum = None
            if "OTR" in prop_str:
                pt_enum = PropertyType.OTR
            elif "CO2TR" in prop_str:
                pt_enum = PropertyType.CO2TR
            elif "WVTR" in prop_str:
                pt_enum = PropertyType.WVTR

            if pt_enum:
                val_min = rec.get("uncertainty_range_lower")
                val_max = rec.get("uncertainty_range_upper")
                has_range = val_min is not None and val_max is not None
                obs = MaterialBarrierObservation(
                    evidence_id=evidence.id,
                    material_id=material.id,
                    property_type=pt_enum,
                    value=rec.get("predicted_value"),
                    value_min=val_min,
                    value_max=val_max,
                    is_range=has_range,
                    operator="range" if has_range else "=",
                    original_unit=rec.get("unit"),
                    canonical_unit=rec.get("unit"),
                    thickness_value=rec.get("reference_thickness_um"),
                    test_method=rec.get("qsar_algorithm"),
                )
                self.db.add(obs)

    # ===========================================================
    # ValidationResult ingestion
    # ===========================================================
    def _ingest_validation_results(self):
        """Ingest M4 validation summary into ValidationResult rows."""
        vr_data = self._load_validation_results()
        if not vr_data:
            return

        for short_key, vr in vr_data.items():
            dataset = vr.get("dataset", short_key)

            # Idempotency check
            existing = self.db.query(ValidationResult).filter(
                ValidationResult.dataset == dataset
            ).first()
            if existing:
                continue

            # Look up evidence record belonging to this specific dataset
            evidence_records = self.dataset_evidence_map.get(short_key) or self.dataset_evidence_map.get(
                SHORT_KEY_TO_LONG_MAP.get(short_key, "")
            )

            # Fallback query if not in memory map
            if not evidence_records:
                long_name = SHORT_KEY_TO_LONG_MAP.get(short_key)
                for src in self.db.query(Source).all():
                    # Match dataset name or tokens
                    if (long_name and long_name in src.source_name.lower()) or (short_key in src.source_name.lower()):
                        evidence_records = self.db.query(EvidenceRecord).filter_by(source_id=src.id).all()
                        if evidence_records:
                            break

            evidence_id = evidence_records[0].id if evidence_records else None
            if evidence_id is None:
                continue

            obs = ValidationResult(
                evidence_id=evidence_id,
                dataset=dataset,
                field="*",
                rule="M4_DATASET_VALIDATION",
                status="VALID" if vr.get("invalid_records", 0) == 0 else "INVALID",
                severity="INFO" if vr.get("invalid_records", 0) == 0 else "ERROR",
                message=(
                    f"M4 validation: {vr.get('valid_records', 0)}/{vr.get('total_records', 0)} valid, "
                    f"{vr.get('records_with_warnings', 0)} warnings, "
                    f"{vr.get('invalid_records', 0)} invalid"
                ),
                original_value=json.dumps(vr),
            )
            self.db.add(obs)
            self.stats["validation_results_ingested"] += 1

    # ===========================================================
    # DataTransformation ingestion
    # ===========================================================
    def _ingest_data_transformations(self):
        """Ingest M4 cleaning_log.json into DataTransformation rows."""
        cleaning_log = self._load_cleaning_log()
        if not cleaning_log:
            return

        for entry in cleaning_log:
            dataset_short = entry.get("dataset", "")
            record_id = str(entry.get("record_id", ""))
            field = entry.get("field", "")

            # Idempotency check
            existing = self.db.query(DataTransformation).filter(
                DataTransformation.field == field,
                DataTransformation.rule_id == entry.get("rule_id"),
                DataTransformation.original_value == str(entry.get("original_value", "")),
            ).first()
            if existing:
                continue

            # Find matching evidence record by cached ID or DB query
            evidence = self.evidence_by_record_id.get(record_id)
            if not evidence:
                evidence = self.db.query(EvidenceRecord).filter(
                    EvidenceRecord.record_identifier_in_source == record_id
                ).first()

            if evidence is None:
                continue

            dt = DataTransformation(
                evidence_id=evidence.id,
                field=field,
                original_value=str(entry.get("original_value", "")),
                transformed_value=str(entry.get("transformed_value", "")),
                transformation_type=entry.get("transformation_type"),
                rule_id=entry.get("rule_id"),
            )
            self.db.add(dt)
            self.stats["data_transformations_ingested"] += 1

    # ===========================================================
    # Entity count collection
    # ===========================================================
    def _collect_entity_counts(self):
        from app.models.evidence import (
            Source as SourceModel, EvidenceRecord as ERModel,
            ValidationResult as VRModel, DataTransformation as DTModel,
            FoodCommodity as FCModel, FoodObservation as FOModel,
            RespirationObservation as ROModel,
            PostharvestStorageLimits as PSLModel,
            PostharvestGasTolerances as PGTModel,
            PackagingMaterial as PMModel,
            MaterialBarrierObservation as MBOModel,
            MicrobialOrganism as MOModel,
            MicrobialCardinalParameters as MCPModel,
            MicrobialGrowthKinetics as MGKModel,
            MicrobialGasInhibitionResponse as MGIRModel,
        )
        self.stats["entity_counts"] = {
            "Source": self.db.query(SourceModel).count(),
            "EvidenceRecord": self.db.query(ERModel).count(),
            "ValidationResult": self.db.query(VRModel).count(),
            "DataTransformation": self.db.query(DTModel).count(),
            "FoodCommodity": self.db.query(FCModel).count(),
            "FoodObservation": self.db.query(FOModel).count(),
            "RespirationObservation": self.db.query(ROModel).count(),
            "PostharvestStorageLimits": self.db.query(PSLModel).count(),
            "PostharvestGasTolerances": self.db.query(PGTModel).count(),
            "PackagingMaterial": self.db.query(PMModel).count(),
            "MaterialBarrierObservation": self.db.query(MBOModel).count(),
            "MicrobialOrganism": self.db.query(MOModel).count(),
            "MicrobialCardinalParameters": self.db.query(MCPModel).count(),
            "MicrobialGrowthKinetics": self.db.query(MGKModel).count(),
            "MicrobialGasInhibitionResponse": self.db.query(MGIRModel).count(),
        }

    # ===========================================================
    # Report generation
    # ===========================================================
    def generate_report(self):
        report_path = self.reference_dir / "m5b3_ingestion_reconciliation.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2)
