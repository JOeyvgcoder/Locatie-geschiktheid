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
        pdf.ln(20)

        # Locatiegegevens
        loc_data = st.session_state.df[st.session_state.df["Locatie"] == locatie].iloc[0]

        # 1. Scoretabel + Totaalscore
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(0, 10, txt="1. Score Overzicht", ln=1)
        pdf.set_font("Arial", size=10)

        # Bereken totaalscore
        scores = [loc_data[criterium] for criterium in SCORE_LEGEND.keys()]
        totaalscore = sum(scores)
        max_score = len(SCORE_LEGEND) * 5

        # Voeg totaalscore toe boven de tabel
        pdf.set_font("Arial", size=12, style='B')
        pdf.cell(0, 10, txt=f"Totaalscore: {totaalscore}/{max_score} ({totaalscore/max_score:.0%})", ln=1)
        pdf.set_font("Arial", size=10)

        # Tabel met scores
        col_width = pdf.w / 3
        row_height = pdf.font_size * 2

        for criterium in SCORE_LEGEND.keys():
            score = loc_data[criterium]
            pdf.set_fill_color(*hex_to_rgb(SCORE_COLORS[score]))
            pdf.cell(col_width, row_height, criterium, border=1, fill=True)
            pdf.cell(col_width, row_height, f"Score: {score}/5", border=1)
            pdf.cell(col_width, row_height, SCORE_LEGEND[criterium][score][:50]+"...", border=1, ln=1)

        pdf.ln(10)

        # 2. Grafieken
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(0, 10, txt="2. Visualisaties", ln=1)

        # Staafdiagram
        fig = create_bar_chart(locatie)
        img_path = fig_to_bytes(fig)
        pdf.image(img_path, x=10, w=pdf.w-20)
        plt.close(fig)

        # Voeg scorebalk toe
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, txt="Score voortgang:", ln=1)
        pdf.set_fill_color(200, 200, 200)  # Grijze achtergrond
        pdf.cell(pdf.w-20, 10, "", border=1, fill=True)
        pdf.set_fill_color(*hex_to_rgb(SCORE_COLORS[5]))  # Groene voortgang
        pdf.cell((pdf.w-20)*(totaalscore/max_score), 10, "", fill=True, ln=1)

        # Radarplot (als er meerdere locaties zijn)
        if len(st.session_state.df) > 1:
            fig = create_radar_chart(st.session_state.df, [locatie] +
                                   [l for l in st.session_state.df["Locatie"].unique() if l != locatie][:2])
            img_path = fig_to_bytes(fig)
            pdf.add_page()
            pdf.image(img_path, x=10, w=pdf.w-20)
            plt.close(fig)

        # 3. Details
        pdf.add_page()
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(0, 10, txt="3. Details", ln=1)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 8, txt=f"Adres: {loc_data.get('Adres', 'Onbekend')}")
        pdf.ln(5)
        pdf.multi_cell(0, 8, txt=f"Opmerkingen: {loc_data.get('Opmerkingen', 'Geen')}")

        # Opschonen
        if os.path.exists(img_path):
            os.unlink(img_path)

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
    st.session_state.df = pd.DataFrame(columns=[
        "Locatie", "Datum", "Adres", "Latitude", "Longitude",
        "Oppervlakte",  # Bestaande kolom voor grootte
        "Milieucategorie",  # Nieuwe kolom voor milieucategorie
        "Opmerkingen"
    ] + list(SCORE_LEGEND.keys()))  # Alle scorekolommen uit SCORE_LEGEND

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

                # Voeg standaard scores toe
                for criterium in SCORE_LEGEND.keys():
                    nieuwe_locatie[criterium] = 3

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
    st.title("📍 Locatie Beoordelen")
    st.info("Hier ga je met behulp van zorgvuldig gekozen criterium een bouwlocatie beoordelen. Zie hieronder het menu 'Hoe werkt dit beoordelingsysteem' voor meer uitleg.")

    if st.session_state.df.empty:
        st.warning("Voeg eerst een locatie toe via het '➕ Locatie Toevoegen' tabblad")
    else:
        selected_location = st.selectbox(
            "Selecteer locatie",
            st.session_state.df["Locatie"],
            key="loc_select"
        )

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

        # --- Objectieve beoordeling ---
        st.subheader("Bouwlocatie Beoordeling")

        # 1. RUIMTELIJKE ASPECTEN
        with st.expander("🏙️ Ruimtelijke Aspecten", expanded=True):
            st.markdown("### Bestemming")
            st.caption("Controleer de conformiteit met het Omgevingsplan 2024 via het Omgevingsloket.")
            bestemmingsplan = st.radio(
                "Conformiteit omgevingsplan",
                options=["Volledig conform omgevingsplan",
                        "Kleine afwijking, vergunning nodig",
                        "Niet conform, planwijziging vereist"],
                index=None,
                key=f"bestemmingsplan_{selected_location}"
            )
            bestemmingsplan_score = 5 if bestemmingsplan == "Volledig conform omgevingsplan" else 3 if bestemmingsplan == "Kleine afwijking, vergunning nodig" else 1 if bestemmingsplan == "Niet conform, planwijziging vereist" else None

            if bestemmingsplan == "Niet conform, planwijziging vereist":
                st.error("⚠️ Locatie ongeschikt - bestemmingsplan conflict")
                ruimtelijke_score = 1
                bestemmingsplan_score = 1
                kadastraal_score = 1
                nuts_score = 1
                infra_score = 1
            else:
                st.markdown("### Kadastrale beperkingen")
                st.caption("Raadpleeg het Kadaster om eventuele erfdienstbaarheden of beperkingen te controleren.")
                kadastraal = st.radio(
                    "Aanwezigheid beperkingen",
                    options=["Geen beperkingen",
                            "Beperkte erfdienstbaarheden",
                            "Zware beperkingen zoals pandrecht/overpad"],
                    index=None,
                    key=f"kadastraal_{selected_location}"
                )
                kadastraal_score = 5 if kadastraal == "Geen beperkingen" else 3 if kadastraal == "Beperkte erfdienstbaarheden" else 1 if kadastraal == "Zware beperkingen zoals pandrecht/overpad" else None

                st.markdown("### Nutsvoorzieningen")
                st.caption("Check bij netbeheerder (Liander/Enexis) of Kadaster")
                nuts = st.radio(
                    "Beschikbaarheid nutsvoorzieningen",
                    options=["Water, elektra en gas aanwezig met directe aansluiting",
                            "Niet aanwezig, maar makkelijk aan te leggen",
                            "Niet aanwezig en lastig te realiseren"],
                    index=None,
                    key=f"nuts_{selected_location}"
                )
                nuts_score = 5 if nuts == "Water, elektra en gas aanwezig met directe aansluiting" else 3 if nuts == "Niet aanwezig, maar makkelijk aan te leggen" else 1 if nuts == "Niet aanwezig en lastig te realiseren" else None

                st.markdown("### Infrastructuur")
                st.caption("Voer een KLIC-melding uit bij het Kadaster om ondergrondse infrastructuur te identificeren.")
                infrastructuur = st.radio(
                    "Belemmeringen in grond",
                    options=["Geen obstakels",
                            "Verplaatsbare obstakels aanwezig",
                            "Vaste obstructies, KLIC-melding verplicht"],
                    index=None,
                    key=f"infrastructuur_{selected_location}"
                )
                infrastructuur_score = 5 if infrastructuur == "Geen obstakels" else 3 if infrastructuur == "Verplaatsbare obstakels aanwezig" else 1 if infrastructuur == "Vaste obstructies, KLIC-melding verplicht" else None

                if None not in [bestemmingsplan_score, kadastraal_score, nuts_score, infrastructuur_score]:
                    ruimtelijke_score = round((bestemmingsplan_score + kadastraal_score + nuts_score + infrastructuur_score) / 4)
                    st.info(f"**Eindscore ruimtelijke aspecten**: {ruimtelijke_score}/5")
                else:
                    st.warning("Vul alle ruimtelijke aspecten in voor een score")


        # 2. MILIEU & KLIMAAT
        with st.expander("🌍 Milieu & Klimaat", expanded=True):

            st.markdown("### Bodemkwaliteit")
            st.caption("Voer een bodemonderzoek uit volgens het SIKB-protocol om te bepalen of de grond schoon (Klasse 0) of verontreinigd (Klasse 1-4) is; raadpleeg het Bodemloket.")
            bodem_score = st.radio(
                "Bodemclassificatie",
                options=[1, 3, 5],
                format_func=lambda x: f"{x} - {SCORE_LEGEND['Milieunormen']['Bodemkwaliteit'][x]}",
                horizontal=True,
                index=None,
                key=f"bodem_{selected_location}"
            )

            st.markdown("### Natura 2000-gebied")
            st.caption("Via atlasleefomgeving.nl kun je checken of er een Natura 2000-gebied in de omgeving ligt")
            natura_score = st.radio(
                "Natura 2000-gebied",
                options=[1, 3, 5],
                format_func=lambda x: f"{x} - {SCORE_LEGEND['Milieunormen']['Natura 2000-gebied'][x]}",
                horizontal=True,
                index=None,
                key=f"natura_{selected_location}"
            )

            if None not in [bodem_score, natura_score]:
                milieu_score = round((bodem_score + natura_score) / 2)
                st.info(f"**Eindscore milieu & klimaat**: {milieu_score}/5")
            else:
                st.warning("Vul alle milieu & klimaat aspecten in voor een score")

        # 3. VEILIGHEID & TECHNIEK
        with st.expander("🛡️ Veiligheid & Technisch", expanded=True):
            st.markdown("### Externe veiligheid")
            st.caption("Gebruik de Risicokaart RIVM om te controleren of er BRZO-bedrijven in de omgeving zijn.")
            externe_veiligheid = st.radio(
                "BRZO-bedrijven in omgeving",
                options=["Geen binnen 500m",
                        "1 binnen 500m",
                        "≥2 binnen 500m"],
                index=None,
                key=f"veiligheid_{selected_location}"
            )
            externe_veiligheid_value = 5 if externe_veiligheid == "Geen binnen 500m" else 3 if externe_veiligheid == "1 binnen 500m" else 1 if externe_veiligheid == "≥2 binnen 500m" else None

            st.markdown("### Bodemdraagkracht")
            st.caption("Voer een sondering uit volgens de NEN 9997-1 norm om de funderingsgeschiktheid te bepalen.")
            bodem_geschikt = st.radio(
                "Draagkracht bodem",
                options=["≥120 kN/m² (funderingsmogelijkheden optimaal)",
                        "80-120 kN/m² (aanpassingen nodig)",
                        "<80 kN/m² (paalfundering vereist)"],
                index=None,
                key=f"bodem_geschikt_{selected_location}"
            )
            bodem_geschikt_value = 5 if bodem_geschikt == "≥120 kN/m² (funderingsmogelijkheden optimaal)" else 3 if bodem_geschikt == "80-120 kN/m² (aanpassingen nodig)" else 1 if bodem_geschikt == "<80 kN/m² (paalfundering vereist)" else None


            if None not in [externe_veiligheid_value, bodem_geschikt_value]:
                veiligheid_techniek_score = round((externe_veiligheid_value + bodem_geschikt_value) / 3)
                st.info(f"**Eindscore veiligheid & techniek**: {veiligheid_techniek_score}/5")
            else:
                st.warning("Vul alle veiligheid aspecten in voor een score")

        # 4. BEREIKBAARHEID
        with st.expander("🚆 Bereikbaarheid", expanded=True):
            st.markdown("### Wegontsluiting")
            st.caption("Beoordeel de toegang tot de locatie volgens de CROW-richtlijn, waarbij minimaal één weg van 4m breed vereist is.")
            wegen_score = st.radio(
                "Aantal toegangswegen",
                options=["≥2 toegangswegen (CROW-richtlijn)",
                        "1 toegangsweg",
                        "Geen directe ontsluiting"],
                index=None,
                key=f"wegen_{selected_location}"
            )
            wegen_score_value = 5 if wegen_score == "≥2 toegangswegen (CROW-richtlijn)" else 3 if wegen_score == "1 toegangsweg" else 1 if wegen_score == "Geen directe ontsluiting" else None

            st.markdown("### Openbaar vervoer")
            st.caption("Bepaal de nabijheid van OV-haltes met NS-abonnementen of de OV-planner en ken punten toe per halte binnen 400m.")
            ov_score = st.radio(
                "Afstand OV-halte",
                options=["OV-halte ≤400m",
                        "OV-halte >400m ≤2000m",
                        "Geen OV in de buurt"],
                index=None,
                key=f"ov_{selected_location}"
            )
            ov_score_value = 5 if ov_score == "OV-halte ≤400m" else 3 if ov_score == "OV-halte >400m ≤2000m" else 1 if ov_score == "Geen OV in de buurt" else None

            st.markdown("### Fietsbereikbaarheid")
            st.caption("Controleer aansluiting op LF-routes via de Fietsersbond-classificatie.")
            fiets_score = st.radio(
                "Aansluiting fietsroutes",
                options=["Aansluiting op LF-routes (Fietsersbond)",
                        "Redelijke verbindingen",
                        "Slechte fietsroutes"],
                index=None,
                key=f"fiets_{selected_location}"
            )
            fiets_score_value = 5 if fiets_score == "Aansluiting op LF-routes (Fietsersbond)" else 3 if fiets_score == "Redelijke verbindingen" else 1 if fiets_score == "Slechte fietsroutes" else None

            if None not in [wegen_score_value, ov_score_value, fiets_score_value]:
                bereikbaarheid_score = round((wegen_score_value + ov_score_value + fiets_score_value) / 3)
                st.info(f"**Eindscore bereikbaarheid**: {bereikbaarheid_score}/5")
            else:
                st.warning("Vul alle bereikbaarheid aspecten in voor een score")

        # --- Visualisaties ---
        st.subheader("📊 Totaalbeoordeling")

        # Data voorbereiden
        scores_data = {
            "Categorie": ["Ruimtelijk", "Milieu", "Veiligheid", "Bereikbaarheid"],
            "Score": [
                ruimtelijke_score if 'ruimtelijke_score' in locals() else None,
                milieu_score if 'milieu_score' in locals() else None,
                veiligheid_techniek_score if 'veiligheid_techniek_score' in locals() else None,
                bereikbaarheid_score if 'bereikbaarheid_score' in locals() else None
            ]
        }
        scores_df = pd.DataFrame(scores_data).dropna()

        if not scores_df.empty:
            # Staafdiagram
            fig, ax = plt.subplots(figsize=(10,4))
            bars = ax.bar(
                scores_df["Categorie"],
                scores_df["Score"],
                color=[SCORE_COLORS[max(1, min(5, round(x)))] for x in scores_df["Score"]]
            )
            ax.set_ylim(0,5)
            plt.title(f"Scores voor {selected_location}")

            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom')
            st.pyplot(fig)

            # Update DataFrame met scores
            loc_index = st.session_state.df[st.session_state.df["Locatie"] == selected_location].index[0]
            if 'ruimtelijke_score' in locals():
                st.session_state.df.at[loc_index, "Ruimtelijke Inpassing"] = ruimtelijke_score
            if 'milieu_score' in locals():
                st.session_state.df.at[loc_index, "Milieunormen"] = milieu_score
            if 'veiligheid_techniek_score' in locals():
                st.session_state.df.at[loc_index, "Veiligheid"] = veiligheid_techniek_score
            if 'bereikbaarheid_score' in locals():
                st.session_state.df.at[loc_index, "Bereikbaarheid"] = bereikbaarheid_score

            # Opslaan van subcategorie scores
            st.session_state.df.at[loc_index, "Bestemmingsplan"] = bestemmingsplan_score if 'bestemmingsplan_score' in locals() else 3
            st.session_state.df.at[loc_index, "Kadastrale beperkingen"] = kadastraal_score if 'kadastraal_score' in locals() else 3
            st.session_state.df.at[loc_index, "Nutsvoorzieningen"] = nuts_score if 'nuts_score' in locals() else 3
            st.session_state.df.at[loc_index, "Infrastructuur"] = infrastructuur_score if 'infrastructuur_score' in locals() else 3
            st.session_state.df.at[loc_index, "Geluid"] = geluid_score if 'geluid_score' in locals() else 3
            st.session_state.df.at[loc_index, "Luchtkwaliteit"] = lucht_score if 'lucht_score' in locals() else 3
            st.session_state.df.at[loc_index, "Bodemkwaliteit"] = bodem_score if 'bodem_score' in locals() else 3
            st.session_state.df.at[loc_index, "Waterhuishouding"] = water_score if 'water_score' in locals() else 3
            st.session_state.df.at[loc_index, "Externe veiligheid"] = externe_veiligheid_value if 'externe_veiligheid_value' in locals() else 3
            st.session_state.df.at[loc_index, "Bodemgeschiktheid"] = bodem_geschikt_value if 'bodem_geschikt_value' in locals() else 3
            st.session_state.df.at[loc_index, "Bouwtechniek"] = bouwtechniek_value if 'bouwtechniek_value' in locals() else 3
            st.session_state.df.at[loc_index, "Wegontsluiting"] = wegen_score_value if 'wegen_score_value' in locals() else 3
            st.session_state.df.at[loc_index, "Openbaar vervoer"] = ov_score_value if 'ov_score_value' in locals() else 3
            st.session_state.df.at[loc_index, "Fietsbereikbaarheid"] = fiets_score_value if 'fiets_score_value' in locals() else 3
            st.session_state.df.at[loc_index, "Parkeren"] = parkeren_score_value if 'parkeren_score_value' in locals() else 3

        # Aanvullende opmerkingen
        with st.expander("📝 Aanvullende notities", expanded=False):
            nieuwe_opmerking = st.text_area(
                "Voeg aanvullende opmerkingen toe",
                value=locatie_details.get('Opmerkingen', ''),
                key=f"opmerkingen_{selected_location}"
            )
            if st.button("Opslaan", key=f"save_opmerkingen_{selected_location}"):
                st.session_state.df.at[loc_index, "Opmerkingen"] = nieuwe_opmerking
                st.success("Opmerkingen opgeslagen!")


