import { useState } from "react";
import { postFile, postJSON } from "../api";
import { AIExplanation, Badge, Bar, Err, Upload, toneFor, useTask } from "../components";

export default function Recognize() {
  const [file, setFile] = useState(null);
  const [detected, setDetected] = useState(null);
  const [selected, setSelected] = useState({}); // food -> servings
  const [nutrition, setNutrition] = useState(null);
  const [manual, setManual] = useState("");
  const t = useTask();

  const recognize = () =>
    t.run(async () => {
      const r = await postFile("/api/food/recognize", file);
      setDetected(r);
      setNutrition(null);
      setSelected(Object.fromEntries(r.detected.slice(0, 1).map((d) => [d.food, 1])));
    });

  const analyze = () =>
    t.run(async () => {
      const items = Object.entries(selected).map(([food, servings]) => ({ food, servings: Number(servings) || 1 }));
      setNutrition(await postJSON("/api/food/nutrition", { items }));
    });

  const toggle = (food) =>
    setSelected((s) => {
      const n = { ...s };
      if (n[food]) delete n[food]; else n[food] = 1;
      return n;
    });

  const addManual = () => {
    const f = manual.trim().toLowerCase();
    if (f) setSelected((s) => ({ ...s, [f]: 1 }));
    setManual("");
  };

  return (
    <>
      <h1>Food Recognition &amp; Nutrition</h1>
      <p className="muted">Upload a food photo, confirm what was detected, then get calories, macros and a health score.</p>
      <div className="card">
        <Upload accept="image/*" kind="image" label="Choose a food photo" onFile={setFile} />
        <div style={{ marginTop: ".75rem" }}>
          <button className="primary" disabled={!file || t.loading} onClick={recognize}>
            {t.loading ? "Working…" : "Identify food"}
          </button>
        </div>
        <Err msg={t.error} />
      </div>

      {detected && (
        <div className="card">
          <h2>Detected <span className="muted">({detected.method})</span></h2>
          <p className="muted">{detected.note}</p>
          <div className="chips">
            {detected.detected.map((d) => (
              <label key={d.food} className="chip" style={{ cursor: "pointer" }}>
                <input type="checkbox" style={{ width: "auto", margin: "0 .4rem 0 0" }} checked={!!selected[d.food]}
                  onChange={() => toggle(d.food)} />
                {d.food} · {Math.round(d.confidence * 100)}%
              </label>
            ))}
          </div>
          <div className="row" style={{ marginTop: ".75rem" }}>
            <label>Add another food<input value={manual} onChange={(e) => setManual(e.target.value)} placeholder="e.g. dal, roti, egg" /></label>
            <button className="ghost" onClick={addManual}>Add</button>
          </div>
          {Object.entries(selected).map(([food, s]) => (
            <div className="row" key={food} style={{ marginTop: ".5rem" }}>
              <strong style={{ flex: "1 1 120px" }}>{food}</strong>
              <label>Servings
                <input type="number" min="0.5" step="0.5" value={s}
                  onChange={(e) => setSelected((x) => ({ ...x, [food]: e.target.value }))} />
              </label>
            </div>
          ))}
          <div style={{ marginTop: ".75rem" }}>
            <button className="primary" disabled={!Object.keys(selected).length || t.loading} onClick={analyze}>
              Analyse nutrition
            </button>
          </div>
        </div>
      )}

      {nutrition && (
        <div className="card">
          <h2>Nutrition summary</h2>
          <div className="grid">
            <div className="stat"><div className="muted">Calories</div><div className="v">{nutrition.totals.kcal}</div></div>
            <div className="stat"><div className="muted">Protein</div><div className="v">{nutrition.totals.protein_g} g</div></div>
            <div className="stat"><div className="muted">Carbs</div><div className="v">{nutrition.totals.carbs_g} g</div></div>
            <div className="stat"><div className="muted">Fat</div><div className="v">{nutrition.totals.fat_g} g</div></div>
          </div>
          <h3 style={{ marginTop: "1rem" }}>Health score <Badge tone={toneFor(nutrition.health_score)}>{nutrition.health_score}/100</Badge></h3>
          <Bar value={nutrition.health_score} />
          <table style={{ marginTop: "1rem" }}>
            <thead><tr><th>Food</th><th>Serving</th><th>kcal</th><th>P</th><th>C</th><th>F</th></tr></thead>
            <tbody>
              {nutrition.items.map((i) => (
                <tr key={i.food}><td>{i.food}</td><td>{i.servings} × {i.serving}</td><td>{i.kcal}</td>
                  <td>{i.protein_g}</td><td>{i.carbs_g}</td><td>{i.fat_g}</td></tr>
              ))}
            </tbody>
          </table>
          <ul className="clean">{nutrition.advice.map((a) => <li key={a}>{a}</li>)}</ul>
          {nutrition.unknown?.length > 0 && <p className="muted">Not in database: {nutrition.unknown.join(", ")}</p>}
          <AIExplanation text={nutrition.ai_explanation} />
          <p className="disclaimer">Estimates based on typical servings; not medical advice.</p>
        </div>
      )}
    </>
  );
}
