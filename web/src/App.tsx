import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ROUTES } from "./routes";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {ROUTES.map((r) => (
          <Route key={r.chemin} path={r.chemin} element={r.element} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
