import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://aethonwebcomics.com/"
OUTPUT = Path("Shadow_Slave.ics")

TZ = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# Premier épisode connu du planning hebdomadaire.
LAUNCH_DATE = datetime(
    2026, 8, 19, 21, 0, tzinfo=TZ
)

# Nombre d'épisodes futurs à mettre dans le calendrier.
FUTURE_EPISODES = 8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; ShadowSlaveCalendar/1.0; "
        "+https://github.com/Sky-077/shadow-slave-calendar)"
    )
}


def fetch_home():
    response = requests.get(
        BASE_URL,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def episode_links(soup):
    """
    Détecte les liens du type :
    /comic-episode/episode-11/
    """

    found = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]

        match = re.search(
            r"/comic-episode/episode-(\d+)/?",
            href,
            re.IGNORECASE,
        )

        if not match:
            continue

        episode = int(match.group(1))

        title = link.get_text(
            " ",
            strip=True,
        )

        if not title:
            title = f"Episode {episode}"

        found[episode] = title

    return found


def parse_episode_number(text):
    """
    Cherche :
    Episode 12
    Ep. 12
    EP 12
    """

    match = re.search(
        r"(?:episode|ep\.?)\s*[^0-9]{0,10}(\d+)",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return None


def announcement_links(soup):
    """
    Récupère les liens /updates/ présents sur Aethon.
    """

    results = []

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/updates/" not in href:
            continue

        title = link.get_text(
            " ",
            strip=True,
        )

        results.append(
            (href, title)
        )

    # Suppression des doublons
    return list(dict.fromkeys(results))


def parse_explicit_date(text):
    """
    Cherche différentes formes de dates :

    2026-10-07
    2026/10/07
    07-10-2026
    07/10/2026
    """

    patterns = [
        r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b",
        r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
        )

        if not match:
            continue

        groups = match.groups()

        try:
            # YYYY-MM-DD
            if len(groups[0]) == 4:
                year = int(groups[0])
                month = int(groups[1])
                day = int(groups[2])

            # DD-MM-YYYY
            else:
                day = int(groups[0])
                month = int(groups[1])
                year = int(groups[2])

            return datetime(
                year,
                month,
                day,
                21,
                0,
                tzinfo=TZ,
            )

        except ValueError:
            pass

    return None


def parse_relative_wednesday(text):
    """
    Détecte une annonce du type :
    "next Wednesday"
    """

    if not re.search(
        r"\bnext\s+wednesday\b",
        text,
        re.IGNORECASE,
    ):
        return None

    now = datetime.now(TZ)

    # Wednesday = 2
    days_until = (2 - now.weekday()) % 7

    if days_until == 0:
        days_until = 7

    date = now + timedelta(
        days=days_until
    )

    return date.replace(
        hour=21,
        minute=0,
        second=0,
        microsecond=0,
    )


def get_release_date(text):
    date = parse_explicit_date(text)

    if date:
        return date

    return parse_relative_wednesday(text)


def fetch_announcement(url):
    if url.startswith("/"):
        url = BASE_URL.rstrip("/") + url

    elif not url.startswith("http"):
        url = (
            BASE_URL.rstrip("/")
            + "/"
            + url.lstrip("/")
        )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    return soup.get_text(
        " ",
        strip=True,
    )


def build_future_events(last_episode):
    """
    Construit le planning prévisionnel
    à partir du rythme hebdomadaire.
    """

    events = []

    first_episode = max(
        last_episode + 1,
        1,
    )

    last_future_episode = (
        last_episode
        + FUTURE_EPISODES
    )

    for episode in range(
        first_episode,
        last_future_episode + 1,
    ):
        release_date = (
            LAUNCH_DATE
            + timedelta(
                days=7 * (episode - 1)
            )
        )

        events.append(
            {
                "episode": episode,
                "start": release_date,
                "title": (
                    f"Shadow Slave — "
                    f"Episode {episode}"
                ),
                "description": (
                    "Date prévue selon le "
                    "rythme hebdomadaire du "
                    "webcomic."
                ),
            }
        )

    return events


def escape_ics(value):
    """
    Échappement des caractères spéciaux ICS.
    """

    value = str(value)

    value = value.replace(
        "\\",
        "\\\\",
    )

    value = value.replace(
        ";",
        "\\;",
    )

    value = value.replace(
        ",",
        "\\,",
    )

    value = value.replace(
        "\r\n",
        "\\n",
    )

    value = value.replace(
        "\n",
        "\\n",
    )

    return value


def format_utc(date):
    return date.astimezone(
        UTC
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def make_ics(events):
    """
    Génère le fichier iCalendar.
    """

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Sky-077//Shadow Slave Calendar//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Shadow Slave",
        "X-WR-TIMEZONE:America/New_York",
    ]

    generated_at = datetime.now(UTC)

    for event in events:
        episode = event["episode"]
        start = event["start"]

        end = start + timedelta(
            hours=1
        )

        uid = (
            f"shadow-slave-episode-"
            f"{episode}@sky-077"
        )

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{format_utc(generated_at)}",
                f"DTSTART:{format_utc(start)}",
                f"DTEND:{format_utc(end)}",
                (
                    "SUMMARY:"
                    + escape_ics(
                        event["title"]
                    )
                ),
                (
                    "DESCRIPTION:"
                    + escape_ics(
                        event["description"]
                    )
                ),
                "END:VEVENT",
            ]
        )

    lines.append(
        "END:VCALENDAR"
    )

    return (
        "\r\n".join(lines)
        + "\r\n"
    )


def refine_events_from_announcements(
    soup,
    events,
):
    """
    Cherche les annonces Shadow Slave
    et remplace les dates prévisionnelles
    lorsqu'une date explicite est trouvée.
    """

    announcements = announcement_links(
        soup
    )

    for href, title in announcements:

        title_lower = title.lower()
        href_lower = href.lower()

        # On ne garde que les annonces
        # susceptibles de concerner Shadow Slave.
        if (
            "shadow" not in title_lower
            and "shadow" not in href_lower
        ):
            continue

        try:
            text = fetch_announcement(
                href
            )

        except requests.RequestException as error:
            print(
                f"Annonce ignorée : {href}"
            )
            print(
                f"Erreur : {error}"
            )
            continue

        combined_text = (
            title
            + " "
            + text
        )

        episode = parse_episode_number(
            combined_text
        )

        if episode is None:
            continue

        release_date = get_release_date(
            combined_text
        )

        if release_date is None:
            continue

        for event in events:
            if event["episode"] == episode:
                event["start"] = release_date

                event["description"] = (
                    "Date issue d'une "
                    "annonce Aethon Webcomics."
                )

                break


def main():
    print(
        "Vérification de Aethon Webcomics..."
    )

    soup = fetch_home()

    episodes = episode_links(
        soup
    )

    last_episode = (
        max(episodes)
        if episodes
        else 0
    )

    print(
        f"Dernier épisode détecté : "
        f"S1:E{last_episode}"
    )

    events = build_future_events(
        last_episode
    )

    refine_events_from_announcements(
        soup,
        events,
    )

    events.sort(
        key=lambda event: event["start"]
    )

    calendar = make_ics(
        events
    )

    OUTPUT.write_text(
        calendar,
        encoding="utf-8",
        newline="",
    )

    print(
        f"Calendrier mis à jour : "
        f"{OUTPUT}"
    )

    print(
        f"{len(events)} épisodes présents "
        f"dans le calendrier."
    )

    print(
        "Vérification terminée."
    )


if __name__ == "__main__":
    main()
