import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";

export function TypingText({ text, className = "" }) {
  const safe = useMemo(() => (text || "").replace(/\r/g, ""), [text]);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    setIdx(0);
  }, [safe]);

  useEffect(() => {
    if (idx >= safe.length) return;
    const speed = safe.length > 1200 ? 1 : 2;
    const t = window.setTimeout(() => setIdx((v) => Math.min(v + speed, safe.length)), 12);
    return () => window.clearTimeout(t);
  }, [idx, safe]);

  const shown = safe.slice(0, idx);

  return (
    <motion.div
      initial={{ opacity: 0.2 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25 }}
      className={className}
    >
      <span className="whitespace-pre-wrap">{shown}</span>
    </motion.div>
  );
}
