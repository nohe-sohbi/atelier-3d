import { Outlet } from "react-router-dom";
import { EnTete } from "./EnTete";
import "./Layout.css";

export function Layout() {
  return (
    <div className="layout">
      <EnTete />
      <main className="layout__contenu">
        <Outlet />
      </main>
    </div>
  );
}
