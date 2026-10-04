
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
    match = re.search(
        r"(?:episode|ep\.?)\s*[^0-9]{0,10}(\d+)",
        text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return None


def announcement_links(soup):
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

    return list(dict.fromkeys(results))


def parse_explicit_date(text):
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
            if len(groups[0]) == 4:
                year = int(groups[0])
                month = int(groups[1])
                day = int(groups[2])
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
    if not re.search(
        r"\bnext\s+wednesday\b",
        text,
        re.IGNORECASE,
    ):
        return None

    now = datetime.now(TZ)

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


def next_wednesday_21h():
    """
    Retourne le prochain mercredi à 21h
    dans le fuseau America/New_York.
    """

    now = datetime.now(TZ)

    days_until = (2 - now.weekday()) % 7

    # Si nous sommes déjà mercredi mais
    # que 21h est passée, on prend mercredi suivant.
    candidate = now + timedelta(
        days=days_until
    )

    candidate = candidate.replace(
        hour=21,
        minute=0,
        second=0,
        microsecond=0,
    )

    if candidate <= now:
        candidate += timedelta(days=7)

    return candidate


def build_future_events(last_episode):
    """
    Construit le planning à partir du
    prochain mercredi.

    Exemple :
    dernier épisode = E11
    prochain mercredi = E12
    puis E13, E14, etc. chaque 7 jours.
    """

    events = []

    first_episode = last_episode + 1

    first_date = next_wednesday_21h()

    for index in range(FUTURE_EPISODES):
        episode = first_episode + index

        release_date = (
            first_date
            + timedelta(days=7 * index)
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

        end = start + timedelta(hours=1)

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
    announcements = announcement_links(
        soup
    )

    for href, title in announcements:
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

        # On vérifie le contenu complet de
        # l'annonce, pas seulement son titre.
        if "shadow slave" not in combined_text.lower():
            continue

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

                print(
                    f"Date confirmée pour E{episode} : "
                    f"{release_date.strftime('%Y-%m-%d %H:%M')}"
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

    print(
        "Planning prévisionnel :"
    )

    for event in events:
        print(
            f"  E{event['episode']} -> "
            f"{event['start'].strftime('%Y-%m-%d %H:%M %Z')}"
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
