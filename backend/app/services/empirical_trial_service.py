"""
Phase 4 Step 2 — Empirical Trial Ingestion & Validation Service Boundary.

Provides a thread-safe repository (EmpiricalTrialRepository) and ingestion service
(EmpiricalTrialIngestionService) for ingesting, validating, and persisting empirical trial records.

STRICT BOUNDARIES:
- ZERO scientific model execution (no physics ODE, no surrogate model, no M11 search).
- ZERO model retraining, residual learning, continual learning, or MAP expansion.
- Duplicate trial_id rejection with explicit machine-readable error (ValueError).
- Missing scientific fields remain explicitly None (never coerced to 0.0 or defaults).
- Environmental trajectories remain raw continuous observation arrays.
- Data status MUST remain REAL_EMPIRICAL (rejects SYNTHETIC or MODEL_PREDICTED).
- Quarantined records are preserved in the repository with machine-readable failure reasons.
"""

import threading
from typing import Any, Dict, List, Optional

from app.schemas.ai_data import AIDataStatusEnum
from app.schemas.empirical_trial import (
    EmpiricalTrialRecord,
    EmpiricalTrialStatusEnum,
    EmpiricalTrialQualityGateEngine,
    EmpiricalTrialIngestionResult,
)


class DuplicateTrialIDError(ValueError):
    """
    Raised when attempting to save an empirical trial with a trial_id that already exists.
    Provides explicit machine-readable error_code='DUPLICATE_TRIAL_ID' and trial_id context.
    """

    error_code: str = "DUPLICATE_TRIAL_ID"

    def __init__(self, trial_id: str, message: Optional[str] = None) -> None:
        self.trial_id = trial_id
        self.error_code = "DUPLICATE_TRIAL_ID"
        self.message = message or f"Duplicate trial_id '{trial_id}': record already exists in repository."
        super().__init__(self.message)


class EmpiricalTrialRepository:
    """
    Thread-safe in-memory repository store for empirical validation trial records.
    Supports CRUD operations and queries by status and commodity.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store: Dict[str, EmpiricalTrialRecord] = {}

    def save(self, record: EmpiricalTrialRecord) -> EmpiricalTrialRecord:
        """
        Persists an EmpiricalTrialRecord into the repository.
        
        Raises:
            DuplicateTrialIDError: If a record with the same trial_id already exists (strict duplicate rejection).
        """
        with self._lock:
            if record.trial_id in self._store:
                raise DuplicateTrialIDError(
                    trial_id=record.trial_id,
                    message=f"Duplicate trial_id '{record.trial_id}': record already exists in repository."
                )
            self._store[record.trial_id] = record
            return record

    def get_by_id(self, trial_id: str) -> Optional[EmpiricalTrialRecord]:
        """Retrieves an empirical trial record by its unique trial_id."""
        with self._lock:
            return self._store.get(trial_id)

    def list_all(self) -> List[EmpiricalTrialRecord]:
        """Returns all stored empirical trial records."""
        with self._lock:
            return list(self._store.values())

    def list_validated(self) -> List[EmpiricalTrialRecord]:
        """Returns all stored empirical trial records that passed quality gates (VALIDATED)."""
        with self._lock:
            return [rec for rec in self._store.values() if rec.status == EmpiricalTrialStatusEnum.VALIDATED]

    def list_quarantined(self) -> List[EmpiricalTrialRecord]:
        """Returns all stored empirical trial records that failed quality gates (QUARANTINED)."""
        with self._lock:
            return [rec for rec in self._store.values() if rec.status == EmpiricalTrialStatusEnum.QUARANTINED]

    def filter_by_commodity(self, commodity: str) -> List[EmpiricalTrialRecord]:
        """
        Returns all stored empirical trial records matching the given food commodity (case-insensitive).
        """
        target = commodity.strip().lower()
        with self._lock:
            return [
                rec for rec in self._store.values()
                if rec.food_spec.commodity and rec.food_spec.commodity.strip().lower() == target
            ]

    def count(self) -> int:
        """Returns total count of stored records."""
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        """Clears all stored records (useful for test isolation)."""
        with self._lock:
            self._store.clear()


class EmpiricalTrialIngestionService:
    """
    Service boundary for ingesting, validating, and persisting empirical packaging trials.
    Executes EmpiricalTrialQualityGateEngine to determine VALIDATED vs QUARANTINED status,
    then saves the evaluated record into EmpiricalTrialRepository.
    """

    def __init__(
        self,
        repository: Optional[EmpiricalTrialRepository] = None,
        gate_engine: Optional[EmpiricalTrialQualityGateEngine] = None,
    ) -> None:
        self.repository = repository or EmpiricalTrialRepository()
        self.gate_engine = gate_engine or EmpiricalTrialQualityGateEngine()

    def ingest_dict(self, payload: Dict[str, Any]) -> EmpiricalTrialIngestionResult:
        """
        Parses raw dictionary payload into EmpiricalTrialRecord, preserves raw_payload,
        runs quality gates, and saves to repository.
        """
        record = EmpiricalTrialRecord(**payload)
        if record.raw_payload is None:
            record.raw_payload = payload
        return self.ingest_record(record)

    def ingest_record(self, record: EmpiricalTrialRecord) -> EmpiricalTrialIngestionResult:
        """
        Ingests an EmpiricalTrialRecord instance, enforces REAL_EMPIRICAL status,
        runs quality gates, and saves to repository.
        """
        if record.data_status != AIDataStatusEnum.REAL_EMPIRICAL:
            raise ValueError(
                f"EmpiricalTrialIngestionService rejects non-empirical data_status '{record.data_status}'. "
                "Only REAL_EMPIRICAL datasets are accepted."
            )

        # Run 8 quality gates
        evaluated_record = self.gate_engine.evaluate_and_validate(record)

        # Save to repository (raises DuplicateTrialIDError on duplicate trial_id)
        saved_record = self.repository.save(evaluated_record)

        return EmpiricalTrialIngestionResult(
            trial_id=saved_record.trial_id,
            status=saved_record.status,
            quarantine_reasons=list(saved_record.quarantine_reasons),
            record=saved_record,
        )

