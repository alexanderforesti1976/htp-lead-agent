"""
HTP Lead Research Agent v2
Cerca potenziali clienti per HTP con query tecniche specifiche.
"""
h
import os
import json
import time
import datetime
import anthropic
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = "1X6_7RiA773b_e1b3s3-pvtunsHI35g0Lqqj2n_sZCUA"
SHEET_NAME = "Leads"
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_CREDENTIALS_JSON = os.environ["GOOGLE_CREDENTIALS_JSON"]

# Query tecniche specifiche per aziende che usano guarnizioni elastomeriche
SEARCH_TARGETS = [
    # Italia - valvole e raccordi
    {"paese": "Italia", "settore": "Valvole industriali", "query": "produttori valvole industriali Italia guarnizioni elastomero tenuta sede valvola"},
    {"paese": "Italia", "settore": "Pompe", "query": "produttori pompe centrifughe volumetriche Italia tenuta meccanica elastomero"},
    {"paese": "Italia", "settore": "Raccordi idraulici", "query": "produttori raccordi idraulici pneumatici Italia guarnizioni O-ring NBR FKM"},
    {"paese": "Italia", "settore": "Climatizzazione", "query": "produttori componenti HVAC climatizzazione Italia tenuta refrigerante guarnizioni elastomero"},
    {"paese": "Italia", "settore": "Automotive Tier2", "query": "produttori componenti automotive Tier2 Italia sistemi tenuta fluidi guarnizioni gomma metallo"},
    {"paese": "Italia", "settore": "Oil Gas", "query": "produttori componenti oil gas Italia valvole guarnizioni FKM EPDM alta pressione tenuta"},
    
    # Germania
    {"paese": "Germania", "settore": "Valvole industriali", "query": "Hersteller Industrieventile Dichtungen Elastomer EPDM NBR FKM Deutschland Sitzventil"},
    {"paese": "Germania", "settore": "Pompe", "query": "Hersteller Pumpen Deutschland Wellendichtung Elastomer Gleitringdichtung Gummi"},
    {"paese": "Germania", "settore": "Automotive", "query": "Automobilzulieferer Deutschland Dichtungssystem Kuehlmittel Hydraulik Gummi Metall overmolded"},
    {"paese": "Germania", "settore": "Hydraulik", "query": "Hersteller Hydraulikkomponenten Deutschland Dichtungen NBR FKM Hochdruck"},
    
    # Francia
    {"paese": "Francia", "settore": "Valvole", "query": "fabricants robinets vannes industrielles France joints elastomere EPDM NBR etancheite"},
    {"paese": "Francia", "settore": "Pompes", "query": "fabricants pompes industrielles France joints dynamiques etancheite elastomere"},
    {"paese": "Francia", "settore": "Automotive", "query": "equipementiers automobiles France joints etancheite fluides gomme metal surmoulage"},
    
    # Spagna
    {"paese": "Spagna", "settore": "Valvulas", "query": "fabricantes valvulas industriales España juntas elastomero EPDM NBR estanqueidad"},
    {"paese": "Spagna", "settore": "Automotive", "query": "proveedores componentes automocion España juntas estanqueidad caucho metal sobremoldeo"},
    
    # Polonia - mercato in crescita
    {"paese": "Polonia", "settore": "Automotive", "query": "producenci podzespolow samochodowych Polska uszczelnienia elastomer guma metal"},
    {"paese": "Polonia", "settore": "Przemysl", "query": "producenci zaworow pomp przemyslowych Polska uszczelnienia elastomerowe NBR EPDM"},
    
    # Benelux
    {"paese": "Belgio/Olanda", "settore": "Valves", "query": "manufacturers industrial valves Belgium Netherlands elastomer seals EPDM NBR FKM high pressure"},
    {"paese": "Belgio/Olanda", "settore": "Automotive", "query": "automotive suppliers Belgium Netherlands rubber metal overmolded sealing gaskets Tier2"},
    
    # UK
    {"paese": "UK", "settore": "Valves pumps", "query": "manufacturers valves pumps UK elastomer seals rubber metal overmoulded gaskets fluid sealing"},
    
    # Svezia/Scandinavia
    {"paese": "Svezia/Scandinavia", "settore": "Industrial", "query": "manufacturers industrial valves pumps Sweden Norway Denmark elastomer seals rubber gaskets"},
]

