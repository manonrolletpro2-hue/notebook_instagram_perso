"""Rush 4 — Usage d'Instagram et bien-être : application Streamlit.

Version interactive du notebook `rush4_lien_usage_stress.ipynb`, avec les mêmes calculs.
Lancement depuis le dossier du projet :

    streamlit run app.py

Règle de confidentialité : l'application ne manipule que des résultats agrégés.
Aucune ligne individuelle n'est affichée, et aucun groupe de moins de 100 utilisateurs.
"""
import inspect
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Rush 4 · Instagram et bien-être", layout="wide")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
DOSSIER = Path(__file__).resolve().parent
FICHIER = DOSSIER / "data" / "instagram_usage_lifestyleSafe.csv"
FICHIER_AUTRE = DOSSIER / "data" / "instagram_users_lifestyleSafe.csv"

STRESS = "perceived_stress_score"
BONHEUR = "self_reported_happiness"
TEMPS = "daily_active_minutes_instagram"
MIN_N = 100  # taille minimale d'un groupe affiché

CAT_TEMPS = ["< 1 h", "1–2 h", "2–3 h", "3–4 h", "4–5 h", "5 h et +"]
BORNES_TEMPS = [0, 60, 120, 180, 240, 300, np.inf]
TRANCHES_AGE = ["13–17 ans", "18–24 ans", "25–34 ans", "35–44 ans", "45–54 ans", "55–65 ans"]
GROUPES_SEGMENT = ["13–17 ans", "18–34 ans", "35–54 ans", "55–65 ans"]
BORNES_AGE_SEGMENT = [13, 18, 35, 55, 66]
PROFILS = ["Serein et heureux", "Serein mais peu heureux", "Stressé mais heureux", "Stressé et peu heureux"]

# Couleurs (palette vérifiée pour les daltonismes les plus courants)
SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLEU, ORANGE = "#2a78d6", "#eb6834"
RAMPE_4 = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


# ---------------------------------------------------------------------------
# Outils de mise en forme
# ---------------------------------------------------------------------------
def fr(valeur, decimales=1):
    """Écrit un nombre à la française : virgule décimale, espace pour les milliers."""
    if pd.isna(valeur):
        return "—"
    if round(valeur, decimales) == 0:
        valeur = 0.0
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


def tableau(table, decimales=1):
    """Tableau agrégé avec des nombres au format français."""
    def formater(v):
        if isinstance(v, (bool, np.bool_)):
            return "oui" if v else "non"
        if isinstance(v, (int, np.integer)):
            return fr(v, 0)
        if isinstance(v, (float, np.floating)):
            return fr(v, decimales)
        return v
    st.table(table.apply(lambda colonne: colonne.map(formater)))


def chiffres(table, decimales=1, titre="Voir les chiffres"):
    """Le tableau de valeurs d'un graphique, replié sous le graphique."""
    with st.expander(titre):
        tableau(table, decimales)


def habiller(graphique):
    """Style commun à tous les graphiques."""
    return (graphique
            .configure(background=SURFACE, font="system-ui, -apple-system, Segoe UI, sans-serif")
            .configure_view(strokeWidth=0)
            .configure_mark(tooltip=False)  # pas d'infobulle automatique : seules les infobulles prévues s'affichent
            .configure_axis(gridColor=GRID, domainColor=AXIS, tickColor=AXIS, labelColor=INK2,
                            titleColor=INK2, labelFontSize=12, titleFontSize=12, titleFontWeight=400,
                            labelPadding=6, titlePadding=10)
            .configure_legend(orient="bottom", direction="horizontal", labelColor=INK2, titleColor=INK2,
                              labelFontSize=12, titleFontSize=12, columnPadding=18, symbolStrokeWidth=0)
            .configure_title(color=INK, fontSize=15, fontWeight=600, anchor="start", subtitleColor=INK2,
                             subtitleFontSize=12.5, subtitlePadding=6, offset=14))


_LARGEUR = ({"width": "stretch"} if "width" in inspect.signature(st.altair_chart).parameters
            else {"use_container_width": True})


def montrer(graphique):
    st.altair_chart(habiller(graphique), theme=None, **_LARGEUR)


def titre(texte, sous_titre):
    return alt.TitleParams(texte, subtitle=sous_titre)


AXE_HEURES = alt.Axis(values=list(range(0, 9)), labelExpr="datum.value + ' h'", grid=True)
AXE_POURCENT = alt.Axis(labelExpr="datum.value + ' %'")


def retenir(texte):
    st.success(f"**Ce qu'on retient :** {texte}")


def conclusion_produit(texte):
    st.info(f"**Conclusion pour les équipes produit :** {texte}")


