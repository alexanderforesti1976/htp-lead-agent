"""
HTP Lead Research Agent
Cerca potenziali clienti per HTP (automotive e industrial) e li salva su Google Sheet.
Gira su Render come cron job ogni notte.
"""

import os
import json
import time
import datetime
import anthropic
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Configurazione ──────────────────────────────────────────────────────────
SHEET_ID = "1X6_7RiA773b_e1b3s3-pvtunsHI35g0Lqqj2n_sZCUA"
SHEET_NAME = "Leads"
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]  # JSON come stringa

# Settori e paesi target
SEARCH_TARGETS = [
    # Italia
    {"paese": "Italia", "settore": "automotive", "query": "produttori componenti automotive Italia sistemi tenuta guarnizioni valvole"},
    {"paese": "Italia", "settore": "industrial", "query": "produttori valvole raccordi componenti idraulici industriali Italia"},
    # Germania
    {"paese": "Germania", "settore": "automotive", "query": "Automobilzulieferer Dichtungen Gummi Metall Deutschland Hersteller"},
    {"paese": "Germania", "settore": "industrial", "query": "Hersteller Ventile hydraulische Komponenten Dichtungen Deutschland"},
    # Francia
    {"paese": "Francia", "settore": "automotive", "query": "fabricants composants automobile joints étanchéité caoutchouc métal France"},
    {"paese": "Francia", "settore": "industrial", "query": "fabricants vannes raccords composants hydrauliques industriels France"},
    # Polonia
    {"paese": "Polonia", "settore": "automotive", "query": "producenci komponentów samochodowych uszczelnienia Polska"},
    # Spagna
    {"paese": "Spagna", "settore": "automotive", "query": "fabricantes componentes automoción juntas estanqueidad caucho metal España"},
]

# ── Google Sheets ────────────────────────────────────────────────────────────
def get_sheets_service():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return build("sheets", "v4", credentials=creds)

def init_sheet(service):
    """Crea l'intestazione se il foglio è vuoto."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!A1:A1"
    ).execute()
    
    if not result.get("values"):
        headers = [[
            "Data", "Azienda", "Paese", "Settore", "Dimensione",
            "Sito web", "Contatto", "Ruolo", "Email", "LinkedIn",
            "Telefono", "Perché HTP", "Stato", "Note"
        ]]
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME}!A1",
            valueInputOption="RAW",
            body={"values": headers}
        ).execute()

def get_existing_companies(service):
    """Legge le aziende già presenti per evitare duplicati."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!B:B"
    ).execute()
    values = result.get("values", [])
    return {row[0].strip().lower() for row in values if row}

def append_leads(service, leads):
    """Aggiunge nuovi lead al foglio."""
    if not leads:
        return
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": leads}
    ).execute()

# ── Web Search ───────────────────────────────────────────────────────────────
def web_search(query: str) -> str:
    """Usa l'API di Claude con web search tool."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": query}]
    )
    
    # Estrai testo dalla risposta
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text
    return text

# ── Agent Core ───────────────────────────────────────────────────────────────
def research_companies(target: dict, existing_companies: set) -> list:
    """Cerca aziende per un target specifico e restituisce lead qualificati."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    print(f"  → Cercando: {target['paese']} / {target['settore']}")
    
    # Step 1: Ricerca aziende
    search_prompt = f"""Sei un agente di ricerca commerciale per HTP - High Tech Project S.r.l., 
produttore italiano specializzato in guarnizioni sovrastampate gomma-metallo e gomma-plastica.

Cerca aziende potenzialmente interessate ai prodotti HTP in {target['paese']} nel settore {target['settore']}.

Query di ricerca: {target['query']}

HTP produce:
- Guarnizioni sovrastampate gomma-metallo e gomma-plastica
- Componenti di tenuta per automotive (Tier 2)
- Componenti di tenuta per applicazioni industriali (valvole, raccordi, pompe, sistemi idraulici)
- Articoli tecnici in gomma

Cerca almeno 5 aziende che:
1. Producono componenti che richiedono guarnizioni o sistemi di tenuta
2. Hanno 50-1000 dipendenti
3. Operano nei settori automotive o industrial

Per ogni azienda trovata fornisci:
- Nome azienda
- Sito web
- Dimensione (dipendenti stimati)
- Cosa producono
- Perché potrebbero aver bisogno di guarnizioni sovrastampate
- Contatto trovato (nome, ruolo, email o LinkedIn se pubblici)
- Numero di telefono se disponibile

Rispondi in formato JSON con una lista di aziende."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": search_prompt}]
    )
    
    # Estrai testo
    full_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            full_text += block.text
    
    if not full_text:
        return []
    
    # Step 2: Struttura i risultati
    parse_prompt = f"""Basandoti su questo testo di ricerca, estrai le informazioni sulle aziende trovate 
