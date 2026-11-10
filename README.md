# La mia libreria

Libreria interattiva per Notion, ispirata al layout editoriale "The Personal Curation":
dorsi colorati su una mensola, libri in lettura esposti di copertina, scheda di dettaglio al clic.

- `index.html` — la pagina (nessuna dipendenza, solo Google Fonts)
- `books.json` — i libri, generato da `sync.py`
- `sync.py` — legge il database **Library** di Notion e riscrive `books.json`
- `.github/workflows/sync.yml` — esegue `sync.py` ogni 30 minuti su GitHub Actions

Indirizzo pubblico: https://elisamagli.github.io/libreria/ (incorporato nella pagina Notion "Libreria").

## Messa online (una volta sola)

1. **Integrazione Notion** — vai su https://www.notion.so/profile/integrations → *Nuova integrazione*
   → nome "Libreria", tipo *Interna*, capacità solo *Leggi contenuti* → copia il *Secret*.
2. **Condividi il database** — in Notion apri il database *Library* → `•••` in alto a destra
   → *Connessioni* → aggiungi "Libreria".
3. **Repository** — su GitHub crea il repository pubblico `libreria` e carica `index.html`,
   `books.json`, `sync.py`, `README.md` (*Add file → Upload files*).
4. **Workflow** — *Add file → Create new file*, nome `.github/workflows/sync.yml`, incolla il contenuto del file omonimo.
5. **Token** — *Settings → Secrets and variables → Actions → New repository secret*:
   nome `NOTION_TOKEN`, valore il Secret del punto 1.
6. **Pages** — *Settings → Pages* → Source *Deploy from a branch* → `main` / `(root)` → Save.
7. **Primo aggiornamento** — *Actions → Sincronizza libreria da Notion → Run workflow*.

## Come si aggiorna

Aggiungi o modifica un libro nel database Library: entro 30 minuti compare sulla mensola
(per farlo subito: *Actions → Run workflow*). Usa Name, Author, Editore, Genre, Rating, Status,
Total Pages, Pages Read, Date Finished.

**Copertine**: se la pagina del libro ha una copertina impostata come *Link* (Cambia copertina → Link),
viene usata quella; altrimenti si cerca su Open Library; se non c'è, la libreria disegna una copertina tipografica.

GitHub sospende i workflow programmati dopo 60 giorni senza attività nel repository: se succede,
basta premere *Enable workflow* nella scheda Actions.
