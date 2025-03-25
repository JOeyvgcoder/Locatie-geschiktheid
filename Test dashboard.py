import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

# ======================
# SCORE DEFINITIES & CONTEXT (volledig uitgebreid)
# ======================
SCORE_LEGEND = {
    "Ruimtelijke Inpassing": {
        1: "Bestemmingsplan komt niet overeen",
        2: "Beperkte overeenkomst",
        3: "Redelijke overeenkomst",
        4: "Goede overeenkomst",
        5: "Perfecte match"
    },
    "Milieueisen": {
        1: "Zware milieurisico's",
        2: "Significante beperkingen",
        3: "Matige effecten",
        4: "Minimale beperkingen",
        5: "Geen belemmeringen"
    },
    "Veiligheid en Gezondheid": {
        1: "Grote risico's",
        2: "Extra maatregelen nodig",
        3: "Voldoet aan normen",
        4: "Boven gemiddeld",
        5: "Uitstekend"
    },
    "Participatie en Draagvlak": {
        1: "Sterke tegenstand",
        2: "Beperkt draagvlak",
        3: "Neutrale houding",
        4: "Positieve betrokkenheid",
        5: "Sterke ondersteuning"
    },
    "Duurzaamheid en Klimaatadaptatie": {
        1: "Onvoldoende",
        2: "Beperkte voorzieningen",
        3: "Voldoet aan normen",
        4: "Bovenwettelijke maatregelen",
        5: "Koploper"
    },
    "Technische en Financiële Haalbaarheid": {
        1: "Onhaalbaar",
        2: "Grote uitdagingen",
        3: "Haalbaar met aanpassingen",
        4: "Goede balans",
        5: "Uitstekende haalbaarheid"
    }
}

# ======================
# KLEURENSCHEMA
# ======================
SCORE_COLORS = {
    1: "#ff6b6b",  # Donkerrood
    2: "#ffa502",  # Oranje
    3: "#ffd166",  # Geel
    4: "#06d6a0",  # Lichtgroen
    5: "#1b9e75"   # Donkergroen
}

# ======================
# DATA INITIALISATIE
# ======================
if 'df' not in st.session_state:
    data = {
        "Locatie": ["Locatie A", "Locatie B", "Locatie C", "Locatie D"],
        **{k: [3]*4 for k in SCORE_LEGEND.keys()}
    }
    st.session_state.df = pd.DataFrame(data)

# ======================
# PAGINA LAYOUT - TABBEN
# ======================
st.set_page_config(layout="wide")
tab1, tab2 = st.tabs(["🏠 Locatie Beoordelen", "📊 Locaties Vergelijken"])

with tab1:
    # ======================
    # TAB 1: SCORE-INVOER PER LOCATIE
    # ======================
    st.title("📍 Locatie Beoordelen")
    
    selected_location = st.selectbox(
        "Selecteer locatie", 
        st.session_state.df["Locatie"],
        key="loc_select"
    )
    
    # Klikbare score-invoer voor ALLE criteria
    st.subheader("📋 Criteria Beoordelen")
    for criterium, scores in SCORE_LEGEND.items():
        current_score = st.session_state.df.loc[
            st.session_state.df["Locatie"] == selected_location, 
            criterium
        ].values[0]
        
        st.markdown(f"**{criterium}**")
        cols = st.columns(5)
        for score, uitleg in scores.items():
            with cols[score-1]:
                if st.button(
                    f"⭐{score}\n{uitleg}",
                    key=f"btn_{criterium}_{score}",
                    help=uitleg,
                    type="primary" if score == current_score else "secondary"
                ):
                    loc_index = st.session_state.df[st.session_state.df["Locatie"] == selected_location].index[0]
                    st.session_state.df.at[loc_index, criterium] = score
                    st.rerun()
        st.markdown("---")
    
    # Huidige scores weergeven
    st.subheader("📈 Huidige Beoordeling")
    current_data = st.session_state.df[st.session_state.df["Locatie"] == selected_location].set_index("Locatie").T
    st.dataframe(
        current_data.style
        .apply(lambda x: [f'background-color: {SCORE_COLORS[v]}' for v in x])
    )
    
    # Staafdiagram
    st.subheader("📊 Scoreverdeling")
    fig, ax = plt.subplots(figsize=(10,4))
    filtered_df = st.session_state.df[st.session_state.df["Locatie"] == selected_location].melt(
        id_vars=["Locatie"],
        var_name="Criterium",
        value_name="Score"
    )
    bars = ax.bar(
        filtered_df["Criterium"],
        filtered_df["Score"],
        color=[SCORE_COLORS[x] for x in filtered_df["Score"]]
    )
    ax.set_ylim(0,5)
    plt.xticks(rotation=45)
    plt.title(f"Scores voor {selected_location}")
    
    # Voeg scorelabels toe
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom')
    st.pyplot(fig)
    
    # Totaalscore
    st.subheader("✅ Totaalbeoordeling")
    totaalscore = filtered_df["Score"].sum()
    max_score = len(SCORE_LEGEND) * 5
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Totaalscore", f"{totaalscore}/{max_score}")
    with col_b:
        st.metric("Gemiddelde", f"{filtered_df['Score'].mean():.1f} ⭐")
    
    st.progress(
        totaalscore/max_score, 
        text=f"{totaalscore/max_score:.0%} van maximale score"
    )

