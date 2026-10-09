"""
HTP Lead Research Agent v3
Cerca potenziali clienti per HTP con query tecniche specifiche.
"""

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

# Tutti i materiali elastomerici lavorati da HTP (aggiunti alle query di ricerca)
MATERIALI_HTP = "NBR EPDM FKM HNBR VMQ MVQ FMVQ ACM AEM ECO CR"

# Ogni notte vengono processati MAX_TARGETS_PER_RUN target scelti ciclicamente
# così da coprire sempre query diverse senza ripetere le stesse
MAX_TARGETS_PER_RUN = 8

SEARCH_TARGETS = [
    # ── ITALIA ──────────────────────────────────────────────────────────────
    {"paese": "Italia", "settore": "Valvole industriali", "query": "produttori valvole industriali italiani guarnizioni elastomero tenuta sede valvola NBR EPDM"},
    {"paese": "Italia", "settore": "Pompe centrifughe", "query": "produttori pompe centrifughe Italia tenuta meccanica elastomero guarnizioni gomma"},
    {"paese": "Italia", "settore": "Raccordi idraulici", "query": "produttori raccordi idraulici pneumatici Italia guarnizioni O-ring NBR FKM"},
    {"paese": "Italia", "settore": "HVAC climatizzazione", "query": "produttori componenti HVAC climatizzazione Italia tenuta refrigerante guarnizioni elastomero"},
    {"paese": "Italia", "settore": "Automotive Tier2", "query": "fornitori automotive Tier2 Italia sistemi tenuta fluidi guarnizioni gomma metallo sovrastampaggio"},
    {"paese": "Italia", "settore": "Oil Gas", "query": "produttori componenti oil gas Italia valvole guarnizioni FKM EPDM alta pressione"},
    {"paese": "Italia", "settore": "Alimentare food processing", "query": "produttori attrezzature food processing alimentare Italia guarnizioni FDA EPDM tenuta igienica"},
    {"paese": "Italia", "settore": "Trattamento acque", "query": "produttori sistemi trattamento acque depurazione Italia valvole guarnizioni EPDM cloro resistenti"},
    {"paese": "Italia", "settore": "Farmaceutico", "query": "produttori componenti farmaceutici biofarmaceutici Italia guarnizioni silicone VMQ EPDM FDA"},
    {"paese": "Italia", "settore": "Compressori aria", "query": "produttori compressori aria industriali Italia valvole guarnizioni elastomero tenuta pistone"},
    {"paese": "Italia", "settore": "Macchine agricole", "query": "produttori componenti macchine agricole Italia guarnizioni idraulica elastomero"},
    {"paese": "Italia", "settore": "Antincendio", "query": "produttori sistemi antincendio sprinkler Italia valvole guarnizioni tenuta EPDM"},
    {"paese": "Italia", "settore": "Stampi e macchine utensili", "query": "costruttori macchine utensili presse Italia guarnizioni idrauliche NBR tenuta olio"},
    {"paese": "Italia", "settore": "Pneumatica", "query": "produttori attuatori cilindri pneumatici Italia guarnizioni NBR tenuta aria compressa"},

    # ── GERMANIA ────────────────────────────────────────────────────────────
    {"paese": "Germania", "settore": "Industrieventile", "query": "Hersteller Industrieventile Dichtungen Elastomer EPDM NBR FKM Deutschland Sitzventil"},
    {"paese": "Germania", "settore": "Pumpen", "query": "Hersteller Pumpen Deutschland Wellendichtung Elastomer Gleitringdichtung Gummi"},
    {"paese": "Germania", "settore": "Automotive", "query": "Automobilzulieferer Deutschland Dichtungssystem Kuehlmittel Hydraulik Gummi Metall overmolded"},
    {"paese": "Germania", "settore": "Hydraulik", "query": "Hersteller Hydraulikkomponenten Zylinder Deutschland Dichtungen NBR FKM Hochdruck"},
    {"paese": "Germania", "settore": "Lebensmitteltechnik", "query": "Hersteller Lebensmittelmaschinen Deutschland FDA Dichtungen EPDM Silikon Hygiene"},
    {"paese": "Germania", "settore": "Chemietechnik", "query": "Hersteller Chemieventile Reaktoren Deutschland FKM PTFE Dichtungen chemikalienbestaendig"},
    {"paese": "Germania", "settore": "Druckluft Pneumatik", "query": "Hersteller Druckluftkomponenten Pneumatikzylinder Deutschland NBR Dichtungen"},
    {"paese": "Germania", "settore": "Wassertechnik", "query": "Hersteller Wasseraufbereitung Klaeranlage Deutschland EPDM Dichtungen Absperrventile"},

    # ── FRANCIA ─────────────────────────────────────────────────────────────
    {"paese": "Francia", "settore": "Robinetterie industrielle", "query": "fabricants robinets vannes industrielles France joints elastomere EPDM NBR etancheite"},
    {"paese": "Francia", "settore": "Pompes industrielles", "query": "fabricants pompes industrielles France joints dynamiques etancheite elastomere"},
    {"paese": "Francia", "settore": "Automotive", "query": "equipementiers automobiles France joints etancheite fluides gomme metal surmoulage"},
    {"paese": "Francia", "settore": "Agroalimentaire", "query": "fabricants equipements agroalimentaires France joints FDA EPDM silicone etancheite hygiénique"},
    {"paese": "Francia", "settore": "Hydraulique", "query": "fabricants composants hydrauliques France joints NBR FKM haute pression verin"},

    # ── SPAGNA ──────────────────────────────────────────────────────────────
    {"paese": "Spagna", "settore": "Valvulas industriales", "query": "fabricantes valvulas industriales España juntas elastomero EPDM NBR estanqueidad"},
    {"paese": "Spagna", "settore": "Automotive", "query": "proveedores componentes automocion España juntas estanqueidad caucho metal sobremoldeo"},
    {"paese": "Spagna", "settore": "Alimentaria", "query": "fabricantes equipos industria alimentaria España juntas FDA EPDM silicona higiénica"},
    {"paese": "Spagna", "settore": "Tratamiento aguas", "query": "fabricantes sistemas tratamiento aguas España valvulas juntas EPDM"},

    # ── POLONIA ─────────────────────────────────────────────────────────────
    {"paese": "Polonia", "settore": "Automotive", "query": "producenci podzespolow samochodowych Polska uszczelnienia elastomer guma metal"},
    {"paese": "Polonia", "settore": "Przemysl zawory", "query": "producenci zaworow pomp przemyslowych Polska uszczelnienia elastomerowe NBR EPDM"},
    {"paese": "Polonia", "settore": "Hydraulika", "query": "producenci komponentow hydraulicznych Polska uszczelnienia NBR wysocisnieniowe silowniki"},

    # ── BENELUX ─────────────────────────────────────────────────────────────
    {"paese": "Belgio/Olanda", "settore": "Valves industrial", "query": "manufacturers industrial valves Belgium Netherlands elastomer seals EPDM NBR FKM"},
    {"paese": "Belgio/Olanda", "settore": "Automotive", "query": "automotive suppliers Belgium Netherlands rubber metal overmolded sealing gaskets Tier2"},
    {"paese": "Belgio/Olanda", "settore": "Food processing", "query": "food processing equipment manufacturers Belgium Netherlands FDA EPDM silicone seals hygienic"},
    {"paese": "Belgio/Olanda", "settore": "Water treatment", "query": "water treatment equipment Netherlands Belgium EPDM seals valves pumps"},

    # ── UK ──────────────────────────────────────────────────────────────────
    {"paese": "UK", "settore": "Valves pumps", "query": "manufacturers valves pumps UK elastomer seals rubber metal overmoulded gaskets fluid sealing"},
    {"paese": "UK", "settore": "Oil Gas offshore", "query": "manufacturers oil gas offshore components UK FKM HNBR seals high pressure valves"},
    {"paese": "UK", "settore": "Pharmaceutical", "query": "pharmaceutical biotech equipment manufacturers UK FDA silicone EPDM seals hygienic"},

    # ── SVEZIA / SCANDINAVIA ─────────────────────────────────────────────────
    {"paese": "Svezia/Scandinavia", "settore": "Industrial valves", "query": "manufacturers industrial valves pumps Sweden Norway Denmark elastomer seals rubber"},
    {"paese": "Svezia/Scandinavia", "settore": "Mining", "query": "mining equipment manufacturers Sweden Norway rubber seals high wear elastomer components"},

    # ── AUSTRIA ─────────────────────────────────────────────────────────────
    {"paese": "Austria", "settore": "Maschinenbau", "query": "Maschinenbau Hersteller Oesterreich Dichtungen Elastomer Hydraulik Pneumatik Ventile"},
    {"paese": "Austria", "settore": "Automotive", "query": "Automobilzulieferer Oesterreich Dichtungssysteme Gummi Metall overmolded"},

    # ── SVIZZERA ─────────────────────────────────────────────────────────────
    {"paese": "Svizzera", "settore": "Pharma Medtech", "query": "pharma medtech equipment manufacturers Switzerland FDA silicone EPDM seals clean room"},
    {"paese": "Svizzera", "settore": "Valvole precisione", "query": "Hersteller Praezisionsventile Schweiz Dichtungen Elastomer Reinraum"},

    # ── REPUBBLICA CECA / SLOVACCHIA ─────────────────────────────────────────
    {"paese": "Rep. Ceca/Slovacchia", "settore": "Automotive", "query": "automotive component manufacturers Czech Republic Slovakia rubber metal seals overmolded Tier2"},
    {"paese": "Rep. Ceca/Slovacchia", "settore": "Industrial", "query": "vyrobci prumyslovych ventilu cerpadel Ceska Republika tesneni elastomer"},

    # ── UNGHERIA / ROMANIA ───────────────────────────────────────────────────
    {"paese": "Ungheria/Romania", "settore": "Automotive", "query": "automotive suppliers Hungary Romania rubber seals overmolded components Tier1 Tier2"},

    # ── PORTOGALLO ───────────────────────────────────────────────────────────
    {"paese": "Portogallo", "settore": "Automotive", "query": "fornecedores componentes automovel Portugal vedantes borracha metal sobremoldagem"},

    # ── QUERY PER NICCHIA TECNICA (cross-paese) ──────────────────────────────
    {"paese": "Europa", "settore": "Valvole a farfalla", "query": "butterfly valve manufacturers Europe elastomer lined seat rubber EPDM NBR"},
    {"paese": "Europa", "settore": "Valvole a sfera", "query": "ball valve seat manufacturers Europe PTFE rubber EPDM FKM sealing"},
    {"paese": "Europa", "settore": "Attuatori rotativi", "query": "rotary actuator manufacturers Europe rubber metal seals hydraulic pneumatic"},
    {"paese": "Europa", "settore": "Pompe dosatrici", "query": "dosing pump diaphragm pump manufacturers Europe EPDM FKM rubber diaphragm seals"},
    {"paese": "Europa", "settore": "Sistemi freno automotive", "query": "automotive brake system component manufacturers Europe rubber metal seals EPDM"},
    {"paese": "Europa", "settore": "Raffreddamento automotive", "query": "automotive cooling system component manufacturers Europe rubber metal overmolded gaskets hoses"},
    {"paese": "Europa", "settore": "Compressori frigoriferi", "query": "refrigeration compressor manufacturers Europe NBR HNBR FKM seals refrigerant"},
    {"paese": "Europa", "settore": "Filtrazione industriale", "query": "industrial filtration housing manufacturers Europe rubber gaskets EPDM NBR sealing"},
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


def get_run_state(service):
    """Legge l'indice del prossimo target da processare dal foglio 'State'."""
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheet_names = [s["properties"]["title"] for s in spreadsheet["sheets"]]
        if "State" not in sheet_names:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={"requests": [{"addSheet": {"properties": {"title": "State"}}}]}
            ).execute()
            return 0
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range="State!A1"
        ).execute()
        values = result.get("values", [])
        if values and values[0]:
            return int(values[0][0])
        return 0
    except Exception as e:
        print(f"  Errore lettura state: {e}")
        return 0


