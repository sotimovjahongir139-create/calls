import SignalsPanel from "./components/SignalsPanel";
import TasksPanel   from "./components/TasksPanel";
import RatingPanel  from "./components/RatingPanel";
import StatsPanel   from "./components/StatsPanel";

export default function App() {
  const today = new Date().toLocaleDateString("uz-UZ");
  return (
    <div className="min-h-screen bg-slate-900 p-4 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">CRM Real-time Dashboard</h1>
        <span className="text-xs text-slate-400">{today}</span>
      </header>

      <SignalsPanel />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ minHeight: 380 }}>
        <TasksPanel />
        <RatingPanel />
      </div>

      <StatsPanel />
    </div>
  );
}
