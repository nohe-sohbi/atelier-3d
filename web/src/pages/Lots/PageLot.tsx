import { useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import type { CleEtapeLot } from "../../api/types";
import { EtatVide } from "../../components/Etats";
import { Brief } from "./Brief";
import { EnTeteLot } from "./EnTeteLot";
import { Generation } from "./Generation";
import { References } from "./References";
import { ETAPE_DU_PLAN } from "./commun";
import "./Lots.css";

/** Un écran de lot : l'en-tête commun, puis le Brief, les Références ou la Génération, ou « Arrive à l'étape N » pour la Revue. */
export function PageLot({ etape }: { etape: CleEtapeLot }) {
  const { id } = useParams();
  const lotId = Number(id);
  const [version, setVersion] = useState(0);
  const changement = useCallback(() => setVersion((v) => v + 1), []);

  return (
    <div className="page-lot">
      <EnTeteLot lotId={lotId} etape={etape} version={version} />
      {etape === "brief" ? (
        <Brief lotId={lotId} onChangement={changement} />
      ) : etape === "references" ? (
        <References lotId={lotId} onChangement={changement} />
      ) : etape === "generation" ? (
        <Generation lotId={lotId} onChangement={changement} />
      ) : (
        <EtatVide titre={`Arrive à l'étape ${ETAPE_DU_PLAN[etape]} du plan`} />
      )}
    </div>
  );
}
