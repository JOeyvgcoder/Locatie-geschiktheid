4.3	 Het opgestelde model
In dit interactieve dashboard is ontworpen om gebruikers te ondersteunen bij het beoordelen en vergelijken van locaties op basis van zes belangrijke criteria, zoals Ruimtelijke Inpassing, Milieueisen, en Technische Haalbaarheid. Het systeem is ontwikkeld in Python (Van Rossum & Drake, 2023) met behulp van Streamlit, een framework voor het bouwen van webapplicaties (Streamlit, 2023).Hieronder wordt stap voor stap uitgelegd hoe het dashboard werkt.

De link naar het opgestelde dashboard: http://dashboardlocatiegeschiktheid.streamlit.app/

Stap 1: Een locatie toevoegen
Voordat een locatie beoordeeld kan worden, moet deze eerst worden toegevoegd aan het systeem. 
1.	Navigeer naar het tabblad ➕ Locatie Toevoegen
o	Hier vind je een formulier waarin de basisgegevens van de locatie kunnen worden ingevuld.
2.	Vul de vereiste gegevens in:
o	Locatienaam* (verplicht): Bijvoorbeeld "Kantoorpand Rotterdam-Zuid".
o	Datum* (automatisch ingesteld op vandaag, maar kan worden aangepast).
o	Adres (optioneel): Het fysieke adres van de locatie.
o	Opmerkingen (optioneel): Extra notities, zoals "Potentieel geluidsoverlast van snelweg".
3.	Klik op Locatie toevoegen
o	De locatie wordt nu opgeslagen in het systeem met standaardscores (3 sterren voor elk criterium).
o	Deze scores kunnen later worden aangepast in het tabblad 🏠 Locatie Beoordelen.
4.	Bestaande locaties bekijken
o	Onder het formulier verschijnt een tabel met alle eerder toegevoegde locaties, inclusief hun naam, datum en adres.

Stap 2: Een locatie beoordelen
Nadat een locatie is toegevoegd, kunnen de scores per criterium worden aangepast.
1.	Ga naar het tabblad 🏠 Locatie Beoordelen
o	Selecteer een locatie uit de dropdown-lijst.
2.	Bekijk locatiedetails
o	Onder een uitklapbare sectie (📌 Locatiedetails) staan het adres, de datum en eventuele opmerkingen.
3.	Pas de scores aan
o	Elk van de zes criteria heeft vijf mogelijke scores (1-5 sterren), waarbij:
	1 ster = Zeer slecht (bv. "Ernstige bodemverontreiniging")
	5 sterren = Uitstekend (bv. "Volledig milieuvriendelijk")
o	Klik op een sterrenscore om deze toe te wijzen. De geselecteerde score wordt direct opgeslagen.
4.	Bekijk de resultaten
o	Scoretabel: Een overzicht van alle scores, met kleurcodering (rood → groen).
o	Totaalscore: De som van alle criteria, weergegeven als "X/30" (maximaal haalbaar). 
o	Voortgangsbalk: Een visuele weergave van hoe goed de locatie scoort ten opzichte van het maximum.
5.	Gemiddelde score
o	Het dashboard berekent ook het gemiddelde van alle criteria, bijvoorbeeld "3.8 ⭐".

Stap 3: Locaties vergelijken
Het dashboard maakt het mogelijk om meerdere locaties naast elkaar te analyseren.
1.	Ga naar het tabblad 📊 Locaties Vergelijken
o	Selecteer twee of meer locaties in het multiselect-menu. 
2.	Vergelijkingsmogelijkheden:
o	Scoretabel: Toont alle scores per criterium, met de beste (groen) en slechtste (rood) resultaten gemarkeerd.
o	Staafdiagram: Een visuele weergave van hoe locaties scoren per criterium.
o	Radarplot: Een spindiagram dat alle criteria in één oogopslag vergelijkt.
o	Totaalscore-ranking: Een horizontale balkgrafiek die laat zien welke locatie het hoogst scoort. 

Stap 4: Rapportage en export
Het systeem ondersteunt het genereren van professionele rapporten.
1.	PDF-rapport genereren
o	Klik in de zijbalk op 📄 Genereer PDF Rapport voor de geselecteerde locatie.
o	Het rapport bevat:
	Een titelpagina met locatienaam en datum.
	Een overzicht van alle scores met toelichting.
	Dezelfde grafieken als in het dashboard.
	Locatiedetails (adres, opmerkingen).
2.	CSV-export
o	Download de volledige dataset als een puntkommagescheiden bestand (geschikt voor Excel) via de knop 📥 Download CSV.

