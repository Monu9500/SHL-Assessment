const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

/**
 * @typedef {{ role: "user" | "assistant" | "system", content: string }} ChatMessageDTO
 * @typedef {{ name: string, url: string, test_type?: string }} RecommendationDTO
 */

/**
 * @param {ChatMessageDTO[]} messages
 * @returns {Promise<{reply: string, recommendations: RecommendationDTO[], end_of_conversation: boolean}>}
 */
export async function postChat(messages) {
  const resp = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  let payloadText = "";
  try {
    payloadText = await resp.text();
  } catch {
    throw new Error("Failed to read backend response.");
  }

  if (!resp.ok) {
    throw new Error(
      typeof payloadText === "string" && payloadText.trim()
        ? payloadText.slice(0, 800)
        : `Backend error (${resp.status})`,
    );
  }

  /** @type {any} */
  let data;
  try {
    data = JSON.parse(payloadText);
  } catch {
    throw new Error("Backend returned non-JSON. Check your `/chat` deployment.");
  }

  const reply = typeof data.reply === "string" ? data.reply : "";
  const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];
  const end =
    typeof data.end_of_conversation === "boolean" ? data.end_of_conversation : false;

  return { reply, recommendations, end_of_conversation: end };
}

export async function getHealth() {
  const resp = await fetch(`${API_BASE}/health`);
  if (!resp.ok) return { status: "down" };
  try {
    return await resp.json();
  } catch {
    return { status: "unknown" };
  }
}
