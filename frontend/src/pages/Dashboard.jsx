import { useEffect, useState } from "react";
import { del, getJSON } from "../api";
import { Err, Spark, useTask } from "../components";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const t = useTask();
  const load = () => t.run(async () => setData(await getJSON("/api/insights")));
  useEffect(() => { load(); }, []);
  const clear = () => t.run(async () => { await del("/api/insights"); await load(); });

  return (
    <>
      <h1>Insights Dashboard</h1>
      <p className="muted">Everything you analyse in FoodVerse AI is summarised here with alerts and trends.</p>
      <Err msg={t.error} />
      {data && data.total_events === 0 && (
        <div className="card">Nothing yet. Analyse a meal, a food photo or a kitchen video and results will appear here.</div>
      )}
      {data?.alerts.length > 0 && (
        <div className="card">
          <h2>Alerts</h2>
          {data.alerts.map((a, i) => <div key={i} className={`alert ${a.level}`}>{a.text}</div>)}
        </div>
      )}
      {data?.cards.length > 0 && (
        <div className="grid">
          {data.cards.map((c) => (
            <div className="stat" key={c.title}>
              <div className="muted">{c.title}</div><div className="v">{c.value}</div><div className="muted">{c.sub}</div>
            </div>
          ))}
        </div>
      )}
      {data?.total_events > 0 && (
        <div className="grid" style={{ marginTop: "1rem" }}>
          <div className="card"><h3>Meal health score</h3><Spark values={data.series.nutrition.map((x) => x.score)} /></div>
          <div className="card"><h3>Freshness score</h3><Spark values={data.series.freshness.map((x) => x.score)} /></div>
          <div className="card"><h3>Hygiene score</h3><Spark values={data.series.hygiene.map((x) => x.score)} /></div>
        </div>
      )}
      {data?.total_events > 0 && <button className="ghost" onClick={clear}>Clear history</button>}
    </>
  );
}