def get_sheets_service():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return build("sheets", "v4", credentials=creds)

def ensure_sheet_exists(service):
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    sheet_names = [s["properties"]["title"] for s in spreadsheet["sheets"]]
    if SHEET_NAME not in sheet_names:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": SHEET_NAME}}}]}
        ).execute()
        print(f"Foglio '{SHEET_NAME}' creato.")

def init_sheet(service):
    ensure_sheet_exists(service)
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
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"{SHEET_NAME}!B:B"
    ).execute()
    values = result.get("values", [])
    return {row[0].strip().lower() for row in values if row}

def append_leads(service, leads):
    if not leads:
        return
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": leads}
    ).execute()

def research_companies(target: dict, existing_companies: set) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print(f"  → Cercando: {target['paese']} / {target['settore']}")

    search_prompt = f"""Sei un agente di ricerca commerciale B2B per HTP - High Tech Project S.r.l., 
produttore italiano specializzato in guarnizioni sovrastampate gomma-metallo e gomma-plastica.

HTP produce componenti di tenuta in elastomero sovrastampati su inserto metallico o plastico:
- Guarnizioni statiche e dinamiche sovrastampate
- Componenti per valvole (sedi valvola, otturatori con guarnizione integrata)
- Tenute per pompe e sistemi idraulici
- Componenti automotive (sistemi di tenuta fluidi, raffreddamento, climatizzazione)
- Articoli tecnici in gomma NBR, EPDM, FKM, HNBR, VMQ su progetto

I CLIENTI IDEALI di HTP sono aziende che:
- Producono valvole industriali, raccordi, componenti idraulici o pneumatici
- Producono pompe centrifughe, volumetriche, dosatrici
- Producono componenti automotive (sistemi raffreddamento, climatizzazione, freni, carburante)
- Producono sistemi HVAC, refrigerazione, trattamento acque
- Hanno nel loro prodotto guarnizioni elastomeriche gomma-metallo o guarnizioni statiche/dinamiche in gomma tecnica
- Hanno 50-1000 dipendenti
- Sono in {target['paese']}

Esegui questa ricerca web: {target['query']}

Trova almeno 5-8 aziende CONCRETE con nome reale, non agenzie o distributori.
Per ogni azienda fornisci:
- Nome azienda esatto
- Sito web
- Città e paese
- Dimensione stimata (dipendenti)
- Prodotto principale che richiederebbe guarnizioni elastomeriche
- Nome e ruolo del responsabile acquisti o R&D se trovabile pubblicamente
- Email o LinkedIn se pubblici
- Telefono se disponibile

Rispondi SOLO in JSON con questa struttura:
{{"aziende": [{{"nome": "", "sito": "", "citta": "", "paese": "", "dimensione": "", "prodotto": "", "contatto_nome": "", "contatto_ruolo": "", "email": "", "linkedin": "", "telefono": "", "perche_htp": ""}}]}}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": search_prompt}]
    )

    full_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            full_text += block.text

    if not full_text:
        return []

    # Pulisci e parsa JSON
    text = full_text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            if part.startswith("json"):
                text = part[4:].strip()
                break
            elif "{" in part:
                text = part.strip()
                break

    try:
        # Trova il JSON nella risposta
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
        else:
            return []
        aziende = data.get("aziende", [])
    except:
        print(f"    ⚠ Errore parsing JSON")
        return []

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
            az.get("prodotto", target["settore"]),
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

def main():
    print(f"\n{'='*50}")
    print(f"HTP Lead Agent v2 - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}\n")

    print("Connessione a Google Sheets...")
    service = get_sheets_service()
    init_sheet(service)
    existing = get_existing_companies(service)
    print(f"Aziende già presenti: {len(existing)}\n")

    all_leads = []
    for target in SEARCH_TARGETS:
        try:
            leads = research_companies(target, existing)
            all_leads.extend(leads)
            time.sleep(2)
        except Exception as e:
            print(f"  ⚠ Errore per {target['paese']}/{target['settore']}: {e}")

    if all_leads:
        print(f"\nSalvataggio {len(all_leads)} nuovi lead su Google Sheet...")
        append_leads(service, all_leads)
        print(f"✓ Completato!")
    else:
        print("\nNessun nuovo lead trovato.")

    print(f"\nProssima esecuzione: domani notte\n")

if __name__ == "__main__":
    main()
