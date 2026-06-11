import { useState } from "react";
import SignalsPanel from "./components/SignalsPanel";
import TasksPanel   from "./components/TasksPanel";
import RatingPanel  from "./components/RatingPanel";
import StatsPanel   from "./components/StatsPanel";

export default function App() {
  const [mainTab, setMainTab] = useState("calls");
  const today = new Date().toLocaleDateString("uz-UZ");

  return (
    <div className="min-h-screen bg-slate-900 p-4 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">CRM Real-time Dashboard</h1>
        <span className="text-xs text-slate-400">{today}</span>
      </header>

      {/* Top navigation */}
      <nav className="flex gap-1">
        {[
          { id: "calls",    label: "Qoʼngʼiroqlar" },
          { id: "telegram", label: "Telegram" },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setMainTab(t.id)}
            className={`px-5 py-2 rounded-lg text-sm font-semibold transition-colors ${
              mainTab === t.id
                ? "bg-blue-600 text-white shadow-lg"
                : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {mainTab === "calls" && (
        <>
          <SignalsPanel />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ minHeight: 380 }}>
            <TasksPanel />
            <RatingPanel />
          </div>
          <StatsPanel view="calls" />
        </>
      )}

      {mainTab === "telegram" && (
        <StatsPanel view="telegram" />
      )}
    </div>
  );
}
