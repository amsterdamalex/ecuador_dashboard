"""
Ecuador OSINT Dashboard — Constants & Configuration.

No external dependencies. Safe to import anywhere.
"""

SOURCES: dict[str, str] = {
    "El Universo":          "https://www.eluniverso.com/rss/",
    "Primicias":            "https://www.primicias.ec/rss/",
    "El Comercio":          "https://www.elcomercio.com/rss/",
    "BBC Mundo":            "https://www.bbc.com/mundo/topics/c8n7z3k8y5zt/rss",
    "Reuters LatAm":        "https://www.reuters.com/world/americas/rss/",
    "InSight Crime":        "https://insightcrime.org/feed/",
    "France 24 Américas":   "https://www.france24.com/es/rss/americas",
    "Crisis Group LatAm":   "https://www.crisisgroup.org/rss/73",
    "OHCHR News":           "https://www.ohchr.org/en/rss/NewsEvents",
    "Human Rights Watch":   "https://www.hrw.org/rss/news",
    "Global Voices LatAm":  "https://globalvoices.org/world/latin-america/rss/",
}

KEYWORD_THEMES: dict[str, list[str]] = {
    "Security & Crime": [
        "narcotráfico", "cocaína", "homicidio", "violencia", "asesinato",
        "sicario", "masacre", "crimen", "Los Choneros", "Lobos", "Fito",
        "extorsión", "banda", "secuestro", "prison", "cárcel", "pandilla",
    ],
    "Political": [
        "Noboa", "Correa", "gobierno", "presidente", "asamblea",
        "elecciones", "política", "ministro", "estado de excepción",
        "decreto", "congreso", "correísmo",
    ],
    "Humanitarian": [
        "desplazado", "refugiado", "derechos humanos", "pobreza",
        "migración", "ACNUR", "CICR", "Cruz Roja", "comunidad",
        "indígena", "víctima", "protección", "humanitario",
    ],
    "Economic": [
        "economía", "petróleo", "exportación", "puerto", "Guayaquil",
        "Posorja", "dolarización", "FMI", "deuda", "inversión",
    ],
}

HIGH_SEVERITY = {
    "masacre", "asesinato", "homicidio", "sicario", "bomba", "ataque",
    "muerte", "muerto", "víctima", "secuestro", "desaparecido",
    "tortura", "ejecución", "violación", "matanza",
}

MEDIUM_SEVERITY = {
    "violencia", "crimen", "narcotráfico", "extorsión", "amenaza",
    "detenido", "arrestado", "operación", "banda", "pandilla",
    "protesta", "disturbio", "represión", "desplazado",
}

LOCATION_COORDS: dict[str, tuple[float, float]] = {
    "guayaquil":    (-2.1894, -79.8891),
    "quito":        (-0.1807, -78.4678),
    "esmeraldas":   (0.9592, -79.6516),
    "manta":        (-0.9677, -80.7089),
    "cuenca":       (-2.9001, -79.0059),
    "portoviejo":   (-1.0546, -80.4545),
    "machala":      (-3.2581, -79.9554),
    "santo domingo": (-0.2526, -79.1719),
    "loja":         (-3.9931, -79.2042),
    "ambato":       (-1.2543, -78.6228),
    "posorja":      (-2.6833, -80.2333),
    "tumaco":       (1.8002, -78.7772),
    "cali":         (3.4516, -76.5320),
    "bogotá":       (4.7110, -74.0721),
    "colombia":     (4.5709, -74.2973),
    "perú":         (-9.1900, -75.0152),
}
