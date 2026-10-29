import os
import sqlite3
import psycopg2
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQLITE_PATH = ROOT / "food_packaging.db"
PG_URL = "postgresql://postgres:Chharlatha2005@localhost:5432/food_packaging_db"

def migrate():
    s_conn = sqlite3.connect(SQLITE_PATH)
    s_cur = s_conn.cursor()

    os.environ["DATABASE_URL"] = "postgresql+psycopg2://postgres:Chharlatha2005@localhost:5432/food_packaging_db"
    os.environ["USE_TEST_DB_URL"] = os.environ["DATABASE_URL"]
    
    import sys
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "backend"))
    from app.core.database import engine, Base
    import app.models

    print("Ensuring tables in PostgreSQL...")
    Base.metadata.create_all(bind=engine)

    p_conn = psycopg2.connect(PG_URL)
    p_cur = p_conn.cursor()

    # Disable FK checks temporarily for bulk load
    p_cur.execute("SET session_replication_role = 'replica';")

    tables = [
        "source",
        "food_commodity",
        "packaging_material",
        "microbial_organism",
        "evidence_record",
        "food_observation",
        "respiration_observation",
        "postharvest_storage_limits",
        "postharvest_gas_tolerances",
        "material_barrier_observation",
        "microbial_cardinal_parameters",
        "microbial_growth_kinetics",
        "microbial_gas_inhibition_response",
        "data_transformation",
        "packaging_feedback_record",
        "model_update_candidate",
        "validation_result",
        "users",
        "password_resets"
    ]

    for table in tables:
        try:
            s_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not s_cur.fetchone():
                continue

            s_cur.execute(f"PRAGMA table_info({table})")
            sqlite_cols = [r[1] for r in s_cur.fetchall()]

            p_cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """)
            pg_col_dict = {r[0]: r[1] for r in p_cur.fetchall()}
            
            common_cols = [c for c in sqlite_cols if c in pg_col_dict]
            if not common_cols:
                continue

            col_str = ", ".join([f'"{c}"' for c in common_cols])
            s_cur.execute(f"SELECT {col_str} FROM {table}")
            raw_rows = s_cur.fetchall()
            if not raw_rows:
                print(f"Table '{table}': 0 rows to migrate.")
                continue

            # Convert 0/1 integers to boolean for boolean columns
            clean_rows = []
            for r in raw_rows:
                row_list = list(r)
                for idx, col in enumerate(common_cols):
                    if pg_col_dict[col] == "boolean" and row_list[idx] is not None:
                        row_list[idx] = bool(row_list[idx])
                clean_rows.append(tuple(row_list))

            placeholders = ", ".join(["%s"] * len(common_cols))
            insert_query = f"""
                INSERT INTO "{table}" ({col_str})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            p_cur.executemany(insert_query, clean_rows)
            p_conn.commit()
            print(f"Table '{table}': successfully migrated {len(clean_rows)} rows.")
        except Exception as e:
            p_conn.rollback()
            print(f"Error migrating '{table}': {e}")

    # Re-enable standard foreign key enforcement
    p_cur.execute("SET session_replication_role = 'origin';")
    p_conn.commit()

    s_conn.close()
    p_conn.close()
    print("ALL TABLES MIGRATED TO POSTGRESQL!")

if __name__ == "__main__":
    migrate()
