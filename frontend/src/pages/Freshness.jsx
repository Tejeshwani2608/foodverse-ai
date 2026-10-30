import { useState } from "react";
import { postFile } from "../api";
import { AIExplanation, Badge, Bar, Err, Upload, useTask } from "../components";

const TONE = { Fresh: "ok", "Moderately Fresh": "warn", Spoiled: "bad" };

export default function Freshness() {
  const [file, setFile] = useState(null);
  const [res, setRes] = useState(null);
  const t = useTask();
  const go = () => t.run(async () => setRes(await postFile("/api/freshness/analyze", file)));

  return (
    <>
      <h1>Freshness &amp; Spoilage Detection</h1>
      <p className="muted">Colour, discolouration and surface-pattern analysis classifies food as Fresh, Moderately Fresh or Spoiled.</p>
      <div className="card">
        <Upload accept="image/*" kind="image" label="Choose a clear, well-lit photo of the food" onFile={setFile} />
        <div style={{ marginTop: ".75rem" }}>
          <button className="primary" disabled={!file || t.loading} onClick={go}>{t.loading ? "Analysing…" : "Check freshness"}</button>
        </div>
        <Err msg={t.error} />
      </div>
      {res && (
        <div className="card">
          <div className="row">
            <div><div className="big">{res.freshness_score}</div><div className="muted">freshness score</div></div>
            <Badge tone={TONE[res.label]}>{res.label}</Badge>
          </div>
          <Bar value={res.freshness_score} />
          <h3 style={{ marginTop: "1rem" }}>Findings</h3>
          <ul className="clean">{res.findings.map((f) => <li key={f}>{f}</li>)}</ul>
          <p><strong>Advice:</strong> {res.advice}</p>
          <table>
            <thead><tr><th>Indicator</th><th>Value</th></tr></thead>
            <tbody>{Object.entries(res.indicators).map(([k, v]) => <tr key={k}><td>{k.replace("_", " ")}</td><td>{v}</td></tr>)}</tbody>
          </table>
          <AIExplanation text={res.ai_explanation} />
          <p className="disclaimer">{res.disclaimer}</p>
        </div>
      )}
    </>
  );
}