def barres_simples(data, x, y, etiquette, titre_graphique, x_titre, y_titre, ordre, domaine_y,
                   tooltip, couleur=BLEU, hauteur=320, axe_y=None):
    """Barres verticales avec la valeur écrite au-dessus de chaque barre."""
    base = alt.Chart(data).encode(
        x=alt.X(f"{x}:N", sort=ordre, title=x_titre, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{y}:Q", title=y_titre, scale=alt.Scale(domain=domaine_y), axis=axe_y),
    )
    barres = base.mark_bar(size=34, cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=couleur).encode(tooltip=tooltip)
    textes = base.mark_text(dy=-9, fontSize=12.5, color=INK).encode(text=f"{etiquette}:N")
    return (barres + textes).properties(title=titre_graphique, height=hauteur)


# ---------------------------------------------------------------------------
# Calculs (résultats agrégés uniquement)
# ---------------------------------------------------------------------------
def agreger(data, cles, **mesures):
    table = data.groupby(cles, observed=True).agg(n=(STRESS, "size"), **mesures)
    return table[table["n"] >= MIN_N]


def part_expliquee(data, y, cles):
    moyenne_groupe = data.groupby(cles, observed=True)[y].transform("mean")
    return 1 - ((data[y] - moyenne_groupe) ** 2).sum() / ((data[y] - data[y].mean()) ** 2).sum()


def lien_a_temps_egal(data, colonne, cible=STRESS):
    rx, ry = data[colonne].rank(pct=True), data[cible].rank(pct=True)
    rx = rx - rx.groupby(data["tranche_10min"]).transform("mean")
    ry = ry - ry.groupby(data["tranche_10min"]).transform("mean")
    return float(np.corrcoef(rx, ry)[0, 1])


@st.cache_data(show_spinner="Calcul des résultats…")
def calculer():
    df = pd.read_csv(FICHIER)
    r = {"n": len(df), "n_colonnes": df.shape[1], "manquants": int(df.isna().sum().sum())}

    # --- 0.2 Choix du fichier (comparaison avec l'autre version de la réplique)
    r["comparaison"] = None
    if FICHIER_AUTRE.exists():
        autre = pd.read_csv(FICHIER_AUTRE)
        differences = pd.Series({c: int((df[c].astype(str) != autre[c].astype(str)).sum()) for c in autre.columns})
        mineurs = df["age"] < 18
        utilisees = [STRESS, BONHEUR, TEMPS, "age", "sleep_hours_per_night", "daily_steps_count",
                     "exercise_hours_per_week", "sessions_per_day", "average_session_length_minutes"]
        r["comparaison"] = {
            "meme_ordre": bool(df["user_id"].equals(autre["user_id"])),
            "identiques": int((differences == 0).sum()),
            "total": len(differences),
            "differences": differences[differences > 0].rename("lignes différentes").to_frame().rename_axis("colonne"),
            "mineurs": pd.DataFrame({
                "fichier usage (analysé)": {
                    "part déclarée salariée à temps plein (%)": (df.loc[mineurs, "employment_status"] == "Full-time employed").mean() * 100,
                    "heures de travail par semaine (moyenne)": df.loc[mineurs, "weekly_work_hours"].mean()},
                "fichier users (autre version)": {
                    "part déclarée salariée à temps plein (%)": (autre.loc[mineurs, "employment_status"] == "Full-time employed").mean() * 100,
                    "heures de travail par semaine (moyenne)": autre.loc[mineurs, "weekly_work_hours"].mean()},
            }),
            "n_mineurs": int(mineurs.sum()),
            "utilisees_identiques": all(df[c].astype(str).equals(autre[c].astype(str)) for c in utilisees),
        }
        del autre

    # --- Variables construites
    df["heures"] = df[TEMPS] / 60
    df["tranche_10min"] = (df[TEMPS] // 10).astype(int)
    df["tranche_30min"] = ((df[TEMPS] // 30) * 30).astype(int)
    df["cat_temps"] = pd.cut(df[TEMPS], BORNES_TEMPS, right=False, labels=CAT_TEMPS)
    df["tranche_age"] = pd.cut(df["age"], [13, 18, 25, 35, 45, 55, 66], right=False, labels=TRANCHES_AGE)
    df["groupe_segment"] = pd.cut(df["age"], BORNES_AGE_SEGMENT, right=False, labels=GROUPES_SEGMENT)
    df["stress_eleve"] = df[STRESS] >= 27
    df["tres_heureux"] = df[BONHEUR] >= 9
    df["tres_malheureux"] = df[BONHEUR] <= 2

    # --- 0.3 Ce que chaque variable apporte
    r["apport"] = pd.DataFrame({"part du stress expliquée (%)": [
        part_expliquee(df, STRESS, ["tranche_10min"]) * 100,
        part_expliquee(df, STRESS, ["cat_temps"]) * 100,
        part_expliquee(df, STRESS, ["cat_temps", "groupe_segment"]) * 100,
        part_expliquee(df, STRESS, ["cat_temps", "tranche_age"]) * 100,
    ]}, index=["temps passé, par tranches de 10 min (référence)", "6 catégories de temps passé",
               "6 catégories de temps × 4 groupes d'âge (nos segments)", "6 catégories de temps × 6 tranches d'âge"])
    niveaux = pd.cut(df[STRESS], [-1, 13, 26, 40], labels=["faible (0–13)", "modéré (14–26)", "élevé (27–40)"])
    r["niveaux"] = niveaux.value_counts(normalize=True).mul(100).sort_index().to_frame("part (%)").rename_axis("niveau")
    parties = df[["time_on_feed_per_day", "time_on_reels_per_day", "time_on_explore_per_day", "time_on_messages_per_day"]]
    essais = df[["tranche_10min", STRESS]].assign(
        passif=(parties.iloc[:, :3].sum(axis=1) / parties.sum(axis=1)).fillna(0),
        interactions=(df["likes_given_per_day"] + df["comments_written_per_day"]) / df[TEMPS],
        ratio=df["following_count"] / df["followers_count"])
    r["ecartees"] = pd.Series({
        "part du temps passée à regarder sans interagir": lien_a_temps_egal(essais, "passif"),
        "likes et commentaires par minute": lien_a_temps_egal(essais, "interactions"),
        "ratio abonnements / abonnés": lien_a_temps_egal(essais, "ratio"),
    }, name="lien avec le stress à temps égal (−1 à 1)").to_frame()

    # --- 1. Pistes sans lien
    r["sommeil"] = agreger(df, "cat_temps", sommeil_moyen=("sleep_hours_per_night", "mean"),
                           part_moins_de_6h=("sleep_hours_per_night", lambda s: (s < 6).mean() * 100))
    r["activite"] = agreger(df, "cat_temps", pas_par_jour=("daily_steps_count", "mean"),
                            sport_heures_semaine=("exercise_hours_per_week", "mean"))
    r["correlations_vie"] = pd.DataFrame({
        "lien avec le stress": {nom: df[c].corr(df[STRESS], method="spearman") for c, nom in
                                (("sleep_hours_per_night", "Sommeil"), ("daily_steps_count", "Pas par jour"),
                                 ("exercise_hours_per_week", "Sport"))},
        "lien avec le bonheur": {nom: df[c].corr(df[BONHEUR], method="spearman") for c, nom in
                                 (("sleep_hours_per_night", "Sommeil"), ("daily_steps_count", "Pas par jour"),
                                  ("exercise_hours_per_week", "Sport"))},
    })
    r["pas_bornes"] = (df["daily_steps_count"].quantile(0.01), df["daily_steps_count"].quantile(0.99))

    # --- 2. Temps passé
    r["stress_30min"] = agreger(df, "tranche_30min", stress=(STRESS, "mean"),
                                q1=(STRESS, lambda s: s.quantile(0.25)), q3=(STRESS, lambda s: s.quantile(0.75)))
    r["stress_cat"] = agreger(df, "cat_temps", stress_moyen=(STRESS, "mean"))
    r["pente"] = float(np.polyfit(df["heures"], df[STRESS], 1)[0])
    r["r2_stress"] = part_expliquee(df, STRESS, ["tranche_10min"])
    r["bonheur_cat"] = agreger(df, "cat_temps",
                               part_tres_heureux=("tres_heureux", lambda s: s.mean() * 100),
                               part_tres_malheureux=("tres_malheureux", lambda s: s.mean() * 100))
    r["profils_temps"] = pd.DataFrame({
        groupe: {"temps médian par jour (min)": df.loc[masque, TEMPS].median(),
                 "le quart qui y passe le moins : moins de (min)": df.loc[masque, TEMPS].quantile(0.25),
                 "sessions par jour": df.loc[masque, "sessions_per_day"].mean(),
                 "durée d'une session (min)": df.loc[masque, "average_session_length_minutes"].mean()}
        for groupe, masque in (("Plus heureux (9–10)", df["tres_heureux"]), ("Autres", ~df["tres_heureux"]),
                               ("Plus malheureux (1–2)", df["tres_malheureux"]))})

    # --- 3. Âge
    r["age_3_4h"] = agreger(df[df["cat_temps"] == "3–4 h"], "tranche_age", minutes=(TEMPS, "mean"), stress=(STRESS, "mean"))
    r["grille_age"] = agreger(df, ["tranche_age", "cat_temps"], stress=(STRESS, "mean"))
    ecart = df[STRESS] - df.groupby("tranche_10min")[STRESS].transform("mean")
    r["pente_age"] = float(np.polyfit(df["age"], ecart, 1)[0] * 10)
    r["exposition"] = agreger(df, "tranche_age", minutes=(TEMPS, "mean"),
                              part_3h_ou_plus=(TEMPS, lambda s: (s >= 180).mean() * 100))

    # --- 4. Stress et bonheur
    r["stress_bonheur_30min"] = agreger(df, "tranche_30min", stress=(STRESS, "mean"), bonheur=(BONHEUR, "mean"))
    r["stress_bonheur_cat"] = agreger(df, "cat_temps", stress=(STRESS, "mean"), bonheur=(BONHEUR, "mean"))
    r["r2_bonheur"] = part_expliquee(df, BONHEUR, ["tranche_10min"])

    # --- 5. Segmentation
    usage = {"likes_given_per_day": "Likes donnés", "stories_viewed_per_day": "Stories vues",
             "time_on_feed_per_day": "Temps sur le fil", "time_on_reels_per_day": "Temps sur les Reels",
             "comments_written_per_day": "Commentaires", "dms_received_per_week": "Messages reçus",
             "ads_viewed_per_day": "Publicités vues", "sessions_per_day": "Sessions par jour"}
    r["copies"] = pd.Series({nom: df[c].corr(df[TEMPS], method="spearman") for c, nom in usage.items()},
                            name="corrélation avec le temps passé").to_frame()
    segments = agreger(df, ["groupe_segment", "cat_temps"], stress=(STRESS, "mean"),
                       part_stress_eleve=("stress_eleve", lambda s: s.mean() * 100))
    r["segments"] = segments
    grille = segments["part_stress_eleve"].unstack("cat_temps")
    moitie = np.where(df["user_id"] % 2 == 0, "A", "B")
    stabilite = (df.assign(moitie=moitie).groupby(["moitie", "groupe_segment", "cat_temps"], observed=True)["stress_eleve"]
                 .mean().mul(100).unstack("moitie"))
    ecarts_age = grille.max() - grille.min()
    r["criteres"] = pd.DataFrame([
        ("1. Distingue bien le bien-être", "part en stress élevé, du segment le plus bas au plus haut",
         f"de {fr(grille.min().min(), 0)} % à {fr(grille.max().max(), 0)} %"),
        ("2. Apporte plus que le temps seul", "plus grand écart entre groupes d'âge à temps égal",
         f"{fr(ecarts_age.max(), 0)} points (catégorie {ecarts_age.idxmax()})"),
        ("3. S'applique à tout utilisateur", "valeurs manquantes dans l'âge et le temps passé",
         str(int(df[["age", TEMPS]].isna().sum().sum()))),
        ("4. Est stable", "plus grand écart entre deux moitiés du fichier",
         f"{fr((stabilite['A'] - stabilite['B']).abs().max(), 1)} points"),
        ("5. N'isole personne", "plus petit segment",
         f"{fr(df.groupby(['groupe_segment', 'cat_temps'], observed=True).size().min(), 0)} utilisateurs"),
        ("6. Aucune donnée de santé", "variables utilisées", "âge et temps passé par jour"),
    ], columns=["critère", "mesure", "résultat"]).set_index("critère")
    profil = np.select([~df["stress_eleve"] & (df[BONHEUR] >= 7), ~df["stress_eleve"] & (df[BONHEUR] < 7),
                        df["stress_eleve"] & (df[BONHEUR] >= 7)], PROFILS[:3], default=PROFILS[3])
    r["profils"] = pd.crosstab(df["cat_temps"], profil, normalize="index").mul(100)[PROFILS]

    # --- 6. Protection des données
    r["segment_max"] = segments["part_stress_eleve"].idxmax()
    r["part_max"] = float(segments["part_stress_eleve"].max())
    revelateurs = segments[segments["part_stress_eleve"] >= 80]
    r["revelateurs"] = (len(revelateurs), len(segments), float(revelateurs["n"].sum() / len(df) * 100))
    r["tailles"] = pd.Series({
        "catégories de temps": df.groupby("cat_temps", observed=True).size().min(),
        "segments âge × temps": df.groupby(["groupe_segment", "cat_temps"], observed=True).size().min(),
        "âge × temps (tranches fines)": df.groupby(["tranche_age", "cat_temps"], observed=True).size().min(),
    }, name="plus petit groupe (utilisateurs)").to_frame()

    # --- 7. Limites : le lien caché entre stress et bonheur
    residu = lambda c: df[c] - df.groupby("tranche_10min")[c].transform("mean")  # noqa: E731
    r["corr_globale"] = float(df[STRESS].corr(df[BONHEUR]))
    r["corr_temps_egal"] = float(np.corrcoef(residu(STRESS), residu(BONHEUR))[0, 1])
    niveau_bonheur = pd.cut(df[BONHEUR], [0, 2, 4, 6, 8, 10], labels=["1–2", "3–4", "5–6", "7–8", "9–10"])
    r["lien_cache"] = agreger(df[df["cat_temps"] == "2–3 h"].assign(niveau_bonheur=niveau_bonheur),
                              "niveau_bonheur", stress_moyen=(STRESS, "mean"))
    return r


if not FICHIER.exists():
    st.error(f"Fichier introuvable : `{FICHIER}`. Placez `app.py` à côté du dossier `data/`.")
    st.stop()

R = calculer()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def page_introduction():
    st.title("Segmentation des utilisateurs d'Instagram : usage et bien-être")
    st.caption("Rush 4 · Bootcamp Data · version interactive du notebook")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Utilisateurs", fr(R["n"], 0))
    c2.metric("Stress expliqué", f"{fr(R['r2_stress'] * 100, 0)} %",
              help="Part des écarts de stress entre utilisateurs expliquée par le temps passé sur Instagram")
    c3.metric("Stress par heure", f"+{fr(R['pente'])}",
              help="Points de stress (sur 40) en plus pour chaque heure passée sur Instagram")
    c4.metric("Segments", f"{len(R['segments'])}",
              help="Segments construits à partir du temps passé et de l'âge")

    st.header("La demande")
    st.markdown("""
Le département Innovation d'Instagram nous demande de **livrer une segmentation des utilisateurs** qui :
- **repose sur leur usage** de l'application ;
- **explique le lien entre l'usage et le bien-être** ;
- est **utilisable par les équipes produit** ;
- est **défendue devant un jury**.
""")
    st.header("Le contexte")
    st.markdown("""
Les réseaux sociaux doivent prouver qu'ils ne nuisent pas à leurs utilisateurs : les régulateurs posent des questions, la presse publie des études et les annonceurs ne veulent pas être associés à une plateforme qui rend les gens malheureux. Instagram veut **sa propre réponse, fondée sur ses propres données**.

- Les données de **bien-être et de santé** (stress, bonheur, sommeil…) viennent d'un **panel de volontaires** qui ont accepté une étude bien-être.
- Les données d'**usage** (temps passé, sessions, likes…) et de **profil** (âge, pays…) existent pour **tous** les utilisateurs.
- Nous travaillons sur une **réplique synthétique** du panel, fournie par l'équipe vie privée. Nos recommandations, elles, s'appliqueront à de vrais utilisateurs.
""")
    st.header("Les indicateurs de bien-être")
    st.markdown("""
- **Stress perçu** (`perceived_stress_score`, de 0 à 40) : c'est la plage de l'échelle **PSS-10**, sans que la documentation le confirme. On considère le stress comme **élevé à partir de 27**, une convention de lecture courante et non un seuil de diagnostic.
- **Bonheur déclaré** (`self_reported_happiness`, de 1 à 10).
""")
    st.header("Les règles suivies")
    st.markdown("""
- **Aucune donnée individuelle n'est affichée** : seulement des moyennes de groupes, et jamais un groupe de **moins de 100 utilisateurs**.
- **Résultats identiques à chaque exécution** : aucun tirage aléatoire.
- **Ce sont des corrélations**, pas des preuves de cause à effet.

Utilisez le menu à gauche pour parcourir les parties, dans l'ordre du notebook.
""")


def page_donnees():
    st.title("0 · Les données et les variables")

    st.header("Quel fichier croire, et sur quels champs ?")
    st.markdown("Instagram nous a envoyé **deux versions** de la réplique. L'une a subi un nettoyage non documenté, et les deux ne concordent pas entièrement. La consigne nous demande de décider laquelle croire, champ par champ.")
    comparaison = R["comparaison"]
    if comparaison is None:
        st.warning("Le fichier `instagram_users_lifestyleSafe.csv` est absent : la comparaison n'est pas recalculée.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Colonnes identiques", f"{comparaison['identiques']} sur {comparaison['total']}")
        c2.metric("Mineurs déclarés salariés à temps plein (fichier usage)",
                  f"{fr(comparaison['mineurs'].iloc[0, 0], 0)} %")
        c3.metric("Colonnes utilisées identiques dans les deux fichiers",
                  "oui" if comparaison["utilisees_identiques"] else "non")
        gauche, droite = st.columns(2)
        with gauche:
            st.markdown("**Colonnes qui diffèrent (nombre de lignes concernées)**")
            tableau(comparaison["differences"], 0)
        with droite:
            st.markdown(f"**Les 13–17 ans ({fr(comparaison['n_mineurs'], 0)} utilisateurs) dans les deux fichiers**")
            tableau(comparaison["mineurs"])
    st.markdown("""
**Notre décision**
- **Toutes les colonnes que nous utilisons** (stress, bonheur, temps passé, âge, sessions, sommeil, pas, sport) sont **identiques dans les deux fichiers** : nos résultats ne dépendent pas de ce choix.
- **Pour l'emploi et les heures de travail**, nous faisons confiance au fichier `users`, qui a corrigé l'incohérence des mineurs (45 % déclarés salariés à temps plein, 40 h de travail par semaine dans le fichier `usage`). Nous n'utilisons pas ces colonnes.
- Les autres écarts (études, couple, enfants, année de création) ne peuvent pas être départagés sans la documentation du nettoyage. Ces colonnes ne servent pas à notre segmentation.
""")
    retenir("nous travaillons sur le fichier `usage`, et ce choix est sans risque : les colonnes utilisées sont strictement les mêmes dans les deux versions.")

    st.header("Les variables construites, et ce qu'elles apportent")
    st.markdown("""
- **Six catégories de temps passé** (moins d'1 h, 1–2 h… 5 h et plus) : des paliers d'une heure, lisibles par les équipes produit.
- **Quatre groupes d'âge** (13–17, 18–34, 35–54, 55–65 ans) : les mineurs à part pour des raisons légales.
- **Un indicateur « stress élevé »** (27 ou plus sur 40) : la borne haute de la convention de lecture de l'échelle PSS-10.
""")
    apport = R["apport"].reset_index().rename(columns={"index": "decoupage", "part du stress expliquée (%)": "part"})
    apport["etiquette"] = apport["part"].map(lambda v: f"{fr(v)} %")
    graphique = alt.Chart(apport).encode(
        y=alt.Y("decoupage:N", sort=None, title=None, axis=alt.Axis(labelLimit=420)),
        x=alt.X("part:Q", title="Part du stress expliquée", scale=alt.Scale(domain=[0, 80]), axis=AXE_POURCENT),
    )
    graphique = (graphique.mark_bar(size=22, cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=BLEU)
                 .encode(tooltip=[alt.Tooltip("decoupage:N", title="Découpage"), alt.Tooltip("etiquette:N", title="Part expliquée")])
                 + graphique.mark_text(align="left", dx=6, fontSize=12, color=INK).encode(text="etiquette:N"))
    montrer(graphique.properties(title=titre("Regrouper par heure ne fait presque rien perdre",
                                             "Part des écarts de stress expliquée par chaque découpage"), height=200))
    gauche, droite = st.columns(2)
    with gauche:
        st.markdown("**Répartition des utilisateurs par niveau de stress**")
        tableau(R["niveaux"])
    with droite:
        st.markdown("**Variables construites puis écartées**")
        tableau(R["ecartees"], 3)
    st.markdown("""
- **Les six catégories de temps** expliquent presque autant le stress (**69 %**) que le temps mesuré à 10 minutes près (**71 %**).
- **Les quatre groupes d'âge** ajoutent environ **2 points** (**71 %**), autant que six tranches d'âge plus fines. L'âge pèse peu dans la moyenne, mais beaucoup sur la part de stress élevé à temps égal (jusqu'à 34 points d'écart, voir la segmentation).
- **Le seuil de stress élevé** concerne un tiers des utilisateurs (**34 %**).
- **Les autres variables testées** n'ont aucun lien avec le stress à temps égal : nous ne les avons pas gardées.
""")
    retenir("chaque variable gardée apporte quelque chose de mesurable, et celles qui n'apportaient rien ont été écartées.")


def page_pistes_sans_lien():
    st.title("1 · Les pistes explorées sans lien")
    st.markdown("Nous sommes partis de deux idées appuyées par des sources de santé publique : Instagram pourrait réduire le **sommeil** ou l'**activité physique**. **Dans notre panel, ni l'une ni l'autre ne se vérifie.** Un indicateur sans lien avec l'usage est aussi un résultat.")

    st.header("Piste 1 — Le sommeil")
    st.markdown("**Questions :** Instagram fait-il baisser le nombre d'heures de sommeil de ses utilisateurs ? Le manque de sommeil joue-t-il un rôle dans le bien-être ?")
    st.caption("Source : [info.gouv.fr, « Santé mentale : pourquoi le sommeil joue un rôle clé », 2025](https://www.info.gouv.fr/actualite/sante-mentale-pourquoi-le-sommeil-joue-un-role-cle) — « Avoir une bonne santé du sommeil contribue à avoir une bonne santé mentale. »")
    sommeil = R["sommeil"].reset_index()
    sommeil["etiquette"] = sommeil["sommeil_moyen"].map(lambda v: f"{fr(v)} h")
    sommeil["moins6"] = sommeil["part_moins_de_6h"].map(lambda v: f"{fr(v)} %")
    montrer(barres_simples(
        sommeil, "cat_temps", "sommeil_moyen", "etiquette",
        titre("Environ 7 h de sommeil, quel que soit le temps passé sur Instagram", "Sommeil moyen par catégorie de temps passé"),
        "Temps passé sur Instagram par jour", "Sommeil moyen (heures par nuit)", CAT_TEMPS, [0, 9],
        [alt.Tooltip("cat_temps:N", title="Temps par jour"), alt.Tooltip("etiquette:N", title="Sommeil moyen"),
         alt.Tooltip("moins6:N", title="Dorment moins de 6 h")]))
    chiffres(R["sommeil"].rename_axis("temps par jour"), 2)
    st.markdown("""
- Le sommeil moyen est d'environ **7 h** dans toutes les catégories, de moins d'1 h à plus de 5 h par jour sur Instagram.
- La part de petits dormeurs (moins de 6 h) est la même partout, autour de 17 %.
- Le sommeil n'est lié ni au stress ni au bonheur (corrélations proches de 0, tableau plus bas).
""")
    retenir("dans notre panel, Instagram n'est pas associé à moins de sommeil, et le sommeil n'est pas associé au bien-être. **Pas de lien.**")

    st.header("Piste 2 — L'activité physique (pas par jour et sport)")
    st.markdown("**Questions :** le temps passé sur Instagram fait-il baisser l'activité physique ? L'activité physique joue-t-elle un rôle sur le bien-être ?")
    st.caption("Source : [Ameli, « Sport et activité physique : un atout pour le bien-être »](https://www.ameli.fr/assure/sante/themes/activite-physique-sante/sport-et-activite-physique-un-atout-pour-le-bien-etre) — l'activité physique réduit le stress et l'anxiété, régule l'humeur et améliore le sommeil.")
    activite = R["activite"].reset_index()
    activite["etiquette_pas"] = activite["pas_par_jour"].map(lambda v: fr(v, 0))
    activite["etiquette_sport"] = activite["sport_heures_semaine"].map(lambda v: f"{fr(v)} h")
    gauche, droite = st.columns(2)
    with gauche:
        montrer(barres_simples(
            activite, "cat_temps", "pas_par_jour", "etiquette_pas",
            titre("Pas par jour", "Moyenne par catégorie de temps passé"), "Temps passé sur Instagram par jour",
            "Pas par jour", CAT_TEMPS, [0, 9500],
            [alt.Tooltip("cat_temps:N", title="Temps par jour"), alt.Tooltip("etiquette_pas:N", title="Pas par jour")]))
    with droite:
        montrer(barres_simples(
            activite, "cat_temps", "sport_heures_semaine", "etiquette_sport",
            titre("Sport (heures par semaine)", "Moyenne par catégorie de temps passé"), "Temps passé sur Instagram par jour",
            "Heures de sport par semaine", CAT_TEMPS, [0, 8.5],
            [alt.Tooltip("cat_temps:N", title="Temps par jour"), alt.Tooltip("etiquette_sport:N", title="Sport par semaine")]))
    chiffres(R["activite"].rename_axis("temps par jour"))
    st.markdown(f"""
- Environ **8 000 pas par jour** et **7,2 h de sport par semaine** dans toutes les catégories de temps passé.
- Ni les pas ni le sport ne sont liés au stress ou au bonheur (corrélations proches de 0).
- Le nombre de pas varie très peu (98 % des utilisateurs entre {fr(R['pas_bornes'][0], 0)} et {fr(R['pas_bornes'][1], 0)}) : cette variable ne permet pas de distinguer des profils.
""")
    st.markdown("**Liens avec le bien-être** (corrélations de −1 à 1, 0 = aucun lien)")
    tableau(R["correlations_vie"], 3)
    retenir("dans notre panel, Instagram n'est pas associé à moins d'activité physique, et l'activité physique n'est pas associée au bien-être. **Pas de lien.** Nos sources laissaient attendre l'inverse : c'est une limite de la réplique synthétique.")


def page_temps():
    st.title("2 · Le temps passé sur Instagram : le cœur du lien")

    st.header("Piste 1.1 — Le temps passé chaque jour est-il le facteur d'usage le plus lié au stress ?")
    c1, c2, c3 = st.columns(3)
    c1.metric("Part du stress expliquée par le temps", f"{fr(R['r2_stress'] * 100, 0)} %")
    c2.metric("Stress en plus par heure", f"+{fr(R['pente'])} points")
    c3.metric("Stress moyen à 5 h et plus", f"{fr(R['stress_cat'].loc['5 h et +', 'stress_moyen'])} / 40")

    data = R["stress_30min"].reset_index()
    data["heures"] = (data["tranche_30min"] + 15) / 60
    data["tranche"] = data["tranche_30min"].map(lambda m: f"{m // 60} h {m % 60:02d} à {(m + 30) // 60} h {(m + 30) % 60:02d}")
    for colonne in ("stress", "q1", "q3"):
        data[f"{colonne}_txt"] = data[colonne].map(fr)
    data["n_txt"] = data["n"].map(lambda v: fr(v, 0))
    base = alt.Chart(data).encode(x=alt.X("heures:Q", title="Temps passé sur Instagram par jour", axis=AXE_HEURES,
                                          scale=alt.Scale(domain=[0, 8.5])))
    bande = base.mark_area(color=BLEU, opacity=0.12).encode(y=alt.Y("q1:Q", title="Stress perçu (0–40)",
                                                                    scale=alt.Scale(domain=[0, 40])), y2="q3:Q")
    ligne = base.mark_line(color=BLEU, strokeWidth=2).encode(y="stress:Q")
    points = base.mark_point(filled=True, size=70, color=BLEU, stroke=SURFACE, strokeWidth=1.5, opacity=1).encode(
        y="stress:Q",
        tooltip=[alt.Tooltip("tranche:N", title="Temps par jour"), alt.Tooltip("stress_txt:N", title="Stress moyen"),
                 alt.Tooltip("q1_txt:N", title="25 % des utilisateurs sous"), alt.Tooltip("q3_txt:N", title="25 % au-dessus de"),
                 alt.Tooltip("n_txt:N", title="Utilisateurs")])
    reperes = pd.DataFrame({"y": [13.5, 26.5]})
    lignes_reperes = alt.Chart(reperes).mark_rule(color=AXIS, strokeWidth=1).encode(y="y:Q")
    zones = pd.DataFrame({"y": [6.5, 20, 33.5], "texte": ["stress faible", "stress modéré", "stress élevé"], "x": [8.45] * 3})
    textes_zones = alt.Chart(zones).mark_text(align="right", fontSize=11, color=MUTED).encode(x="x:Q", y="y:Q", text="texte:N")
    montrer((bande + lignes_reperes + ligne + points + textes_zones).properties(
        title=titre("Le stress monte régulièrement avec le temps passé sur Instagram",
                    "Stress moyen par tranche de 30 minutes · zone bleue : la moitié centrale des utilisateurs · survolez les points"),
        height=380))
    chiffres(R["stress_cat"].rename_axis("temps par jour"))
    st.markdown("""
- Le stress moyen passe de **4,6** (moins de 30 min par jour) à **plus de 37** (7 h et plus).
- La hausse est **régulière** : environ **+5,4 points de stress par heure** passée sur Instagram.
- Le temps passé explique à lui seul **71 %** des écarts de stress entre utilisateurs.
""")
    conclusion_produit("le temps quotidien passé sur l'application est **l'indicateur numéro un** à suivre pour repérer les groupes d'utilisateurs les plus stressés. Instagram le mesure déjà pour tous ses utilisateurs, sans rien leur demander.")
    st.caption("Sources : [Riehm et al., 2019 (Johns Hopkins)](https://hub.jhu.edu/2019/09/11/social-media-teen-mental-health/) — au-delà de 3 h par jour, le risque d'anxiété et de dépression des adolescents augmente · [Liu et al., 2022, méta-analyse](https://pmc.ncbi.nlm.nih.gov/articles/PMC9103874/) — chaque heure de plus par jour va avec environ 13 % de risque de dépression en plus.")
    retenir("oui, **le temps passé est le facteur d'usage le plus lié au stress**. Plus on passe de temps sur Instagram, plus on est stressé, de façon régulière.")

    st.header("Piste 1.2 — Le temps passé chaque jour est-il aussi lié au bonheur ?")
    profils = R["profils_temps"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Temps médian des plus heureux", f"{fr(profils.loc['temps médian par jour (min)', 'Plus heureux (9–10)'], 0)} min")
    c2.metric("Temps médian des plus malheureux", f"{fr(profils.loc['temps médian par jour (min)', 'Plus malheureux (1–2)'], 0)} min")
    c3.metric("Sessions par jour : plus heureux / autres",
              f"{fr(profils.loc['sessions par jour', 'Plus heureux (9–10)'])} / {fr(profils.loc['sessions par jour', 'Autres'])}")

    parts = R["bonheur_cat"].reset_index().melt(id_vars=["cat_temps", "n"],
                                                value_vars=["part_tres_heureux", "part_tres_malheureux"],
                                                var_name="groupe", value_name="part")
    parts["groupe"] = parts["groupe"].map({"part_tres_heureux": "Très heureux (bonheur 9–10)",
                                           "part_tres_malheureux": "Très malheureux (bonheur 1–2)"})
    parts["etiquette"] = parts["part"].map(lambda v: f"{fr(v)} %")
    couleurs = alt.Scale(domain=["Très heureux (bonheur 9–10)", "Très malheureux (bonheur 1–2)"], range=[BLEU, ORANGE])
    base = alt.Chart(parts).encode(
        x=alt.X("cat_temps:N", sort=CAT_TEMPS, title="Temps passé sur Instagram par jour", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("part:Q", title="Part des utilisateurs", scale=alt.Scale(domain=[0, 45]), axis=AXE_POURCENT),
        color=alt.Color("groupe:N", scale=couleurs, title=None))
    lignes = base.mark_line(strokeWidth=2) + base.mark_point(filled=True, size=80, stroke=SURFACE, strokeWidth=1.5, opacity=1).encode(
        tooltip=[alt.Tooltip("cat_temps:N", title="Temps par jour"), alt.Tooltip("groupe:N", title="Groupe"),
                 alt.Tooltip("etiquette:N", title="Part")])
    extremites = base.mark_text(dy=-12, fontSize=12, color=INK2).encode(text="etiquette:N", color=alt.value(INK2)).transform_filter(
        alt.FieldOneOfPredicate(field="cat_temps", oneOf=["< 1 h", "5 h et +"]))
    medianes = pd.DataFrame({"groupe": ["Plus heureux (9–10)", "Plus malheureux (1–2)"],
                             "minutes": [profils.loc["temps médian par jour (min)", "Plus heureux (9–10)"],
                                         profils.loc["temps médian par jour (min)", "Plus malheureux (1–2)"]]})
    medianes["etiquette"] = medianes["minutes"].map(lambda v: f"{fr(v, 0)} min")
    gauche, droite = st.columns([2.2, 1])
    with gauche:
        montrer((lignes + extremites).properties(
            title=titre("La part de très heureux s'effondre avec le temps passé",
                        "Part des utilisateurs très heureux et très malheureux · survolez les points"), height=360))
    with droite:
        base_m = alt.Chart(medianes).encode(
            x=alt.X("groupe:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, labelLimit=200)),
            y=alt.Y("minutes:Q", title="Temps médian par jour (min)", scale=alt.Scale(domain=[0, 290])))
        barres_m = base_m.mark_bar(size=48, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            color=alt.Color("groupe:N", scale=alt.Scale(domain=list(medianes["groupe"]), range=[BLEU, ORANGE]), legend=None),
            tooltip=[alt.Tooltip("groupe:N", title="Groupe"), alt.Tooltip("etiquette:N", title="Temps médian")])
        montrer((barres_m + base_m.mark_text(dy=-9, fontSize=12.5, color=INK).encode(text="etiquette:N")).properties(
            title=titre("Deux fois moins de temps", "Temps médian passé chaque jour"), height=360))
    chiffres(R["bonheur_cat"].rename_axis("temps par jour"))
    chiffres(profils, titre="Voir le profil d'usage des plus heureux et des plus malheureux")
    st.markdown("""
- Moins d'1 h par jour : **10 fois plus** de très heureux que de très malheureux (40,5 % contre 4,0 %).
- 5 h et plus : **8 fois plus** de très malheureux que de très heureux (38,3 % contre 4,8 %).
- Les plus heureux **ouvrent moins souvent l'application** : 7,3 sessions par jour contre 11,1 pour les autres, avec des sessions un peu plus courtes (18,9 min contre 20,9).
""")
    retenir("le temps passé est aussi lié au bonheur. **Les plus heureux sont ceux qui utilisent le moins Instagram**, en temps comme en nombre de sessions.")


def page_age():
    st.title("3 · Le rôle de l'âge")

    st.header("Piste 2 — D'après l'âge, à usage égal, qui est le plus stressé ?")
    st.markdown("Pour comparer des utilisateurs à **usage égal**, on regarde ceux qui passent **entre 3 et 4 h par jour** sur Instagram.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Stress des 13–17 ans (3–4 h par jour)", fr(R["age_3_4h"].loc["13–17 ans", "stress"]))
    c2.metric("Stress des 55–65 ans (3–4 h par jour)", fr(R["age_3_4h"].loc["55–65 ans", "stress"]))
    c3.metric("Stress en plus par tranche de 10 ans", f"+{fr(R['pente_age'])} point")
    age = R["age_3_4h"].reset_index()
    age["etiquette"] = age["stress"].map(fr)
    age["minutes_txt"] = age["minutes"].map(lambda v: f"{fr(v, 0)} min")
    montrer(barres_simples(
        age, "tranche_age", "stress", "etiquette",
        titre("À usage égal, le stress augmente avec l'âge", "Stress moyen des utilisateurs passant 3 à 4 h par jour sur Instagram"),
        None, "Stress moyen (0–40)", TRANCHES_AGE, [0, 30],
        [alt.Tooltip("tranche_age:N", title="Âge"), alt.Tooltip("etiquette:N", title="Stress moyen"),
         alt.Tooltip("minutes_txt:N", title="Temps moyen par jour")]))

    grille = R["grille_age"].reset_index()
    grille["etiquette"] = grille["stress"].map(fr)
    grille["n_txt"] = grille["n"].map(lambda v: fr(v, 0))
    base = alt.Chart(grille).encode(
        x=alt.X("cat_temps:N", sort=CAT_TEMPS, title="Temps passé sur Instagram par jour", axis=alt.Axis(labelAngle=0, ticks=False, domain=False)),
        y=alt.Y("tranche_age:N", sort=TRANCHES_AGE, title=None, axis=alt.Axis(ticks=False, domain=False)))
    cases = base.mark_rect(stroke=SURFACE, strokeWidth=2).encode(
        color=alt.Color("stress:Q", scale=alt.Scale(domain=[0, 40], range=SEQ),
                        legend=alt.Legend(title="Stress moyen", orient="right", direction="vertical", gradientLength=180)),
        tooltip=[alt.Tooltip("tranche_age:N", title="Âge"), alt.Tooltip("cat_temps:N", title="Temps par jour"),
                 alt.Tooltip("etiquette:N", title="Stress moyen"), alt.Tooltip("n_txt:N", title="Utilisateurs")])
    textes = base.mark_text(fontSize=12.5).encode(
        text="etiquette:N", color=alt.condition("datum.stress >= 22", alt.value("white"), alt.value(INK)))
    montrer((cases + textes).properties(
        title=titre("Le même écart d'âge dans toutes les catégories de temps",
                    "Stress moyen par âge et par temps passé · lire chaque colonne de haut en bas"), height=300))
    st.markdown("""
- Entre 3 et 4 h par jour, le stress passe de **18,4** chez les 13–17 ans à **26,2** chez les 55–65 ans.
- À temps égal, le stress augmente de **+1,2 point par tranche de 10 ans**, et le même écart se retrouve dans toutes les catégories de temps passé.
""")
    retenir("**à usage égal, ce sont les plus âgés qui sont les plus stressés.** Le temps passé ne suffit donc pas : l'âge apporte une information en plus.")

    st.header("Piste 3 — Les plus jeunes passent-ils plus de temps sur Instagram ?")
    exposition = R["exposition"].reset_index()
    exposition["etiquette"] = exposition["part_3h_ou_plus"].map(lambda v: f"{fr(v)} %")
    exposition["minutes_txt"] = exposition["minutes"].map(lambda v: f"{fr(v, 0)} min")
    c1, c2 = st.columns(2)
    c1.metric("13–17 ans à 3 h ou plus par jour", exposition.loc[0, "etiquette"])
    c2.metric("55–65 ans à 3 h ou plus par jour", exposition.loc[len(exposition) - 1, "etiquette"])
    montrer(barres_simples(
        exposition, "tranche_age", "part_3h_ou_plus", "etiquette",
        titre("Plus on est jeune, plus on passe de temps sur Instagram", "Part des utilisateurs qui y passent 3 h ou plus par jour"),
        None, "Utilisateurs à 3 h ou plus par jour", TRANCHES_AGE, [0, 75],
        [alt.Tooltip("tranche_age:N", title="Âge"), alt.Tooltip("etiquette:N", title="À 3 h ou plus"),
         alt.Tooltip("minutes_txt:N", title="Temps moyen par jour")], axe_y=AXE_POURCENT))
    chiffres(R["exposition"].rename_axis("âge"))
    st.markdown("""
- **63 %** des 13–17 ans passent 3 h ou plus par jour sur Instagram, contre **43 %** des 55–65 ans.
- Le temps moyen baisse régulièrement avec l'âge, de 223 minutes à 159 minutes par jour.
""")
    conclusion_produit("les plus jeunes sont **les plus exposés** en temps passé. Ce sont eux que les outils de limitation de temps touchent le plus souvent, et ils incluent des **mineurs**, qui demandent des précautions particulières.")
    st.caption("Source : [question écrite à l'Assemblée nationale citant le rapport « Enfants et écrans » (2024)](https://www.assemblee-nationale.fr/dyn/16/questions/QANR5L16QE18298.pdf) — chez les 16–19 ans, le temps d'écran dépasse les cinq heures ; les experts évoquent la nocivité des réseaux sociaux, « facteur de risque » de dépression ou d'anxiété en cas de « vulnérabilité préexistante ».")
    retenir("**oui, les plus jeunes passent plus de temps sur Instagram.** Deux effets opposés : les jeunes sont plus exposés en temps, les plus âgés sont plus stressés à temps égal.")


def page_stress_bonheur():
    st.title("4 · Stress et bonheur")
    st.header("Piste 4 — Le stress lié à l'usage s'accompagne-t-il d'une baisse de bonheur ?")
    c1, c2 = st.columns(2)
    c1.metric("Stress expliqué par le temps passé", f"{fr(R['r2_stress'] * 100, 0)} %")
    c2.metric("Bonheur expliqué par le temps passé", f"{fr(R['r2_bonheur'] * 100, 0)} %")

    data = R["stress_bonheur_30min"].reset_index()
    data["heures"] = (data["tranche_30min"] + 15) / 60
    data["tranche"] = data["tranche_30min"].map(lambda m: f"{m // 60} h {m % 60:02d} à {(m + 30) // 60} h {(m + 30) % 60:02d}")
    data["stress_txt"] = data["stress"].map(fr)
    data["bonheur_txt"] = data["bonheur"].map(lambda v: fr(v, 2))
    x = alt.X("heures:Q", title="Temps passé sur Instagram par jour", axis=AXE_HEURES, scale=alt.Scale(domain=[0, 8.5]))
    base = alt.Chart(data).encode(x=x)
    stress = (base.mark_line(color=BLEU, strokeWidth=2).encode(y=alt.Y("stress:Q", title="Stress perçu (0–40)", scale=alt.Scale(domain=[0, 40])))
              + base.mark_point(filled=True, size=45, color=BLEU, stroke=SURFACE, strokeWidth=1.2, opacity=1).encode(
                  y="stress:Q", tooltip=[alt.Tooltip("tranche:N", title="Temps par jour"), alt.Tooltip("stress_txt:N", title="Stress moyen")]))
    plateau = alt.Chart(pd.DataFrame({"debut": [2], "fin": [4]})).mark_rect(color=ORANGE, opacity=0.08).encode(x="debut:Q", x2="fin:Q")
    notes = alt.Chart(pd.DataFrame({"x": [3, 6.4], "y": [8.9, 5.0], "texte": ["plateau entre 2 h et 4 h", "chute après 5 h"]})).mark_text(
        fontSize=11.5, color=INK2, align="center").encode(x="x:Q", y="y:Q", text="texte:N")
    bonheur = (plateau + base.mark_line(color=ORANGE, strokeWidth=2).encode(
        y=alt.Y("bonheur:Q", title="Bonheur déclaré (1–10)", scale=alt.Scale(domain=[1, 10])))
               + base.mark_point(filled=True, size=45, color=ORANGE, stroke=SURFACE, strokeWidth=1.2, opacity=1).encode(
                   y="bonheur:Q", tooltip=[alt.Tooltip("tranche:N", title="Temps par jour"), alt.Tooltip("bonheur_txt:N", title="Bonheur moyen")])
               + notes)
    gauche, droite = st.columns(2)
    with gauche:
        montrer(stress.properties(title=titre("Le stress monte régulièrement", f"{fr(R['r2_stress'] * 100, 0)} % des écarts expliqués par le temps passé"), height=340))
    with droite:
        montrer(bonheur.properties(title=titre("Le bonheur baisse par paliers", f"{fr(R['r2_bonheur'] * 100, 0)} % des écarts expliqués par le temps passé"), height=340))
    chiffres(R["stress_bonheur_cat"].rename_axis("temps par jour"))
    st.markdown("""
- Le **stress** monte **régulièrement** avec le temps passé.
- Le **bonheur**, lui, baisse surtout **dans la première heure**, reste **stable entre 2 h et 4 h**, puis **chute après 5 h**.
- Le temps passé explique **71 %** des écarts de stress, mais seulement **16 %** des écarts de bonheur.
""")
    conclusion_produit("il faut **suivre le stress et le bonheur séparément** : un utilisateur peut être très stressé et très heureux à la fois. Le lien principal d'Instagram est avec **le stress**, pas avec le bonheur en général.")
    st.caption("Source : [le modèle « dual continua » de Keyes (Frontiers in Psychology, 2022)](https://www.frontiersin.org/articles/10.3389/fpsyg.2022.885278/full) — la santé mentale positive et la détresse sont deux dimensions distinctes.")
    retenir("le stress lié à l'usage s'accompagne d'une baisse de bonheur, mais **beaucoup plus faible et moins régulière**. Stress et bonheur sont deux indicateurs différents.")


def page_segmentation():
    st.title("5 · La segmentation")
    st.markdown("**Deux informations suffisent** à construire des segments : le **temps passé par jour** et l'**âge**. Toutes deux sont connues pour **tous** les utilisateurs, et aucune n'est une donnée de santé.")

    st.header("Pourquoi cette méthode ?")
    st.markdown("""
La consigne propose deux voies : **prédire un indicateur de bien-être** à partir de l'usage, ou **regrouper automatiquement** les utilisateurs (*clustering*). Nous avons choisi la première, sous une forme simple : des **segments par paliers** de temps passé et d'âge.

- **Un regroupement automatique retrouverait surtout le temps passé** : presque toutes les variables d'usage en sont des copies (graphique ci-dessous).
- **Ses groupes sont difficiles à expliquer** et peuvent changer d'une exécution à l'autre.
- **Il ne vise pas le bien-être** : il regroupe des usages qui se ressemblent, pas des utilisateurs dont le stress diffère.
- **Nos segments sont construits pour séparer le stress**, lisibles, applicables à tous et sans donnée de santé.
""")
    copies = R["copies"].reset_index().rename(columns={"index": "variable", "corrélation avec le temps passé": "correlation"})
    copies["etiquette"] = copies["correlation"].map(lambda v: fr(v, 2))
    base = alt.Chart(copies).encode(
        y=alt.Y("variable:N", sort="-x", title=None),
        x=alt.X("correlation:Q", title="Corrélation avec le temps passé par jour (0 à 1)", scale=alt.Scale(domain=[0, 1.05]),
                axis=alt.Axis(labelExpr="replace(format(datum.value, '.1f'), '.', ',')")))
    montrer((base.mark_bar(size=20, cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=BLEU).encode(
        tooltip=[alt.Tooltip("variable:N", title="Variable"), alt.Tooltip("etiquette:N", title="Corrélation")])
             + base.mark_text(align="left", dx=6, fontSize=12, color=INK).encode(text="etiquette:N")).properties(
        title=titre("Les variables d'usage sont presque des copies du temps passé",
                    "Un regroupement automatique sur ces variables retrouverait surtout le temps passé"), height=260))
    retenir("plutôt qu'un regroupement automatique difficile à expliquer, nous construisons des segments simples, choisis parce qu'ils séparent le stress.")

    st.header("La carte des segments et le simulateur")
    st.markdown("Entrez l'âge et le temps quotidien d'un **utilisateur fictif** : l'application lui attribue son segment et l'encadre sur la carte.")
    col_age, col_minutes = st.columns(2)
    age = col_age.slider("Âge", min_value=13, max_value=65, value=16)
    minutes = col_minutes.slider("Temps passé sur Instagram par jour (minutes)", min_value=0, max_value=540, value=250, step=5)
    groupe = pd.cut([age], BORNES_AGE_SEGMENT, right=False, labels=GROUPES_SEGMENT)[0]
    categorie = pd.cut([minutes], BORNES_TEMPS, right=False, labels=CAT_TEMPS)[0]
    segment = R["segments"].loc[(groupe, categorie)]
    c1, c2, c3 = st.columns(3)
    c1.metric("Segment", f"{groupe} · {categorie}")
    c2.metric("Part en stress élevé dans ce segment", f"{fr(segment['part_stress_eleve'], 0)} %")
    c3.metric("Utilisateurs dans ce segment", fr(segment["n"], 0))
    if age < 18:
        st.warning("Utilisateur mineur : seules des protections activées par défaut sont envisageables (rappel de temps, mode sommeil), sans profilage publicitaire.")

    cases = R["segments"].reset_index()
    cases["etiquette"] = cases["part_stress_eleve"].map(lambda v: f"{fr(v, 0)} %")
    cases["stress_txt"] = cases["stress"].map(fr)
    cases["n_txt"] = cases["n"].map(lambda v: fr(v, 0))
    base = alt.Chart(cases).encode(
        x=alt.X("cat_temps:N", sort=CAT_TEMPS, title="Temps passé sur Instagram par jour", axis=alt.Axis(labelAngle=0, ticks=False, domain=False)),
        y=alt.Y("groupe_segment:N", sort=GROUPES_SEGMENT, title=None, axis=alt.Axis(ticks=False, domain=False)))
    carte = base.mark_rect(stroke=SURFACE, strokeWidth=2).encode(
        color=alt.Color("part_stress_eleve:Q", scale=alt.Scale(domain=[0, 100], range=SEQ),
                        legend=alt.Legend(title="Stress élevé (%)", orient="right", direction="vertical", gradientLength=160)),
        tooltip=[alt.Tooltip("groupe_segment:N", title="Âge"), alt.Tooltip("cat_temps:N", title="Temps par jour"),
                 alt.Tooltip("etiquette:N", title="En stress élevé"), alt.Tooltip("stress_txt:N", title="Stress moyen"),
                 alt.Tooltip("n_txt:N", title="Utilisateurs")])
    textes = base.mark_text(fontSize=13).encode(
        text="etiquette:N", color=alt.condition("datum.part_stress_eleve >= 55", alt.value("white"), alt.value(INK)))
    choix = alt.Chart(pd.DataFrame({"cat_temps": [categorie], "groupe_segment": [groupe]})).mark_rect(
        fill=None, stroke=ORANGE, strokeWidth=4).encode(x=alt.X("cat_temps:N", sort=CAT_TEMPS), y=alt.Y("groupe_segment:N", sort=GROUPES_SEGMENT))
    montrer((carte + textes + choix).properties(
        title=titre("Carte des segments : part des utilisateurs en stress élevé",
                    "24 segments construits uniquement à partir du temps passé et de l'âge · cadre orange : l'utilisateur simulé"),
        height=280))
    chiffres(R["segments"].rename_axis(["âge", "temps par jour"]))
    st.markdown("""
- Les segments vont de **0 %** à **97 %** d'utilisateurs en stress élevé.
- À temps égal, l'âge change fortement le résultat : entre 3 h et 4 h par jour, environ **15 %** de stress élevé chez les 13–17 ans contre **49 %** chez les 55–65 ans.
""")
    retenir("une segmentation **simple** (temps passé × âge), **applicable à tous les utilisateurs** et **sans donnée de santé**, qui apporte plus qu'un simple classement par temps passé.")

    st.header("Nos critères d'une bonne segmentation")
    st.markdown("Personne ne nous a dit ce qu'est une bonne segmentation : nous fixons nos propres critères, tous **vérifiables sur les données**.")
    st.table(R["criteres"])
    retenir("les six critères sont atteints : la segmentation est discriminante, utile au-delà du temps passé, applicable à tous, stable, sans risque d'isoler quelqu'un et sans donnée de santé.")

    st.header("Piste 5 — Quatre profils de bien-être selon le temps passé")
    st.markdown("On croise le stress (élevé à partir de 27) et le bonheur (élevé à partir de 7).")
    parts = R["profils"].reset_index().melt(id_vars="cat_temps", var_name="profil", value_name="part")
    parts["ordre"] = parts["profil"].map({p: i for i, p in enumerate(PROFILS)})
    parts = parts.sort_values(["cat_temps", "ordre"])
    parts["fin"] = parts.groupby("cat_temps", observed=True)["part"].cumsum()
    parts["milieu"] = parts["fin"] - parts["part"] / 2
    parts["etiquette"] = parts["part"].map(lambda v: f"{fr(v, 0)} %")
    parts["etiquette_detail"] = parts["part"].map(lambda v: f"{fr(v)} %")
    base = alt.Chart(parts).encode(x=alt.X("cat_temps:N", sort=CAT_TEMPS, title="Temps passé sur Instagram par jour", axis=alt.Axis(labelAngle=0)))
    empile = base.mark_bar(size=46, stroke=SURFACE, strokeWidth=1.5).encode(
        y=alt.Y("part:Q", stack="zero", title="Part des utilisateurs", scale=alt.Scale(domain=[0, 100]), axis=AXE_POURCENT),
        color=alt.Color("profil:N", scale=alt.Scale(domain=PROFILS, range=RAMPE_4), title=None, legend=alt.Legend(columns=2)),
        order=alt.Order("ordre:Q", sort="ascending"),
        tooltip=[alt.Tooltip("cat_temps:N", title="Temps par jour"), alt.Tooltip("profil:N", title="Profil"),
                 alt.Tooltip("etiquette_detail:N", title="Part")])
    etiquettes = base.mark_text(fontSize=12).encode(
        y="milieu:Q", text="etiquette:N",
        color=alt.condition(f"datum.profil == '{PROFILS[0]}'", alt.value(INK), alt.value("white"))).transform_filter("datum.part >= 12")
    montrer((empile + etiquettes).properties(
        title=titre("Plus le temps passé augmente, plus le bien-être se dégrade",
                    "Répartition des quatre profils de bien-être par catégorie de temps passé · survolez les barres"), height=400))
    chiffres(R["profils"].rename_axis(index="temps par jour", columns="profil"))
    st.markdown("""
- En dessous d'1 h par jour, **plus des deux tiers** des utilisateurs sont sereins et heureux.
- Au-delà de 5 h, **les trois quarts** sont stressés et peu heureux.
- Entre les deux, on passe d'abord par « serein mais peu heureux », puis par « stressé mais heureux ».
""")
    conclusion_produit("ces profils décrivent **le parcours du bien-être selon la dose d'usage**. C'est plus parlant qu'un seul indicateur. Ils restent une lecture des résultats agrégés : **on ne les attribue pas à un utilisateur**, puisqu'ils reposent sur des données de santé du panel.")
    retenir("plus la dose d'usage augmente, plus les utilisateurs glissent d'un profil serein et heureux vers un profil stressé et peu heureux.")


def page_protection():
    st.title("6 · Protection des données")
    st.markdown("La consigne nous demande de prendre position, pour les utilisateurs de l'Union européenne et du Royaume-Uni, y compris les moins de 18 ans, sur deux questions.")

    st.header("Sur quelles variables les segments peuvent-ils reposer pour du ciblage ?")
    st.markdown("""
**Uniquement le temps passé par jour et l'âge.**
- Ce sont des données qu'Instagram détient **pour tous ses utilisateurs**, et ce ne sont **pas des données de santé**.
- **Les variables de santé et de bien-être sont exclues** (stress, bonheur, sommeil, IMC, tension, tabac, alcool, alimentation, sport) : ce sont des données sensibles au sens de l'article 9 du RGPD ([CNIL](https://www.cnil.fr/fr/definition/donnee-sensible)), données seulement pour l'étude bien-être.
- **Les autres variables de profil sont exclues aussi** (genre, revenu, emploi, couple, enfants) : elles n'apportent rien, et le RGPD demande de ne traiter que les données nécessaires.
""")
    st.header("Placer un utilisateur dans un segment peut-il révéler quelque chose sur sa santé ?")
    groupe_max, temps_max = R["segment_max"]
    nb, total, part = R["revelateurs"]
    c1, c2 = st.columns(2)
    c1.metric("Segment le plus révélateur", f"{groupe_max} · {temps_max}", delta=f"{fr(R['part_max'], 0)} % en stress élevé", delta_color="off")
    c2.metric("Segments à 80 % de stress élevé ou plus", f"{nb} sur {total}", delta=f"{fr(part, 0)} % des utilisateurs", delta_color="off")
    st.markdown("""
**Oui.** Même construits sans donnée de santé, certains segments laissent deviner un état de stress avec une forte probabilité. Une donnée qui révèle indirectement un état de santé doit être traitée comme une donnée de santé. D'où trois conditions :
- **nommer les segments par l'usage** (« 4–5 h par jour, 55–65 ans »), jamais par le stress attendu ;
- **ne stocker aucun score de stress** par utilisateur ;
- **réserver les segments aux outils de protection** (rappels de temps, mode sommeil), sans publicité.
""")
    st.header("Les mineurs")
    st.markdown("""
- **Royaume-Uni :** le code de conception adapté à l'âge de l'ICO demande que **le profilage des enfants soit désactivé par défaut**, sauf raison impérieuse dans leur intérêt ([résumé par RPC](https://www.rpclegal.com/snapshots/data-protection/ico-age-appropriate-design-code-for-information-society-services/)).
- **Union européenne :** le DSA (article 28) **interdit les publicités fondées sur le profilage** d'un utilisateur dont la plateforme sait qu'il est mineur ([EUR-Lex](https://eur-lex.europa.eu/eli/reg/2022/2065/oj)).
""")
    st.header("Les mesures que nous appliquons et recommandons")
    st.markdown("""
- **Seuil de 100 utilisateurs :** aucune ligne individuelle ni aucun groupe de moins de 100 personnes n'est affiché, dans le notebook comme dans cette application.
- **Données brutes hors du dépôt Git :** le dossier `data/` est ajouté au fichier `.gitignore`.
- **Une section « Limites et protection des données »** dans le notebook et dans le README.
- **Interdiction écrite** d'utiliser les segments pour la publicité ou de les transmettre aux annonceurs.
- **Informer les utilisateurs** du classement en segments, dans la politique de confidentialité.
- **Inscrire le traitement au registre des traitements**, avec sa finalité, les données utilisées et la durée de conservation.
""")
    st.markdown("**Vérification de la règle des 100 utilisateurs**")
    tableau(R["tailles"], 0)


def page_limites():
    st.title("7 · Limites")
    st.markdown("Ce que nos données **ne permettent pas d'affirmer**, et les points à garder en tête avant d'appliquer ces résultats à de vrais utilisateurs.")
    st.header("Pas de cause à effet")
    st.markdown("Tous nos liens sont des **corrélations**. On ne peut pas dire qu'Instagram *cause* le stress : les personnes stressées pourraient aussi passer plus de temps sur l'application. Seules des expériences, où l'on fait varier le temps passé, peuvent tester une cause.")
    st.header("Un panel de volontaires")
    st.markdown("Le stress et le bonheur ne sont mesurés que chez les **volontaires** de l'étude bien-être. Ils ne ressemblent pas forcément à l'ensemble des utilisateurs.")
    st.header("Une réplique synthétique")
    st.markdown("""
- **Le lien entre temps passé et stress est très fort** : 71 % des écarts expliqués, contre 0,4 % au maximum dans les études réelles ([Orben & Przybylski, 2019](https://www.oii.ox.ac.uk/technology-use-explains-at-most-0-4-of-adolescent-wellbeing/)).
- **Des effets connus sont absents** : le sommeil et le sport n'ont aucun lien ici.
- **Un lien caché, très probablement artificiel, entre stress et bonheur** :
""")
    c1, c2 = st.columns(2)
    c1.metric("Corrélation stress ↔ bonheur, sur tous les utilisateurs", fr(R["corr_globale"], 2))
    c2.metric("Corrélation stress ↔ bonheur, à temps passé égal", fr(R["corr_temps_egal"], 2))
    cache = R["lien_cache"].reset_index()
    cache["etiquette"] = cache["stress_moyen"].map(fr)
    cache["n_txt"] = cache["n"].map(lambda v: fr(v, 0))
    montrer(barres_simples(
        cache, "niveau_bonheur", "stress_moyen", "etiquette",
        titre("À temps égal, les plus heureux sont aussi les plus stressés",
              "Stress moyen selon le bonheur, chez les utilisateurs passant 2 à 3 h par jour"),
        "Bonheur déclaré (1–10)", "Stress moyen (0–40)", ["1–2", "3–4", "5–6", "7–8", "9–10"], [0, 30],
        [alt.Tooltip("niveau_bonheur:N", title="Bonheur"), alt.Tooltip("etiquette:N", title="Stress moyen"),
         alt.Tooltip("n_txt:N", title="Utilisateurs")], couleur=MUTED))
    st.markdown("""
- Sur l'ensemble des utilisateurs, stress et bonheur **ne sont pas liés** (corrélation de 0,00). Mais **à temps passé égal**, ils sont **fortement liés, dans le même sens** (+0,60).
- Les deux effets s'annulent : plus de temps passé va avec plus de stress et moins de bonheur, mais à temps égal, les plus heureux sont aussi les plus stressés.
- **C'est très probablement un effet de la génération des données** : dans la réalité, on s'attend plutôt à ce que les personnes stressées soient moins heureuses. Ce lien ne sert pas à la segmentation.
""")
    st.header("D'autres points de prudence")
    st.markdown("""
- **Le seuil de stress élevé (27)** est une convention de lecture de l'échelle PSS-10, pas un seuil de diagnostic.
- **Le choix du fichier** n'est sûr que pour les colonnes utilisées : les autres écarts entre les deux versions ne peuvent pas être départagés sans la documentation du nettoyage.
""")
    retenir("nos résultats décrivent **des tendances fortes dans une réplique synthétique**. Ils indiquent où regarder, mais doivent être **confirmés sur de vraies données**, et ne permettent jamais de conclure à une cause.")


def page_conclusion():
    st.title("8 · Conclusion générale")
    st.header("Le lien entre l'usage d'Instagram et le bien-être")
    st.markdown("""
- **Le temps passé chaque jour est le facteur central.** Il explique **71 %** des écarts de stress (environ +5,4 points par heure) et **16 %** des écarts de bonheur. Les plus heureux passent deux fois moins de temps sur l'application que les plus malheureux (128 min contre 247 min).
- **L'âge change ce lien.** Les plus jeunes passent plus de temps sur Instagram, mais à temps égal, les plus âgés sont plus stressés (+1,2 point par tranche de 10 ans).
- **Le sommeil et l'activité physique ne sont pas liés à l'usage** dans notre panel.
- **Stress et bonheur sont deux indicateurs distincts**, à suivre séparément.
""")
    st.header("Une segmentation utilisable par les équipes produit")
    st.markdown("""
- Deux informations suffisent, **le temps passé et l'âge**, connues pour tous les utilisateurs et sans donnée de santé.
- La carte des segments donne directement **les groupes à accompagner en priorité**, et un nouvel utilisateur peut y être placé (simulateur de la partie 5).
- Les quatre profils de bien-être décrivent **le parcours du bien-être selon la dose d'usage**.
- **Les limites** (partie 7) : des corrélations et non des causes, un panel de volontaires, et une réplique synthétique.
""")
    st.header("Trois recommandations pour les équipes produit")
    st.markdown("""
1. **Un rappel de temps quotidien cumulé, avec un seuil selon l'âge.** Entre 2 h et 3 h par jour, environ 19 % des 55–65 ans sont déjà en stress élevé, contre 2 % des 13–17 ans. Nous recommandons un rappel vers **2 h par jour pour les 55–65 ans** et vers **3 h pour les 13–17 ans**, **activé par défaut pour les mineurs**, qui compte le temps **de toute la journée**.
2. **Faire du temps quotidien passé l'indicateur de suivi numéro un**, par segment, dans les tableaux de bord produit, et **suivre le stress et le bonheur séparément** dans les études bien-être.
3. **Réserver les segments aux outils de protection** (rappels, mode sommeil) : jamais de publicité, des segments nommés par l'usage, et une analyse d'impact sur la protection des données avant tout déploiement.
""")
    st.success("**En une phrase :** plus on passe de temps sur Instagram, plus on est stressé, et ce lien est plus fort chez les plus âgés ; une segmentation simple par temps passé et âge permet aux équipes produit de cibler leurs outils de protection, sans utiliser de données de santé.")


def page_sources():
    st.title("Sources")
    st.markdown("""
- info.gouv.fr, 2025 : [le sommeil et la santé mentale](https://www.info.gouv.fr/actualite/sante-mentale-pourquoi-le-sommeil-joue-un-role-cle)
- Ameli : [activité physique et bien-être](https://www.ameli.fr/assure/sante/themes/activite-physique-sante/sport-et-activite-physique-un-atout-pour-le-bien-etre)
- Riehm et al., 2019, *JAMA Psychiatry* : [présentation par Johns Hopkins](https://hub.jhu.edu/2019/09/11/social-media-teen-mental-health/)
- Liu et al., 2022, méta-analyse dose–effet : [texte intégral (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9103874/)
- Assemblée nationale, question écrite citant le rapport « Enfants et écrans » (2024) : [PDF](https://www.assemblee-nationale.fr/dyn/16/questions/QANR5L16QE18298.pdf)
- Modèle de Keyes : [Frontiers in Psychology, 2022](https://www.frontiersin.org/articles/10.3389/fpsyg.2022.885278/full)
- Orben & Przybylski, 2019, *Nature Human Behaviour* : [Oxford Internet Institute](https://www.oii.ox.ac.uk/technology-use-explains-at-most-0-4-of-adolescent-wellbeing/)
- Échelle PSS-10 : [guide de cotation (NovoPsych)](https://novopsych.com.au/wp-content/uploads/2022/02/pss-10-report-PDF.pdf)
- Protection des données : [CNIL, données sensibles](https://www.cnil.fr/fr/definition/donnee-sensible) · [DSA (EUR-Lex)](https://eur-lex.europa.eu/eli/reg/2022/2065/oj) · [code de l'ICO (résumé par RPC)](https://www.rpclegal.com/snapshots/data-protection/ico-age-appropriate-design-code-for-information-society-services/)
""")


PAGES = {
    "Introduction": page_introduction,
    "0 · Données et variables": page_donnees,
    "1 · Pistes sans lien": page_pistes_sans_lien,
    "2 · Temps passé": page_temps,
    "3 · Âge": page_age,
    "4 · Stress et bonheur": page_stress_bonheur,
    "5 · Segmentation": page_segmentation,
    "6 · Protection des données": page_protection,
    "7 · Limites": page_limites,
    "8 · Conclusion": page_conclusion,
    "Sources": page_sources,
}

with st.sidebar:
    st.markdown("### Rush 4 · Instagram et bien-être")
    choix_page = st.radio("Parties", list(PAGES), label_visibility="collapsed")
    st.divider()
    st.caption(f"{fr(R['n'], 0)} utilisateurs synthétiques · résultats agrégés uniquement, aucun groupe de moins de {MIN_N} utilisateurs.")

PAGES[choix_page]()
