"""
Phase 3A — Layer 5 — Issue 8: Benchmark Harness Adapters for Inverse-Design Search Engines.

Provides algorithm-neutral benchmark adapter implementations for M9 (Deterministic Baseline),
M10 (Adaptive Baseline), and M11 (AI-Surrogate Prioritized Search Engine).

STRICT ARCHITECTURAL BOUNDARIES:
- ZERO modification to M9, M10, or M11 scientific search policies or candidate selection rules.
- Captures common benchmark telemetry under identical versioned inputs and candidate space.
- Applies a common raw exact-physics evaluation counting boundary across all search engines.
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.candidate_feasibility import FilteringResult
from app.schemas.optimization import (
    OptimizationInputEnvelope,
    PackagingCandidate,
    PackageGeometry,
    ParetoFront,
    SolverConfiguration,
    OptimizationExecutionTier,
)
from app.schemas.packaging_requirements import PackagingRequirementEnvelope
from app.schemas.ai_surrogate import SurrogateModelRegistry
from scientific_engine.optimization.benchmark_contracts import (
    IOptimizerAdapter,
    BenchmarkScenario,
    BenchmarkAlgorithmConfig,
    BenchmarkExecutionStatus,
)
from scientific_engine.optimization.search_engine import (
    AbstractInverseDesignSearchEngine,
    DeterministicEnumerationSearchEngine,
    IntelligentInverseDesignSearchEngine,
    AISurrogatePrioritizedSearchEngine,
    InverseDesignSearchResult,
)


class BenchmarkRunTelemetry(BaseModel):
    """
    Common benchmark execution telemetry captured during a search run.
    """
    run_id: str = Field(..., description="Unique search run ID")
    algorithm_id: str = Field(..., description="Engine name / algorithm ID")
    n_canonical: int = Field(0, description="Total candidate space size")
    n_gate1_valid: int = Field(0, description="Candidates passing Gate 1 thickness bounds")
    n_evaluable_canonical: int = Field(0, description="Candidates passing Gate 3 pre-execution evaluability")
    n_unique_physics_evaluated: int = Field(0, description="Unique candidates undergoing exact physics evaluation")
    n_evaluable_not_evaluated: int = Field(0, description="Evaluable candidates un-evaluated prior to termination")
    n_raw_physics_calls: int = Field(0, description="Total exact physics evaluation operation invocations")
    t_surrogate_total_ms: float = Field(0.0, description="Total wall-clock time spent in surrogate applicability & inference")
    t_physics_total_ms: float = Field(0.0, description="Total wall-clock time spent in exact physics calculations")
    t_wall_total_ms: float = Field(0.0, description="End-to-end total wall-clock time including search & overhead")
    feasible_count: int = Field(0, description="Number of Phase 5 FEASIBLE candidates discovered")
    infeasible_count: int = Field(0, description="Number of Phase 5 INFEASIBLE candidates discovered")
    unknown_count: int = Field(0, description="Number of Phase 5 UNKNOWN / UNRESOLVED candidates")
    stopping_reason: str = Field("COMPLETED", description="Search termination reason")
    pareto_front: Optional[ParetoFront] = Field(None, description="Discovered Pareto front")


class BaseEngineBenchmarkAdapter(IOptimizerAdapter):
    """
    Base benchmark adapter wrapper around AbstractInverseDesignSearchEngine.
    Enforces common benchmark scenario execution, monotonic timing, and metric extraction.
    """

    def __init__(self, engine: AbstractInverseDesignSearchEngine):
        self.engine = engine
        self.scenario: Optional[BenchmarkScenario] = None
        self.eligible_candidates: List[PackagingCandidate] = []
        self.config: Optional[BenchmarkAlgorithmConfig] = None
        self.last_result: Optional[InverseDesignSearchResult] = None
        self.telemetry: Optional[BenchmarkRunTelemetry] = None
        self.terminated: bool = False

    def initialize(
        self,
        scenario: BenchmarkScenario,
        eligible_candidates: List[PackagingCandidate],
        config: BenchmarkAlgorithmConfig,
    ) -> None:
        self.scenario = scenario
        self.eligible_candidates = list(eligible_candidates)
        self.config = config
        self.last_result = None
        self.telemetry = None
        self.terminated = False

    def _build_input_envelope(self) -> OptimizationInputEnvelope:
        if not self.scenario or not self.config:
            raise ValueError("Adapter must be initialized prior to execution.")

        max_evals = self.config.parameters.get("max_evaluations")
        solver_config = SolverConfiguration(
            execution_tier=OptimizationExecutionTier.DEEP_OPTIMIZATION,
            max_iterations=max_evals if max_evals and max_evals > 0 else len(self.eligible_candidates),
        )

        filt_res = FilteringResult(
            commodity=self.scenario.requirement_envelope.commodity,
            total_candidates_evaluated=len(self.eligible_candidates),
            feasible_candidates=[],
            infeasible_candidates=[],
            unknown_candidates=[],
            all_results=[],
        )

        return OptimizationInputEnvelope(
            optimization_run_id=f"bench_{self.scenario.scenario_id}_{self.config.algorithm_id}",
            commodity=self.scenario.requirement_envelope.commodity,
            target_shelf_life_days=int(self.scenario.requirement_envelope.target_shelf_life_days),
            storage_temperature_c=self.scenario.requirement_envelope.storage_temperature_c,
            relative_humidity_percent=self.scenario.requirement_envelope.relative_humidity_percent,
            package_geometry=self.scenario.package_geometry,
            packaging_requirement_envelope=self.scenario.requirement_envelope,
            filtering_result=filt_res,
            eligible_candidate_materials=self.eligible_candidates,
            active_objectives=self.scenario.active_objectives,
            solver_configuration=solver_config,
        )

    def execute_search(self) -> InverseDesignSearchResult:
        """Execute search engine and extract unified telemetry."""
        envelope = self._build_input_envelope()
        
        t_start = time.perf_counter()
        result = self.engine.search_with_summary(envelope)
        t_wall_ms = (time.perf_counter() - t_start) * 1000.0

        self.last_result = result
        self.terminated = True

        # Extract or derive common raw physics telemetry
        n_unique_phys = result.total_candidates_evaluated
        n_raw_phys = getattr(result, "n_raw_physics_calls_M11", None)
        if n_raw_phys is None:
            # Common benchmark boundary for engines without scenario calls: 1 raw physics call per unique evaluation
            n_raw_phys = n_unique_phys

        n_gate1 = getattr(result, "n_gate1_valid", None) or n_unique_phys
        n_eval_canon = getattr(result, "n_evaluable_canonical", None) or n_unique_phys
        n_uneval_not_eval = getattr(result, "n_evaluable_not_evaluated_M11", None)
        if n_uneval_not_eval is None:
            n_uneval_not_eval = max(0, n_eval_canon - n_unique_phys)

        t_surrogate = getattr(result, "t_surrogate_total_ms", None) or 0.0
        t_physics = getattr(result, "t_physics_total_ms", None) or result.execution_time_ms

        stopping = "SEARCH_SPACE_EXHAUSTED"
        if n_unique_phys < n_eval_canon:
            stopping = "BUDGET_EXHAUSTED"

        self.telemetry = BenchmarkRunTelemetry(
            run_id=result.optimization_run_id,
            algorithm_id=result.algorithm_name,
            n_canonical=result.total_candidates_considered,
            n_gate1_valid=n_gate1,
            n_evaluable_canonical=n_eval_canon,
            n_unique_physics_evaluated=n_unique_phys,
            n_evaluable_not_evaluated=n_uneval_not_eval,
            n_raw_physics_calls=n_raw_phys,
            t_surrogate_total_ms=t_surrogate,
            t_physics_total_ms=t_physics,
            t_wall_total_ms=t_wall_ms,
            feasible_count=result.feasible_candidates_count,
            infeasible_count=result.infeasible_candidates_count,
            unknown_count=result.unknown_candidates_count,
            stopping_reason=stopping,
            pareto_front=result.pareto_front,
        )
        return result

    def step(self) -> Dict[str, Any]:
        if not self.terminated:
            self.execute_search()
        return {"status": "COMPLETED", "evaluations": self.get_evaluations_count()}

    def get_current_pareto_front(self) -> ParetoFront:
        if self.last_result:
            return self.last_result.pareto_front
        raise RuntimeError("Adapter has not executed search.")

    def is_terminated(self) -> bool:
        return self.terminated

    def get_evaluations_count(self) -> int:
        if self.telemetry:
            return self.telemetry.n_unique_physics_evaluated
        return 0


class M9BenchmarkAdapter(BaseEngineBenchmarkAdapter):
    """Benchmark adapter for M9 Deterministic Exhaustive Inverse-Design Search Baseline."""
    def __init__(self, policy_version: str = "1.0"):
        super().__init__(engine=DeterministicEnumerationSearchEngine(policy_version=policy_version))


class M10BenchmarkAdapter(BaseEngineBenchmarkAdapter):
    """Benchmark adapter for M10 Adaptive Inverse-Design Search Baseline."""
    def __init__(self, policy_version: str = "1.0"):
        super().__init__(engine=IntelligentInverseDesignSearchEngine(policy_version=policy_version))


class M11BenchmarkAdapter(BaseEngineBenchmarkAdapter):
    """Benchmark adapter for M11 AI-Surrogate Prioritized Inverse-Design Search Engine."""
    def __init__(
        self,
        policy_version: str = "1.0",
        max_evaluations: Optional[int] = None,
        surrogate_manifest_id: Optional[str] = None,
        surrogate_registry: Optional[SurrogateModelRegistry] = None,
    ):
        engine = AISurrogatePrioritizedSearchEngine(
            policy_version=policy_version,
            max_evaluations=max_evaluations,
            surrogate_manifest_id=surrogate_manifest_id,
            surrogate_registry=surrogate_registry,
        )
        super().__init__(engine=engine)
