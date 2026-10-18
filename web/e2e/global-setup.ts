import { demarrer } from "./serveur";

export default async function globalSetup() {
  await demarrer();
}
