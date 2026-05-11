import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { RecommendationsPanel } from "./components/RecommendationsPanel.jsx";
import { TypingText } from "./components/TypingText.jsx";
import { getHealth, postChat } from "./services/api.js";

function TurnMeta({ endOfConversation, recCount, theme }) {
  const dark = theme !== "light";
  const divider = dark ? "border-slate-800/70" : "border-slate-200";
  const text = dark ? "text-slate-500" : "text-slate-600";
  const dot = dark ? "text-slate-700" : "text-slate-300";
  const flag = dark ? "text-rose-400/90" : "text-rose-600";

  return (
    <div className={`mt-3 border-t ${divider} pt-3 font-mono text-[11px] ${text}`}>
      <span className={flag}>'end_of_conversation': {String(endOfConversation)}</span>
      <span className={`mx-2 ${dot}`}>·</span>
      <span>
        {recCount === 0
          ? "No recommendations this turn (recommendations: [])"
          : `recommendations: ${recCount} item(s)`}
      </span>
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem("theme");
    return stored === "light" ? "light" : "dark";
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const [draft, setDraft] = useState("");
  /** @type {[{role: "user"|"assistant"|"system", content: string}]} */
  const [messages, setMessages] = useState([]);
  /** @type {Array<{assistant: string, recommendations: any[], metadata: any}>} */
  const [turnDetails, setTurnDetails] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  const bottomRef = useRef(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: "unknown" }));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turnDetails.length, messages.length, isSending]);

  const canSend = useMemo(() => draft.trim().length > 0 && !isSending, [draft, isSending]);

  async function onSend() {
    const text = draft.trim();
    if (!text || isSending) return;

    const nextMsgs = [...messages, { role: "user", content: text }];
    setMessages(nextMsgs);
    setDraft("");
    setError("");
    setIsSending(true);

    try {
      const out = await postChat(nextMsgs);
      const assistant = out.reply ?? "";
      setMessages([...nextMsgs, { role: "assistant", content: assistant }]);
      const recs = Array.isArray(out.recommendations) ? out.recommendations : [];

      const turnIndex = Math.floor(nextMsgs.filter((m) => m.role === "user").length);

      setTurnDetails((prev) => [
        ...prev,
        {
          user: text,
          assistant,
          recommendations: recs,
          end_of_conversation: Boolean(out.end_of_conversation),
          turnIndex,
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div
      className={
        theme === "dark"
          ? "min-h-full bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900"
          : "min-h-full bg-gradient-to-b from-slate-50 via-white to-slate-100"
      }
    >
      <div className="mx-auto flex min-h-full max-w-6xl flex-col px-4 pb-10 pt-6 sm:px-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-400/90">
              TalentLens
            </div>
            <h1
              className={
                theme === "dark"
                  ? "mt-2 text-2xl font-semibold text-slate-50 sm:text-3xl"
                  : "mt-2 text-2xl font-semibold text-slate-900 sm:text-3xl"
              }
            >
              Conversational SHL Assessment Recommender
            </h1>
            <p
              className={
                theme === "dark"
                  ? "mt-2 max-w-2xl text-sm leading-relaxed text-slate-400"
                  : "mt-2 max-w-2xl text-sm leading-relaxed text-slate-600"
              }
            >
              Statelessly mirrors the assignment API: every request sends the full transcript. The UI surfaces the
              evaluator-friendly JSON fields (shortlist + end flag) in a terminal-inspired layout like the sample traces.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <div
              className={
                theme === "dark"
                  ? "rounded-full border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-xs text-slate-300 shadow-glow"
                  : "rounded-full border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm"
              }
            >
              <span className="font-semibold text-slate-400">backend</span>{" "}
              <span className="font-mono">
                {(health && health.status === "ok" && "● ok") ||
                  `● unknown (${String(health?.status ?? "n/a")})`}
              </span>
            </div>

            <button
              type="button"
              onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
              className={
                theme === "dark"
                  ? "rounded-full border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-900/40"
                  : "rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-900 hover:bg-slate-50"
              }
            >
              {theme === "dark" ? "Light" : "Dark"}
            </button>
          </div>
        </header>

        <main className="mt-8 flex-1">
          <div
            className={
              theme === "dark"
                ? "rounded-2xl border border-slate-800/80 bg-slate-950/35 p-5 shadow-glow sm:p-6"
                : "rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
            }
          >
            <div className="flex items-baseline justify-between gap-4">
              <div
                className={
                  theme === "dark"
                    ? "font-mono text-sm font-semibold text-slate-200"
                    : "font-mono text-sm font-semibold text-slate-900"
                }
              >
                Conversation
              </div>
              <div className={theme === "dark" ? "text-xs text-slate-500" : "text-xs text-slate-600"}>
                POST <span className="font-mono">/chat</span> · stateless history
              </div>
            </div>

            <div className="mt-5 space-y-6">
              <AnimatePresence initial={false}>
                {turnDetails.map((t) => (
                  <motion.section
                    key={`${t.turnIndex}-${t.user.slice(0, 24)}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.22 }}
                    className={
                      theme === "dark"
                        ? "rounded-xl border border-slate-800/70 bg-slate-950/40 p-4"
                        : "rounded-xl border border-slate-200 bg-slate-50 p-4"
                    }
                  >
                    <div className="text-xs font-semibold tracking-wide text-slate-500">
                      Turn {t.turnIndex}
                    </div>

                    <div className="mt-3">
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                        User
                      </div>
                      <div
                        className={
                          theme === "dark"
                            ? "mt-1 font-mono text-sm text-slate-100"
                            : "mt-1 font-mono text-sm text-slate-900"
                        }
                      >
                        <span className="text-slate-500">&gt;</span> {t.user}
                      </div>
                    </div>

                    <div className="mt-4">
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                        Agent
                      </div>
                      <div
                        className={
                          theme === "dark"
                            ? "mt-1 text-sm leading-relaxed text-slate-200"
                            : "mt-1 text-sm leading-relaxed text-slate-800"
                        }
                      >
                        <TypingText text={t.assistant} />
                      </div>
                      <RecommendationsPanel items={t.recommendations} theme={theme} />
                      <TurnMeta
                        endOfConversation={t.end_of_conversation}
                        recCount={t.recommendations?.length || 0}
                        theme={theme}
                      />
                    </div>
                  </motion.section>
                ))}
              </AnimatePresence>
            </div>

            {error ? (
              <div className="mt-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                {error}
              </div>
            ) : null}

            <div className="mt-6 border-t border-slate-800/60 pt-5">
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Message
              </label>
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={3}
                className={
                  theme === "dark"
                    ? "mt-2 w-full resize-y rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-sky-500/40 focus:ring-2 focus:ring-sky-500/20"
                    : "mt-2 w-full resize-y rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-sky-400/60 focus:ring-2 focus:ring-sky-300/30"
                }
                placeholder="Describe the role, constraints, languages, and priority (e.g. cognitive vs personality vs simulation)…"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    onSend();
                  }
                }}
              />
              <div className="mt-3 flex items-center justify-between gap-3">
                <div className="text-xs text-slate-500">
                  Tip: <span className="font-mono">Ctrl/⌘ + Enter</span> to send
                </div>
                <button
                  type="button"
                  disabled={!canSend}
                  onClick={onSend}
                  className={
                    canSend
                      ? "inline-flex items-center justify-center rounded-xl bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-sky-400"
                      : "inline-flex cursor-not-allowed items-center justify-center rounded-xl bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-500"
                  }
                >
                  {isSending ? "Thinking…" : "Send"}
                </button>
              </div>
            </div>

            <div ref={bottomRef} />
          </div>
        </main>

        <footer className="mt-10 text-center text-xs text-slate-600">
          UI is for humans; the evaluator only checks your FastAPI JSON contract.
        </footer>
      </div>
    </div>
  );
}
