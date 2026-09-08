import { NavLink, Route, Routes } from "react-router-dom";
import Annotations from "./pages/Annotations";
import Costs from "./pages/Costs";
import Datasets from "./pages/Datasets";
import Evaluations from "./pages/Evaluations";
import Overview from "./pages/Overview";
import Prompts from "./pages/Prompts";
import Regression from "./pages/Regression";
import TraceDetail from "./pages/TraceDetail";
import Traces from "./pages/Traces";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/traces", label: "Traces" },
  { to: "/evaluations", label: "Evaluations" },
  { to: "/prompts", label: "Prompts" },
  { to: "/datasets", label: "Datasets" },
  { to: "/regression", label: "Regression Tests" },
  { to: "/costs", label: "Costs" },
  { to: "/annotations", label: "Annotations" },
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Northwind<span>LLMOps</span>
        </div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
          >
            {item.label}
          </NavLink>
        ))}
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/traces" element={<Traces />} />
          <Route path="/traces/:traceId" element={<TraceDetail />} />
          <Route path="/evaluations" element={<Evaluations />} />
          <Route path="/prompts" element={<Prompts />} />
          <Route path="/datasets" element={<Datasets />} />
          <Route path="/regression" element={<Regression />} />
          <Route path="/costs" element={<Costs />} />
          <Route path="/annotations" element={<Annotations />} />
        </Routes>
      </main>
    </div>
  );
}
