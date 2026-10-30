import { useEffect, useState } from "react";
import { getJSON } from "./api";
import Cooking from "./pages/Cooking.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Freshness from "./pages/Freshness.jsx";
import Hygiene from "./pages/Hygiene.jsx";
import MealPlan from "./pages/MealPlan.jsx";
import Recognize from "./pages/Recognize.jsx";

const TABS = [
  { id: "dash", icon: "📊", label: "Dashboard", C: Dashboard },
  { id: "food", icon: "🍎", label: "Recognize & Nutrition", C: Recognize },
  { id: "fresh", icon: "🥬", label: "Freshness", C: Freshness },
  { id: "hyg", icon: "🧤", label: "Kitchen Hygiene", C: Hygiene },
  { id: "cook", icon: "🍳", label: "Cooking Assistant", C: Cooking },
  { id: "plan", icon: "🗓️", label: "Meal Plan", C: MealPlan },
];

export default function App() {
  const [tab, setTab] = useState("dash");
  const [health, setHealth] = useState(null);
  useEffect(() => { getJSON("/api/health").then(setHealth).catch(() => setHealth(false)); }, []);
  const Page = TABS.find((t) => t.id === tab).C;

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">🍽️ FoodVerse AI</div>
        <nav className="nav">
          {TABS.map((t) => (
            <button key={t.id} className={tab === t.id ? "active" : ""} onClick={() => setTab(t.id)}>
              <span aria-hidden>{t.icon}</span>{t.label}
            </button>
          ))}
        </nav>
        <div className="status">
          <span className={`dot ${health ? "on" : ""}`} />
          {health === null ? "Connecting…" : health ? `API online · ${health.llm_enabled ? "LLM on" : "local models"}` : "API offline – start the backend"}
        </div>
      </aside>
      <main className="main"><Page key={tab} /></main>
    </div>
  );
}
