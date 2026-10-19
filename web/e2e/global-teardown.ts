import { arreter } from "./serveur";

export default async function globalTeardown() {
  await arreter();
}
