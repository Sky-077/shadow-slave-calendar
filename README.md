# Shadow Slave Calendar

Calendrier iCalendar automatique pour suivre les sorties du webcomic **Shadow Slave**.

Le calendrier est généré automatiquement à partir des informations disponibles sur Aethon Webcomics.

## Fonctionnement

GitHub Actions vérifie automatiquement Aethon Webcomics toutes les 2 heures.

Le workflow :

1. récupère les informations d'Aethon Webcomics ;
2. détecte le dernier épisode ;
3. construit le calendrier prévisionnel ;
4. recherche les annonces concernant Shadow Slave ;
5. corrige les dates lorsqu'une annonce donne une date précise ;
6. génère `Shadow_Slave.ics` ;
7. publie la nouvelle version sur GitHub.

## Calendrier

Le fichier iCalendar est disponible ici :

https://raw.githubusercontent.com/Sky-077/shadow-slave-calendar/main/Shadow_Slave.ics

## Google Calendar

Pour ajouter le calendrier à Google Calendar :

1. Ouvrir Google Calendar sur ordinateur.
2. Aller dans **Autres agendas**.
3. Cliquer sur **À partir de l'URL**.
4. Coller :

https://raw.githubusercontent.com/Sky-077/shadow-slave-calendar/main/Shadow_Slave.ics

5. Cliquer sur **Ajouter un agenda**.

Le calendrier apparaîtra ensuite dans Google Calendar sur le téléphone connecté au même compte.

La synchronisation de Google Calendar n'est pas instantanée : Google récupère périodiquement les mises à jour du fichier.

## Mise à jour manuelle

Le workflow peut également être lancé manuellement depuis :

**GitHub → Actions → Shadow Slave Calendar → Run workflow**

## Fuseau horaire

Les horaires de sortie sont gérés avec :

`America/New_York`

Cela permet de prendre correctement en compte les changements d'heure été/hiver aux États-Unis.
