# EXPLAIN.md (beginner-friendly)

### What does this project do?

It mimics **“Speak to a recruiter assistant”**:

1. You type what you’re hiring for.
2. The assistant asks a **sharp** follow-up question if you’re vague.
3. When it understands enough context, it returns a **small table-ish list**: assessment name, catalog link, compact test categories.

Behind the scenes, it only pulls items from SHL’s **official catalog**.

### Stateless API?

Every `POST /chat` call includes **the entire prior chat log** (`messages`). The backend does **not remember** chats in Redis or databases.

Think of this like emailing someone the entire thread each time instead of trusting them to memorize it.

### What is “RAG” here?

“RAG” means **retrieve** relevant catalog rows **before** answering.

1. Embed the transcript + normalized catalog descriptors.
2. Find the nearest catalog items (semantic neighbors).
3. Show those numbered candidates to the language model.
4. The model picks numbers; the server maps numbers back to real catalog rows.

### Why not let the model invent answers?

Because it can “sound right” while being wrong. For hiring compliance, **wrong assessment URLs are unacceptable**.

### What is Groq doing?

Groq hosts a fast LLM. We ask it to choose what to say *and* which candidate numbers to pick (if any), as JSON.

### What do I run first?

Start the backend (so `/health` works), then start the frontend. See the root `README.md`.

### How does deployment work?

- Backend on **Render** (Python web service)
- Frontend on **Vercel** (static build)
- You point the frontend at the backend using `VITE_API_BASE`.

### How would SHL test this automatically?

They replay conversations through your API and check:

- JSON keys never change
- recommendations are always valid arrays
- recommended items match their catalog
- behaviors (refuse / clarify / refine) match probes
