# Write your code here :-)
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from io import BytesIO
import tempfile
import os
from fpdf import FPDF
from math import pi
import requests
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import folium_static
from geopy.extra.rate_limiter import RateLimiter
import plotly.express as px

# ======================
# CONSTANTEN - AANGEPASTE VERSIE MET DUIDELIJKERE BEOORDELINGEN
# ======================
SCORE_LEGEND = {
    "Ruimtelijke Inpassing": {
        "Bestemmingsplan": {
            5: "Volledig conform omgevingsplan",
            3: "Kleine afwijking, vergunning nodig",
            1: "Niet conform, planwijziging vereist"
        },
        "Kadastrale beperkingen": {
            5: "Geen beperkingen",
            3: "Beperkte erfdienstbaarheden",
            1: "Zware beperkingen zoals pandrecht/overpad"
        },
        "Nutsvoorzieningen": {
            5: "Water, elektra en gas aanwezig (directe aansluiting)",
            3: "Niet aanwezig, maar makkelijk aan te leggen",
            1: "Niet aanwezig en lastig te realiseren"
        },
        "Infrastructuur": {
            5: "Geen obstakels",
            3: "Verplaatsbare obstakels aanwezig",
            1: "Vaste obstructies, KLIC-melding verplicht"
        }
    },
    "Milieunormen": {
        "Natura 2000-gebied": {
            5: "Meer dan 5km verwijderd van Natura 2000-gebied",
            3: "Bevindt zich binnen 3-5km van Natura 2000-gebied",
            1: "In nabijheid <3km van Natura 2000-gebied"
        },
        "Luchtkwaliteit": {
            5: "Ruim binnen NSL-norm",
            3: "Net aan NSL-norm",
            1: "NSL-norm overschreden"
        },
        "Bodemkwaliteit": {
            5: "Klasse 0 (schoon)",
            3: "Klasse 1-2 (beperkte sanering)",
            1: "Klasse 3-4 (zware verontreiniging)"
        }
    },
    "Veiligheid": {
        "Externe veiligheid": {
            5: "Geen BRZO-bedrijven binnen 500m",
            3: "1 BRZO-bedrijf binnen 500m",
            1: "≥2 BRZO-bedrijven binnen 500m"
        },
        "Bodemgeschiktheid": {
            5: "≥120 kN/m² (funderingsmogelijkheden optimaal)",
            3: "80-120 kN/m² (aanpassingen nodig)",
            1: "<80 kN/m² (paalfundering vereist)"
        },
        "Bouwtechniek": {
            5: "Geen bijzondere maatregelen nodig",
            3: "Aanpassingen vereist",
            1: "Fundamentele problemen"
        }
    },
    "Bereikbaarheid": {
        "Wegontsluiting": {
            5: "≥2 toegangswegen (CROW-richtlijn)",
            3: "1 toegangsweg",
            1: "Geen directe ontsluiting"
        },
        "Openbaar vervoer": {
            5: "OV-halte ≤400m",
            3: "OV-halte >400m",
            1: "Geen OV in de buurt"
        },
        "Fietsbereikbaarheid": {
            5: "Aansluiting op LF-routes (Fietsersbond)",
            3: "Redelijke verbindingen",
            1: "Slechte fietsroutes"
        },
        "Parkeren": {
            5: "Ruim voldoende parkeren",
            3: "Voldoende parkeren",
            1: "Onvoldoende capaciteit"
        }
    }
}

SCORE_COLORS = {
    1: "#ff6b6b",  # Rood
    2: "#ffa502",  # Oranje
    3: "#ffd166",  # Geel
    4: "#06d6a0",  # Lichtgroen
    5: "#1b9e75"   # Donkergroen
}

@st.cache_data(show_spinner=False, ttl=3600)
def cached_geocode(address):
    """Gecachede versie van geolocatie-opzoekingen"""
    geolocator = Nominatim(user_agent="cached_locator")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    return geocode(address)

