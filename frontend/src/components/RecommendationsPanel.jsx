import { AnimatePresence, motion } from "framer-motion";

function prettyTestType(tt) {
  const s = typeof tt === "string" ? tt.trim() : "";
  if (!s) return "-";
  return s;
}

export function RecommendationsPanel({ items, theme }) {
  if (!items || items.length === 0) return null;

  const dark = theme !== "light";

  const shell = dark
    ? "overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/40 shadow-glow"
    : "overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm";

  const thead = dark
    ? "sticky top-0 z-10 bg-slate-950/90 backdrop-blur"
    : "sticky top-0 z-10 bg-white/90 backdrop-blur";

  const headText = dark ? "text-xs font-semibold text-slate-300" : "text-xs font-semibold text-slate-700";
  const rowBorder = dark ? "border-slate-800/60" : "border-slate-200";
  const nameText = dark ? "text-slate-100" : "text-slate-900";
  const monoText = dark ? "text-slate-200" : "text-slate-800";
  const idxText = dark ? "text-slate-400" : "text-slate-600";
  const subtitle = dark ? "text-slate-400" : "text-slate-600";
  const label = dark ? "text-sky-400/85" : "text-sky-700";

  return (
    <div className="mt-5">
      <div className="mb-3 flex items-center justify-between">
        <div className={`text-xs font-semibold uppercase tracking-[0.18em] ${label}`}>
          Recommendations ({items.length})
        </div>
        <div className={`text-[11px] ${subtitle}`}>Grounded to SHL catalog URLs</div>
      </div>

      <div className={shell}>
        <table className="min-w-[980px] w-full border-collapse text-left text-sm">
          <thead className={thead}>
            <tr className={`border-b ${rowBorder} ${headText}`}>
              <th className="px-3 py-2 w-10">#</th>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2 w-24">Test type</th>
              <th className="px-3 py-2 w-28">URL</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {items.map((r, i) => (
                <motion.tr
                  key={`${r.url}-${i}`}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.18, delay: Math.min(i * 0.03, 0.25) }}
                  className={`border-b ${rowBorder} last:border-b-0`}
                >
                  <td className={`px-3 py-2 font-mono text-xs ${idxText}`}>{i + 1}</td>
                  <td className={`px-3 py-2 ${nameText}`}>{r.name}</td>
                  <td className={`px-3 py-2 font-mono text-xs ${monoText}`}>
                    {prettyTestType(r.test_type)}
                  </td>
                  <td className="px-3 py-2">
                    <a
                      className={
                        dark
                          ? "inline-flex rounded-md bg-sky-500/15 px-2 py-1 text-xs font-semibold text-sky-300 underline decoration-sky-500/35 underline-offset-4 hover:bg-sky-500/25"
                          : "inline-flex rounded-md bg-sky-600/10 px-2 py-1 text-xs font-semibold text-sky-700 underline decoration-sky-600/30 underline-offset-4 hover:bg-sky-600/15"
                      }
                      href={r.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open
                    </a>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  );
}
