from pathlib import Path


class Config:
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 5000
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # Main directoris
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    HERB_CSV_PATH = DATA_DIR / "hair_herbs_comprehensive.csv"
    FRONTEND_DIR = BASE_DIR.parent / "frontend"

    # Recommended defaults
    DEFAULT_LIMIT = 6
    CONDITION_SCORE_WEIGHTS = {
        "benefit_match": 3,
        "condition_match": 2,
        "name_match": 1,
        "partial_match": 1,
        "hair_type_bonus": 3,
    }