# ======================
# PDF HULPFUNCTIES
# ======================
def fig_to_bytes(fig):
    """Converteer matplotlib figuur naar tijdelijk bestand"""
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    fig.savefig(temp_file.name, format='png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    return temp_file.name

def generate_clean_csv(df):
    """Genereer een goed geformatteerde CSV"""
    export_df = df.copy()
    csv = export_df.to_csv(index=False, sep=';', encoding='utf-8')
    return csv.encode('utf-8')

def generate_pdf(locatie):
    """Genereer een compleet PDF rapport met visualisaties en totaalscore"""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=16, style='B')

        # Titelpagina
        pdf.cell(0, 20, txt=f"Locatie Rapport: {locatie}", ln=1, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, txt=f"Datum: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=1)
        pdf.ln(10)

        loc_data = st.session_state.df[st.session_state.df["Locatie"] == locatie].iloc[0]

        # Scores printen
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(0, 10, txt="Scores per criterium", ln=1)
        pdf.set_font("Arial", size=10)

        totaalscore = 0
        maxscore = 0
        for criterium in SCORE_LEGEND.keys():
            score = loc_data.get(criterium, None)
            if score is not None:
                totaalscore += score
                maxscore += 5
                pdf.cell(0, 10, f"{criterium}: {score}/5", ln=1)

        pdf.ln(5)
        if maxscore > 0:
            percentage = totaalscore / maxscore * 100
            pdf.set_font("Arial", size=12, style='B')
            pdf.cell(0, 10, f"Totaalscore: {totaalscore}/{maxscore} ({percentage:.0f}%)", ln=1)

        pdf.ln(10)
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(0, 10, txt="Opmerkingen", ln=1)
        pdf.set_font("Arial", size=10)
        opmerkingen = str(loc_data.get("Opmerkingen") or "Geen")
        pdf.multi_cell(0, 10, txt=opmerkingen.replace('\n', ' '))

        return pdf.output(dest="S").encode("latin1")
    except Exception as e:
        st.error(f"Fout bij genereren PDF: {str(e)}")
        return None


def hex_to_rgb(hex_color):
    """Converteer hex kleur naar RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_bar_chart(locatie):
    """Maak staafdiagram voor PDF"""
    fig, ax = plt.subplots(figsize=(10, 5))
    data = st.session_state.df[st.session_state.df["Locatie"] == locatie][list(SCORE_LEGEND.keys())].T
    data.plot(kind='bar', ax=ax, color=[SCORE_COLORS[x] for x in data.values[0]])
    plt.title(f"Scores voor {locatie}")
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def create_radar_chart(df, locaties):
    """Maak radarplot voor locatievergelijking"""
    categories = list(SCORE_LEGEND.keys())
    N = len(categories)

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)

    for loc in locaties:
        values = df[df["Locatie"] == loc][categories].values.flatten().tolist()
        values += values[:1]
        angles = [n / float(N) * 2 * pi for n in range(N)]
        angles += angles[:1]
        ax.plot(angles, values, linewidth=1, linestyle='solid', label=loc)
        ax.fill(angles, values, alpha=0.1)

    ax.set_theta_offset(pi / 2)
    ax.set_theta_direction(-1)
    plt.xticks(angles[:-1], categories)
    ax.set_rlabel_position(0)
    plt.ylim(0, 5)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    return fig

def verwijder_locatie(locatie):
    """Verwijder een locatie uit de dataset"""
    if locatie in st.session_state.df["Locatie"].values:
        st.session_state.df = st.session_state.df[st.session_state.df["Locatie"] != locatie]
        st.success(f"Locatie '{locatie}' is verwijderd")
        st.rerun()
    else:
        st.error("Locatie niet gevonden")

def get_coordinates(address):
    """Haal coördinaten op voor een adres met geopy"""
    geolocator = Nominatim(user_agent="locatie_beoordeling_app")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    try:
        location = geocode(address)
        if location:
            return (location.latitude, location.longitude)
        return None
    except Exception as e:
        st.error(f"Fout bij ophalen coördinaten: {str(e)}")
        return None

def show_map(latitude, longitude, zoom=15):
    """Toon een interactieve kaart met folium"""
    if latitude and longitude:
        m = folium.Map(location=[latitude, longitude], zoom_start=zoom)
        folium.Marker(
            [latitude, longitude],
            tooltip="Geselecteerde locatie"
        ).add_to(m)
 # Voeg volgend lijnen toe voor interactiviteit
        folium.plugins.MousePosition().add_to(m)
        folium.plugins.Fullscreen().add_to(m)
        return m
    return None

def validate_location(address):
    """Geavanceerdere locatievalidatie met feedback"""
    if not address:
        return False, "Voer een adres in"

    try:
        geolocator = Nominatim(user_agent="locatie_app")
        location = geolocator.geocode(address)
        if not location:
            return False, "Adres niet gevonden - voer coördinaten handmatig in"
        return True, f"Locatie bevestigd: {location.address}"
    except Exception as e:
        return False, f"Validatiefout: {str(e)}"

def suggest_similar_locations(address):
    """Suggesties voor vergelijkbare locaties om duplicaten te voorkomen"""
    existing_locations = st.session_state.df['Locatie'].unique()
    matches = [loc for loc in existing_locations if address.lower() in loc.lower()]
    return matches if matches else None

# ======================
# DATA INITIALISATIE
# ======================

if 'df' not in st.session_state:
    # Verzamel alle subcategorieën uit SCORE_LEGEND
    all_columns = ["Locatie", "Datum", "Adres", "Latitude", "Longitude",
                   "Oppervlakte", "Milieucategorie", "Opmerkingen"]
    
    for hoofdgroep in SCORE_LEGEND.values():
        all_columns.extend(hoofdgroep.keys())  # ✅ Goed: voeg subcategorieën toe
    
    st.session_state.df = pd.DataFrame(columns=all_columns)

def toon_locatie_formulier():
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False

    with st.form(key='locatie_form'):
        st.markdown("Nieuwe locatie toevoegen")

        # Verplichte velden
        naam = st.text_input("Locatienaam*", value="" if st.session_state.form_submitted else None)
        datum = st.date_input("Datum*", value=datetime.now() if not st.session_state.form_submitted else datetime.now())

        # Adresvelden (alleen verplicht als coördinaten niet ingevuld zijn)
        plaats = st.text_input("Plaats", value="" if st.session_state.form_submitted else None,
                             help="Niet verplicht als je coördinaten invult")
        adres = st.text_input("Adres", value="" if st.session_state.form_submitted else None,
                            help="Vul een geldig adres in voor de kaartweergave (niet verplicht als je coördinaten invult)")

        # Nieuwe velden toevoegen
        col1, col2 = st.columns(2)
        with col1:
            oppervlakte = st.number_input("Oppervlakte (m²)",
                                        min_value=0,
                                        value=0 if st.session_state.form_submitted else None,
                                        help="Vul de grootte van de locatie in vierkante meters in")
        with col2:
            milieucategorie = st.selectbox("Milieucategorie (optioneel)",
                                         options=["", "Categorie I", "Categorie II", "Categorie III", "Categorie IV"],
                                         index=0)

        # Optionele velden
        opmerkingen = st.text_area("Opmerkingen", value="" if st.session_state.form_submitted else None)

        # Coördinaten handmatig invoeren
        st.markdown("**Coördinaten (handmatig invullen overslaat adresverificatie)**")
        col1, col2 = st.columns(2)
        with col1:
            latitude = st.number_input("Latitude", value=0.0 if st.session_state.form_submitted else 0.0, format="%.6f")
        with col2:
            longitude = st.number_input("Longitude", value=0.0 if st.session_state.form_submitted else 0.0, format="%.6f")

        submitted = st.form_submit_button("Locatie toevoegen")
        if submitted:
            st.session_state.form_submitted = True
            if not naam or not datum:
                st.error("Locatienaam en datum zijn verplichte velden")
                st.session_state.form_submitted = False
            else:
                # Alleen adres verifiëren als coördinaten niet handmatig zijn ingevuld
                if latitude == 0 and longitude == 0:
                    if not adres or not plaats:
                        st.error("Vul adres en plaats in of voer handmatig coördinaten in")
                        st.session_state.form_submitted = False
                        return

                    volledig_adres = f"{adres}, {plaats}"
                    coords = get_coordinates(volledig_adres)
                    if coords:
                        latitude, longitude = coords
                    else:
                        st.error("Kon geen coördinaten vinden voor dit adres. Voer handmatig coördinaten in.")
                        st.session_state.form_submitted = False
                        return
                else:
                    # Gebruik handmatige coördinaten, adres is optioneel
                    volledig_adres = f"{adres}, {plaats}" if adres and plaats else "Onbekend adres"

                nieuwe_locatie = {
                    "Locatie": naam,
                    "Datum": datum.strftime("%Y-%m-%d"),
                    "Plaats": plaats if plaats else None,
                    "Adres": volledig_adres if adres and plaats else None,
                    "Latitude": latitude,
                    "Longitude": longitude,
                    "Oppervlakte": oppervlakte if oppervlakte else None,
                    "Milieucategorie": milieucategorie if milieucategorie else None,
                    "Opmerkingen": opmerkingen
                }

                for categorie in ["Bestemmingsplan", "Bereikbaarheid", "Locatiekenmerken", "Milieu"]:
                    nieuwe_locatie[categorie] = 0

                # Voeg standaard scores toe
                for criterium in SCORE_LEGEND.keys():
                    nieuwe_locatie[criterium] = 0

                # Voeg toe aan dataframe
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([nieuwe_locatie])], ignore_index=True)
                st.success(f"Locatie '{naam}' succesvol toegevoegd!")
                st.session_state.form_submitted = True
                st.rerun()

    if st.session_state.form_submitted:
        st.session_state.form_submitted = False


# ======================
# PAGINA LAYOUT - TABBEN
# ======================
st.set_page_config(layout="wide")

# Voeg dit CSS-blok hier toe ##############
# Zet deze code DIRECT na st.set_page_config()
st.markdown(
    """
    <style>
    /* Fixeer tabs bovenaan het scherm */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stTabs"] {
        position: fixed;
        top: 0;
        background: white;
        z-index: 99999;
        width: calc(100% - 6rem);
        padding: 1rem 3rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Voeg padding toe aan hoofdcontent om tabs niet te overlappen */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div:has(> div[data-testid="stTabs"]) + div {
        padding-top: 100px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

###########################################

tab1, tab2, tab3, tab4 = st.tabs(["📍 Locatie Beoordelen", "📊 Dashboard Locaties Vergelijken", "➕ Locatie Toevoegen", "🔍 Locatie Zoeken"])

with tab3:
    # ======================
    # TAB 3: LOCATIE TOEVOEGEN & VERWIJDEREN
    # ======================
    st.title("➕ Nieuwe Locatie Toevoegen")
    toon_locatie_formulier()

    # Toon bestaande locaties met verwijderoptie
    if not st.session_state.df.empty:
        st.markdown("Bestaande locaties")

        # Toon dataframe met verwijderknop per rij
        for idx, row in st.session_state.df[["Locatie", "Datum", "Adres"]].iterrows():
            cols = st.columns([4, 1])
            with cols[0]:
                st.write(f"**{row['Locatie']}** - {row['Datum']}")
                if pd.notna(row['Adres']):
                    st.caption(f"Adres: {row['Adres']}")
            with cols[1]:
                if st.button("❌ Verwijder", key=f"del_{row['Locatie']}"):
                    verwijder_locatie(row['Locatie'])

with tab1:
    st.title("📍 Locatie Beoordeling - Definitief Model")

    # Custom CSS voor vetgedrukte titels en score styling
    st.markdown("""
    <style>
    .question-title {
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        margin-bottom: 8px !important;
    }
    .score-display {
        padding: 6px 12px;
        background-color: #f8f9fa;
        border-radius: 20px;
        display: inline-block;
        margin-top: 8px;
        border: 2px solid;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.df.empty:
        st.warning("Voeg eerst een locatie toe via het '➕ Locatie Toevoegen' tabblad")
    else:
        selected_location = st.selectbox(
            "Selecteer locatie*",
            st.session_state.df["Locatie"],
            key="main_loc_select"
        )
        st.session_state.loc_select = selected_location

        loc_data = st.session_state.df[st.session_state.df["Locatie"] == selected_location].iloc[0]

        # --- Locatiedetails & Kaart ---
        locatie_details = st.session_state.df[st.session_state.df["Locatie"] == selected_location].iloc[0]
        col_details, col_map = st.columns([2, 1])

        with col_details:
            with st.expander("📌 Locatiedetails", expanded=True):
                st.write(f"**Invoerdatum:** {locatie_details['Datum']}")
                if pd.notna(locatie_details['Adres']):
                    st.write(f"**Adres:** {locatie_details['Adres']}")
                if pd.notna(locatie_details['Latitude']) and pd.notna(locatie_details['Longitude']):
                    st.write(f"**Coördinaten:** {locatie_details['Latitude']:.6f}, {locatie_details['Longitude']:.6f}")
                if pd.notna(locatie_details['Oppervlakte']):
                    st.write(f"**Oppervlakte:** {locatie_details['Oppervlakte']} m²")
                if pd.notna(locatie_details['Milieucategorie']):
                    st.write(f"**Milieucategorie:** {locatie_details['Milieucategorie']}")
                if pd.notna(locatie_details['Opmerkingen']):
                    st.write(f"**Opmerkingen:** {locatie_details['Opmerkingen']}")

        with col_map:
            if pd.notna(locatie_details['Latitude']) and pd.notna(locatie_details['Longitude']):
                st.markdown("**Locatiekaart**")
                m = show_map(locatie_details['Latitude'], locatie_details['Longitude'])
                if m:
                    folium_static(m, width=350, height=250)
            else:
                st.warning("Geen kaart beschikbaar - voeg coördinaten toe")

        with st.expander("📋 Hoe werkt dit beoordelingssysteem?", expanded=False):
            st.markdown("""
            **Werkwijze:**

            1. **Selecteer eerst een locatie** in het bovenstaande dropdown-menu
            2. **Doorloop alle secties** (Ruimtelijk, Milieu, etc.) en geef een score
            **Let op!** boven de beoordeling van een bepaald onderdeel staat aangegeven hoe en waar je de betreffende informatie kan vinden voor de beoordeling.
            3. **Vul alle verplichte velden** in voor een volledige beoordeling
            4. **Analyseer de eindscore** die automatisch wordt berekend

            **Scoring:**
            - Elke categorie krijgt een score van 1-5 (1=ongunstig, 5=zeer gunstig)
            - De weging tussen categorieën is gelijk
            - Eindscore is het gemiddelde van alle categorieën
            """)
        
        with st.expander("Onderbouwing scoresysteem", expanded=False):
            st.markdown("""
    Hieronder vind je de uitleg en toelichting bij de keuzeopties per criterium in het scoresysteem.

    ---
    
    ### 1. Conformiteit omgevingsplan  
    Vanuit de interviews is duidelijk geworden dat als de bestemming niet overeenkomt dat het eigenlijk gelijk een ongeschikte locatie is. 
    Daarom is gekozen voor een score van 5 als het conform is en 1 als het niet conform is. 
    

    ### 2. Bereikbaarheid

    **2.1 Snelwegafstanden**  
    1. *Snelwegafstand ≤ 5 km (Score 2)*  
    Bij een ontwerpsnelheid van 50 km/uur (CROW, 2012) levert 5 km een rijtijd van circa 6 minuten op. Beleidsmatig wordt in Nederland vaak een reistijd van maximaal 10 minuten als acceptabel gehanteerd (Ministerie van Verkeer en Waterstaat, 2005), zodat 5 km ruim binnen deze grens valt.  

    2. *Snelwegafstand 5–10 km (Score 1)*  
    Afstanden tussen 5 en 10 km bij 50 km/uur corresponderen met ongeveer 6–12 minuten rijtijd (CROW, 2012; KiM, 2018). Dit valt nog binnen of net iets boven de algemeen geaccepteerde 10 minuten, en wordt daarom als middelmatig beoordeeld.  

    3. *Snelwegafstand > 10 km (Score 0)*  
    Afstanden boven 10 km leiden tot rijtijden van meer dan 12 minuten. Uit analyses blijkt dat reisafstanden die resulteren in meer dan circa 15 minuten reistijd een remmende factor vormen voor zowel bedrijfstransport als woon-werkverkeer (KiM, 2017).  

    **2.2 OV-halteafstanden**  
    - *≤ 500 m (Score 2)*: Uit onderzoek (o.a. NS en 9292) blijkt dat de meeste mensen bereid zijn maximaal 5–7 min te lopen naar een halte – wat overeenkomt met circa 400–600 m. Bij ≤ 500 m is de halte “op loopafstand” en bevordert het frequent gebruik van het OV door werknemers en bezoekers.  
    - *500–1 000 m (Score 1)*: Afstanden tot 1 km (10–12 min lopen) worden nog wel geaccepteerd, maar verlagen de gebruiks¬bereidheid licht. Voor sommige doelgroepen (bijv. tweeploegendienst of reizigers met bagage) kan dit als minder comfortabel ervaren worden.  
    - *> 1 000 m (Score 0)*: Lopen van meer dan 1 km (12+ minuten) tot de dichtstbijzijnde halte leidt in de praktijk tot minder OV-gebruik en is een drempel voor woon-werk¬verkeer zonder auto.  

    **2.3 Fietsbereikbaarheid**  
    - *LF-routes direct (Score 2)*: Landelijke Fietsroutes (LF) en belangrijke knooppuntroutes bieden doorgaans goede doorstroming en uitstekende bewegwijzering. Als er ≥ 2 van deze routes binnen 500 m liggen, is de locatie optimaal ontsloten voor fietsers – zowel lokaal als regionaal.  
    - *Redelijk (Score 1)*: Eén belangrijke route binnen 500 m, of meerdere binnen 1 km, betekent dat er wel fiets¬mogelijkheden zijn, maar net iets meer omrijden of zoeken nodig is. Dit is acceptabel, maar minder optimaal voor bedrijven die sterk leunen op fietsverkeer (bijv. high-tech of logistiek personeel).  
    - *Slecht (Score 0)*: Geen bruikbare fietsroutes binnen 1 km betekent dat medewerkers en bezoekers vaak via drukke lokale wegen of grote omwegen moeten fietsen, wat de veiligheid en aantrekkelijkheid vermindert.  

    Eindscore bereikbaarheid = (Snelweg + OV + Fiets) / 3, afgerond op hele punten (max. 2).

    ---

    ### 3. Locatiekenmerken

    **3.1 Kadastrale beperkingen (Score 1–3–5)**  
    - Indicator: Aantal publiekrechtelijke beperkingen en zakelijke rechten op perceel.  
    - Databron: Kadaster – Publiekrechtelijke beperkingen (Kadaster, n.d.-a).  
    - Drempels & Score:  
      - 0 beperkingen → Score 5  
        Perceel is ‘schoon’, zonder bouw- of gebruiksbeperkingen (Kadaster, n.d.-a).  
      - 1–2 beperkingen → Score 3  
        Enkele aantekeningen (erfpacht, bouwverbod e.d.) aanwezig (Kadaster, n.d.-b).  
      - ≥ 3 beperkingen → Score 1  
        Meerdere en ingrijpende beperkingen (Kadaster, n.d.-b).  

    **3.2 Nutsvoorzieningen (Score 1–3–5)**  
    - Indicator: Beschikbaarheid van stroom, gas, drinkwater en telecom.  
    - Databron: Netbeheerders Liander, Stedin, Enexis en KPN (Liander, 2023).  
    - Drempels & Score:  
      - Alle 4 voorzieningen direct aanwezig → Score 5  
        Volledige infrastructuur op opleverdatum aanwezig (Liander, 2023).  
      - Één voorziening ontbreekt of moet worden aangelegd → Score 3  
        Klein aanlegtraject (< 6 mnd) nodig (Liander, 2023).  
      - Meer dan één ontbreekt of technisch onmogelijk → Score 1  
        Grootcapaciteits- of tracéproblemen (Liander, 2023).  

    **3.3 Zwaarte elektravoorziening (informatief, geen score)**  
    - Indicator: Maximale levercapaciteit (kVA/MVA) volgens netkaart.  
    - Databron: Beheerder (Liander, 2023).  
    - Gebruik: wordt als kwantitatieve bijlage meegeleverd, níet gescoord.  

    ---

    ### 4. Milieu & Klimaat

    **4.1 Natura 2000-afstand (Score 1–3–5)**  
    - Indicator: Wegafstand tot de grens van het dichtstbijzijnde Natura 2000-gebied.  
    - Databron: EU-richtlijnen Natura 2000 (European Commission, 2007) en Atlas Leefomgeving (RIVM, 2024).  
    - Drempels & Score:  
      - > 1 000 m → Score 5  
        Ruime afstand, geen planeffecten (European Commission, 2007).  
      - 500–1 000 m → Score 3  
        Mogelijk randzone-effect, mitigatie nodig (RIVM, 2024).  
      - ≤ 500 m → Score 1  
        Direct grenscontact, hoge kans op natuurtoets (European Commission, 2007).  

    **4.2 Stikstofdepositie (mol N/ha/jr) (Score 1–3–5)**  
    - Indicator: Berekende depositie via AERIUS-Calculator (RIVM, 2024).  
    - Databron: RIVM AERIUS (RIVM, 2024).  
    - Drempels & Score:  
      - ≤ 0- 1000 mol → Score 5  
        Geen extra depositie; ruimte voor ontwikkeling (RIVM, 2024).  
      - 1000–2.500 mol → Score 3  
        Matige depositie, mogelijk functioneel binnen PAS-richtlijnen (RIVM, 2024).  
      - ≥ 2.500 mol → Score 1  
        Hoge depositie; streng natuurtoets-risico (RIVM, 2024).  
        *Toelichting:* PAS‐grenswaarden gebruiken 2 500 mol/ha/jr als significante bijdrage (RIVM, 2024).
    """)


        # === 1. BESTEMMINGSPLAN ===
        with st.expander("📜 1. Bestemming (30%)", expanded=True):
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown('<div class="question-title">Planconformiteit*</div>', unsafe_allow_html=True)
                st.caption("Controleer de conformiteit met het [Omgevingsloket](https://www.omgevingsloket.nl) voor Omgevingsplan 2024.")
                bestemmingsplan = st.radio(
                    "",
                    options=["Volledig conform omgevingsplan", "Niet conform (locatie ongeschikt)"],
                    index=None,  # Geen standaard selectie
                    key=f"bestemming_radio_{selected_location}",
                    label_visibility="collapsed"
                )
            with col2:
                if bestemmingsplan:
                    bestemmingsplan_score = 5 if "Volledig conform omgevingsplan" in bestemmingsplan else 1
                    st.markdown(f'<div class="score-display" style="border-color: {SCORE_COLORS[bestemmingsplan_score]}">Score: {bestemmingsplan_score}/5</div>',
                              unsafe_allow_html=True)
                else:
                    st.warning("Selecteer een optie")

            if bestemmingsplan == "Niet conform (locatie ongeschikt)":
                st.error("""
                ⚠️ **Locatie ongeschikt**
                Planwijziging vereist volgens artikel 3.1.2 van het Omgevingsbesluit
                """)
                if st.button("Toch doorgaan met beoordeling", key=f"force_continue_{selected_location}"):
                    st.session_state.force_continue = True
                if not st.session_state.get('force_continue'):
                    st.stop()

        # === 2. BEREIKBAARHEID ===
        with st.expander("🚗 2. Bereikbaarheid (30%)", expanded=True):
            st.caption(
                "Bepaal de afstand tot de dichtstbijzijnde snelweg via de [Rijkswaterstaat Infraatlas](https://www.rijkswaterstaat.nl/infraatlas) "
                "of [Google Maps](https://www.google.com/maps), meet loopafstand via [9292.nl](https://www.9292.nl) en controleer LF-routes "
                "via de [Fietsersbond Routeplanner](https://www.fietsersbond.nl/fietsrouteplanner) of de “Cycle Map” laag in "
                "[OpenStreetMap](https://www.openstreetmap.org)."
            )
            cols = st.columns(3)
            criteria = [
                ("Snelwegafstand", ["≤5 km", "5–10 km", ">10 km"], [5,3,1]),
                ("OV-halte", ["≤500 m", "500–1000 m", ">1000 m"], [5,3,1]),
                ("Fietsinfrastructuur", ["LF-routes direct", "Eén belangrijke route binnen 500 m, of meerdere binnen 1 km.", "Geen bruikbare fietsroutes binnen 1 km."], [5,3,1])
            ]

            bereik_scores = []
            for i, (label, options, values) in enumerate(criteria):
                with cols[i]:
                    st.markdown(f'<div class="question-title">{label}</div>', unsafe_allow_html=True)
                    selected = st.radio(
                        "", options,
                        index=None,  # Geen standaard selectie
                        key=f"bereik_{i}_{selected_location}",
                        label_visibility="collapsed"
                    )

                    if selected:
                        score = values[options.index(selected)]
                        st.markdown(f'<div class="score-display" style="border-color: {SCORE_COLORS[score]}">Score: {score}/5</div>',
                                  unsafe_allow_html=True)
                        bereik_scores.append(score)
                    else:
                        st.warning("Selecteer een optie")

            if len(bereik_scores) == 3:
                bereikbaarheid_score = round(sum(bereik_scores)/3, 1)
                st.markdown(f"""
                <div style="margin-top: 16px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                    🏁 Gemiddelde score bereikbaarheid: {bereikbaarheid_score}/5
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Vul alle bereikbaarheidsvelden in")

        # === 3. LOCATIEKENMERKEN ===
        with st.expander("🏭 3. Locatiekenmerken (20%)", expanded=True):
            st.caption(
                "Raadpleeg de [Kadaster Kadastralekaart](https://www.kadaster.nl/kadastralekaart) voor hypotheken, erfdienstbaarheden en pandrechten "
                "en check beschikbaarheid bij [Liander](https://www.liander.nl) of [Enexis](https://www.enexisgroep.nl)."
            )
            col1, col2 = st.columns(2)

            # Kadastrale beperkingen
            with col1:
                st.markdown('<div class="question-title">Kadastrale beperkingen*</div>', unsafe_allow_html=True)

                beperkingen = st.multiselect(
                    "Selecteer beperkingen:",
                    options=["Erfdienstbaarheid", "Pandrecht", "Overpad", "Hypotheek", "Andere"],
                    key=f"beperkingen_{selected_location}",
                    label_visibility="collapsed"
                )

                aantal_beperkingen = len(beperkingen)
                if aantal_beperkingen == 0:
                    beperkingen_score = 5
                elif 1 <= aantal_beperkingen <= 2:
                    beperkingen_score = 3
                else:
                    beperkingen_score = 1

                st.markdown(f'<div class="score-display" style="border-color: {SCORE_COLORS[beperkingen_score]}">Score: {beperkingen_score}/5</div>',
                          unsafe_allow_html=True)

            # Nutsvoorzieningen
            with col2:
                st.markdown('<div class="question-title">Nutsvoorzieningen*</div>', unsafe_allow_html=True)

                stroom = st.selectbox(
                    "Stroomaansluiting:",
                    options=["≥100A (geschikt voor zware industrie)",
                            "60A (gemiddeld bedrijf)",
                            "≤35A (klein bedrijf)"],
                    index=None,  # Geen standaard selectie
                    key=f"stroom_{selected_location}"
                )

                if stroom:
                    if "100A" in stroom:
                        nuts_score = 5
                    elif "60A" in stroom:
                        nuts_score = 3
                    else:
                        nuts_score = 1
                    st.markdown(f'<div class="score-display" style="border-color: {SCORE_COLORS[nuts_score]}">Score: {nuts_score}/5</div>',
                              unsafe_allow_html=True)
                else:
                    st.warning("Selecteer een optie")

            if stroom and beperkingen is not None:
                locatiekenmerken_score = round((beperkingen_score + nuts_score) / 2, 1)
                st.markdown(f"""
                <div style="margin-top: 16px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                    📌 Gemiddelde score locatiekenmerken: {locatiekenmerken_score}/5
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Vul alle locatiekenmerken in")

        # === 4. MILIEU & KLIMAAT ===
        with st.expander("🌳 4. Milieu & Klimaat (20%)", expanded=True):
            st.caption(
                "Bepaal Natura 2000-afstand op de kaart van [Natura2000.nl](https://www.natura2000.nl/kaart) en vraag stikstofdepositie op in de "
                "[PAS-Viewer RVO](https://pas.rvo.nl) of via provinciale omgevingsloketten."
            )
            col1, col2 = st.columns(2)

            with col1:
                st.markdown('<div class="question-title">Natura 2000-afstand*</div>', unsafe_allow_html=True)
                natura = st.radio(
                    "", [">1000 m", "500–1000 m", "≤500 m"],
                    index=None,  # Geen standaard selectie
                    key=f"natura_radio_{selected_location}",
                    label_visibility="collapsed"
                )
                if natura:
                    natura_score = 5 if natura == ">1000 m" else 3 if natura == "500–1000 m" else 1
                    st.markdown(f'<div class="score-display" style="border-color: {SCORE_COLORS[natura_score]}">Score: {natura_score}/5</div>',
                              unsafe_allow_html=True)
                else:
                    st.warning("Selecteer een optie")

            with col2:
                st.markdown('<div class="question-title">Stikstofdepositie*</div>', unsafe_allow_html=True)
                stikstof = st.slider(
                    "Mol/ha/jaar", 0, 5000, 0,
                    key=f"stikstof_slider_{selected_location}",
                    label_visibility="collapsed"
                )
                stikstof_score = 5 if stikstof <= 1000 else 3 if stikstof <= 2500 else 1
                st.markdown(f'<div class="score-display" style="border-color: {SCORE_COLORS[stikstof_score]}">Score: {stikstof_score}/5</div>',
                          unsafe_allow_html=True)

            if natura:
                milieu_score = round((natura_score + stikstof_score) / 2, 1)
                st.markdown(f"""
                <div style="margin-top: 16px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                    🌱 Gemiddelde score milieu: {milieu_score}/5
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("Vul alle milieuvelden in")

        # === EINDSCORE BEREKENING ===
        st.markdown("---")
        st.subheader("📊 Eindbeoordeling")

        # Alleen berekenen als alle velden zijn ingevuld
        if all([bestemmingsplan, len(bereik_scores) == 3, stroom, natura]):
            # Gewichten en scores
            gewichten = {
                "Bestemmingsplan": 0.30,
                "Bereikbaarheid": 0.30,
                "Locatiekenmerken": 0.20,
                "Milieu": 0.20
            }

            scores = {
                "Bestemmingsplan": bestemmingsplan_score,
                "Bereikbaarheid": bereikbaarheid_score,
                "Locatiekenmerken": locatiekenmerken_score,
                "Milieu": milieu_score
            }

            totaalscore = sum(scores[k] * gewichten[k] * 20 for k in scores)
            totaalscore = min(max(totaalscore, 0), 100)

            # Staafdiagram
            fig = px.bar(
                x=list(scores.keys()),
                y=[scores[k] for k in scores],
                color=list(scores.keys()),
                color_discrete_map={
                    "Bestemmingsplan": "#1b9e75",
                    "Bereikbaarheid": "#2c7bb6",
                    "Locatiekenmerken": "#d95f02",
                    "Milieu": "#7570b3"
                },
                labels={'x': 'Categorie', 'y': 'Score (0–5)'},
                text=[f"{scores[k]:.1f}/5" for k in scores],
                height=400
            )
            fig.update_layout(yaxis_range=[0,5], showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            # Scoreoverzicht
            col1, col2 = st.columns([1,2])
            with col1:
                st.markdown("**Totaalscores per categorie:**")
                for categorie, score in scores.items():
                    st.markdown(f"- **{categorie}:** {score:.1f}/5")

                st.markdown(f"### Eindscore: {totaalscore:.1f}/100")
                progress_value = min(max(totaalscore/100, 0.0), 1.0)
                st.progress(progress_value)

            with col2:
                st.markdown("**Toelichting weging:**")
                st.caption("""
                - Bestemmingsplan: 30%
                - Bereikbaarheid: 30%
                - Locatiekenmerken: 20%
                - Milieu & Klimaat: 20%
                """)
                
            if (
                'bestemmingsplan_score' in locals()
                and 'bereikbaarheid_score' in locals()
                and 'locatiekenmerken_score' in locals()
                and 'milieu_score' in locals()
                and 'beperkingen_score' in locals()
                and 'nuts_score' in locals()
                and stroom  # stroom moet ingevuld zijn
            ):
                st.session_state.df.loc[
                    st.session_state.df["Locatie"] == selected_location,
                    "Bestemmingsplan"
                ] = bestemmingsplan_score

                st.session_state.df.loc[
                    st.session_state.df["Locatie"] == selected_location,
                    "Bereikbaarheid"
                ] = bereikbaarheid_score

                st.session_state.df.loc[
                    st.session_state.df["Locatie"] == selected_location,
                    "Locatiekenmerken"
                ] = locatiekenmerken_score

                st.session_state.df.loc[
                    st.session_state.df["Locatie"] == selected_location,
                    "Milieu"
                ] = milieu_score

                st.session_state.df.loc[
                    st.session_state.df["Locatie"] == selected_location,
                    "Kadastrale beperkingen"
                ] = beperkingen_score

                st.session_state.df.loc[
                    st.session_state.df["Locatie"] == selected_location,
                    "Stroomaansluiting"
                ] = nuts_score

                st.session_state.df.loc[
                    st.session_state.df["Locatie"] == selected_location,
                    "Stroomaansluiting tekst"
                ] = stroom
            else:
                st.warning("Niet alle velden zijn ingevuld, dus de scores worden nog niet opgeslagen.")


with tab2:
    # ======================
    # TAB 2: LOCATIE VERGELIJKING
    # ======================
    st.title("📊 Dashboard Locaties Vergelijken")
    st.info("Hier kun je meerdere locaties met elkaar vergelijken. Hiervoor moeten de locaties wel eerst beoordeeld zijn onder het menu 'Locatie beoordelen'.")

    if st.session_state.df.empty:
        st.warning("Voeg eerst locaties toe via het '➕ Locatie Toevoegen' tabblad")
    else:
        # Multi-select voor locaties
        selected_locs = st.multiselect(
            "Selecteer locaties om te vergelijken",
            options=st.session_state.df["Locatie"],
            default=st.session_state.df["Locatie"].tolist()[:2] if len(st.session_state.df) > 1 else st.session_state.df["Locatie"].tolist()
        )


        if len(selected_locs) > 0:
            # Vergelijkingstabel
            st.markdown("📋 Scorevergelijking")

            # Zorg dat de vereiste kolommen bestaan
            vereiste_kolommen = ["Bestemmingsplan", "Bereikbaarheid", "Locatiekenmerken", "Milieu", "Oppervlakte"]
            for kolom in vereiste_kolommen:
                if kolom not in st.session_state.df.columns:
                    st.session_state.df[kolom] = 0

            # Selectie en opmaak van vergelijkingstabel
            comparison_df = st.session_state.df[
                st.session_state.df["Locatie"].isin(selected_locs)
            ].fillna(0).set_index("Locatie")[vereiste_kolommen]

            
            # Formatteer de scores zonder decimalen
            styled_df = comparison_df.style.format("{:.0f}", subset=["Bestemmingsplan", "Bereikbaarheid", 
                                                                    "Locatiekenmerken", "Milieu",
                                                                    ])
            
            st.dataframe(
                styled_df
                .apply(lambda x: [f'background-color: {SCORE_COLORS.get(v, "#ffffff")}' 
                                for v in x], subset=["Bestemmingsplan", "Bereikbaarheid", 
                                                    "Locatiekenmerken", "Milieu",
                                                    ])
                .highlight_max(axis=1, color="#1b9e75", subset=["Bestemmingsplan", "Bereikbaarheid", 
                                                              "Locatiekenmerken", "Milieu"])
                .highlight_min(axis=1, color="#ff6b6b", subset=["Bestemmingsplan", "Bereikbaarheid", 
                                                              "Locatiekenmerken", "Milieu"]),
                use_container_width=True
            )

            # Aanvullende informatie sectie
            with st.expander("🔍 Detailinformatie per locatie", expanded=True):
                for loc in selected_locs:
                    loc_data = st.session_state.df[st.session_state.df["Locatie"] == loc].iloc[0]
                    st.subheader(loc)
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Kadastrale beperkingen**")
                        if pd.notna(loc_data["Kadastrale beperkingen"]):
                            beperkingen = ["Erfdienstbaarheid", "Pandrecht", "Overpad", "Hypotheek", "Andere"]
                            aanwezig = [b for b in beperkingen if b in str(loc_data["Kadastrale beperkingen"])]
                            if aanwezig:
                                st.write(", ".join(aanwezig))
                            else:
                                st.write("Geen beperkingen")
                        else:
                            st.write("Niet ingevuld")
                    
                    with col2:
                        st.markdown("**Technische details**")
                        st.write(f"Stroomaansluiting: {loc_data.get('Stroomaansluiting tekst', 'Onbekend')}")
                        st.write(f"Oppervlakte: {loc_data.get('Oppervlakte', 'Onbekend')} m²")

            # Staafdiagram vergelijking per criterium
            st.markdown("📈 Vergelijkende scores per criterium")
            fig1, ax1 = plt.subplots(figsize=(12, 6))
            melted_df = st.session_state.df[st.session_state.df["Locatie"].isin(selected_locs)].melt(
                id_vars=["Locatie"],
                value_vars=["Bestemmingsplan", "Bereikbaarheid", "Locatiekenmerken", "Milieu"],
                var_name="Criterium",
                value_name="Score"
            )
            sns.barplot(
                data=melted_df,
                x="Criterium",
                y="Score",
                hue="Locatie",
                palette="viridis",
                ax=ax1
            )
            ax1.set_ylim(0, 5)
            ax1.legend(title="Locatie", bbox_to_anchor=(1.05, 1))
            plt.xticks(rotation=45)
            st.pyplot(fig1)

            # Totaalscore ranking
            st.markdown("🏆 Totaalscore ranking")
            total_scores = st.session_state.df[st.session_state.df["Locatie"].isin(selected_locs)].set_index("Locatie")[list(SCORE_LEGEND.keys())].sum(axis=1)

            # Tabel + staafdiagram in kolommen
            col1, col2 = st.columns([1, 2])
            with col1:
                st.dataframe(
                    total_scores.sort_values(ascending=False)
                    .to_frame("Totaalscore")
                    .style.background_gradient(cmap="YlGn")
                )

            with col2:
                fig2, ax2 = plt.subplots(figsize=(10, 4))
                sorted_scores = total_scores.sort_values(ascending=True)
                color_list = [SCORE_COLORS[min(5, max(1, round(score/(len(SCORE_LEGEND)*5*0.2))))] for score in sorted_scores]
                sorted_scores.plot(
                    kind='barh',
                    color=color_list,
                    ax=ax2
                )
                ax2.set_title("Totaalscore vergelijking")
                ax2.set_xlabel("Score")
                ax2.set_xlim(0, len(SCORE_LEGEND)*5)

                # Voeg scorelabels toe
                for p in ax2.patches:
                    width = p.get_width()
                    ax2.text(width + 0.5, p.get_y() + p.get_height()/2,
                             f"{int(width)}",
                             ha='left', va='center')

                st.pyplot(fig2)
        else:
            st.warning("Selecteer minimaal 1 locatie")

with tab4:
    # ======================
    # TAB 4: LOCATIE ZOEKEN
    # ======================
    st.title("🔍 Geavanceerd Zoeken")

    # Zoekfunctionaliteit in twee kolommen
    col_filters, col_results = st.columns([1, 2])

    with col_filters:
        with st.form(key='search_form'):
            st.markdown("Zoekfilters")

            # Basis zoekopdracht
            search_query = st.text_input("Adres, plaatsnaam of postcode",
                                       help="Laat leeg om alle locaties te doorzoeken")

            # Locatiefilters
            with st.expander("📍 Locatiefilters", expanded=True):
                # Straalzoeken (altijd zichtbaar)
                radius_km = st.slider("Straal zoeken (km)", 0.0, 50.0, 0.0, 0.1,
                                    help="0 km betekent geen straal filter")

                # Nieuwe filters voor oppervlakte en milieucategorie
                min_oppervlakte = st.number_input("Minimale oppervlakte (m²)",
                                                min_value=0,
                                                value=0,
                                                help="Filter op minimale grootte van de locatie")

                milieucategorie_filter = st.selectbox(
                    "Milieucategorie",
                    options=["Alle categorieën", "Categorie I", "Categorie II", "Categorie III", "Categorie IV"],
                    index=0
                )

                if search_query and radius_km > 0:
                    try:
                        geolocator = Nominatim(user_agent="radius_search_app")
                        location = geolocator.geocode(search_query)
                        if location:
                            st.success(f"Centrumpunt: {location.address[:50]}...")
                            center_coords = (location.latitude, location.longitude)
                        else:
                            st.warning("Geen geldig centrumpunt gevonden")
                            center_coords = None
                    except Exception as e:
                        st.error(f"Zoekfout: {str(e)}")
                        center_coords = None
                else:
                    center_coords = None

            # Scorefilters met selectboxen
            with st.expander("Scorefilters", expanded=False):
                # Totaalscore filter
                min_total = st.selectbox(
                    "Minimale totaalscore",
                    options=[0, 10, 15, 20, 25, 30],
                    index=0,
                    help="Selecteer minimale totaalscore (0 = geen minimum)"
                )

                # Individuele score filters
                score_filters = {}
                for criterium in ["Bestemmingsplan", "Bereikbaarheid", "Locatiekenmerken", "Milieu"]:
                    score_filters[criterium] = st.selectbox(
                        f"Minimum {criterium}",
                        options=[0, 1, 2, 3, 4, 5],
                        index=0,
                        help=f"Selecteer minimum score voor {criterium}"
                    )

            # Zoekknop binnen de form
            submitted = st.form_submit_button("Zoek locaties")

with col_results:
    if submitted:
        st.markdown("Zoekresultaten")

        if 'df' not in st.session_state or st.session_state.df.empty:
            st.warning("Nog geen locaties beschikbaar - voeg eerst locaties toe")
        else:
            search_df = st.session_state.df.copy()

            # Straalfilter toepassen (eerste filter)
            if radius_km > 0 and center_coords:
                from geopy.distance import geodesic
                try:
                    search_df = search_df[
                        search_df.apply(
                            lambda row: (
                                pd.notna(row['Latitude']) and
                                pd.notna(row['Longitude']) and
                                geodesic(center_coords, (row['Latitude'], row['Longitude'])).km <= radius_km
                            ),
                            axis=1
                        )
                    ]
                    st.success(f"{len(search_df)} locaties gevonden binnen {radius_km} km van {search_query}")
                except Exception as e:
                    st.error(f"Fout bij straalfilter: {e}")

            # Overige filters toepassen
            if search_query and not radius_km > 0:
                search_df = search_df[
                    search_df['Locatie'].str.contains(search_query, case=False) |
                    search_df['Adres'].str.contains(search_query, case=False)
                ]

            if min_oppervlakte > 0:
                search_df = search_df[
                    (pd.notna(search_df['Oppervlakte'])) &
                    (search_df['Oppervlakte'] >= min_oppervlakte)
                ]

            if milieucategorie_filter != "Alle categorieën":
                search_df = search_df[
                    (pd.notna(search_df['Milieucategorie'])) &
                    (search_df['Milieucategorie'] == milieucategorie_filter)
                ]

            if min_total > 0:
                search_df['Totaalscore'] = search_df[list(SCORE_LEGEND.keys())].sum(axis=1)
                search_df = search_df[search_df['Totaalscore'] >= min_total]

            for criterium, min_score in score_filters.items():
                if min_score > 0:
                    search_df = search_df[search_df[criterium] >= min_score]

            # Kaartweergave
            if not search_df.empty:
                map_center = center_coords if (radius_km > 0 and center_coords) else [52.1326, 5.2913]
                m = folium.Map(location=map_center, zoom_start=12 if radius_km > 0 else 8)

                if radius_km > 0 and center_coords:
                    folium.Circle(
                        center_coords,
                        radius=radius_km * 1000,
                        color='#3186cc',
                        fill=True,
                        fill_opacity=0.2
                    ).add_to(m)

                for _, row in search_df.iterrows():
                    if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
                        popup_content = f"""
                        <b>{row['Locatie']}</b><br>
                        Adres: {row.get('Adres', 'Onbekend')}<br>
                        Oppervlakte: {row.get('Oppervlakte', 'Onbekend')} m²<br>
                        Score: {row.get('Totaalscore', 'Onbekend')}/20
                        """
                        folium.Marker(
                            [row['Latitude'], row['Longitude']],
                            popup=folium.Popup(popup_content, max_width=300),
                            icon=folium.Icon(color='blue')
                        ).add_to(m)

                folium_static(m, width=700, height=500)

                with st.expander("📋 Toon details", expanded=True):
                    st.dataframe(
                        search_df.style.apply(
                            lambda x: [
                                f'background-color: {SCORE_COLORS.get(int(round(v)), "#ffffff")}'
                                if x.name in SCORE_LEGEND else '' for v in x
                            ],
                            axis=0
                        ),
                        height=min(400, 35 * len(search_df)),
                        use_container_width=True
                    )
            else:
                st.warning("Geen locaties gevonden met de huidige filters")
                if radius_km > 0:
                    st.info(f"Geen locaties binnen {radius_km} km van {search_query} gevonden")



# ======================
# SIDEBAR EXPORT AANPASSING
# ======================
with st.sidebar:
    with st.expander("📤 Exporteren", expanded=False):
        if not st.session_state.df.empty:
            # Aangepaste CSV export
            st.download_button(
                label="📥 CSV (puntkomma)",
                data=generate_clean_csv(st.session_state.df),
                file_name="locatie_scores.csv",
                mime="text/csv",
                help="Download als CSV met puntkomma als scheidingsteken"
            )

            # PDF export
            if 'loc_select' in st.session_state:
                selected_location = st.session_state.loc_select
                if selected_location in st.session_state.df["Locatie"].values:
                    if st.button("📄 PDF Rapport"):
                        with st.spinner("Rapport genereren..."):
                            pdf_bytes = generate_pdf(selected_location)
                            if pdf_bytes:
                                st.download_button(
                                    label="⬇️ Download PDF",
                                    data=pdf_bytes,
                                    file_name=f"rapport_{selected_location}.pdf",
                                    mime="application/pdf"
                                )
                st.caption("Genereer een uitgebreid PDF rapport voor de geselecteerde locatie")

    # Toon geselecteerde locatie in opvallend wit vakje
    if 'loc_select' in st.session_state:
        selected_location = st.session_state.loc_select
        st.markdown(f"""
        <div style="
            background-color: white;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="font-size: 0.85rem; color: #666; margin-bottom: 5px;">
                Huidige locatie:
            </div>
            <div style="font-size: 1.1rem; font-weight: bold; color: black;">
                {selected_location}
            </div>
        </div>
        """, unsafe_allow_html=True)


        # Live totaalscore in sidebar


with st.sidebar:
    st.markdown("""
    <style>
    .score-header {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 10px 0 5px 0;
        text-align: center;
    }
    .score-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

    if 'loc_select' in st.session_state:
        selected_location = st.session_state.loc_select
        if not st.session_state.df.empty and selected_location in st.session_state.df["Locatie"].values:
            loc_data = st.session_state.df[st.session_state.df["Locatie"] == selected_location].iloc[0]

            # Bereken scores opnieuw uit de actuele data
            def get_gradient_color(perc):
                r = int(255 * (1 - perc**0.7))
                g = int(255 * perc**1.3)
                b = 40
                return f"#{r:02x}{g:02x}{b:02x}"

            try:
                scores = {
                    "Bestemming": loc_data.get("Bestemmingsplan", 0) or 0,
                    "Bereikbaarheid": loc_data.get("Bereikbaarheid", 0) or 0,
                    "Locatiekenmerken": loc_data.get("Locatiekenmerken", 0) or 0,
                    "Milieu": loc_data.get("Milieu", 0) or 0
                }

                totaal = sum([v for v in scores.values() if v is not None])
                max_score = len([v for v in scores.values() if v is not None]) * 5

                circle_size = 160  # Standaardwaarde, zodat de variabele altijd gedefinieerd is
                if 'df' in st.session_state and not st.session_state.df.empty:
                    circle_size = 160 if len(st.session_state.df) < 5 else 140

                # Bereken de totaalscore
                totaal = sum(scores.values())
                max_score = len(scores) * 5 if len(scores) > 0 else 1  # Voorkomt deling door 0
                percentage = totaal / max_score if totaal > 0 else 0
                gemiddelde = totaal / len(scores) if totaal > 0 else 0

# Stel een standaard kleur in voor als er geen scores zijn
                main_color = "#d3d3d3"  # Lichtgrijs als er geen data is
                if totaal > 0:
                    main_color = get_gradient_color(percentage)  # Bereken de kleur als er scores zijn

                # Cirkel met animatie
                st.markdown(f"""
                <div style="margin: 0 auto; width: {circle_size}px; height: {circle_size}px; position: relative;">
                    <svg width="{circle_size}" height="{circle_size}" viewBox="0 0 36 36" style="transform: rotate(-90deg)">
                        <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none" stroke="#e9ecef" stroke-width="3" stroke-dasharray="100, 100"/>
                        <path class="color-transition" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                            fill="none" stroke="{main_color}" stroke-width="3"
                            stroke-dasharray="{percentage*100}, 100"/>
                    </svg>
                    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                         text-align: center; width: 100%;">
                        <div class="color-transition" style="font-size: {circle_size*0.2}px; font-weight: bold; line-height: 1; color: {main_color};">{totaal}</div>
                        <div style="font-size: {circle_size*0.08}px; color: #6c757d;">van {max_score}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Metrics in vakjes
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div class="score-container">
                        <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">Gemiddelde</div>
                        <div style="font-size: 20px; font-weight: bold; color: {main_color};">
                            {gemiddelde:.1f} ⭐
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div class="score-container">
                        <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">Percentage</div>
                        <div style="font-size: 20px; font-weight: bold; color: {main_color};">
                            {percentage:.0%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Emoji breakdown
                st.markdown("---")
                st.markdown("**Categorieën**")

                EMOJI_SCALE = {1: "❌", 2: "⚠️", 3: "🟡", 4: "👍", 5: "✅"}

                for criterium, score in scores.items():
                    st.markdown(f"""
                    <div style="display: flex; align-items: center;
                        margin: 8px 0; padding: 6px 0;">
                        <div style="font-size: 18px; width: 30px;">{EMOJI_SCALE.get(round(score), "❓")}</div>
                        <div style="flex: 1; font-size: 13px;">{criterium.split()[0]}</div>
                        <div style="font-weight: bold; color: {SCORE_COLORS.get(round(score), '#666')};
                            width: 40px; text-align: right;">
                            {score}/5
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Fout bij tonen scores: {str(e)}")
