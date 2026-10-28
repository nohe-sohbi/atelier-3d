import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { estActif } from "./navigation";

export function Icone({ d, taille = 22 }: { d: string; taille?: number }) {
  return (
    <svg width={taille} height={taille} viewBox="0 0 24 24" aria-hidden="true" style={{ display: "block", flex: "none" }}>
      <path d={d} style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" }} />
    </svg>
  );
}

export function LienMenu({ chemin, className, children }: { chemin: string; className: string; children: ReactNode }) {
  const { pathname } = useLocation();
  const actif = estActif(chemin, pathname);
  return (
    <Link to={chemin} className={className} aria-current={actif ? "page" : undefined}>
      {children}
    </Link>
  );
}
