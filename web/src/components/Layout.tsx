import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import "./Layout.css";

export function Layout() {
  return (
    <div className="layout">
      <Sidebar />
      <div className="layout__corps">
        <TopBar />
        <main className="layout__contenu">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