def save_run_state(service, next_index):
    """Salva l'indice del prossimo target da processare."""
    try:
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range="State!A1",
            valueInputOption="RAW",
            body={"values": [[next_index]]}
        ).execute()
    except Exception as e:
        print(f"  Errore salvataggio state: {e}")


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


def extract_json_from_text(text: str) -> dict | None:
    """Estrae il JSON dalla risposta testuale in modo robusto."""
    if not text:
        return None

    # 1. Prova blocco ```json ... ```
    if "```json" in text:
        try:
            start = text.index("```json") + 7
            end = text.index("```", start)
            candidate = text[start:end].strip()
            return json.loads(candidate)
        except Exception:
            pass

    # 2. Prova blocco ``` ... ```
    if "```" in text:
        parts = text.split("```")
        for part in parts[1::2]:  # parti dispari = dentro i backtick
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                try:
                    return json.loads(part)
                except Exception:
                    pass

    # 3. Trova il primo { e l'ultimo } bilanciato
    start = text.find("{")
    if start == -1:
        return None

    # Cerca il } bilanciato partendo dall'inizio del JSON
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        return None

    try:
        return json.loads(text[start:end])
    except Exception:
        pass

    # 4. Fallback: cerca dall'ultimo { (a volte c'è testo prima del JSON reale)
    last_start = text.rfind('{"aziende"')
    if last_start != -1:
        try:
            return json.loads(text[last_start:])
        except Exception:
            pass

    return None


