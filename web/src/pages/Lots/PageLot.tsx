import { useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import type { CleEtapeLot } from "../../api/types";
import { Aide } from "../../components/Aide";
import { EtatVide } from "../../components/Etats";
import { Brief } from "./Brief";
import { EnTeteLot } from "./EnTeteLot";
import { Generation } from "./Generation";
import { References } from "./References";
import { ETAPE_DU_PLAN } from "./commun";
import "./Lots.css";

/** Ce que l'utilisateur fait à chaque étape, en une phrase : l'encadré d'aide en haut de l'écran. */
const AIDES: Partial<Record<CleEtapeLot, { titre: string; texte: string }>> = {
  brief: {
    titre: "Ici, tu choisis ce qui sera fabriqué.",
    texte: "L'app propose une liste d'objets d'après ta demande. Décoche ce dont tu n'as pas besoin : tu pourras en ajouter plus tard.",
  },
  references: {
    titre: "Ici, tu choisis à quoi ressemble chaque objet.",
    texte: "Pour chacun, l'app a dessiné plusieurs images. Garde celle qui ressemble le plus à ce que tu imagines : la 3D sera fabriquée d'après elle.",
  },
  generation: {
    titre: "Ici, il n'y a rien à faire.",
    texte: "L'app fabrique les objets. Tu es prévenu quand c'est prêt. Si un objet échoue, elle réessaie seule, sans te demander.",
  },
};

const A_VENIR: Partial<Record<CleEtapeLot, string>> = {
  revue: "La validation arrive",
  essai: "L'essai en scène arrive",
  jeu: "La récupération du pack arrive",
};

/** Un écran de projet : l'en-tête commun, l'aide de l'étape, puis l'écran (Objets, Look, Fabrication) ou « arrive à l'étape N » pour la suite. */
export function PageLot({ etape }: { etape: CleEtapeLot }) {
  const { id } = useParams();
  const lotId = Number(id);
  const [version, setVersion] = useState(0);
  const changement = useCallback(() => setVersion((v) => v + 1), []);
  const aide = AIDES[etape];

  return (
    <div className="page-lot">
      <EnTeteLot lotId={lotId} etape={etape} version={version} />
      {aide ? (
        <Aide cle={etape} titre={aide.titre}>
          {aide.texte}
        </Aide>
      ) : null}
      {etape === "brief" ? (
        <Brief lotId={lotId} onChangement={changement} />
      ) : etape === "references" ? (
        <References lotId={lotId} onChangement={changement} />
      ) : etape === "generation" ? (
        <Generation lotId={lotId} onChangement={changement} />
      ) : (
        <EtatVide titre={`${A_VENIR[etape]} à l'étape ${ETAPE_DU_PLAN[etape]} du plan`} />
      )}
    </div>
  );
}
