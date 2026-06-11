import { useState } from "react";
import SignalsPanel from "./components/SignalsPanel";
import TasksPanel   from "./components/TasksPanel";
import RatingPanel  from "./components/RatingPanel";
import StatsPanel   from "./components/StatsPanel";

export default function App() {
  const [mainTab, setMainTab] = useState("calls");
  const today = new Date().toLocaleDateString("uz-UZ");

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm px-5 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">CRM Dashboard</h1>
        <span className="text-xs text-gray-400">{today}</span>
      </header>

      <div className="p-4 space-y-4 max-w-7xl mx-auto">
        <nav className="flex gap-2">
          {[
            { id: "calls",    label: "📞 Qoʼngʼiroqlar" },
            { id: "telegram", label: "💬 Telegram" },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setMainTab(t.id)}
              className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${
                mainTab === t.id
                  ? "bg-blue-600 text-white shadow-sm"
                  : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {mainTab === "calls" && (
          <>
            <SignalsPanel />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
    </div>
  );
}
