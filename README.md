# HTP Lead Research Agent

Agente autonomo che cerca potenziali clienti per HTP ogni notte e li salva su Google Sheet.

## Come funziona

- Gira ogni notte alle 2:00 su Render
- Cerca aziende automotive e industrial in Italia, Germania, Francia, Polonia, Spagna
- Salva nome, contatto, sito, telefono, email e motivazione su Google Sheet
- Evita duplicati automaticamente

## Deploy su Render

1. Carica questo codice su un repository GitHub (es. `htp-lead-agent`)
2. Vai su render.com → New → Cron Job
3. Collega il repository GitHub
4. Aggiungi le variabili d'ambiente:
   - `ANTHROPIC_API_KEY` = la tua chiave API Anthropic
   - `GOOGLE_CREDENTIALS_JSON` = il contenuto del file JSON scaricato da Google Cloud

## Google Sheet

ID foglio: `1X6_7RiA773b_e1b3s3-pvtunsHI35g0Lqqj2n_sZCUA`

Colonne:
- Data, Azienda, Paese, Settore, Dimensione
- Sito web, Contatto, Ruolo, Email, LinkedIn, Telefono
- Perché HTP, Stato, Note
