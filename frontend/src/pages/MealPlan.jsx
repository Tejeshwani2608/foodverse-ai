import { useState } from "react";
import { postJSON } from "../api";
import { Err, useTask } from "../components";

const DEFAULTS = { age: 21, sex: "male", height_cm: 172, weight_kg: 65, activity: "light", goal: "maintain", diet: "vegetarian", avoid: "", days: 3 };

export default function MealPlan() {
  const [f, setF] = useState(DEFAULTS);
  const [res, setRes] = useState(null);
  const t = useTask();
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));
  const num = (k) => ({ type: "number", value: f[k], onChange: set(k) });

  const go = () =>
    t.run(async () =>
      setRes(await postJSON("/api/mealplan/generate", {
        ...f,
        age: +f.age, height_cm: +f.height_cm, weight_kg: +f.weight_kg, days: +f.days,
        avoid: f.avoid.split(",").map((s) => s.trim()).filter(Boolean),
      })));

  const sel = (k, opts) => (
    <select value={f[k]} onChange={set(k)}>{opts.map((o) => <option key={o}>{o}</option>)}</select>
  );

  return (
    <>
      <h1>Personalised Meal Planner</h1>
      <p className="muted">Calorie and macro targets (Mifflin-St Jeor) turned into a day-by-day plan that fits your diet.</p>
      <div className="card">
        <div className="row">
          <label>Age<input {...num("age")} min="10" max="100" /></label>
          <label>Sex{sel("sex", ["male", "female"])}</label>
          <label>Height (cm)<input {...num("height_cm")} /></label>
          <label>Weight (kg)<input {...num("weight_kg")} /></label>
        </div>
        <div className="row" style={{ marginTop: ".5rem" }}>
          <label>Activity{sel("activity", ["sedentary", "light", "moderate", "active"])}</label>
          <label>Goal{sel("goal", ["lose", "maintain", "gain"])}</label>
          <label>Diet{sel("diet", ["any", "vegetarian", "vegan", "eggetarian"])}</label>
          <label>Days<input {...num("days")} min="1" max="7" /></label>
        </div>
        <label style={{ marginTop: ".5rem" }}>Foods to avoid (comma separated)
          <input value={f.avoid} onChange={set("avoid")} placeholder="e.g. paneer, egg" />
        </label>
        <div style={{ marginTop: ".75rem" }}><button className="primary" disabled={t.loading} onClick={go}>Generate plan</button></div>
        <Err msg={t.error} />
      </div>

      {res && (
        <>
          <div className="grid">
            <div className="stat"><div className="muted">Daily target</div><div className="v">{res.targets.kcal} kcal</div></div>
            <div className="stat"><div className="muted">Protein</div><div className="v">{res.targets.protein_g} g</div></div>
            <div className="stat"><div className="muted">Carbs / Fat</div><div className="v">{res.targets.carbs_g} / {res.targets.fat_g} g</div></div>
            <div className="stat"><div className="muted">BMI</div><div className="v">{res.targets.bmi}</div></div>
          </div>
          {res.plan.map((d) => (
            <div className="card" key={d.day} style={{ marginTop: "1rem" }}>
              <h2>Day {d.day} <span className="muted">· {d.kcal} kcal · {d.protein_g} g protein</span></h2>
              <table>
                <tbody>
                  {Object.entries(d.meals).map(([slot, items]) => (
                    <tr key={slot}>
                      <th style={{ textTransform: "capitalize", width: 110 }}>{slot}</th>
                      <td>{items.map((i) => `${i.servings}× ${i.food} (${i.kcal} kcal)`).join(", ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          {res.notes.map((n) => <p key={n} className="disclaimer">{n}</p>)}
        </>
      )}
    </>
  );
}
