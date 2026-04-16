# Mein Projekt-Kontext für Claude

## Über mich
- Ich bin Torsten (GitHub: totocotonio)
- Ich arbeite mit verschiedenen Programmiersprachen – je nach Projekt
- Mein Hauptthema ist **Home Assistant / Smart Home**

## Schwerpunkte
- **YAML Konfiguration** – configuration.yaml, automations.yaml, scripts.yaml usw.
- **Lovelace Dashboard / UI** – Cards, Views, custom:button-card, picture-elements usw.
- **Python Scripts** – Shell Commands, Python Scripts in Home Assistant
- **Automationen** – Trigger, Conditions, Actions in HA

## Wie ich Antworten möchte
- **Immer auf Deutsch**
- **Ausführlich erklären** – ich möchte verstehen warum etwas so gemacht wird
- Schritt-für-Schritt vorgehen, nicht alles auf einmal
- Bei YAML immer den **vollständigen Code-Block** zeigen, nicht nur Ausschnitte
- Wenn es mehrere Lösungswege gibt, kurz erklären welcher der beste ist und warum

## Infrastruktur / Setup
- **Virtualisierung:** Proxmox mit Home Assistant als **LXC Container**
- **Konfigurationsdateien:** erreichbar über `Z:\` (Samba Share, IP: `192.168.178.193`)
- Direkter Dateizugriff auf HA-Config über Windows – kein SSH nötig
- Ich nutze **beide PCs** – Arbeit (michatr) und Zuhause (Torst)
- GitHub Repo für Konfiguration: https://github.com/totocotonio/claude-config

## Wichtige Hinweise
- YAML-Einrückungen immer mit **2 Leerzeichen** (kein Tab!)
- Home Assistant Version: aktuell (falls relevant bitte nachfragen)
- Konfigurationsdateien immer unter `Z:\` lesen/schreiben

## Was ich NICHT möchte
- Keine englischen Antworten
- Keinen Code ohne Erklärung
- Nicht zu viel auf einmal – lieber kleine Schritte

## Nützliche Befehle (Home Assistant)
- HA Konfiguration prüfen: `ha core check`
- HA neu starten: `ha core restart`
- Logs anzeigen: `ha core logs`
