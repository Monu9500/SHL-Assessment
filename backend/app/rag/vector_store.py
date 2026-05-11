from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

try:
    import faiss  # type: ignore
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "FAISS is required. Install backend/requirements.txt in your environment."
    ) from exc

from app.rag.catalog_models import ProcessedAssessment

log = logging.getLogger(__name__)


class FaissRetriever:
    def __init__(
        self,
        *,
        assessments: list[ProcessedAssessment],
        embedding_model_name: str,
        index_dir: Path,
        batch_size: int = 64,
    ):
        from sentence_transformers import SentenceTransformer

        self.assessments = assessments
        self.embedding_model_name = embedding_model_name
        self.index_dir = index_dir
        self.batch_size = batch_size
        self.index_dir.mkdir(parents=True, exist_ok=True)

        meta_path = self.index_dir / "meta.json"
        emb_path = self.index_dir / "embeddings.npy"
        faiss_path = self.index_dir / "faiss.index"

        self._encoder: SentenceTransformer | None = None
        self._index: faiss.Index | None = None
        self._matrix: np.ndarray | None = None

        stale = False
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("embedding_model_name") != self.embedding_model_name:
                stale = True
            if meta.get("count") != len(self.assessments):
                stale = True
        else:
            stale = True

        if not stale and emb_path.exists() and faiss_path.exists():
            log.info(
                "Loading cached embeddings/FAISS from %s",
                self.index_dir.as_posix(),
            )
            self._encoder = SentenceTransformer(self.embedding_model_name)
            self._matrix = np.load(emb_path)
            self._index = faiss.read_index(str(faiss_path))
            return

        log.info(
            "Building FAISS index (model=%s, items=%s)",
            self.embedding_model_name,
            len(self.assessments),
        )
        self._encoder = SentenceTransformer(self.embedding_model_name)
        texts = [a.searchable_text for a in self.assessments]
        vecs_list: list[np.ndarray] = []
        for start in range(0, len(texts), self.batch_size):
            chunk = texts[start : start + self.batch_size]
            vecs = self._encoder.encode(
                chunk,
                batch_size=min(self.batch_size, len(chunk)),
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            vecs_list.append(vecs)
        matrix = np.vstack(vecs_list).astype(np.float32)

        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)

        faiss.write_index(index, str(faiss_path))
        np.save(emb_path, matrix)
        meta_path.write_text(
            json.dumps(
                {
                    "embedding_model_name": self.embedding_model_name,
                    "count": len(self.assessments),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        self._matrix = matrix
        self._index = index

    def search(self, *, query_text: str, top_k: int) -> list[ProcessedAssessment]:
        if self._encoder is None or self._index is None:
            raise RuntimeError("Retriever is not initialized.")
        q = self._encoder.encode(
            query_text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        q = q.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(q)
        k = max(1, min(int(top_k), len(self.assessments)))
        scores, idxs = self._index.search(q, k)

        picks: list[ProcessedAssessment] = []
        seen: set[str] = set()
        for position, idx in enumerate(idxs[0].tolist()):
            if idx < 0:
                continue
            item = self.assessments[idx]
            key = item.entity_id
            if key in seen:
                continue
            seen.add(key)
            _ = scores[0][position]
            picks.append(item)
        return picks
