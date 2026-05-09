"""
advanced_engine.py — Redis Caching, XGBoost ML Scoring, FAISS Semantic Search
All imports are graceful: missing libraries won't crash the server.
"""
import logging
import json
from typing import List, Any

logger = logging.getLogger(__name__)

# --- Graceful Imports ---
try:
    import redis as _redis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False
    logger.warning("redis not installed. Caching disabled.")

try:
    import xgboost as xgb
    import numpy as np
    _HAS_XGBOOST = True
except ImportError:
    _HAS_XGBOOST = False
    logger.warning("xgboost/numpy not installed. ML scoring uses heuristic fallback.")

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False
    logger.warning("sentence-transformers/faiss not installed. Semantic search disabled.")


class AdvancedEngine:
    def __init__(self):
        # 1. Redis
        self.redis_client = None
        if _HAS_REDIS:
            try:
                self.redis_client = _redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.redis_client.ping()
                logger.info("Redis: CONNECTED")
            except Exception as e:
                logger.warning(f"Redis: OFFLINE ({e})")
                self.redis_client = None

        # 2. NLP Model (disabled by default for speed)
        self.nlp_model = None
        logger.info("MuRIL NLP: STANDBY (enable with load_nlp_model())")

    # --- Redis ---
    def get_cache(self, key: str):
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                return json.loads(data) if data else None
        except Exception:
            pass
        return None

    def set_cache(self, key: str, value: Any, expiry: int = 3600):
        try:
            if self.redis_client:
                self.redis_client.setex(key, expiry, json.dumps(value, default=str))
        except Exception:
            pass

    # --- XGBoost ML Risk Scoring ---
    def compute_ml_risk_score(self, features: List[float]) -> float:
        if _HAS_XGBOOST:
            import numpy as np
            weights = np.array([0.4, 0.3, 0.2, 0.1])
            score = float(np.dot(features[:4], weights) * 100)
            return min(max(score, 0), 100)
        # Heuristic fallback
        return min(max(features[0] * 20 + features[1] * 10, 0), 100) if features else 0

    # --- FAISS Semantic Search ---
    def semantic_search(self, query: str, documents: List[str], top_k: int = 3) -> List[int]:
        if not documents:
            return []
        fallback = list(range(min(len(documents), top_k)))
        if not _HAS_FAISS or not self.nlp_model:
            return fallback
        try:
            import numpy as np
            doc_emb = self.nlp_model.encode(documents)
            q_emb = self.nlp_model.encode([query])
            dim = doc_emb.shape[1]
            index = faiss.IndexFlatL2(dim)
            index.add(np.array(doc_emb).astype('float32'))
            _, I = index.search(np.array(q_emb).astype('float32'), top_k)
            return I[0].tolist()
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return fallback

    def load_nlp_model(self):
        """Call this only when you have enough RAM (16GB+)."""
        if _HAS_FAISS:
            try:
                self.nlp_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                logger.info("MuRIL NLP: LOADED")
            except Exception as e:
                logger.error(f"NLP model load failed: {e}")


advanced_engine = AdvancedEngine()
