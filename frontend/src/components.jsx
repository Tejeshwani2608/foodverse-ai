import { useEffect, useState } from "react";

/** Run an async function with loading/error state. */
export function useTask() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const run = async (fn) => {
    setLoading(true);
    setError("");
    try {
      return await fn();
    } catch (e) {
      setError(e.message || "Something went wrong");
      return undefined;
    } finally {
      setLoading(false);
    }
  };
  return { loading, error, run, setError };
}

export const Err = ({ msg }) => (msg ? <div className="err" role="alert">{msg}</div> : null);

export const Badge = ({ tone = "ok", children }) => <span className={`badge ${tone}`}>{children}</span>;

export const Bar = ({ value }) => (
  <div className="bar" aria-label={`${value}%`}><span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>
);

export const toneFor = (score) => (score >= 70 ? "ok" : score >= 40 ? "warn" : "bad");

/** File picker with live preview for images or video. */
export function Upload({ accept, kind, onFile, label }) {
  const [url, setUrl] = useState(null);
  useEffect(() => () => url && URL.revokeObjectURL(url), [url]);
  const pick = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setUrl(URL.createObjectURL(f));
    onFile(f);
  };
  return (
    <div className="drop">
      <label>
        {label}
        <input type="file" accept={accept} onChange={pick} />
      </label>
      {url && kind === "image" && <img src={url} alt="Selected upload preview" />}
      {url && kind === "video" && <video src={url} controls muted />}
    </div>
  );
}

/** Tiny dependency-free sparkline. */
export function Spark({ values, max = 100 }) {
  if (!values?.length) return <p className="muted">No data yet.</p>;
  const w = 300, h = 60, step = values.length > 1 ? w / (values.length - 1) : 0;
  const pts = values.map((v, i) => `${i * step},${h - (Math.min(v, max) / max) * h}`).join(" ");
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label="trend">
      <polyline points={pts} fill="none" stroke="var(--brand)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export const AIExplanation = ({ text }) =>
  text ? <div className="card" style={{ background: "var(--bg)" }}><h3>AI explanation</h3><p>{text}</p></div> : null;
