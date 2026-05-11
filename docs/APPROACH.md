# Approach (≤ 2 pages)

## Goal

Pass SHL’s automated harness: **strict JSON schema**, **catalog-only recommendations**, **realistic multi-turn behavior** (clarify when vague, refine when constraints change, compare only with catalog fields, refuse off-topic), under **tight turn + latency budgets**.

## Design choices

### Catalog ingestion + cleanup

Upstream JSON can include imperfect string hygiene (embedded newlines in fields). Rather than brittle manual fixes, ingestion runs through `json-repair`, then deterministic normalization (`app/rag/preprocess.py`): trim control characters, keep only `*.shl.com` **Individual Solution** URLs in the scraped shape, derive `test_type` abbreviations from the official `keys` taxonomy (K/A/P/etc.), build a searchable string for embeddings.

### Retrieval

We embed both **conversation text** (last several turns flattened) plus **normalized catalog fields**. Retrieval uses **`sentence-transformers/all-MiniLM-L6-v2`** embeddings with **cosine/IP on L2-normalized vectors** (`IndexFlatIP` + normalized embeddings). Persistence caches vectors + faiss artifacts under `backend/data/faiss_store/` to amortize startup.

### Ranking + grounding (anti-hallucination)

Groq emits JSON with `selected_indices`, referencing numbered rows from the retrieval window shown in the prompt **for that POST only**.

The backend maps indices → **`name/url/test_type`** from the processed catalog tuple. Therefore the model cannot “invent URLs”; worst case it picks suboptimal neighbor items.

Late in the transcript, a **forced commit flag** biases toward emitting a shortlist within evaluator turn limits.

### Prompting

System instructions enforce:

- JSON-only output (with server-side JSON repair when needed)
- refusal behavior
- compare vs recommend vs clarify separation
- “never pick items not present in the candidate block”

We also pass prior assistant count + `force_shortlist` as explicit JSON metadata to reduce ambiguity.

## What failed / changed during iteration

- **Naive `json.loads` on raw catalog** failed on embedded newlines inside JSON strings; adding `json-repair` fixed robustness.
- **Trusting the LLM to output URLs** is unsafe for automated scoring; indices-only selection removed that entire failure mode.
- **LLM JSON mode** is not universally consistent across models; code falls back to plain completion if JSON mode errors.

## Evaluation strategy (local)

- Schema unit tests for Pydantic response **field stability**
- Manual replays of SHL’s public traces after dropping them into `conversation_traces/`
- Spot checks for refusal prompts (legal/salary/jailbreak) ensuring `recommendations: []`

## AI tools used

This repository scaffold and implementation were assisted by an AI coding agent (Cursor/ChatGPT-class tooling) **with human review**. It was used heavily for scaffolding, refactoring, prose documentation, and test wiring.