e restituisci un JSON valido con questa struttura esatta:

{{
  "aziende": [
    {{
      "nome": "Nome Azienda",
      "paese": "{target['paese']}",
      "settore": "{target['settore']}",
      "dimensione": "100-200 dipendenti",
      "sito": "www.esempio.com",
      "contatto_nome": "Mario Rossi (o vuoto se non trovato)",
      "contatto_ruolo": "Responsabile Acquisti (o vuoto)",
      "email": "email@esempio.com (o vuoto)",
      "linkedin": "url linkedin (o vuoto)",
      "telefono": "+39... (o vuoto)",
      "perche_htp": "Breve spiegazione perché potrebbero aver bisogno di HTP"
    }}
  ]
}}

Testo da analizzare:
{full_text[:3000]}

Restituisci SOLO il JSON, senza altro testo."""

    parse_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": parse_prompt}]
    )
    
    parse_text = ""
    for block in parse_response.content:
        if hasattr(block, "text"):
            parse_text += block.text
    
    # Pulisci e parsa JSON
    parse_text = parse_text.strip()
    if parse_text.startswith("```"):
        parse_text = parse_text.split("```")[1]
        if parse_text.startswith("json"):
            parse_text = parse_text[4:]
    
    try:
        data = json.loads(parse_text)
        aziende = data.get("aziende", [])
    except:
        print(f"    ⚠ Errore parsing JSON per {target['paese']}/{target['settore']}")
        return []
    
    # Filtra duplicati e prepara righe per Google Sheet
    today = datetime.date.today().strftime("%d/%m/%Y")
    rows = []
    
    for az in aziende:
        nome = az.get("nome", "").strip()
        if not nome or nome.lower() in existing_companies:
            continue
        
        existing_companies.add(nome.lower())
        
        rows.append([
            today,
            nome,
            az.get("paese", target["paese"]),
            az.get("settore", target["settore"]),
            az.get("dimensione", ""),
            az.get("sito", ""),
            az.get("contatto_nome", ""),
            az.get("contatto_ruolo", ""),
            az.get("email", ""),
            az.get("linkedin", ""),
            az.get("telefono", ""),
            az.get("perche_htp", ""),
            "Da contattare",
            ""
        ])
    
    print(f"    ✓ Trovate {len(rows)} nuove aziende")
    return rows

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"HTP Lead Agent - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}\n")
    
    # Setup Google Sheets
    print("Connessione a Google Sheets...")
    service = get_sheets_service()
    init_sheet(service)
    existing = get_existing_companies(service)
    print(f"Aziende già presenti: {len(existing)}\n")
    
    # Ricerca per ogni target
    all_leads = []
    for target in SEARCH_TARGETS:
        try:
            leads = research_companies(target, existing)
            all_leads.extend(leads)
            time.sleep(3)  # Pausa tra le ricerche
        except Exception as e:
            print(f"  ⚠ Errore per {target['paese']}/{target['settore']}: {e}")
    
    # Salva su Google Sheet
    if all_leads:
        print(f"\nSalvataggio {len(all_leads)} nuovi lead su Google Sheet...")
        append_leads(service, all_leads)
        print(f"✓ Completato!")
    else:
        print("\nNessun nuovo lead trovato in questa sessione.")
    
    print(f"\nProssima esecuzione: domani notte\n")

if __name__ == "__main__":
    main()
