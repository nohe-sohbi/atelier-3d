import { useEffect, useState } from "react";
import { api, messageErreur } from "../../api/client";
import type { StyleDetail, StyleModifie } from "../../api/types";
import { Fenetre } from "../../components/Fenetre";

interface Props {
  ouverte: boolean;
  style: StyleDetail;
  onFermer: () => void;
  onModifie: (d: StyleDetail) => void;
}

/** Fenêtre « Modifier » (non dessinée dans la maquette, voir A-TRANCHER.md) : nom, description, palette, budgets, texels. */
export function ModifierStyle({ ouverte, style, onFermer, onModifie }: Props) {
  const [nom, setNom] = useState(style.nom);
  const [description, setDescription] = useState(style.description);
  const [palette, setPalette] = useState(style.palette);
  const [budgets, setBudgets] = useState<Record<string, string>>({});
  const [texel, setTexel] = useState(String(style.texel_density));
  const [erreur, setErreur] = useState<string | null>(null);
  const [occupe, setOccupe] = useState(false);

  useEffect(() => {
    if (!ouverte) return;
    setNom(style.nom);
    setDescription(style.description);
    setPalette(style.palette);
    setBudgets(Object.fromEntries(style.budgets.map((b) => [b.cle, b.tris === null ? "" : String(b.tris)])));
    setTexel(String(style.texel_density));
    setErreur(null);
  }, [ouverte, style]);

  const enregistrer = async () => {
    const corps: StyleModifie = {
      nom: nom.trim(),
      description: description.trim(),
      palette: Object.fromEntries(palette.filter((c) => c.nom.trim()).map((c) => [c.nom.trim(), c.hex])),
      budgets_tris: Object.fromEntries(Object.entries(budgets).map(([k, v]) => [k, Number(v)])),
      texel_density_px_per_m: Number(texel),
    };
    setOccupe(true);
    setErreur(null);
    try {
      onModifie(await api<StyleDetail>(`/styles/${style.id}`, { method: "PUT", body: JSON.stringify(corps) }));
    } catch (e) {
      setErreur(messageErreur(e));
    } finally {
      setOccupe(false);
    }
  };

  return (
    <Fenetre ouverte={ouverte} titre={`Modifier · ${style.nom}`} onFermer={onFermer}>
      {erreur ? (
        <div role="alert" className="fenetre-style__alerte" style={{ margin: "16px 24px 0" }}>
          {erreur}
        </div>
      ) : null}
      <div className="fenetre-style__corps">
        <div className="fenetre-style__grille2">
          <div className="fenetre-style__champ">
            <label htmlFor="ms-nom">Nom</label>
            <input id="ms-nom" type="text" className="champ" value={nom} onChange={(e) => setNom(e.target.value)} />
          </div>
          <div className="fenetre-style__champ">
            <label htmlFor="ms-texel">Densité de texels (px/m)</label>
            <input id="ms-texel" type="number" min={1} className="champ" value={texel} onChange={(e) => setTexel(e.target.value)} />
          </div>
        </div>
        <div className="fenetre-style__champ">
          <label htmlFor="ms-desc">Description</label>
          <textarea id="ms-desc" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="fenetre-style__champ">
          <span className="fenetre-style__legende-champ" id="ms-palette">
            Palette <span className="secondaire">· 8 à 12 couleurs ; les matériaux suivent leur couleur de base</span>
          </span>
          <ul role="list" aria-labelledby="ms-palette" className="fenetre-style__pastilles">
            {palette.map((c, i) => (
              <li key={i} className="fenetre-style__couleur">
                <input type="color" aria-label={`Couleur ${c.nom}`} value={c.hex} onChange={(e) => setPalette(palette.map((x, j) => (j === i ? { ...x, hex: e.target.value.toUpperCase() } : x)))} />
                <input type="text" aria-label={`Nom de la couleur ${i + 1}`} value={c.nom} onChange={(e) => setPalette(palette.map((x, j) => (j === i ? { ...x, nom: e.target.value } : x)))} />
              </li>
            ))}
          </ul>
        </div>
        <div className="fenetre-style__grille2">
          {style.budgets.map((b) => (
            <div key={b.cle} className="fenetre-style__champ">
              <label htmlFor={`ms-budget-${b.cle}`}>{b.libelle} (tris)</label>
              <input id={`ms-budget-${b.cle}`} type="number" min={1} className="champ" value={budgets[b.cle] ?? ""} onChange={(e) => setBudgets({ ...budgets, [b.cle]: e.target.value })} />
            </div>
          ))}
        </div>
      </div>
      <div className="fenetre-style__pied">
        <button type="button" className="bouton" onClick={onFermer}>
          Annuler
        </button>
        <span className="fenetre-style__espace" />
        <button type="button" className="bouton bouton--primaire" onClick={enregistrer} disabled={occupe || !nom.trim()}>
          Enregistrer
        </button>
      </div>
    </Fenetre>
  );
}
