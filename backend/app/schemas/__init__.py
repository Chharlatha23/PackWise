"""
App schemas package.

Exports:
- PropertyStatus, PropertyStatusEnum
- PackagingRequest
- FoodEvidenceRecord, FoodEvidenceDataset
- PackagingMaterialSpec, MaterialPropertyEvidence, LayerSpec, CoatingSpec, ActiveFunctionalitySpec
- Controlled vocabularies (FoodProperty, CommodityCategory, ProcessingState, ProductForm, MaturityStage, etc.)
- Property inference schemas (InferredProperty, PropertyInferenceProfile, InferenceResolutionLevel, InferenceWarning)
- Physics schemas (CalculationStatus, ScientificTraceability, ScientificResult)
- Packaging requirement schemas (DeteriorationMechanismStatus, DeteriorationProfile, GasExchangeRequirement,
  MoistureRequirement, MicrobialRequirement, ShelfLifeRequirement, PackagingRequirementEnvelope)
"""

from app.schemas.property_status import PropertyStatus, PropertyStatusEnum
from app.schemas.packaging_request import PackagingRequest
from app.schemas.food_evidence import FoodEvidenceRecord, FoodEvidenceDataset
from app.schemas.material_evidence import (
    PackagingMaterialSpec,
    MaterialPropertyEvidence,
    LayerSpec,
    CoatingSpec,
    ActiveFunctionalitySpec,
)
from app.schemas.vocabularies import (
    FoodProperty,
    CommodityCategory,
    ProcessingState,
    ProductForm,
    MaturityStage,
    ValueType,
    SourceType,
    EvidenceStrength,
    MaterialCategory,
    PackagingProperty,
)
from app.schemas.inference import (
    InferredProperty,
    PropertyInferenceProfile,
    InferenceResolutionLevel,
    UncertaintyLevelEnum,
    InferenceWarning,
)
from app.schemas.physics import (
    CalculationStatus,
    ScientificTraceability,
    ScientificResult,
)
from app.schemas.packaging_requirements import (
    DeteriorationMechanismStatus,
    DeteriorationProfile,
    GasExchangeRequirement,
    MoistureRequirement,
    MicrobialRequirement,
    ShelfLifeRequirement,
    PackagingRequirementEnvelope,
)
from app.schemas.constraints import (
    ConstraintStatus,
    ComparisonOperator,
    ConditionMatchLevel,
    ConstraintEvaluation,
)
from app.schemas.candidate_feasibility import (
    CandidateFeasibility,
    FilteringResult,
)
from app.schemas.optimization import (
    ObjectiveDirection,
    EvidenceTier,
    UncertaintyType,
    OptimizationExecutionTier,
    CandidateEvidenceReference,
    BarrierPropertyMetric,
    CandidateBarrierProperties,
    PackageGeometry,
    CandidateDecisionVariables,
    PackagingCandidate,
    CandidateScientificEvaluationRequest,
    CandidateScientificEvaluationResult,
    ObjectiveValue,
    CandidateConstraintStatus,
    UncertaintyProfile,
    ExplanationPayload,
    ParetoCandidate,
    SolverConfiguration,
    OptimizationInputEnvelope,
    OptimizationMetadata,
    ParetoFront,
    CounterfactualPerturbations,
    CounterfactualQuery
)

from app.schemas.feedback import (
    ObservationOrigin,
    ValidationStatus,
    ComparisonStatus,
    ModelUpdateStatus,
    PackageConfigurationSchema,
    StorageConditionsSchema,
    PredictedOutputSchema,
    FeedbackSubmission,
    MeasurementComparison,
    ModelUpdateCandidateSchema,
    FeedbackResponse
)

from app.schemas.ai_data import (
    AIDataStatusEnum,
    AIProvenanceRecord,
    AIFeatureValue,
    AIDataRecord,
    from_food_evidence,
    from_material_evidence,
    from_inferred_profile,
)

from app.schemas.ai_target import (
    AITargetEnum,
    AITargetClassificationEnum,
    AITargetCriteriaAssessment,
    AITargetAuditResult,
    AITargetPreparationRecord,
    AITargetPreparationSet,
    get_default_target_audit_registry,
    prepare_targets_from_ai_data_record,
)

from app.schemas.ai_dataset import (
    GenerationStoppingReasonEnum,
    ThicknessDomainTypeEnum,
    MaterialThicknessDomain,
    MaterialThicknessBoundsManager,
    AIPhysicsReferenceRecord,
    DatasetQualityDiagnostics,
    AIPhysicsDataset,
    PhysicsReferenceDatasetGenerator,
)

from app.schemas.ai_surrogate import (
    SurrogateModelFamilyEnum,
    SurrogateAcceptanceStatusEnum,
    SplitStrategyEnum,
    TargetTransformationEnum,
    SurrogateCompatibilityError,
    FeatureSchemaDefinition,
    TargetTransformationConfig,
    SurrogateDatasetEligibilityResult,
    DatasetSplitResult,
    SubgroupMetrics,
    HighErrorRegionAnalysis,
    ConstraintBoundaryAnalysis,
    RankingAgreementAnalysis,
    ApplicabilitySignalAudit,
    SurrogatePerformanceMetrics,
    ComputationalCostMetrics,
    SurrogatePhysicalValidityCheck,
    ApplicabilityDiagnostic,
    SurrogateModelManifest,
    SurrogatePredictionResult,
    SurrogateFeatureExtractor,
    SurrogateTargetEligibilityEngine,
    SurrogateDatasetSplitter,
    SurrogateBenchmarker,
    SurrogateApplicabilityEngine,
    SurrogateModelRegistry,
)

