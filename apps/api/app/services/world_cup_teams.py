from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class TeamDefinition:
    canonical: str
    api_names: tuple[str, ...]
    aliases: tuple[str, ...]


WORLD_CUP_TEAMS: tuple[TeamDefinition, ...] = (
    TeamDefinition("Germany", ("Germany",), ("Alemania", "Deutschland")),
    TeamDefinition("Algeria", ("Algeria",), ("Argelia",)),
    TeamDefinition("Argentina", ("Argentina",), ()),
    TeamDefinition("Australia", ("Australia",), ()),
    TeamDefinition("Austria", ("Austria",), ("Austria",)),
    TeamDefinition("Belgium", ("Belgium",), ("Bélgica", "Belgica")),
    TeamDefinition("Bosnia and Herzegovina", ("Bosnia and Herzegovina", "Bosnia-Herzegovina"), ("Bosnia y Herzegovina", "Bosnia")),
    TeamDefinition("Brazil", ("Brazil",), ("Brasil",)),
    TeamDefinition("Cape Verde", ("Cape Verde", "Cabo Verde"), ("Cabo Verde",)),
    TeamDefinition("Canada", ("Canada",), ("Canadá",)),
    TeamDefinition("Colombia", ("Colombia",), ()),
    TeamDefinition("South Korea", ("South Korea", "Korea Republic", "Republic of Korea"), ("Corea del Sur", "Corea", "Sur Korea", "Korea del Sur")),
    TeamDefinition("Ivory Coast", ("Ivory Coast", "Côte d'Ivoire", "Cote d'Ivoire"), ("Costa de Marfil", "Costa Marfil")),
    TeamDefinition("Croatia", ("Croatia",), ("Croacia",)),
    TeamDefinition("Curaçao", ("Curaçao", "Curacao"), ("Curazao",)),
    TeamDefinition("Ecuador", ("Ecuador",), ()),
    TeamDefinition("Egypt", ("Egypt",), ("Egipto",)),
    TeamDefinition("Scotland", ("Scotland",), ("Escocia",)),
    TeamDefinition("Spain", ("Spain",), ("España", "Espana", "La Roja")),
    TeamDefinition("United States", ("United States", "USA", "United States of America"), ("US", "Estados Unidos", "EEUU", "EE.UU.")),
    TeamDefinition("France", ("France",), ("Francia",)),
    TeamDefinition("Ghana", ("Ghana",), ()),
    TeamDefinition("Haiti", ("Haiti", "Haïti"), ("Haití",)),
    TeamDefinition("England", ("England",), ("Inglaterra",)),
    TeamDefinition("Iran", ("Iran",), ("Irán",)),
    TeamDefinition("Iraq", ("Iraq",), ("Irak",)),
    TeamDefinition("Japan", ("Japan",), ("Japón", "Japon")),
    TeamDefinition("Jordan", ("Jordan",), ("Jordania",)),
    TeamDefinition("Morocco", ("Morocco",), ("Marruecos",)),
    TeamDefinition("Mexico", ("Mexico",), ("México", "Mejico", "Méjico")),
    TeamDefinition("New Zealand", ("New Zealand",), ("Nueva Zelanda",)),
    TeamDefinition("Norway", ("Norway",), ("Noruega",)),
    TeamDefinition("Netherlands", ("Netherlands", "Holland"), ("Países Bajos", "Paises Bajos", "Holanda")),
    TeamDefinition("Panama", ("Panama",), ("Panamá",)),
    TeamDefinition("Paraguay", ("Paraguay",), ()),
    TeamDefinition("Portugal", ("Portugal",), ()),
    TeamDefinition("Qatar", ("Qatar",), ("Catar",)),
    TeamDefinition("Czechia", ("Czechia", "Czech Republic"), ("República Checa", "Republica Checa", "Chequia")),
    TeamDefinition("DR Congo", ("Congo DR", "DR Congo", "Democratic Republic of the Congo"), ("República Democrática del Congo", "Republica Democratica del Congo", "RD Congo")),
    TeamDefinition("Saudi Arabia", ("Saudi Arabia",), ("Arabia Saudí", "Arabia Saudi", "Arabia Saudita")),
    TeamDefinition("Senegal", ("Senegal",), ("Senégal",)),
    TeamDefinition("South Africa", ("South Africa",), ("Sudáfrica", "Sudafrica", "Sur África", "Sur Africa", "RSA")),
    TeamDefinition("Sweden", ("Sweden",), ("Suecia",)),
    TeamDefinition("Switzerland", ("Switzerland",), ("Suiza",)),
    TeamDefinition("Turkey", ("Turkey", "Türkiye", "Turkiye"), ("Turquía", "Turquia")),
    TeamDefinition("Tunisia", ("Tunisia",), ("Túnez", "Tunez")),
    TeamDefinition("Uruguay", ("Uruguay",), ()),
    TeamDefinition("Uzbekistan", ("Uzbekistan",), ("Uzbekistán",)),
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower().replace(".", " ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def team_aliases_by_canonical() -> dict[str, tuple[str, ...]]:
    return {team.canonical: aliases_for_team_name(team.canonical) for team in WORLD_CUP_TEAMS}


def aliases_for_team_name(team_name: str) -> tuple[str, ...]:
    definition = team_definition_for_name(team_name)
    if not definition:
        return (team_name,) if team_name else ()
    aliases = (definition.canonical, *definition.api_names, *definition.aliases)
    return tuple(dict.fromkeys(alias for alias in aliases if alias))


def canonical_team_name(team_name: str) -> str:
    definition = team_definition_for_name(team_name)
    return definition.canonical if definition else team_name


def team_definition_for_name(team_name: str) -> TeamDefinition | None:
    normalized = normalize_text(team_name)
    if not normalized:
        return None
    for definition in WORLD_CUP_TEAMS:
        names = (definition.canonical, *definition.api_names, *definition.aliases)
        if normalized in {normalize_text(name) for name in names}:
            return definition
    return None