def discover_companies(target: dict, existing_companies: set, client) -> list:
    """Step 1 — GRATIS, niente web search.
    Chiede a Claude le aziende che conosce già dal training nel settore/paese dato.
    Restituisce lista di dict {nome, sito, citta, paese, dimensione, prodotto, perche_htp}.
    """
    existing_list = ", ".join(sorted(existing_companies)[:60]) if existing_companies else "nessuna"

    prompt = f"""Sei un esperto di mercato industriale europeo. Elenca 5 aziende REALI che conosci
in {target['paese']} nel settore: {target['settore']}.

CRITERI:
- 50-500 dipendenti (PMI, Tier 2/3 — NO multinazionali)
- Producono componenti che incorporano guarnizioni/tenute in gomma: valvole, pompe, attuatori, sistemi idraulici/pneumatici, componenti automotive, ecc.
- Sede principale in {target['paese']}

⛔ ESCLUDI:
- Produttori guarnizioni/O-ring: Freudenberg, Parker Hannifin, Trelleborg, Hutchinson, SKF, NOK, Simrit
- Produttori articoli gomma: MB Guarnizioni, Effegomma, AL-GOM, Elastotech, Novotema
- Multinazionali Tier 1: Eaton, Bosch Rexroth, Kolbenschmidt, Pierburg, Sachs, ZF, Linamar, HYDAC, KSB, Poclain, Bucher Hydraulics, Continental, Faurecia, BorgWarner, Dana, Valeo, Knorr-Bremse, Wabco
- Distributori, agenzie
- Già in lista: {existing_list}

Rispondi SOLO con JSON valido:
{{"aziende": [{{"nome": "", "sito": "", "citta": "", "paese": "", "dimensione": "", "prodotto": "", "perche_htp": ""}}]}}"""

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        print(f"    ⚠ Errore discovery: {e}")
        return []

    text = "".join(b.text for b in resp.content if hasattr(b, "text") and b.text)
    data = extract_json_from_text(text)
    if data is None:
        return []
    return data.get("aziende", [])