from app.schemas.empirical_trial import (
    EmpiricalTrialStatusEnum,
    EmpiricalMeasurementUncertainty,
    EmpiricalFoodSpecification,
    EmpiricalPackagingSpecification,
    EnvironmentTrajectoryPoint,
    EmpiricalStorageEnvironment,
    EmpiricalTimeSeriesObservation,
    EmpiricalShelfLifeOutcome,
    EmpiricalTrialProvenance,
    EmpiricalTrialRecord,
    EmpiricalTrialQualityGateEngine,
)

__all__ = [
    "PropertyStatus",
    "PropertyStatusEnum",
    "PackagingRequest",
    "FoodEvidenceRecord",
    "FoodEvidenceDataset",
    "PackagingMaterialSpec",
    "MaterialPropertyEvidence",
    "LayerSpec",
    "CoatingSpec",
    "ActiveFunctionalitySpec",
    "FoodProperty",
    "CommodityCategory",
    "ProcessingState",
    "ProductForm",
    "MaturityStage",
    "ValueType",
    "SourceType",
    "EvidenceStrength",
    "MaterialCategory",
    "PackagingProperty",
    "InferredProperty",
    "PropertyInferenceProfile",
    "InferenceResolutionLevel",
    "UncertaintyLevelEnum",
    "InferenceWarning",
    "CalculationStatus",
    "ScientificTraceability",
    "ScientificResult",
    "DeteriorationMechanismStatus",
    "DeteriorationProfile",
    "GasExchangeRequirement",
    "MoistureRequirement",
    "MicrobialRequirement",
    "ShelfLifeRequirement",
    "PackagingRequirementEnvelope",
    "ConstraintStatus",
    "ComparisonOperator",
    "ConditionMatchLevel",
    "ConstraintEvaluation",
    "CandidateFeasibility",
    "FilteringResult",
    "ObjectiveDirection",
    "EvidenceTier",
    "UncertaintyType",
    "OptimizationExecutionTier",
    "CandidateEvidenceReference",
    "BarrierPropertyMetric",
    "CandidateBarrierProperties",
    "PackageGeometry",
    "CandidateDecisionVariables",
    "PackagingCandidate",
    "CandidateScientificEvaluationRequest",
    "CandidateScientificEvaluationResult",
    "ObjectiveValue",
    "CandidateConstraintStatus",
    "UncertaintyProfile",
    "ExplanationPayload",
    "ParetoCandidate",
    "SolverConfiguration",
    "OptimizationInputEnvelope",
    "OptimizationMetadata",
    "ParetoFront",
    "CounterfactualPerturbations",
    "CounterfactualQuery",
    "ObservationOrigin",
    "ValidationStatus",
    "ComparisonStatus",
    "ModelUpdateStatus",
    "PackageConfigurationSchema",
    "StorageConditionsSchema",
    "PredictedOutputSchema",
    "FeedbackSubmission",
    "MeasurementComparison",
    "ModelUpdateCandidateSchema",
    "FeedbackResponse",
    "AIDataStatusEnum",
    "AIProvenanceRecord",
    "AIFeatureValue",
    "AIDataRecord",
    "from_food_evidence",
    "from_material_evidence",
    "from_inferred_profile",
    "AITargetEnum",
    "AITargetClassificationEnum",
    "AITargetCriteriaAssessment",
    "AITargetAuditResult",
    "AITargetPreparationRecord",
    "AITargetPreparationSet",
    "get_default_target_audit_registry",
    "prepare_targets_from_ai_data_record",
    "GenerationStoppingReasonEnum",
    "ThicknessDomainTypeEnum",
    "MaterialThicknessDomain",
    "MaterialThicknessBoundsManager",
    "AIPhysicsReferenceRecord",
    "DatasetQualityDiagnostics",
    "AIPhysicsDataset",
    "PhysicsReferenceDatasetGenerator",
    "SurrogateModelFamilyEnum",
    "SurrogateAcceptanceStatusEnum",
    "SplitStrategyEnum",
    "TargetTransformationEnum",
    "SurrogateCompatibilityError",
    "FeatureSchemaDefinition",
    "TargetTransformationConfig",
    "SurrogateDatasetEligibilityResult",
    "DatasetSplitResult",
    "SubgroupMetrics",
    "SurrogatePerformanceMetrics",
    "ComputationalCostMetrics",
    "SurrogatePhysicalValidityCheck",
    "ApplicabilityDiagnostic",
    "SurrogateModelManifest",
    "SurrogatePredictionResult",
    "SurrogateFeatureExtractor",
    "SurrogateTargetEligibilityEngine",
    "SurrogateDatasetSplitter",
    "SurrogateBenchmarker",
    "SurrogateApplicabilityEngine",
    "SurrogateModelRegistry",
    "EmpiricalTrialStatusEnum",
    "EmpiricalMeasurementUncertainty",
    "EmpiricalFoodSpecification",
    "EmpiricalPackagingSpecification",
    "EnvironmentTrajectoryPoint",
    "EmpiricalStorageEnvironment",
    "EmpiricalTimeSeriesObservation",
    "EmpiricalShelfLifeOutcome",
    "EmpiricalTrialProvenance",
    "EmpiricalTrialRecord",
    "EmpiricalTrialQualityGateEngine",
]

import sys
for _k, _v in list(sys.modules.items()):
    if _k == "app" or _k.startswith("app."):
        sys.modules["backend." + _k] = _v



