from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.packaging_request import PackagingRequest
from app.schemas.recommendation import RecommendationResponse
from app.schemas.feedback import FeedbackSubmission, FeedbackResponse, ModelUpdateCandidateSchema
from app.services.recommendation_service import RecommendationService
from app.services.feedback_service import FeedbackService

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Returns a simple status response confirming the API is running."""
    return {"status": "ok", "service": "PackWise API"}


@router.post(
    "/api/v1/recommend",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate scientific packaging recommendation",
    description=(
        "Executes the full end-to-end scientific recommendation pipeline from "
        "user input logistics to exact non-dominated Pareto front construction. "
        "Preserves interval objective bounds and explicit feasibility states."
    ),
)
def generate_recommendation(
    request: PackagingRequest,
    search_engine: Optional[str] = None,
    db: Session = Depends(get_db)
) -> RecommendationResponse:
    """Generate end-to-end scientific recommendation for food packaging."""
    try:
        service = RecommendationService()
        return service.generate_recommendation(request, db, search_engine_type=search_engine)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation pipeline execution error: {str(e)}"
        )


@router.post(
    "/api/v1/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit packaging trial feedback observation",
    description=(
        "Ingests observed real-world packaging trial measurements, validates submission, "
        "compares predicted vs observed performance, and generates traceable model update candidates."
    ),
)
def submit_feedback(
    submission: FeedbackSubmission,
    db: Session = Depends(get_db)
) -> FeedbackResponse:
    """Submit real-world packaging trial observation feedback."""
    try:
        service = FeedbackService()
        return service.submit_feedback(submission, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feedback submission error: {str(e)}"
        )


@router.get(
    "/api/v1/feedback",
    response_model=List[FeedbackResponse],
    status_code=status.HTTP_200_OK,
    summary="List all recorded packaging feedback submissions",
    description="Returns all stored feedback trial submissions with comparisons and update candidates.",
)
def list_all_feedback(
    db: Session = Depends(get_db)
) -> List[FeedbackResponse]:
    """Retrieve all feedback trial records."""
    service = FeedbackService()
    return service.list_all_feedback(db)


@router.get(
    "/api/v1/feedback/model-updates",
    response_model=List[ModelUpdateCandidateSchema],
    status_code=status.HTTP_200_OK,
    summary="List all recorded model update candidates",
    description="Returns all structured model-update candidates generated from trial feedback discrepancies.",
)
def list_model_updates(
    db: Session = Depends(get_db)
) -> List[ModelUpdateCandidateSchema]:
    """Retrieve all model update candidates across packaging trials."""
    service = FeedbackService()
    return service.list_model_update_candidates(db)


@router.get(
    "/api/v1/feedback/{feedback_id}",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve packaging trial feedback record by ID",
    description="Returns stored feedback observation, comparison results, and update candidates for a specific ID.",
)
def get_feedback(
    feedback_id: str,
    db: Session = Depends(get_db)
) -> FeedbackResponse:
    """Retrieve feedback record by UUID."""
    service = FeedbackService()
    result = service.get_feedback_by_id(feedback_id, db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback record not found: {feedback_id}"
        )
    return result


@router.get(
    "/api/v1/materials",
    status_code=status.HTTP_200_OK,
    summary="List available packaging materials with barrier properties",
)
def list_materials(db: Session = Depends(get_db)):
    """Returns canonical packaging materials and barrier properties for comparison."""
    from app.models.evidence import PackagingMaterial, MaterialBarrierObservation
    
    materials = db.query(PackagingMaterial).all()
    results = []
    for mat in materials:
        barriers = db.query(MaterialBarrierObservation).filter_by(material_id=mat.id).all()
        prop_map = {}
        for b in barriers:
            prop_key = b.property_type.value if hasattr(b.property_type, "value") else str(b.property_type)
            prop_map[prop_key] = {
                "value": b.value,
                "unit": b.canonical_unit or b.original_unit,
                "thickness_um": b.thickness_value,
                "temperature_c": b.test_temperature_c_value,
                "rh_percent": b.test_rh_percent_value
            }
        results.append({
            "id": str(mat.id),
            "material_name": mat.material_name,
            "brand_grade": mat.brand_grade,
            "structure_type": mat.structure_type.value if hasattr(mat.structure_type, "value") else str(mat.structure_type),
            "properties": prop_map
        })
    return results


@router.get(
    "/api/v1/evidence",
    status_code=status.HTTP_200_OK,
    summary="List canonical scientific evidence records",
)
def list_evidence(
    limit: int = 50,
    commodity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns traceable scientific evidence records from USDA, UC Davis, and CIRAD/WUR."""
    from app.models.evidence import Source, EvidenceRecord, FoodCommodity, FoodObservation
    
    query = db.query(EvidenceRecord).join(Source, EvidenceRecord.source_id == Source.id)
    records = query.limit(limit).all()
    
    results = []
    for rec in records:
        source_name = rec.source.source_name if rec.source else "Canonical Literature"
        dataset_type = rec.source.dataset_type if rec.source else "Experimental"
        
        # Pull associated food observations if any
        obs = db.query(FoodObservation).filter_by(evidence_id=rec.id).all()
        obs_list = [
            {
                "property_name": o.property_name,
                "value": o.value,
                "unit": o.canonical_unit or o.original_unit,
                "method": o.measurement_method
            }
            for o in obs[:5]
        ]
        
        results.append({
            "id": str(rec.id),
            "source_name": source_name,
            "dataset_type": dataset_type,
            "record_identifier": rec.record_identifier_in_source or "CANONICAL",
            "evidence_classification": rec.evidence_classification.value if hasattr(rec.evidence_classification, "value") else str(rec.evidence_classification),
            "verification_status": rec.verification_status.value if hasattr(rec.verification_status, "value") else str(rec.verification_status),
            "literature_references": rec.literature_references,
            "observations": obs_list
        })
    return results