def find_contacts(companies: list, client) -> list:
    """Step 2 — WEB SEARCH mirato, 1 ricerca per azienda.
    Per ogni azienda cerca il contatto diretto: CEO, General Manager o Responsabile Acquisti.
    Restituisce la lista arricchita con contatto_nome, contatto_ruolo, email, linkedin, telefono.
    """
    if not companies:
        return []

    # Costruisci lista testuale delle aziende per il prompt
    lines = "\n".join(
        f"{i+1}. {az['nome']} — {az.get('sito', 'sito sconosciuto')} — {az.get('paese', '')}"
        for i, az in enumerate(companies)
    )

    max_searches = len(companies)  # 1 ricerca dedicata per azienda

    prompt = f"""Sei un ricercatore B2B. Per OGNUNA delle seguenti aziende devi trovare il contatto
diretto: CEO, Amministratore Delegato, General Manager, o Responsabile Acquisti.

AZIENDE DA CERCARE:
{lines}

STRATEGIA — usa esattamente UNA web_search per azienda:
- Query tipo: "[nome azienda] CEO amministratore delegato LinkedIn" oppure
  "[nome azienda] purchasing manager email" oppure
  "[nome azienda] general manager nome cognome"
- Cerca su LinkedIn, sito aziendale, Kompass, Europages, comunicati stampa

FORMATO RISPOSTA — JSON con tutti i campi:
{{"contatti": [
  {{
    "nome_azienda": "nome esatto come nella lista sopra",
    "contatto_nome": "Nome Cognome",
    "contatto_ruolo": "CEO / Amministratore Delegato / General Manager / Responsabile Acquisti",
    "email": "nome.cognome@azienda.com (SOLO email personale diretta, MAI info@ o contatti@)",
    "linkedin": "https://www.linkedin.com/in/nome-cognome",
    "telefono": "+39 030 xxxxxxx"
  }}
]}}

⚠ REGOLE ASSOLUTE:
- NON inventare nomi, email o LinkedIn — SOLO dati trovati online
- Se non trovi nulla per un'azienda, metti tutti i campi vuoti (ma includi nome_azienda)
- email info@, contatti@, contact@, office@, general@ → lascia email VUOTO"""

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2500,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_searches
            }],
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        print(f"    ⚠ Errore contact lookup: {e}")
        return companies  # restituisce aziende senza contatti piuttosto che niente

    search_count = sum(1 for b in resp.content if hasattr(b, "type") and b.type == "tool_use")
    print(f"    → Web search contatti: {search_count}/{max_searches}")

    text = "".join(b.text for b in resp.content if hasattr(b, "text") and b.text)
    data = extract_json_from_text(text)
    if data is None:
        return companies

    # Merge: abbina i contatti trovati alle aziende per nome
    contacts_by_name = {
        c["nome_azienda"].strip().lower(): c
        for c in data.get("contatti", [])
        if c.get("nome_azienda")
    }

    # Filtro email generiche
    generic_prefixes = ("info@", "contatti@", "contact@", "kontakt@", "general@", "office@", "admin@")

    enriched = []
    for az in companies:
        key = az["nome"].strip().lower()
        c = contacts_by_name.get(key, {})
        email = c.get("email", "").strip()
        if email.lower().startswith(generic_prefixes):
            email = ""
        enriched.append({**az,
            "contatto_nome": c.get("contatto_nome", ""),
            "contatto_ruolo": c.get("contatto_ruolo", ""),
            "email": email,
            "linkedin": c.get("linkedin", ""),
            "telefono": c.get("telefono", ""),
        })
    return enriched


