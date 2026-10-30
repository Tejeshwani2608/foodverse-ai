import { useState } from "react";
import { postJSON } from "../api";
import { Badge, Err, useTask } from "../components";

export default function Cooking() {
  const [ingredients, setIngredients] = useState("dal, onion, tomato, garlic, cumin");
  const [diet, setDiet] = useState("any");
  const [maxMin, setMaxMin] = useState("");
  const [res, setRes] = useState(null);
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState(null);
  const t = useTask();
  const ta = useTask();

  const suggest = () =>
    t.run(async () =>
      setRes(await postJSON("/api/cooking/suggest", {
        ingredients: ingredients.split(",").map((s) => s.trim()).filter(Boolean),
        diet,
        max_minutes: maxMin ? Number(maxMin) : null,
      })));

  const ask = () => ta.run(async () => setAnswer(await postJSON("/api/cooking/ask", { question: q, context: { diet, ingredients } })));

  return (
    <>
      <h1>Smart Cooking Assistant</h1>
      <p className="muted">Tell me what you have and I'll suggest recipes with ingredient lists, steps and tips.</p>
      <div className="card">
        <label>Ingredients you have (comma separated)
          <textarea rows="2" value={ingredients} onChange={(e) => setIngredients(e.target.value)} />
        </label>
        <div className="row" style={{ marginTop: ".5rem" }}>
          <label>Diet
            <select value={diet} onChange={(e) => setDiet(e.target.value)}>
              <option value="any">Any</option><option value="vegetarian">Vegetarian</option>
              <option value="vegan">Vegan</option><option value="eggetarian">Eggetarian</option>
            </select>
          </label>
          <label>Max minutes<input type="number" min="5" value={maxMin} onChange={(e) => setMaxMin(e.target.value)} placeholder="any" /></label>
          <button className="primary" disabled={t.loading || !ingredients.trim()} onClick={suggest}>Suggest recipes</button>
        </div>
        <Err msg={t.error} />
      </div>

      {res && res.recipes.length === 0 && <div className="card">No matching recipes. Try adding more ingredients or relaxing filters.</div>}
      {res?.recipes.map((r) => (
        <div className="card" key={r.name}>
          <div className="row">
            <h2 style={{ margin: 0 }}>{r.name}</h2>
            <Badge tone={r.match_percent >= 70 ? "ok" : "warn"}>{r.match_percent}% match</Badge>
            <span className="muted">{r.minutes} min · {r.cuisine}</span>
          </div>
          <div className="chips">
            {r.have.map((i) => <span key={i} className="chip">✓ {i}</span>)}
            {r.missing.map((i) => <span key={i} className="chip miss">+ {i}</span>)}
          </div>
          <h3>Steps</h3>
          <ol>{r.steps.map((s) => <li key={s}>{s}</li>)}</ol>
          <p className="muted">Tips: {r.tips.join(" ")}</p>
        </div>
      ))}

      <div className="card">
        <h2>Ask a cooking question</h2>
        <div className="row">
          <label style={{ flex: "3 1 260px" }}>Question
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="My curry is too salty – what now?"
              onKeyDown={(e) => e.key === "Enter" && q.trim().length > 1 && ask()} />
          </label>
          <button className="primary" disabled={ta.loading || q.trim().length < 2} onClick={ask}>Ask</button>
        </div>
        <Err msg={ta.error} />
        {answer && <p style={{ marginTop: ".75rem" }}>{answer.answer} <span className="muted">({answer.method})</span></p>}
      </div>
    </>
  );
}
