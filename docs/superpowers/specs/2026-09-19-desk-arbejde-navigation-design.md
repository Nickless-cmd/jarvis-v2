# Desk Arbejde: sammenhængende navigation og sider

## Formål

Alle funktioner i Desk Arbejde skal kunne findes via meningsfulde kategorier. Sider med én lille indstilling samles med beslægtet indhold. Hver side bruger samme sidetitel, introduktion, sektionsoverskrifter, kort, kontroller og afstande. Codex-skærmbillederne fra 19. september 2026 er reference for læsbarhed og konsistens, mens Desk beholder sin egen mørke palet og teal-accent.

## Navigation

Arbejde viser følgende destinationer:

| Gruppe | Destination | Nuværende indhold |
| --- | --- | --- |
| Arbejde | Mission Control | Eksisterende oversigt, kørsler, godkendelser, opgaver, planer, agenter, forbrug og hændelser |
| Arbejde | Agent pool | Agentoversigt, liste og seneste arbejde |
| Arbejde | Modeller og kapacitet | Cheap Lane og udbydere |
| Arbejde | Værktøjer og forbindelser | Marketplace, apps, MCP og plugins |
| Indstillinger | Generelt | Udseende, sprog, svarstil, notifikationer og placering |
| Indstillinger | Konto og sikkerhed | Profil, kvote, enheder, 2FA, privatliv og tilladelser |
| Indstillinger | Arbejdsområde | Workspace og workbench |
| Indstillinger | Jarvis og hukommelse | Hukommelse, tilstedeværelse og Jarvis-indstillinger |
| System | Systemstatus | Central og Jarvis Mind |
| Om | Om og hjælp | Om, genveje og forbindelse |

Owner-only indhold skjules for andre roller som i dag. Direkte `emitZone`-kald med gamle zone-id'er skal fortsat åbne den nye kategori og føre brugeren til den tilsvarende sektion, så Jarvis' `open_ui_panel`, paletten og interne knapper ikke går i stykker.

## Sideopbygning

Hver samlet side har en header med titel og én sætning om, hvad brugeren kan gøre. Indholdet står i navngivne sektioner med fælles layout; detaljerede driftsflader kan bruge fuld bredde, mens indstillinger begrænses til læsbar kolonnebredde. Lange tekniske rådata vises i deres eksisterende detaljevisninger. Denne ændring omfatter ikke nye backend-endpoints eller ændret politik for godkendelser.

## Kvalitetskrav

- Ingen nuværende menu-funktion må forsvinde.
- Ingen side i Arbejde må bestå af én løs kontrol uden sidekontekst.
- Agent pools faner og nøgletal skal bruge tilsigtet Desk-styling.
- Aktivt menupunkt skal følge både brugerklik og programmatisk navigation.
- Eksisterende unit tests, renderer-build og manuel visuel gennemgang af alle nye sider skal bestå.