def research_companies(target: dict, existing_companies: set) -> list:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print(f"  → Cercando: {target['paese']} / {target['settore']}")

    # Step 1: scopri aziende (gratis, solo training Claude)
    companies = discover_companies(target, existing_companies, client)
    # Filtra duplicati
    companies = [az for az in companies if az.get("nome") and az["nome"].strip().lower() not in existing_companies]
    if not companies:
        print(f"    ⚠ Nessuna azienda trovata nello step 1")
        return []
    print(f"    → Aziende trovate (step 1): {len(companies)}")

    # Step 2: cerca contatti diretti con web search mirata
    companies = find_contacts(companies, client)

    today = datetime.date.today().strftime("%d/%m/%Y")
    rows = []

    for az in companies:
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


def cleanup_empty_leads(service):
    """Rimuove dal foglio Leads le righe senza alcun dato di contatto (nome, email, LinkedIn tutti vuoti)."""
    print("Pulizia lead senza contatti...")
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME}!A:N"
        ).execute()
        all_rows = result.get("values", [])

        if len(all_rows) <= 1:
            print("  Nessun dato da pulire.")
            return

        # Identifica righe (0-based, riga 0 = header) dove nome azienda c'è ma contatto, email, linkedin sono tutti vuoti
        to_delete = []
        for i, row in enumerate(all_rows):
            if i == 0:
                continue  # skip header
            nome_az = row[1].strip() if len(row) > 1 else ""
            contatto = row[6].strip() if len(row) > 6 else ""
            email = row[8].strip() if len(row) > 8 else ""
            linkedin = row[9].strip() if len(row) > 9 else ""
            if nome_az and not contatto and not email and not linkedin:
                to_delete.append(i)

        if not to_delete:
            print("  Nessun lead vuoto trovato.")
            return

        print(f"  Trovate {len(to_delete)} righe senza contatti da rimuovere...")

        # Ottieni il sheetId numerico del foglio "Leads"
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheet_id = None
        for s in spreadsheet["sheets"]:
            if s["properties"]["title"] == SHEET_NAME:
                sheet_id = s["properties"]["sheetId"]
                break

        if sheet_id is None:
            print("  ⚠ Foglio Leads non trovato.")
            return

        # Elimina in ordine inverso per non spostare gli indici
        requests = []
        for row_idx in sorted(to_delete, reverse=True):
            requests.append({
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_idx,
                        "endIndex": row_idx + 1
                    }
                }
            })

        service.spreadsheets().batchUpdate(
            spreadsheetId=SHEET_ID,
            body={"requests": requests}
        ).execute()

        print(f"  ✓ Rimosse {len(to_delete)} righe senza contatti dal foglio.")
    except Exception as e:
        print(f"  ⚠ Errore durante pulizia: {e}")