@router.get(
    "/api/v1/overview",
    status_code=status.HTTP_200_OK,
    summary="System overview metrics and counts",
)
def get_system_overview(db: Session = Depends(get_db)):
    """Returns database counts and operational search-stage metrics."""
    from app.models.evidence import PackagingMaterial, FoodCommodity, Source, EvidenceRecord
    from app.models.feedback import PackagingFeedbackRecord, ModelUpdateCandidate
    
    mat_count = db.query(PackagingMaterial).count()
    comm_count = db.query(FoodCommodity).count()
    source_count = db.query(Source).count()
    evidence_count = db.query(EvidenceRecord).count()
    feedback_count = db.query(PackagingFeedbackRecord).count()
    candidate_count = db.query(ModelUpdateCandidate).count()
    
    return {
        "status": "operational",
        "search_tiers": {
            "M9": "Deterministic Enumeration (Exhaustive material lattice)",
            "M10": "Adaptive Heuristic (Deterministic candidate prioritization)",
            "M11": "Surrogate-Assisted (OOD check + Exact-Physics verification authoritative)"
        },
        "database_metrics": {
            "packaging_materials": mat_count,
            "food_commodities": comm_count,
            "scientific_sources": source_count,
            "evidence_records": evidence_count,
            "trial_feedback_records": feedback_count,
            "model_update_candidates": candidate_count
        }
    }


@router.get(
    "/api/v1/commodities",
    status_code=status.HTTP_200_OK,
    summary="List all canonical and database food commodities",
)
def list_commodities(db: Session = Depends(get_db)):
    """Returns all available food commodities across reference data, scientific db, and user db."""
    from app.models.evidence import FoodCommodity
    names = set()
    
    # 1. From FoodCommodity table in food_packaging.db
    try:
        commodities = db.query(FoodCommodity).all()
        for c in commodities:
            if c.commodity_name:
                names.add(c.commodity_name.strip())
    except Exception:
        pass
        
    # 2. From reference food_evidence.json
    try:
        import json
        from pathlib import Path
        ref_file = Path(__file__).resolve().parent.parent.parent.parent / "data" / "reference" / "food_evidence.json"
        if ref_file.exists():
            with open(ref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    if "commodity" in item and item["commodity"]:
                        names.add(item["commodity"].strip().title())
    except Exception:
        pass

    # 3. From MySQL food_products if configured
    try:
        from app.core.database import get_user_db
        from sqlalchemy import text
        user_db_gen = get_user_db()
        user_db = next(user_db_gen)
        try:
            rows = user_db.execute(text("SELECT product_name FROM food_products")).fetchall()
            for r in rows:
                if r[0]:
                    names.add(r[0].strip().title())
        finally:
            user_db.close()
    except Exception:
        pass

    return sorted(list(names))
