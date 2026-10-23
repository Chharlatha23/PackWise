import os
import sys

# Configure python path to find the backend app
sys.path.insert(0, os.path.abspath('backend'))

from app.db.session import SessionLocal
from scientific_engine.optimization.candidate_builder import CandidateBuilder

db = SessionLocal()
builder = CandidateBuilder(db)
candidates = builder.build_candidates()

for c in candidates:
    print(f"{c.material_name}, {c.decision_variables.total_thickness_um} um")