def main():
    print(f"\n{'='*50}")
    print(f"HTP Lead Agent v3 - {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}\n")

    print("Connessione a Google Sheets...")
    service = get_sheets_service()
    init_sheet(service)
    cleanup_empty_leads(service)
    existing = get_existing_companies(service)
    print(f"Aziende già presenti: {len(existing)}")
    print(f"Target totali disponibili: {len(SEARCH_TARGETS)}\n")

    # Leggi da dove riprendere
    start_index = get_run_state(service)
    print(f"Indice di partenza: {start_index} (rotazione su {len(SEARCH_TARGETS)} target)\n")

    # Seleziona MAX_TARGETS_PER_RUN target consecutivi in modo ciclico
    targets_this_run = []
    for i in range(MAX_TARGETS_PER_RUN):
        idx = (start_index + i) % len(SEARCH_TARGETS)
        targets_this_run.append((idx, SEARCH_TARGETS[idx]))

    next_index = (start_index + MAX_TARGETS_PER_RUN) % len(SEARCH_TARGETS)

    all_leads = []
    for idx, target in targets_this_run:
        try:
            leads = research_companies(target, existing)
            all_leads.extend(leads)
            time.sleep(3)
        except Exception as e:
            print(f"  ⚠ Errore per {target['paese']}/{target['settore']}: {e}")

    if all_leads:
        print(f"\nSalvataggio {len(all_leads)} nuovi lead su Google Sheet...")
        append_leads(service, all_leads)
        print(f"✓ Completato!")
    else:
        print("\nNessun nuovo lead trovato in questa run.")

    # Salva il prossimo indice
    save_run_state(service, next_index)
    print(f"Prossima run partirà dall'indice {next_index} ({SEARCH_TARGETS[next_index]['paese']} / {SEARCH_TARGETS[next_index]['settore']})")
    print(f"\nProssima esecuzione: domani notte\n")


if __name__ == "__main__":
    main()
