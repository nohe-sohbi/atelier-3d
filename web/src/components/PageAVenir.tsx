import { EtatVide } from "./Etats";

/** Page d'un écran pas encore construit : jamais de fausses données. */
export function PageAVenir({ titre, etape }: { titre: string; etape: number }) {
  return (
    <>
      <div>
        <h1 className="page-titre">{titre}</h1>
      </div>
      <EtatVide titre={`Arrive à l'étape ${etape} du plan`} />
    </>
  );
}
