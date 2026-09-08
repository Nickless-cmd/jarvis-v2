/**
 * Hvad der VISES af kant og krom i desk-appen.
 *
 * Bjørn 8/9-2026: «der er meget mere og har undgået det længe.» Vi går
 * igennem designet stykke for stykke, og så skal det være billigt at slå
 * noget fra, se på det i en dag, og tage det tilbage hvis det manglede.
 *
 * Derfor ét sted med boolske værdier frem for at rive komponenter ud. Diffen
 * bliver læsbar, og «tænd den igen» er ét tegn — ikke arkæologi i git-loggen.
 *
 * Dette er ikke en indstilling brugeren kan ændre. Det er en designbeslutning
 * vi arbejder på; når noget har stået slukket længe nok til at ingen savner
 * det, ryger koden ud.
 */
export const DESK_CHROME = {
  /** Bund-statusbaren: lane · model · status · session-id. */
  statusbar: false,

  /** Header: git-gren ("main"). Grenen står stadig i miljø-panelet. */
  headerGit: false,

  /** Header: systemsundhed ("Alt kører"). Ægte fejl vises stadig i samtalen. */
  headerHealth: false,

  /** Header: forbindelse + ping ("api.srvlab.dk · 5 ms"). */
  headerConnection: false,

  /**
   * Miljø-panel: Maskine / GPU / Disk. Kontekst BLIVER — det er det ene tal
   * derinde der ændrer en beslutning (skal jeg starte forfra?).
   */
  envMachineRows: false,
} as const