with tab2:
    # ======================
    # TAB 2: LOCATIE VERGELIJKING
    # ======================
    st.title("📊 Dashboard Locaties Vergelijken")
    st.info("Hier kun je meerdere locaties met elkaar vergelijken. Hiervoor moeten de locaties wel eerst beoordeelt zijn onder het menu 'Locatie beoordelen'.")


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
            comparison_df = st.session_state.df[st.session_state.df["Locatie"].isin(selected_locs)].set_index("Locatie")[list(SCORE_LEGEND.keys())].T
            st.dataframe(
                comparison_df.style
                .apply(lambda x: [f'background-color: {SCORE_COLORS.get(v, "#ffffff")}' for v in x])
                .highlight_max(axis=1, color="#1b9e75")
                .highlight_min(axis=1, color="#ff6b6b"),
                use_container_width=True
            )

            # Staafdiagram vergelijking per criterium
            st.markdown("📈 Vergelijkende scores per criterium")
            fig1, ax1 = plt.subplots(figsize=(12, 6))
            melted_df = st.session_state.df[st.session_state.df["Locatie"].isin(selected_locs)].melt(
                id_vars=["Locatie"],
                value_vars=list(SCORE_LEGEND.keys()),
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
                for criterium in SCORE_LEGEND.keys():
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
                    "Ruimtelijke Inpassing": loc_data.get("Ruimtelijke Inpassing", 0) or 0,
                    "Milieunormen": loc_data.get("Milieunormen", 0) or 0,
                    "Veiligheid": loc_data.get("Veiligheid", 0) or 0,
                    "Bereikbaarheid": loc_data.get("Bereikbaarheid", 0) or 0
                }

                totaal = sum(scores.values())
                if totaal == 0:
                    max_score = 1  # Vermijd deling door nul
                else:
                    max_score = len(scores) * 5
                    percentage = totaal / max_score if max_score > 0 else 0
                    gemiddelde = totaal / len(scores) if totaal > 0 else 0

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
