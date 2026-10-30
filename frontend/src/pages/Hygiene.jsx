import { useState } from "react";
import { postFile } from "../api";
import { AIExplanation, Badge, Bar, Err, Spark, Upload, toneFor, useTask } from "../components";

const LABEL = { glove_usage: "Glove usage", hair_cap: "Hair cap", food_handling: "Food handling", cleanliness: "Cleanliness" };
const STATUS_TONE = { Compliant: "ok", "Needs attention": "warn", "Non-compliant": "bad" };

export default function Hygiene() {
  const [file, setFile] = useState(null);
  const [res, setRes] = useState(null);
  const t = useTask();
  const go = () => t.run(async () => setRes(await postFile("/api/hygiene/analyze", file)));

  return (
    <>
      <h1>Restaurant Hygiene Monitor</h1>
      <p className="muted">Upload a kitchen video (MP4/MOV, up to 100 MB). Frames are sampled and scored for gloves, hair caps, food handling and cleanliness.</p>
      <div className="card">
        <Upload accept="video/*" kind="video" label="Choose a kitchen video" onFile={setFile} />
        <div style={{ marginTop: ".75rem" }}>
          <button className="primary" disabled={!file || t.loading} onClick={go}>{t.loading ? "Analysing video…" : "Analyse hygiene"}</button>
        </div>
        <Err msg={t.error} />
      </div>
      {res && (
        <>
          <div className="card">
            <div className="row">
              <div><div className="big">{res.overall_score}</div><div className="muted">overall hygiene</div></div>
              <Badge tone={STATUS_TONE[res.status]}>{res.status}</Badge>
              <span className="muted">{res.frames_analyzed} frames · {res.duration_s}s</span>
            </div>
            <div className="grid" style={{ marginTop: "1rem" }}>
              {Object.entries(res.indicator_scores).map(([k, v]) => (
                <div className="stat" key={k}>
                  <div className="muted">{LABEL[k]}</div>
                  <div className="v">{v}%</div>
                  <Bar value={v} />
                  <Badge tone={toneFor(v)}>{v >= 70 ? "good" : v >= 40 ? "watch" : "poor"}</Badge>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <h2>Alerts</h2>
            {res.alerts.length === 0 && <p>No compliance alerts raised.</p>}
            {res.alerts.map((a) => (
              <div key={a.indicator} className={`alert ${a.severity === "high" ? "danger" : "warn"}`}>
                <strong>{a.message}</strong>
                {a.timestamps_s.length > 0 && <div className="muted">At ~{a.timestamps_s.join("s, ")}s</div>}
              </div>
            ))}
            <h3>Recommendations</h3>
            <ul className="clean">{res.recommendations.map((r) => <li key={r}>{r}</li>)}</ul>
            <h3>Cleanliness over time</h3>
            <Spark values={res.timeline.map((f) => f.cleanliness * 100)} />
            <AIExplanation text={res.ai_explanation} />
            <p className="disclaimer">{res.disclaimer}</p>
          </div>
        </>
      )}
    </>
  );
}
