from typing import List
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
    return {"status": "ok", "service": "FoodPack AI API"}


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
    db: Session = Depends(get_db)
) -> RecommendationResponse:
    """Generate end-to-end scientific recommendation for food packaging."""
    try:
        service = RecommendationService()
        return service.generate_recommendation(request, db)
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
