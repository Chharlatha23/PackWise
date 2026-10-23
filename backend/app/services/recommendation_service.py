"""
Recommendation Service for AI-Food-Packaging-Optimizer.

Orchestrates the end-to-end scientific packaging recommendation pipeline:
USER INPUT
    ↓
Phase 3 Property Inference
    ↓
Phase 4 Scientific Requirement Engine
    ↓
M6-B2A Candidate Construction
    ↓
M9/M10 Inverse-Design Search Engine Layer (Deterministic Baseline or Intelligent Adaptive Engine)
    ↓
RECOMMENDATION RESPONSE

Enforces strict scientific boundaries:
- NO scalar ranking or 'best material' score.
- NO UNKNOWN -> FEASIBLE conversion.
- NO midpoint collapse of objective intervals.
- Preserves exact Pareto front sets.
- Returns explicit empty Pareto front if no candidates are feasible.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.evidence import PackagingMaterial
from app.ingestion.pipeline import DataIngestionPipeline

from app.schemas.packaging_request import PackagingRequest
from app.schemas.recommendation import RecommendationResponse, CandidateEvaluationSummary
from app.schemas.optimization import (
    OptimizationInputEnvelope,
    PackageGeometry,
    SolverConfiguration,
    OptimizationExecutionTier
)
from app.schemas.candidate_feasibility import FilteringResult
from scientific_engine.inference.engine import PropertyInferenceEngine
from scientific_engine.physics.requirements import PackagingRequirementEngine
from scientific_engine.optimization.candidate_builder import CandidateBuilder
from scientific_engine.optimization.search_engine import (
    AbstractInverseDesignSearchEngine,
    DeterministicEnumerationSearchEngine,
    IntelligentInverseDesignSearchEngine,
    AISurrogatePrioritizedSearchEngine
)


class RecommendationService:
    """End-to-end orchestration service for scientific food packaging recommendations."""

    def __init__(
        self,
        search_engine: Optional[AbstractInverseDesignSearchEngine] = None,
        search_engine_type: Optional[str] = None
    ):
        self.inference_engine = PropertyInferenceEngine()
        self.requirement_engine = PackagingRequirementEngine()
        
        if search_engine:
            self.search_engine = search_engine
        elif search_engine_type in ("ai_surrogate_prioritized", "m11", "surrogate_prioritized"):
            self.search_engine = AISurrogatePrioritizedSearchEngine()
        elif search_engine_type == "intelligent":
            self.search_engine = IntelligentInverseDesignSearchEngine()
        else:
            self.search_engine = DeterministicEnumerationSearchEngine()

    def generate_recommendation(
        self,
        request: PackagingRequest,
        db: Session,
        search_engine_type: Optional[str] = None
    ) -> RecommendationResponse:
        """
        Execute full scientific pipeline from request to Pareto recommendation response.
        """
        start_time = time.time()
        run_id = f"run-{uuid.uuid4().hex[:12]}"

        # Resolve active search engine instance for this recommendation run
        active_engine = self.search_engine
        if search_engine_type in ("ai_surrogate_prioritized", "m11", "surrogate_prioritized"):
            active_engine = AISurrogatePrioritizedSearchEngine()
        elif search_engine_type == "intelligent":
            active_engine = IntelligentInverseDesignSearchEngine()
        elif search_engine_type == "deterministic_exhaustive":
            active_engine = DeterministicEnumerationSearchEngine()

        # ------------------------------------------------------------------
        # 0. Ensure database schema and ingested evidence exist
        # ------------------------------------------------------------------
        try:
            Base.metadata.create_all(bind=db.get_bind())
        except Exception:
            pass

        try:
            has_materials = db.query(PackagingMaterial).first() is not None
        except Exception:
            has_materials = False

        if not has_materials:
            pipeline = DataIngestionPipeline(db)
            pipeline.run()

        # ------------------------------------------------------------------
        # 1. Phase 3 Property Inference
        # ------------------------------------------------------------------
        inference_profile = self.inference_engine.infer_profile(request)

        # ------------------------------------------------------------------
        # 2. Phase 4 Scientific Requirement Engine
        # ------------------------------------------------------------------
        requirement_envelope = self.requirement_engine.evaluate_requirements(
            request=request,
            inference_profile=inference_profile,
            product_mass_kg=request.product_mass_kg,
            package_area_m2=request.package_surface_area_m2
        )

        # ------------------------------------------------------------------
        # 3. M6-B2A Candidate Construction
        # ------------------------------------------------------------------
        builder = CandidateBuilder(db)
        candidates = builder.build_candidates()

        # ------------------------------------------------------------------
        # 4. Construct OptimizationInputEnvelope for Search Engine Layer
        # ------------------------------------------------------------------
        geometry = PackageGeometry(
            surface_area_m2=request.package_surface_area_m2,
            headspace_volume_cm3=request.package_headspace_volume_cm3,
            product_mass_kg=request.product_mass_kg
        )

        filtering_result = FilteringResult(
            commodity=request.commodity,
            total_candidates_evaluated=len(candidates)
        )

        input_envelope = OptimizationInputEnvelope(
            optimization_run_id=run_id,
            commodity=request.commodity,
            target_shelf_life_days=request.target_shelf_life_days,
            storage_temperature_c=request.storage_temperature_c,
            relative_humidity_percent=request.relative_humidity_percent,
            package_geometry=geometry,
            packaging_requirement_envelope=requirement_envelope,
            filtering_result=filtering_result,
            eligible_candidate_materials=candidates,
            active_objectives=["f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"],
            solver_configuration=SolverConfiguration(execution_tier=OptimizationExecutionTier.LATTICE_LOOKUP)
        )

        # ------------------------------------------------------------------
        # 5. Execute M9 / M10 Inverse-Design Search Engine Layer
        # ------------------------------------------------------------------
        search_result = active_engine.search_with_summary(input_envelope)

        execution_time_ms = (time.time() - start_time) * 1000.0

        return RecommendationResponse(
            recommendation_run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request=request,
            inference_profile=inference_profile,
            requirement_envelope=requirement_envelope,
            total_candidates_evaluated=search_result.total_candidates_evaluated,
            feasible_candidates_count=search_result.feasible_candidates_count,
            infeasible_candidates_count=search_result.infeasible_candidates_count,
            unknown_candidates_count=search_result.unknown_candidates_count,
            pareto_front=search_result.pareto_front,
            candidate_summaries=search_result.candidate_summaries,
            all_warnings=search_result.all_warnings,
            traceability_log=requirement_envelope.traceability_log,
            pipeline_explainability=search_result.pipeline_explainability
        )