with tab2:
    # ======================
    # TAB 2: LOCATIE VERGELIJKING - VERBETERD
    # ======================
    st.title("📊 Locaties Vergelijken")
    
    # Multi-select voor locaties
    selected_locs = st.multiselect(
        "Selecteer locaties om te vergelijken",
        options=st.session_state.df["Locatie"],
        default=st.session_state.df["Locatie"]
    )
    
    if len(selected_locs) > 0:
        # Vergelijkingstabel
        st.subheader("📋 Scorevergelijking")
        comparison_df = st.session_state.df[st.session_state.df["Locatie"].isin(selected_locs)].set_index("Locatie").T
        st.dataframe(
            comparison_df.style
            .apply(lambda x: [f'background-color: {SCORE_COLORS[v]}' for v in x])
            .highlight_max(axis=1, color="#1b9e75")
            .highlight_min(axis=1, color="#ff6b6b"),
            use_container_width=True
        )
        
        # Staafdiagram vergelijking per criterium
        st.subheader("📈 Vergelijkende scores per criterium")
        fig1, ax1 = plt.subplots(figsize=(12, 6))
        melted_df = st.session_state.df[st.session_state.df["Locatie"].isin(selected_locs)].melt(
            id_vars="Locatie",
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
        st.subheader("🏆 Totaalscore ranking")
        total_scores = st.session_state.df[st.session_state.df["Locatie"].isin(selected_locs)].set_index("Locatie").sum(axis=1)
        
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

# Sidebar met export en live score
with st.sidebar:
    st.subheader("Export")
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download alle scores",
        data=csv,
        file_name="locatie_scores.csv",
        mime="text/csv"
    )
    
    # Live totaalscore in sidebar
    if 'loc_select' in st.session_state:
        selected_location = st.session_state.loc_select
        current_scores = st.session_state.df[st.session_state.df["Locatie"] == selected_location].iloc[:, 1:].values[0]
        totaal = sum(current_scores)
        max_score = len(SCORE_LEGEND) * 5
        
        st.markdown("---")
        st.subheader("Live Totaalscore")
        st.markdown(f"""
        <div style="background: #f0f2f6; padding: 10px; border-radius: 5px;">
            <b>{selected_location}</b>
            <p style="font-size: 24px; margin: 5px 0; text-align: center;">
                {totaal}<small>/{max_score}</small>
            </p>
            <div style="height: 10px; background: #e0e0e0; border-radius: 5px;">
                <div style="width: {totaal/max_score*100}%; height: 100%; 
                     background: linear-gradient(90deg, #ff6b6b, #1b9e75); 
                     border-radius: 5px;"></div>
            </div>
            <p style="text-align: center; margin-top: 5px;">
                {totaal/max_score:.0%} van maximaal
            </p>
        </div>
        """, unsafe_allow_html=True)