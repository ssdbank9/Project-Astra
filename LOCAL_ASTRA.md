# Local Astra

The local application data is in `data/` beside this file. The entire directory
is ignored by Git: it contains private records and must not be published.
On Aly's machine, `Documents/AstraTest` was relocated here on 2026-10-07.
Other installations keep their own data locations.

The consistent pre-move backup is retained locally at
`data/backups/astra-before-consolidation-2026-10-07.sqlite3`.

From the Project-Astra folder, start the existing application with:

```powershell
.\Start-Astra.ps1
```

Open `http://127.0.0.1:8765` and use the existing login. Stop with Ctrl+C.
The launcher sets `ASTRA_HOME` to this checkout's `data` directory for the
server process and restores the previous setting when the server exits.
It refuses to start if the database is missing; it does not initialize accounts.
The normal server startup may run Astra's existing schema migrations.

To check the paths without starting the server:

```powershell
.\Start-Astra.ps1 -Check
```

Do not move this checkout into Dropbox, OneDrive or another file-sync location.
For backups while Astra is running, use SQLite's backup API rather than copying
only `astra.sqlite3`: committed data may still be in its WAL file.
