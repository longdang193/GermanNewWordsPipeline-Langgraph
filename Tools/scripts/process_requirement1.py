#!/usr/bin/env python3
"""
Process Requirement 1: Generate enriched German vocabulary entries from word list.
"""

import re
import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class GermanVocabProcessor:
    """Process German vocabulary words and generate formatted entries."""

    MEANING_OVERRIDES = {
        "Einarbeitung": "Einarbeitung = Zeit und Prozess, in dem jemand in neue Aufgaben eingefuehrt wird / onboarding, training period",
        "fachgerecht": "fachgerecht = so ausgefuehrt, wie es technisch richtig und professionell ist / professionally, properly",
        "Genauigkeit": "Genauigkeit = Eigenschaft, sehr praezise und fehlerarm zu sein / accuracy, precision",
        "Gewährleistung": "Gewaehrleistung = gesetzliche Pflicht des Verkaeufers bei Maengeln an einer Ware / warranty, statutory guarantee",
        "Händler": "Haendler = Person oder Firma, die Waren verkauft / dealer, trader, retailer",
        "Voraussetzung": "Voraussetzung = Bedingung, die zuerst erfuellt sein muss / prerequisite, requirement",
        "Abzug": "Abzug = Betrag, der von einer Summe abgerechnet wird / deduction",
        "Aktennotiz": "Aktennotiz = kurze schriftliche Notiz fuer die Unterlagen / file note, memo",
        "Aktenstruktur": "Aktenstruktur = Ordnung und Aufbau von Dokumenten oder Akten / file structure, records structure",
        "Ausschreibung": "Ausschreibung = offizielle Einladung, Angebote fuer einen Auftrag einzureichen / tender, call for bids",
        "Ast": "Ast = Teil eines Baumes, der vom Stamm abgeht / branch, bough",
        "Bitte nehmen Sie doch Platz.": "Bitte nehmen Sie doch Platz. = hoefliche Bitte, sich zu setzen / please take a seat",
        "Damit haben wir … besprochen.": "Damit haben wir … besprochen. = damit ist alles Wichtige besprochen / with that, we have discussed everything important",
        "Der Vorteil wäre, dass …": "Der Vorteil waere, dass … = Ein Vorteil ist, dass ... / the advantage would be that ...",
        "Die meisten von + Dativ + Verb": "Die meisten von + Dativ + Verb = Ausdruck fuer 'most of ...' mit Dativ / most of ... (dative) ...",
        "Etwas mehr Marketing wäre sicher gut für uns.": "Etwas mehr Marketing waere sicher gut fuer uns. = wir braeuchten mehr Werbung / a bit more marketing would be good for us",
        "Geht man nach links, kommt man zum Bahnhof.": "Geht man nach links, kommt man zum Bahnhof. = wenn man links geht, erreicht man den Bahnhof / if you go left, you get to the station",
        "Ich finde, wir sollten das jetzt wirklich machen.": "Ich finde, wir sollten das jetzt wirklich machen. = ich denke, wir sollten das jetzt tun / I think we should really do that now",
        "Ich habe mir notiert, dass …": "Ich habe mir notiert, dass … = ich habe aufgeschrieben, dass ... / I noted down that ...",
        "Ich möchte Ihnen zuerst … vorstellen.": "Ich moechte Ihnen zuerst … vorstellen. = ich will Ihnen ... als Erstes praesentieren / I'd like to introduce ... first",
        "Kompetenz zeigen": "Kompetenz zeigen = zeigen, dass man etwas gut kann / to demonstrate competence",
        "Sieht man genauer hin, erkennt man den Unterschied.": "Sieht man genauer hin, erkennt man den Unterschied. = wenn man genauer schaut, sieht man den Unterschied / if you look more closely, you see the difference",
        "Und schließlich …": "Und schliesslich … = und am Ende / and finally ...",
        "wann sie wollen": "wann sie wollen = zu jeder Zeit, die sie moechten / whenever they want",
        "Wir haben gehört, dass …": "Wir haben gehoert, dass … = wir haben erfahren / we heard that ...",
        "Wir haben ja schon einmal darüber nachgedacht.": "Wir haben ja schon einmal darueber nachgedacht. = wir haben schon frueher daran gedacht / we already thought about that once",
        "Wir müssen etwas machen.": "Wir muessen etwas machen. = wir sollten handeln / we need to do something",
        "… die speziell für junge Leute gedacht sind": "… die speziell fuer junge Leute gedacht sind = ... intended especially for young people",
        "einen Termin vereinbaren": "einen Termin vereinbaren = einen Termin ausmachen / to arrange an appointment",
        "eine Meinung vertreten": "eine Meinung vertreten = eine Ansicht haben und begruenden / to hold and advocate an opinion",
        "etwas anbieten": "etwas anbieten = etwas zum Kauf oder zur Nutzung vorschlagen / to offer something",
        "etwas durchsprechen": "etwas durchsprechen = etwas gemeinsam genau besprechen / to discuss something thoroughly",
        "etwas machen gehen": "etwas machen gehen = hinausgehen, um etwas zu tun / to go out and do something",
        "mit etwas anfangen": "mit etwas anfangen = mit etwas beginnen; etwas nutzen koennen / to start with something; to be able to use something",
        "übrig bleiben": "uebrig bleiben = nicht verbraucht werden und noch da sein / to remain, be left over",
        "bekäme": "bekaeme = Konjunktiv-II-Form von 'bekommen' / would get, would receive",
        "bezahlbare": "bezahlbare = so guenstig, dass man es sich leisten kann / affordable",
        "Bindestrich": "Bindestrich = kurzer Strich zur Verbindung von Woertern / hyphen",
        "Brückentag": "Brueckentag = Arbeitstag zwischen Feiertag und Wochenende, den viele frei nehmen / bridge day, long-weekend day",
        "dasselbe Datum": "dasselbe Datum = genau der gleiche Kalendertag / the same date",
        "einbeziehen": "einbeziehen = jemanden oder etwas in etwas mit aufnehmen / to include, involve",
        "Erstellung": "Erstellung = das Anfertigen oder Produzieren von etwas / creation, preparation",
        "Erteilung": "Erteilung = offizielles Geben oder Ausstellen von etwas / granting, issuing",
        "Fertigstellung": "Fertigstellung = der Moment oder Prozess, in dem etwas vollendet wird / completion",
        "Grundriss": "Grundriss = zeichnerische Darstellung eines Raums oder Gebaeudes von oben / floor plan, layout",
        "Handwerker": "Handwerker = Person mit praktischem Beruf wie Schreiner, Elektriker oder Installateur / tradesperson, craftsman",
        "lockern": "lockern = weniger streng oder weniger fest machen / to loosen, relax",
        "momentan": "momentan = jetzt gerade, im Augenblick / at the moment, currently",
        "ohne Abzug": "ohne Abzug = ohne dass etwas abgerechnet oder abgezogen wird / without deduction",
        "Rennen": "Rennen = sich schnell laufend bewegen / to run",
        "termingerecht": "termingerecht = rechtzeitig zum vereinbarten Termin / on time, by the deadline",
        "unangenehme Situation": "unangenehme Situation = Lage, die peinlich, schwierig oder belastend ist / unpleasant situation",
        "Urlaubsvertretung": "Urlaubsvertretung = Person, die waehrend des Urlaubs die Aufgaben von jemandem uebernimmt / vacation replacement, stand-in",
        "vorgeht": "vorgehen = etwas auf eine bestimmte Art machen; 3. Person Singular von 'vorgehen' / proceeds, goes about it",
        "zwängen": "zwaengen = sich oder etwas mit Druck in einen engen Raum bringen / to squeeze, cram",
        "Übertrag": "Uebertrag = uebernommener Restbetrag oder uebertragene Information / carryover, transfer",
        "übrig": "uebrig = noch vorhanden, nicht verbraucht oder nicht verteilt / left over, remaining",
        "90 mal 90": "90 mal 90 = neunzig Zentimeter mal neunzig Zentimeter; eine Massangabe / 90 by 90",
        "Abläufe kennenlernen": "Ablaeufe kennenlernen = sich mit Prozessen und Arbeitsschritten vertraut machen / to learn the procedures",
        "alleine machen": "alleine machen = etwas ohne Hilfe selbst erledigen / to do something on one's own",
        "Anrufe bekommen": "Anrufe bekommen = telefonisch kontaktiert werden / to receive phone calls",
        "bei der Erstellung von + Dativ helfen": "bei der Erstellung von + Dativ helfen = beim Anfertigen oder Ausarbeiten von etwas unterstuetzen / to help with the creation of",
        "Bleibt es dabei oder passt es Ihnen später besser?": "Bleibt es dabei oder passt es Ihnen spaeter besser? = Frage, ob ein geplanter Termin so bleibt oder verschoben werden soll / shall we keep it that way or would later suit you better?",
        "den größten Bedarf sehen": "den groessten Bedarf sehen = erkennen, wo etwas am dringendsten gebraucht wird / to see the greatest need",
        "Deswegen sollte es jetzt unser Ziel sein, dass…": "Deswegen sollte es jetzt unser Ziel sein, dass... = Formulierung, mit der man ein gemeinsames Ziel benennt / therefore our goal now should be that...",
        "dürfte ich mal kurz stören?": "duerfte ich mal kurz stoeren? = hoefliche Frage, ob man kurz unterbrechen darf / may I disturb you for a moment?",
        "Erzählen Sie doch mal.": "Erzaehlen Sie doch mal. = freundliche Aufforderung, mehr zu berichten / do tell me more",
        "es freut mich": "es freut mich = Ausdruck von Freude oder Zufriedenheit / I'm glad, that pleases me",
        "es ist gut bei Stress": "es ist gut bei Stress = etwas hilft, wenn man unter Stress steht / it is helpful when you are stressed",
        "es nicht schaffen": "es nicht schaffen = etwas nicht rechtzeitig oder nicht erfolgreich erledigen koennen / not manage to do it",
        "etwas für das Protokoll notieren": "etwas fuer das Protokoll notieren = etwas schriftlich fuer das offizielle Protokoll festhalten / to note something down for the minutes",
        "extra bezahlt": "extra bezahlt = zusaetzlich und nicht im Grundpreis bezahlt / paid extra",
        "früher nach Hause gehen": "frueher nach Hause gehen = vor der ueblichen Zeit nach Hause gehen / to go home earlier",
        "Für einen/ein/eine … sollte man …": "Fuer einen/ein/eine ... sollte man ... = Redemuster fuer Empfehlungen je nach Sache oder Person / for a ..., one should ...",
        "das Gefühl haben": "das Gefuehl haben = meinen oder innerlich spuern, dass etwas so ist / to have the feeling, to feel that",
        "Geräte gehen manchmal nach … kaputt. Deshalb lohnt es sich, …": "Geraete gehen manchmal nach ... kaputt. Deshalb lohnt es sich, ... = Muster, um eine Garantie oder Vorsorge zu begruenden / devices sometimes break after ... so it is worth ...",
        "gleich alleine": "gleich alleine = sofort ohne Hilfe / immediately on your own",
        "Das habe ich wohl falsch verstanden.": "Das habe ich wohl falsch verstanden. = Satz, mit dem man ein Missverstaendnis einraeumt / I must have misunderstood that",
        "Ich finde es sinnvoll/praktisch, …, weil …": "Ich finde es sinnvoll/praktisch, ..., weil ... = Muster, um eine begruendete Meinung auszudruecken / I think it makes sense / is practical ..., because ...",
        "Ich habe Kritik von Ihnen bekommen.": "Ich habe Kritik von Ihnen bekommen. = Satz ueber erhaltene kritische Rueckmeldung / I received criticism from you",
        "Ich schließe immer/nie … ab, weil …": "Ich schliesse immer/nie ... ab, weil ... = Muster, um eine Gewohnheit mit Begruendung zu erklaeren / I always/never lock ... because ...",
        "Ich weiß oft nicht, wie es hier gemacht wird.": "Ich weiss oft nicht, wie es hier gemacht wird. = Satz ueber Unsicherheit bei Arbeitsablaeufen / I often don't know how things are done here",
        "im Moment am wichtigsten sein": "im Moment am wichtigsten sein = derzeit die hoechste Prioritaet haben / to be the most important at the moment",
        "Ist es sinnvoll, eine Garantieverlängerung zu kaufen? Für welche Geräte? Diskutieren Sie.": "Ist es sinnvoll, eine Garantieverlaengerung zu kaufen? Fuer welche Geraete? Diskutieren Sie. = Diskussionsfrage ueber Nutzen von Zusatzgarantien / is it worth buying an extended warranty? For which devices? Discuss.",
        "Das ist schwierig für mich.": "Das ist schwierig fuer mich. = einfache Aussage, dass etwas persoenlich schwerfaellt / that is difficult for me",
        "Kritik bekommen": "Kritik bekommen = rueckmeldende Beanstandungen hoeren / to receive criticism",
        "eine Lösung finden": "eine Loesung finden = ein Problem erfolgreich loesen / to find a solution",
        "Meiner Meinung nach ist es nötig, … zu …, denn …": "Meiner Meinung nach ist es noetig, ... zu ..., denn ... = Muster, um eine begruendete Notwendigkeit auszudruecken / in my opinion it is necessary to ..., because ...",
        "nicht so genaue Regeln": "nicht so genaue Regeln = weniger strenge oder weniger detaillierte Vorschriften / less strict rules",
        "Priorität haben": "Prioritaet haben = wichtiger sein als anderes / to have priority",
        "Protokoll führen": "Protokoll fuehren = wichtige Punkte einer Sitzung schriftlich festhalten / to keep minutes",
        "Rechnungen prüfen": "Rechnungen pruefen = Rechnungen kontrollieren und auf Richtigkeit ueberpruefen / to check invoices",
        "schnell reagieren": "schnell reagieren = ohne lange Verzoegerung antworten oder handeln / to react quickly",
        "Schön, dass Sie da sind.": "Schoen, dass Sie da sind. = freundliche Begruessung bei einer Ankunft / nice to have you here",
        "sehr viel Arbeit machen": "sehr viel Arbeit machen = einen hohen Arbeitsaufwand verursachen / to create a lot of work",
        "selbstständig erledigen": "selbststaendig erledigen = eine Aufgabe ohne Hilfe fertig machen / to complete independently",
        "sich in Verbindung setzen": "sich in Verbindung setzen = Kontakt zu jemandem aufnehmen / to get in touch",
        "Sie/Er hat mich kritisiert.": "Sie/Er hat mich kritisiert. = Satz ueber direkte kritische Rueckmeldung / she/he criticized me",
        "um Unterstützung bitten": "um Unterstuetzung bitten = Hilfe oder Beistand erfragen / to ask for support",
        "Unterstützung bekommen": "Unterstuetzung bekommen = Hilfe oder Rueckhalt erhalten / to receive support",
        "Urlaub nehmen": "Urlaub nehmen = freie Tage von der Arbeit beanspruchen / to take vacation",
        "Urlaubsantrag ausfüllen": "Urlaubsantrag ausfuellen = das Formular fuer beantragten Urlaub ausfuellen / to fill out a vacation request",
        "Verantwortung geben": "Verantwortung geben = jemandem eine zustaendige Aufgabe uebertragen / to give responsibility",
        "Wenn ich besser wüsste, … könnte ich …": "Wenn ich besser wuesste, ... koennte ich ... = Muster fuer eine hypothetische Moeglichkeit bei mehr Wissen / if I knew better ..., I could ...",
        "wöchentlich berichten": "woechentlich berichten = jede Woche Informationen weitergeben / to report weekly",
        "zu tun haben": "zu tun haben = beschaeftigt sein oder mit etwas in Verbindung stehen / to be busy, to have to do with",
        "Überstunden machen": "Ueberstunden machen = laenger als die regulaere Arbeitszeit arbeiten / to work overtime",
    }

    ENTRY_OVERRIDES = {
        "Ablage": {
            "tags": "noun",
            "meaning": "Ablage = Ort oder System, wo Unterlagen geordnet abgelegt werden / filing system, tray",
            "de_1": "Die Rechnung liegt schon in der Ablage für offene Vorgänge.",
            "en_1": "The invoice is already in the tray for open tasks.",
            "word_inf": "die Ablage",
            "noun_gender": "die",
            "noun_genetiv": "der Ablage",
            "noun_plural": "Ablagen",
            "noun_forms": "-, -n",
        },
        "Ast": {
            "tags": "noun",
            "meaning": "Ast = Teil eines Baumes, der vom Stamm abgeht / branch, bough",
            "de_1": "Der Ast ist nach dem Sturm auf den Weg gefallen.",
            "en_1": "The branch fell onto the path after the storm.",
            "word_inf": "der Ast",
            "noun_gender": "der",
            "noun_genetiv": "des Astes",
            "noun_plural": "Aeste",
            "noun_forms": "-es, -e",
        },
        "bevorzugen": {
            "tags": "verb",
            "meaning": "bevorzugen = etwas lieber haben als etwas anderes / to prefer",
            "de_1": "Ich bevorzuge Tee statt Kaffee.",
            "en_1": "I prefer tea over coffee.",
            "word_inf": "bevorzugen",
            "verb_present": "bevorzugt",
            "verb_past": "bevorzugte",
            "verb_perfect": "hat bevorzugt",
        },
        "fangen": {
            "tags": "verb",
            "meaning": "fangen = etwas oder jemanden mit der Hand greifen / to catch",
            "de_1": "Der Hund fängt den Ball.",
            "en_1": "The dog catches the ball.",
            "word_inf": "fangen",
            "verb_present": "fängt",
            "verb_past": "fing",
            "verb_perfect": "hat gefangen",
        },
        "kehren": {
            "tags": "verb",
            "meaning": "kehren = mit einem Besen sauber machen / to sweep",
            "de_1": "Ich kehre den Flur schnell, bevor Besuch kommt.",
            "en_1": "I quickly sweep the hallway before visitors arrive.",
            "word_inf": "kehren",
            "verb_present": "kehrt",
            "verb_past": "kehrte",
            "verb_perfect": "hat gekehrt",
        },
        "reißen": {
            "tags": "verb",
            "meaning": "reißen = so stark ziehen, dass etwas kaputtgeht / to tear, rip",
            "de_1": "Das Papier reißt leicht, wenn es nass ist.",
            "en_1": "The paper tears easily when it is wet.",
            "word_inf": "reißen",
            "verb_present": "reißt",
            "verb_past": "riss",
            "verb_perfect": "hat gerissen",
        },
        "Freizeitprogramm": {
            "tags": "noun",
            "meaning": "Freizeitprogramm = Angebot an Aktivitaeten fuer die freie Zeit / leisure program, activities schedule",
            "de_1": "Im Hotel gibt es ein Freizeitprogramm fuer Kinder und Erwachsene.",
            "en_1": "The hotel has a leisure program for children and adults.",
            "word_inf": "das Freizeitprogramm",
            "noun_gender": "das",
            "noun_genetiv": "des Freizeitprogramms",
            "noun_plural": "Freizeitprogramme",
            "noun_forms": "-s, -e",
        },
        "Kommunikationsstil": {
            "tags": "noun",
            "meaning": "Kommunikationsstil = Art und Weise, wie jemand spricht und kommuniziert / communication style",
            "de_1": "Sein Kommunikationsstil ist direkt, aber respektvoll.",
            "en_1": "His communication style is direct but respectful.",
            "word_inf": "der Kommunikationsstil",
            "noun_gender": "der",
            "noun_genetiv": "des Kommunikationsstils",
            "noun_plural": "Kommunikationsstile",
            "noun_forms": "-s, -e",
        },
        "Kreuzfahrten": {
            "tags": "noun",
            "meaning": "Kreuzfahrten = Reisen mit einem Kreuzfahrtschiff / cruises",
            "de_1": "Viele Leute machen im Sommer Kreuzfahrten im Mittelmeer.",
            "en_1": "Many people take cruises in the Mediterranean in summer.",
            "word_inf": "die Kreuzfahrt",
            "noun_gender": "die (plural)",
            "noun_genetiv": "-",
            "noun_plural": "Kreuzfahrten",
            "noun_forms": "-",
        },
        "Oktopus": {
            "tags": "noun",
            "meaning": "Oktopus = Meerestier mit acht Armen / octopus",
            "de_1": "Im Aquarium habe ich einen Oktopus gesehen.",
            "en_1": "I saw an octopus at the aquarium.",
            "word_inf": "der Oktopus",
            "noun_gender": "der",
            "noun_genetiv": "des Oktopus",
            "noun_plural": "Oktopusse",
            "noun_forms": "-, -se",
        },
        "Rückmeldungen": {
            "tags": "noun",
            "meaning": "Rueckmeldungen = Antworten oder Feedback zu etwas / feedback, responses",
            "de_1": "Wir brauchen Rueckmeldungen von den Kunden, um besser zu werden.",
            "en_1": "We need feedback from customers to improve.",
            "word_inf": "die Rueckmeldung",
            "noun_gender": "die (plural)",
            "noun_genetiv": "-",
            "noun_plural": "Rückmeldungen",
            "noun_forms": "-",
        },
        "Schwerpunkt": {
            "tags": "noun",
            "meaning": "Schwerpunkt = wichtigster Teil oder Fokus / focus, main emphasis",
            "de_1": "Der Schwerpunkt des Treffens liegt heute auf dem Budget.",
            "en_1": "Today the meeting's focus is on the budget.",
            "word_inf": "der Schwerpunkt",
            "noun_gender": "der",
            "noun_genetiv": "des Schwerpunkts",
            "noun_plural": "Schwerpunkte",
            "noun_forms": "-s, -e",
        },
        "Spinnen": {
            "tags": "noun",
            "meaning": "Spinnen = Tiere mit acht Beinen / spiders",
            "de_1": "Spinnen sind fuer viele Menschen unangenehm, aber sie sind nuetzlich.",
            "en_1": "Spiders are unpleasant for many people, but they are useful.",
            "word_inf": "die Spinne",
            "noun_gender": "die (plural)",
            "noun_genetiv": "-",
            "noun_plural": "Spinnen",
            "noun_forms": "-",
        },
        "Zimtschnecken": {
            "tags": "noun",
            "meaning": "Zimtschnecken = suesses Hefegebaeck mit Zimt / cinnamon rolls",
            "de_1": "Zum Fruehstueck backen wir manchmal Zimtschnecken.",
            "en_1": "Sometimes we bake cinnamon rolls for breakfast.",
            "word_inf": "die Zimtschnecke",
            "noun_gender": "die (plural)",
            "noun_genetiv": "-",
            "noun_plural": "Zimtschnecken",
            "noun_forms": "-",
        },
        "ausführliche": {
            "tags": "adj",
            "meaning": "ausfuehrliche = sehr genau und mit vielen Details / detailed, comprehensive",
            "de_1": "Wir brauchen eine ausfuehrliche Erklaerung fuer den neuen Ablauf.",
            "en_1": "We need a detailed explanation for the new process.",
            "word_inf": "ausfuehrlich",
        },
        "bedeutend": {
            "tags": "adj",
            "meaning": "bedeutend = sehr wichtig oder von grosser Wirkung / significant, important",
            "de_1": "Der Fortschritt in diesem Projekt ist fuer uns sehr bedeutend.",
            "en_1": "The progress in this project is very significant for us.",
            "word_inf": "bedeutend",
        },
        "Befragten": {
            "tags": "noun",
            "meaning": "Befragte = Person, die an einer Umfrage teilnimmt / respondent",
            "de_1": "Die Befragten gaben unterschiedliche Antworten auf die Frage.",
            "en_1": "The respondents gave different answers to the question.",
            "word_inf": "die Befragten",
            "noun_gender": "die (plural)",
            "noun_genetiv": "-",
            "noun_plural": "Befragten",
            "noun_forms": "-",
        },
        "diejenigen": {
            "tags": "pronoun",
            "meaning": "diejenigen = genau die genannten Personen oder Dinge / those (specific ones)",
            "de_1": "Diejenigen, die zu spaet kommen, muessen draussen warten.",
            "en_1": "Those who arrive late have to wait outside.",
            "word_inf": "diejenigen",
        },
        "bevorzugt": {
            "tags": "adj",
            "meaning": "bevorzugt = lieber gewaehlt als andere Moeglichkeiten / preferred",
            "de_1": "Dieses Modell wird wegen des niedrigeren Preises bevorzugt.",
            "en_1": "This model is preferred because of the lower price.",
            "word_inf": "bevorzugt",
        },
        "ergab": {
            "tags": "verb",
            "meaning": "ergeben = als Ergebnis zeigen / to result in, to show",
            "de_1": "Die Auswertung ergab ein klares Bild der Situation.",
            "en_1": "The evaluation showed a clear picture of the situation.",
            "word_inf": "ergeben",
            "verb_present": "ergibt",
            "verb_past": "ergab",
            "verb_perfect": "hat ergeben",
        },
        "Fliese": {
            "tags": "noun",
            "meaning": "Fliese = flache Platte fuer Wand oder Boden / tile",
            "de_1": "Eine Fliese in der Kueche ist gestern gebrochen.",
            "en_1": "A tile in the kitchen broke yesterday.",
            "word_inf": "die Fliese",
            "noun_gender": "die",
            "noun_genetiv": "der Fliese",
            "noun_plural": "Fliesen",
            "noun_forms": "-, -n",
        },
        "Katzenschau": {
            "tags": "noun",
            "meaning": "Katzenschau = Ausstellung oder Wettbewerb fuer Katzen / cat show",
            "de_1": "Auf der Katzenschau sind viele Rassen zu sehen.",
            "en_1": "Many breeds are on display at the cat show.",
            "word_inf": "die Katzenschau",
            "noun_gender": "die",
            "noun_genetiv": "der Katzenschau",
            "noun_plural": "Katzenschauen",
            "noun_forms": "-, -en",
        },
        "haltbar": {
            "tags": "adj",
            "meaning": "haltbar = lange nutzbar, nicht schnell kaputt / durable, long-lasting",
            "de_1": "Diese Tasche ist robust und sehr haltbar.",
            "en_1": "This bag is sturdy and very durable.",
            "word_inf": "haltbar",
        },
        "handeln": {
            "tags": "verb",
            "meaning": "handeln = etwas tun oder in einer Lage reagieren / to act",
            "de_1": "In so einer Situation muss man ruhig handeln.",
            "en_1": "In such a situation, you have to act calmly.",
            "word_inf": "handeln",
            "verb_present": "handelt",
            "verb_past": "handelte",
            "verb_perfect": "hat gehandelt",
        },
        "langfristig": {
            "tags": "adv",
            "meaning": "langfristig = ueber einen laengeren Zeitraum / in the long term",
            "de_1": "Langfristig sparen wir mit dieser Loesung viel Geld.",
            "en_1": "In the long term, we save a lot of money with this solution.",
            "word_inf": "langfristig",
        },
        "nachhaltig": {
            "tags": "adj",
            "meaning": "nachhaltig = umweltfreundlich und auf Dauer wirksam / sustainable",
            "de_1": "Wir suchen nach einer nachhaltigeren Verpackung.",
            "en_1": "We are looking for more sustainable packaging.",
            "word_inf": "nachhaltig",
        },
        "Rangliste": {
            "tags": "noun",
            "meaning": "Rangliste = geordnete Liste nach Platz oder Leistung / ranking list",
            "de_1": "Unser Team steht auf Platz zwei der Rangliste.",
            "en_1": "Our team is in second place in the ranking list.",
            "word_inf": "die Rangliste",
            "noun_gender": "die",
            "noun_genetiv": "der Rangliste",
            "noun_plural": "Ranglisten",
            "noun_forms": "-, -n",
        },
        "recherchiert": {
            "tags": "verb",
            "meaning": "recherchieren = Informationen gezielt suchen und pruefen / to research",
            "de_1": "Sie hat das Thema gruendlich recherchiert.",
            "en_1": "She researched the topic thoroughly.",
            "word_inf": "recherchieren",
            "verb_present": "recherchiert",
            "verb_past": "recherchierte",
            "verb_perfect": "hat recherchiert",
        },
        "Reihenfolge": {
            "tags": "noun",
            "meaning": "Reihenfolge = feste Ordnung von mehreren Schritten / sequence, order",
            "de_1": "Bitte erklaeren Sie die Reihenfolge der einzelnen Schritte.",
            "en_1": "Please explain the order of the individual steps.",
            "word_inf": "die Reihenfolge",
            "noun_gender": "die",
            "noun_genetiv": "der Reihenfolge",
            "noun_plural": "Reihenfolgen",
            "noun_forms": "-, -n",
        },
        "roh": {
            "tags": "adj",
            "meaning": "roh = ungekocht oder unbehandelt / raw",
            "de_1": "Das Gemuese wird hier oft roh gegessen.",
            "en_1": "The vegetables are often eaten raw here.",
            "word_inf": "roh",
        },
        "der späteste": {
            "tags": "adj",
            "meaning": "spaeteste = zeitlich am weitesten hinten / latest",
            "de_1": "Der spaeteste Termin ist am Freitag um 18 Uhr.",
            "en_1": "The latest appointment is on Friday at 6 p.m.",
            "word_inf": "spaet",
        },
        "streichen": {
            "tags": "verb",
            "meaning": "streichen = etwas absagen oder entfernen / to cancel, to strike out",
            "de_1": "Wegen des Wetters mussten wir den Termin streichen.",
            "en_1": "Because of the weather, we had to cancel the appointment.",
            "word_inf": "streichen",
            "verb_present": "streicht",
            "verb_past": "strich",
            "verb_perfect": "hat gestrichen",
        },
        "verkleiden": {
            "tags": "verb",
            "meaning": "verkleiden = sich mit anderer Kleidung als Figur zeigen / to dress up, disguise",
            "de_1": "Die Kinder verkleiden sich zum Fest als Piraten.",
            "en_1": "The children dress up as pirates for the celebration.",
            "word_inf": "verkleiden",
            "verb_present": "verkleidet",
            "verb_past": "verkleidete",
            "verb_perfect": "hat verkleidet",
        },
        "zugänglich": {
            "tags": "adj",
            "meaning": "zugaenglich = leicht erreichbar oder leicht verstaendlich / accessible",
            "de_1": "Die Informationen sind fuer alle Nutzer zugaenglich.",
            "en_1": "The information is accessible to all users.",
            "word_inf": "zugaenglich",
        },
        "Überblick": {
            "tags": "noun",
            "meaning": "Ueberblick = kurze, klare Gesamtsicht ueber ein Thema / overview",
            "de_1": "Am Anfang gab der Lehrer einen guten Ueberblick.",
            "en_1": "At the beginning, the teacher gave a good overview.",
            "word_inf": "der Ueberblick",
            "noun_gender": "der",
            "noun_genetiv": "des Ueberblicks",
            "noun_plural": "Ueberblicke",
            "noun_forms": "-s, -e",
        },
        "mindern": {
            "tags": "verb",
            "meaning": "mindern = weniger machen oder verringern / to reduce, lessen",
            "de_1": "Neue Regeln sollen das Risiko deutlich mindern.",
            "en_1": "New rules are meant to significantly reduce the risk.",
            "word_inf": "mindern",
            "verb_present": "mindert",
            "verb_past": "minderte",
            "verb_perfect": "hat gemindert",
        },
        "Spülbecken": {
            "tags": "noun",
            "meaning": "Spuelbecken = Becken in der Kueche zum Waschen / sink",
            "de_1": "Im Spuelbecken steht noch schmutziges Geschirr.",
            "en_1": "There are still dirty dishes in the sink.",
            "word_inf": "das Spuelbecken",
            "noun_gender": "das",
            "noun_genetiv": "des Spuelbeckens",
            "noun_plural": "Spuelbecken",
            "noun_forms": "-s, -",
        },
        "Vergabe": {
            "tags": "noun",
            "meaning": "Vergabe = Zuteilung oder offizielles Erteilen von Aufgaben, Rechten oder Aufträgen / assignment, awarding",
            "de_1": "Die Vergabe der Aufgaben erfolgt morgen im Teammeeting.",
            "en_1": "The assignment of tasks will take place tomorrow in the team meeting.",
            "word_inf": "die Vergabe",
            "noun_gender": "die",
            "noun_genetiv": "der Vergabe",
            "noun_plural": "Vergaben",
            "noun_forms": "-, -n",
        },
        "Vorgehensweise": {
            "tags": "noun",
            "meaning": "Vorgehensweise = Art, wie man bei einer Aufgabe Schritt für Schritt vorgeht / approach, procedure",
            "de_1": "Diese Vorgehensweise spart uns bei der Prüfung viel Zeit.",
            "en_1": "This approach saves us a lot of time during the review.",
            "word_inf": "die Vorgehensweise",
            "noun_gender": "die",
            "noun_genetiv": "der Vorgehensweise",
            "noun_plural": "Vorgehensweisen",
            "noun_forms": "-, -n",
        },
        "Nachdem ich gegessen hatte, bin ich schlafen gegangen.": {
            "tags": "phrase",
            "meaning": "Nachdem ... = beschreibt eine Handlung, die vor einer anderen passiert ist / after ... had ...",
            "de_1": "Nachdem ich gegessen hatte, bin ich schlafen gegangen.",
            "en_1": "After I had eaten, I went to sleep.",
            "word_inf": "Nachdem ich gegessen hatte, bin ich schlafen gegangen.",
        },
        "Nachdem ich aufgestanden war, habe ich Kaffee gemacht.": {
            "tags": "phrase",
            "meaning": "Nachdem ... = Satzmuster fuer zeitliche Reihenfolge in der Vergangenheit / after ... had ...",
            "de_1": "Nachdem ich aufgestanden war, habe ich Kaffee gemacht.",
            "en_1": "After I had gotten up, I made coffee.",
            "word_inf": "Nachdem ich aufgestanden war, habe ich Kaffee gemacht.",
        },
        "Nachdem ich lange darüber nachgedacht hatte, habe ich mich entschieden.": {
            "tags": "phrase",
            "meaning": "Nachdem ... = zeigt eine fruehere Vorbedingung fuer eine Entscheidung / after ... had ...",
            "de_1": "Nachdem ich lange darueber nachgedacht hatte, habe ich mich entschieden.",
            "en_1": "After I had thought about it for a long time, I made my decision.",
            "word_inf": "Nachdem ich lange darueber nachgedacht hatte, habe ich mich entschieden.",
        },
        "Nachdem ich den Bericht geschrieben hatte, habe ich ihn abgeschickt.": {
            "tags": "phrase",
            "meaning": "Nachdem ... = drueckt Vorzeitigkeit in einer Abfolge aus / after ... had ...",
            "de_1": "Nachdem ich den Bericht geschrieben hatte, habe ich ihn abgeschickt.",
            "en_1": "After I had written the report, I sent it.",
            "word_inf": "Nachdem ich den Bericht geschrieben hatte, habe ich ihn abgeschickt.",
        },
        "Kirchgang": {
            "tags": "noun",
            "meaning": "Kirchgang = der Besuch eines Gottesdienstes in der Kirche / going to church, church service",
            "de_1": "Der sonntägliche Kirchgang ist für meine Familie eine wichtige Tradition.",
            "en_1": "Going to church on Sunday is an important tradition for my family.",
            "word_inf": "der Kirchgang",
            "noun_gender": "der",
            "noun_genetiv": "des Kirchgangs",
            "noun_plural": "Kirchgänge",
            "noun_forms": "-s, ⸚e",
        },
        "Angelegenheit": {
            "tags": "noun",
            "meaning": "Angelegenheit = Thema, Problem oder Aufgabe, um die man sich kuemmern muss / matter, issue, affair",
            "de_1": "Diese private Angelegenheit moechte ich nicht im Buero besprechen.",
            "en_1": "I don't want to discuss this private matter in the office.",
            "word_inf": "die Angelegenheit",
            "noun_gender": "die",
            "noun_genetiv": "der Angelegenheit",
            "noun_plural": "Angelegenheiten",
            "noun_forms": "-, -n",
        },
        "Abläufe": {
            "tags": "noun",
            "meaning": "Ablauf = geordnete Folge von Schritten oder Ereignissen / process, sequence, procedure",
            "de_1": "Die neuen Ablaeufe im Team sind jetzt klar dokumentiert.",
            "en_1": "The new processes in the team are now clearly documented.",
            "word_inf": "der Ablauf",
            "noun_gender": "der",
            "noun_genetiv": "des Ablaufs",
            "noun_plural": "Abläufe",
            "noun_forms": "-s, ⸚e",
        },
        "Bauherren": {
            "tags": "noun",
            "meaning": "Bauherr = Person oder Firma, die einen Bau in Auftrag gibt / builder, client, property developer",
            "de_1": "Die Bauherren wollen den neuen Plan noch einmal genau pruefen.",
            "en_1": "The clients want to review the new plan once again carefully.",
            "word_inf": "der Bauherr",
            "noun_gender": "der",
            "noun_genetiv": "des Bauherrn",
            "noun_plural": "Bauherren",
            "noun_forms": "-n, -en",
        },
        "aufkommen": {
            "tags": "verb",
            "meaning": "aufkommen = entstehen oder ploetzlich in Erscheinung treten / to arise, come up",
            "de_1": "Waehrend des Meetings sind einige neue Fragen aufgekommen.",
            "en_1": "Some new questions came up during the meeting.",
            "word_inf": "aufkommen",
            "verb_present": "kommt auf",
            "verb_past": "kam auf",
            "verb_perfect": "ist aufgekommen",
        },
        "Bratäpfeln": {
            "tags": "noun",
            "meaning": "Bratapfel = gebackener Apfel, oft mit einer suessen Fuellung / baked apple",
            "de_1": "Im Winter essen wir oft heisse Brataepfel mit Vanillesosse.",
            "en_1": "In winter, we often eat hot baked apples with vanilla sauce.",
            "word_inf": "der Bratapfel",
            "noun_gender": "der",
            "noun_genetiv": "des Bratapfels",
            "noun_plural": "Bratäpfel",
            "noun_forms": "-s, ⸚",
        },
        "Bronchitis": {
            "tags": "noun",
            "meaning": "Bronchitis = Entzuendung der Bronchien mit Husten und Atemproblemen / bronchitis",
            "de_1": "Wegen einer Bronchitis musste sie die ganze Woche zu Hause bleiben.",
            "en_1": "Because of bronchitis, she had to stay home all week.",
            "word_inf": "die Bronchitis",
            "noun_gender": "die",
            "noun_genetiv": "der Bronchitis",
            "noun_plural": "-",
            "noun_forms": "-, -",
        },
        "Börse": {
            "tags": "noun",
            "meaning": "Boerse = Markt fuer Aktien oder ein organisierter Handelsplatz / stock exchange, market",
            "de_1": "Die Boerse reagierte nervoes auf die neuen Wirtschaftsdaten.",
            "en_1": "The stock exchange reacted nervously to the new economic data.",
            "word_inf": "die Börse",
            "noun_gender": "die",
            "noun_genetiv": "der Börse",
            "noun_plural": "Börsen",
            "noun_forms": "-, -n",
        },
        "Christmette": {
            "tags": "noun",
            "meaning": "Christmette = Mitternachtsmesse in der katholischen Kirche an Heiligabend / Midnight Mass",
            "de_1": "Nach dem Essen gehen meine Grosseltern immer in die Christmette.",
            "en_1": "After dinner, my grandparents always go to Midnight Mass.",
            "word_inf": "die Christmette",
            "noun_gender": "die",
            "noun_genetiv": "der Christmette",
            "noun_plural": "Christmetten",
            "noun_forms": "-, -n",
        },
        "diejenigen": {
            "tags": "pronoun",
            "meaning": "diejenigen = genau die genannten Personen oder Dinge / those (specific ones)",
            "de_1": "Diejenigen, die zu spaet kommen, muessen draussen warten.",
            "en_1": "Those who arrive late have to wait outside.",
            "word_inf": "diejenigen",
        },
        "Eisen": {
            "tags": "noun",
            "meaning": "Eisen = hartes Metall für Werkzeuge / iron",
            "de_1": "Dieses Werkzeug ist aus massivem Eisen gemacht.",
            "en_1": "This tool is made of solid iron.",
            "word_inf": "das Eisen",
            "noun_gender": "das",
            "noun_genetiv": "des Eisens",
            "noun_plural": "-",
            "noun_forms": "-s, -",
        },
        "festgestellt": {
            "tags": "verb",
            "meaning": "feststellen = etwas erkennen, bemerken oder bestaetigen / to note, find, establish",
            "de_1": "Der Arzt hat festgestellt, dass ich voellig gesund bin.",
            "en_1": "The doctor has confirmed that I am completely healthy.",
            "word_inf": "feststellen",
            "verb_present": "stellt fest",
            "verb_past": "stellte fest",
            "verb_perfect": "hat festgestellt",
        },
        "Festtagsbraten": {
            "tags": "noun",
            "meaning": "Festtagsbraten = spezielles Fleischgericht fuer einen Feiertag / holiday roast",
            "de_1": "Der Festtagsbraten braucht drei Stunden im Ofen.",
            "en_1": "The holiday roast needs three hours in the oven.",
            "word_inf": "der Festtagsbraten",
            "noun_gender": "der",
            "noun_genetiv": "des Festtagsbratens",
            "noun_plural": "Festtagsbraten",
            "noun_forms": "-s, -",
        },
        "Großbritannien": {
            "tags": "noun",
            "meaning": "Grossbritannien = Inselstaat im Nordwesten Europas / Great Britain",
            "de_1": "London ist die Hauptstadt von Grossbritannien.",
            "en_1": "London is the capital of Great Britain.",
            "word_inf": "Großbritannien",
            "noun_gender": "das",
            "noun_genetiv": "Großbritanniens",
            "noun_plural": "-",
            "noun_forms": "-s, -",
        },
        "hergekommen": {
            "tags": "verb",
            "meaning": "herkommen = an den Ort kommen, wo der Sprecher ist / to come here",
            "de_1": "Ich weiss nicht, wie dieses kaputte Fahrrad hergekommen ist.",
            "en_1": "I don't know how this broken bicycle got here.",
            "word_inf": "herkommen",
            "verb_present": "kommt her",
            "verb_past": "kam her",
            "verb_perfect": "ist hergekommen",
        },
        "Katzenschau": {
            "tags": "noun",
            "meaning": "Katzenschau = Ausstellung, bei der Rassekatzen praesentiert und bewertet werden / cat show",
            "de_1": "Auf der Katzenschau am Wochenende wurden viele schoene Rassekatzen gezeigt.",
            "en_1": "Many beautiful purebred cats were shown at the cat show this weekend.",
            "word_inf": "die Katzenschau",
            "noun_gender": "die",
            "noun_genetiv": "der Katzenschau",
            "noun_plural": "Katzenschauen",
            "noun_forms": "-, -en",
        },
        "Nikoläuse": {
            "tags": "noun",
            "meaning": "Nikolaus = Figur, die am 6. Dezember Geschenke bringt; Nikolausfigur aus Schokolade / St. Nicholas, chocolate Santa",
            "de_1": "Anfang November gibt es in den Supermaerkten schon Schokoladen-Nikolaeuse.",
            "en_1": "As early as November, there are already chocolate Santas in the supermarkets.",
            "word_inf": "der Nikolaus",
            "noun_gender": "der",
            "noun_genetiv": "des Nikolauses",
            "noun_plural": "Nikoläuse",
            "noun_forms": "-es, ⸚e",
        },
        "Norwegen": {
            "tags": "noun",
            "meaning": "Norwegen = Ein skandinavisches Land im Norden Europas / Norway",
            "de_1": "Urlaub in Norwegen ist wunderschoen, aber auch sehr teuer.",
            "en_1": "Vacationing in Norway is beautiful, but also very expensive.",
            "word_inf": "Norwegen",
            "noun_gender": "das",
            "noun_genetiv": "Norwegens",
            "noun_plural": "-",
            "noun_forms": "-s, -",
        },
        "Plastiktanne": {
            "tags": "noun",
            "meaning": "Plastiktanne = Kuenstlicher Weihnachtsbaum aus Kunststoff / artificial fir tree",
            "de_1": "Wir haben uns eine Plastiktanne gekauft, weil sie nicht nadelt.",
            "en_1": "We bought an artificial tree because it doesn't shed needles.",
            "word_inf": "die Plastiktanne",
            "noun_gender": "die",
            "noun_genetiv": "der Plastiktanne",
            "noun_plural": "Plastiktannen",
            "noun_forms": "-, -n",
        },
        "Plätzchen": {
            "tags": "noun",
            "meaning": "Plaetzchen = suesses Kleingebaeck, oft zu Weihnachten / cookies, biscuits",
            "de_1": "An den Adventstagen backen wir gerne gemeinsam Plaetzchen.",
            "en_1": "On Advent days we like to bake cookies together.",
            "word_inf": "das Plätzchen",
            "noun_gender": "das",
            "noun_genetiv": "des Plätzchens",
            "noun_plural": "Plätzchen",
            "noun_forms": "-s, -",
        },
        "Skibörse": {
            "tags": "noun",
            "meaning": "Skiboerse = Markt oder Veranstaltung zum Kauf und Verkauf von gebrauchten Skiern / ski exchange, ski market",
            "de_1": "Ich habe diese guenstigen Skier am Wochenende auf der Skiboerse gefunden.",
            "en_1": "I found these cheap skis at the ski exchange over the weekend.",
            "word_inf": "die Skibörse",
            "noun_gender": "die",
            "noun_genetiv": "der Skibörse",
            "noun_plural": "Skibörsen",
            "noun_forms": "-, -n",
        },
        "Stollen": {
            "tags": "noun",
            "meaning": "Stollen = traditionelles, suestes Brotgebäck (meist zu Weihnachten) / stollen, traditional fruitcake",
            "de_1": "Der Dresdner Stollen mit Rosinen ist weltberuehmt.",
            "en_1": "The Dresden stollen with raisins is world famous.",
            "word_inf": "der Stollen",
            "noun_gender": "der",
            "noun_genetiv": "des Stollens",
            "noun_plural": "Stollen",
            "noun_forms": "-s, -",
        },
        "Tannenbaum": {
            "tags": "noun",
            "meaning": "Tannenbaum = Nadelbaum, der als Weihnachtsbaum geschmueckt wird / fir tree, Christmas tree",
            "de_1": "Den Tannenbaum schmuecken wir immer erst am Morgen des 24. Dezember.",
            "en_1": "We always decorate the Christmas tree on the morning of December 24th.",
            "word_inf": "der Tannenbaum",
            "noun_gender": "der",
            "noun_genetiv": "des Tannenbaumes",
            "noun_plural": "Tannenbäume",
            "noun_forms": "-es, ⸚e",
        },
        "Tierliebhaber": {
            "tags": "noun",
            "meaning": "Tierliebhaber = Person, die Tiere sehr mag und sich um sie kuemmert / animal lover",
            "de_1": "Als Tierliebhaber spendet er jeden Monat an das oertliche Tierheim.",
            "en_1": "As an animal lover, he donates to the local animal shelter every month.",
            "word_inf": "der Tierliebhaber",
            "noun_gender": "der",
            "noun_genetiv": "des Tierliebhabers",
            "noun_plural": "Tierliebhaber",
            "noun_forms": "-s, -",
        },
        "unbeschreiblich": {
            "tags": "adj",
            "meaning": "unbeschreiblich = so schoen, so stark oder so besonders, dass man es nicht in Worte fassen kann / indescribable",
            "de_1": "Die Aussicht oben vom Berg war einfach unbeschreiblich schoen.",
            "en_1": "The view from the top of the mountain was simply indescribably beautiful.",
            "word_inf": "unbeschreiblich",
        },
        "vermitteln": {
            "tags": "verb",
            "meaning": "vermitteln = einen Kontakt herstellen, einen Kompromiss finden oder etwas beibringen / to convey, mediate, arrange",
            "de_1": "Die Lehrerin moechte den Schuelern Freude am Lesen vermitteln.",
            "en_1": "The teacher wants to convey the joy of reading to the students.",
            "word_inf": "vermitteln",
            "verb_present": "vermittelt",
            "verb_past": "vermittelte",
            "verb_perfect": "hat vermittelt",
        },
        "Vorführung": {
            "tags": "noun",
            "meaning": "Vorführung = Praesentation eines Films, Theaterstuecks oder einer Technik / performance, presentation, showing",
            "de_1": "Die heutige Vorfuehrung des Films beginnt um zwanzig Uhr.",
            "en_1": "Today's showing of the film starts at 8 PM.",
            "word_inf": "die Vorführung",
            "noun_gender": "die",
            "noun_genetiv": "der Vorführung",
            "noun_plural": "Vorführungen",
            "noun_forms": "-, -en",
        },
        "Vorzug": {
            "tags": "noun",
            "meaning": "Vorzug = wertvolle Eigenschaft oder Prioritaet, bei der man etwas einem anderen vorzieht / advantage, preference, merit",
            "de_1": "Dieser Tarif hat den Vorzug, dass man jederzeit kuendigen kann.",
            "en_1": "This plan has the advantage that you can cancel at any time.",
            "word_inf": "der Vorzug",
            "noun_gender": "der",
            "noun_genetiv": "des Vorzuges",
            "noun_plural": "Vorzüge",
            "noun_forms": "-es, ⸚e",
        },
        "Weihnachtsgefühl": {
            "tags": "noun",
            "meaning": "Weihnachtsgefuehl = festliche, besinnliche Stimmung rund um die Feiertage / Christmas spirit, holiday feeling",
            "de_1": "Wenn es draussen schneit, kommt bei mir richtiges Weihnachtsgefuehl auf.",
            "en_1": "When it snows outside, I get a real Christmas feeling.",
            "word_inf": "das Weihnachtsgefühl",
            "noun_gender": "das",
            "noun_genetiv": "des Weihnachtsgefühls",
            "noun_plural": "Weihnachtsgefühle",
            "noun_forms": "-s, -e",
        },
        "\"wer möchte, hat auch…\"": {
            "tags": "phrase",
            "meaning": "wer möchte, hat auch... = wer ein bestimmtes Ziel anstrebt, findet oft auch eine Loesung oder die Mittel dazu / where there's a will, there's a way",
            "de_1": "Er ist sehr zielstrebig und glaubt immer: Wer moechte, hat auch eine Moeglichkeit.",
            "en_1": "He is very goal-oriented and always believes: Where there's a will, there's a way.",
            "word_inf": "wer möchte, hat auch…",
        },
        "abbrechen": {
            "tags": "verb",
            "meaning": "abbrechen = etwas unerwartet frueh beenden oder stoppen / to break off, cancel, abort",
            "de_1": "Wegen des starken Sturms mussten wir unsere Wanderung abbrechen.",
            "en_1": "Because of the severe storm, we had to abort our hike.",
            "word_inf": "abbrechen",
            "verb_present": "bricht ab",
            "verb_past": "brach ab",
            "verb_perfect": "hat abgebrochen",
        },
        "Am Samstag anfangs Regen": {
            "tags": "phrase",
            "meaning": "Am Samstag anfangs Regen = Typische und verkuerzte Wetterprognose: Am Samstag gibt es am Anfang Regen / Initally rain on Saturday",
            "de_1": "Der Wetterbericht meldet: Am Samstag anfangs Regen, spaeter heiter.",
            "en_1": "The weather report says: Initially rain on Saturday, later clear.",
            "word_inf": "Am Samstag anfangs Regen",
        },
        "Aufenthalt planen": {
            "tags": "phrase",
            "meaning": "Aufenthalt planen = organisieren, wo und wie man seine Zeit waehrend einer Reise verbringt / to plan a stay",
            "de_1": "Wenn wir nach Paris reisen, muessen wir den Aufenthalt planen.",
            "en_1": "When we travel to Paris, we have to plan the stay.",
            "word_inf": "Aufenthalt planen",
        },
        "ausgerechnet": {
            "tags": "adv",
            "meaning": "ausgerechnet = ein unerwarteter, oft aergerlicher Zufall (genau das, genau jetzt) / of all things, ironicaly, precisely",
            "de_1": "Es regnet ausgerechnet heute, wo wir draussen feiern wollten.",
            "en_1": "It's raining today of all days, when we wanted to celebrate outside.",
            "word_inf": "ausgerechnet",
        },
        "bei der Wahl": {
            "tags": "phrase",
            "meaning": "bei der Wahl = waehrend eines Auswahlverfahrens oder einer politischen Abstimmung / during the election, at the choice",
            "de_1": "Bei der Wahl am Sonntag lag die Beteiligung bei ueber siebzig Prozent.",
            "en_1": "At the election on Sunday, turnout was over seventy percent.",
            "word_inf": "bei der Wahl",
        },
        "beibehalten": {
            "tags": "verb",
            "meaning": "beibehalten = etwas nicht aendern, weiter so machen wie bisher / to maintain, keep, retain",
            "de_1": "Trotz der Kritik moechte die Firma ihren bisherigen Kurs beibehalten.",
            "en_1": "Despite the criticism, the company wants to maintain its current course.",
            "word_inf": "beibehalten",
            "verb_present": "behält bei",
            "verb_past": "behielt bei",
            "verb_perfect": "hat beibehalten",
        },
        "Dimensionen annehmen": {
            "tags": "phrase",
            "meaning": "Dimensionen annehmen = eine bestimmte (oft unerwartete) Groesse oder ein Ausmass erreichen / to take on dimensions",
            "de_1": "Das Problem koennte sonst voellig neue Dimensionen annehmen.",
            "en_1": "The problem could otherwise take on completely new dimensions.",
            "word_inf": "Dimensionen annehmen",
        },
        "fünfköpfig": {
            "tags": "adj",
            "meaning": "fuenfkoepfig = aus fuenf Personen bestehend / five-member, five-strong",
            "de_1": "Die fuenfkoepfige Familie zog am Wochenende in ein neues Haus.",
            "en_1": "The five-member family moved into a new house over the weekend.",
            "word_inf": "fünfköpfig",
        },
        "Geben Sie sofort Ihre Bestellung auf": {
            "tags": "phrase",
            "meaning": "Geben Sie sofort Ihre Bestellung auf = Aufforderung, schnell etwas zu kaufen oder zu ordern / Place your order immediately",
            "de_1": "Geben Sie sofort Ihre Bestellung auf, solange der Artikel noch auf Lager ist.",
            "en_1": "Place your order immediately while the item is still in stock.",
            "word_inf": "Geben Sie sofort Ihre Bestellung auf",
        },
        "Geschenkvorschlag": {
            "tags": "noun",
            "meaning": "Geschenkvorschlag = Idee oder Empfehlung fuer ein Geschenk / gift suggestion",
            "de_1": "Im Katalog findest du viele tolle Geschenkvorschlaege fuer Weihnachten.",
            "en_1": "In the catalog, you can find many great gift suggestions for Christmas.",
            "word_inf": "der Geschenkvorschlag",
            "noun_gender": "der",
            "noun_genetiv": "des Geschenkvorschlags",
            "noun_plural": "Geschenkvorschläge",
            "noun_forms": "-s, ⸚e",
        },
        "Maß": {
            "tags": "noun",
            "meaning": "Mass = Groesse, Umfang oder genaue Menge von etwas / measure, extent, amount",
            "de_1": "Dieses Mass an Verantwortung kann man nicht allein tragen.",
            "en_1": "You cannot carry this level of responsibility alone.",
            "word_inf": "das Maß",
            "noun_gender": "das",
            "noun_genetiv": "des Maßes",
            "noun_plural": "Maße",
            "noun_forms": "-es, -e",
        },
        "Mangel": {
            "tags": "noun",
            "meaning": "Mangel = Fehler oder etwas, das fehlt / defect, deficiency, lack",
            "de_1": "Den Mangel muessen wir dem Haendler sofort melden.",
            "en_1": "We need to report the defect to the dealer right away.",
            "word_inf": "der Mangel",
            "noun_gender": "der",
            "noun_genetiv": "des Mangels",
            "noun_plural": "Mängel",
            "noun_forms": "-s, ⸚",
        },
        "Heilige Abend": {
            "tags": "noun",
            "meaning": "Heilige Abend = der Abend des 24. Dezember, an dem Weihnachten gefeiert wird / Christmas Eve",
            "de_1": "Am Heiligen Abend sitzen wir zusammen und oeffnen die Geschenke.",
            "en_1": "On Christmas Eve, we sit together and open the presents.",
            "word_inf": "der Heilige Abend",
            "noun_gender": "der",
            "noun_genetiv": "des Heiligen Abends",
            "noun_plural": "-",
            "noun_forms": "-s, -",
        },
        "heiter": {
            "tags": "adj",
            "meaning": "heiter = sonnig und freundlich, ohne dichte Wolken (Wetter) / fair, clear, bright",
            "de_1": "Morgen wird das Wetter ueberwiegend heiter und trocken.",
            "en_1": "Tomorrow the weather will be mostly fair and dry.",
            "word_inf": "heiter",
        },
        "herumtelefonieren": {
            "tags": "verb",
            "meaning": "herumtelefonieren = viele Personen nacheinander anrufen, um etwas herauszufinden / to phone around",
            "de_1": "Um einen Handwerker zu finden, musste ich den ganzen Vormittag herumtelefonieren.",
            "en_1": "To find a craftsman, I had to phone around all morning.",
            "word_inf": "herumtelefonieren",
            "verb_present": "telefoniert herum",
            "verb_past": "telefonierte herum",
            "verb_perfect": "hat herumtelefoniert",
        },
        "immer schwieriger": {
            "tags": "phrase",
            "meaning": "immer schwieriger = mit der Zeit zusaetzlich herausfordernd / increasingly difficult",
            "de_1": "Es wird immer schwieriger, in dieser Stadt eine bezahlbare Wohnung zu finden.",
            "en_1": "It is becoming increasingly difficult to find an affordable apartment in this city.",
            "word_inf": "immer schwieriger",
        },
        "in ein Flugzeug zwängen": {
            "tags": "phrase",
            "meaning": "in ein Flugzeug zwaengen = sich mit wenig Platz in die Kabine eines Flugzeugs druecken / to squeeze into an airplane",
            "de_1": "Waehrend der Ferienzeit muessen sich viele Menschen in ein Flugzeug zwaengen.",
            "en_1": "During holiday season, many people have to squeeze into a plane.",
            "word_inf": "in ein Flugzeug zwängen",
        },
        "Lehre": {
            "tags": "noun",
            "meaning": "Lehre = praktische Berufsausbildung in einem Betrieb / apprenticeship, lesson",
            "de_1": "Nach der Schule hat er eine Lehre als Elektriker angefangen.",
            "en_1": "After school, he started an apprenticeship as an electrician.",
            "word_inf": "die Lehre",
            "noun_gender": "die",
            "noun_genetiv": "der Lehre",
            "noun_plural": "Lehren",
            "noun_forms": "-, -n",
        },
        "niederschlagsfrei": {
            "tags": "adj",
            "meaning": "niederschlagsfrei = ohne Regen oder Schnee / precipitation-free, dry",
            "de_1": "Am Wochenende bleibt es voraussichtlich niederschlagsfrei.",
            "en_1": "The weekend is expected to remain precipitation-free.",
            "word_inf": "niederschlagsfrei",
        },
        "sich beschäftigen mit": {
            "tags": "phrase",
            "meaning": "sich beschaeftigen mit = sich einem Thema oder einer Aufgabe intensiv widmen / to deal with, to occupy oneself with",
            "de_1": "In meiner Freizeit beschaeftige ich mich gern mit Fotografie.",
            "en_1": "In my free time, I enjoy occupying myself with photography.",
            "word_inf": "sich beschäftigen mit",
        },
        "sich drehen um": {
            "tags": "phrase",
            "meaning": "sich drehen um = im Mittelpunkt stehen, das Hauptthema sein / to revolve around, to be about",
            "de_1": "In diesem Film dreht sich alles um die Liebe zweier Menschen.",
            "en_1": "Everything in this movie revolves around the love of two people.",
            "word_inf": "sich drehen um",
        },
        "sich herausstellen": {
            "tags": "verb",
            "meaning": "sich herausstellen = nach einer Weile klar oder deutlich werden / to turn out, become apparent",
            "de_1": "Spaeter stellte sich heraus, dass der Fehler gar nicht bei mir lag.",
            "en_1": "Later it turned out that the mistake wasn't mine at all.",
            "word_inf": "herausstellen",
            "verb_present": "stellt sich heraus",
            "verb_past": "stellte sich heraus",
            "verb_perfect": "hat sich herausgestellt",
        },
        "Tannen": {
            "tags": "noun",
            "meaning": "Tanne = Nadelbaum mit flachen Nadeln / fir tree",
            "de_1": "Hinter dem Haus stehen zwei hohe Tannen.",
            "en_1": "There are two tall fir trees behind the house.",
            "word_inf": "die Tanne",
            "noun_gender": "die",
            "noun_genetiv": "der Tanne",
            "noun_plural": "Tannen",
            "noun_forms": "-, -n",
        },
        "Verträge": {
            "tags": "noun",
            "meaning": "Vertrag = schriftliche Vereinbarung zwischen zwei oder mehr Seiten / contract, agreement",
            "de_1": "Die Vertraege liegen schon zur Unterschrift bereit.",
            "en_1": "The contracts are already ready to be signed.",
            "word_inf": "der Vertrag",
            "noun_gender": "der",
            "noun_genetiv": "des Vertrags",
            "noun_plural": "Verträge",
            "noun_forms": "-s, ⸚e",
        },
        "Vorlagen": {
            "tags": "noun",
            "meaning": "Vorlage = Muster, Dokument oder Basis fuer weiteres Arbeiten / template, model, draft",
            "de_1": "Die neuen Vorlagen sparen uns bei jedem Bericht viel Zeit.",
            "en_1": "The new templates save us a lot of time on every report.",
            "word_inf": "die Vorlage",
            "noun_gender": "die",
            "noun_genetiv": "der Vorlage",
            "noun_plural": "Vorlagen",
            "noun_forms": "-, -n",
        },
        "Mitteilungen": {
            "tags": "noun",
            "meaning": "Mitteilung = Information, die man jemandem weitergibt / message, notice, communication",
            "de_1": "Wichtige Mitteilungen werden morgens an das ganze Team geschickt.",
            "en_1": "Important notices are sent to the whole team in the morning.",
            "word_inf": "die Mitteilung",
            "noun_gender": "die",
            "noun_genetiv": "der Mitteilung",
            "noun_plural": "Mitteilungen",
            "noun_forms": "-, -en",
        },
        "Vereinbarungen": {
            "tags": "noun",
            "meaning": "Vereinbarung = Abmachung zwischen zwei oder mehr Seiten / agreement, arrangement",
            "de_1": "Alle Vereinbarungen sollten am Ende schriftlich festgehalten werden.",
            "en_1": "All agreements should be put in writing at the end.",
            "word_inf": "die Vereinbarung",
            "noun_gender": "die",
            "noun_genetiv": "der Vereinbarung",
            "noun_plural": "Vereinbarungen",
            "noun_forms": "-, -en",
        },
        "Zuständigkeiten": {
            "tags": "noun",
            "meaning": "Zustaendigkeit = Bereich, fuer den jemand verantwortlich ist / responsibility, remit, area of responsibility",
            "de_1": "Die Zustaendigkeiten im Projekt muessen klar verteilt sein.",
            "en_1": "Responsibilities in the project need to be clearly assigned.",
            "word_inf": "die Zuständigkeit",
            "noun_gender": "die",
            "noun_genetiv": "der Zuständigkeit",
            "noun_plural": "Zuständigkeiten",
            "noun_forms": "-, -en",
        },
        "Bleibt es dabei?": {
            "tags": "phrase",
            "meaning": "Bleibt es dabei? = Frage, ob ein Plan oder eine Vereinbarung unveraendert bleibt / does it still stand?",
            "de_1": "Bleibt es dabei, dass wir uns um zehn Uhr treffen?",
            "en_1": "Does it still stand that we are meeting at ten?",
            "word_inf": "Bleibt es dabei?",
        },
        "Sitte": {
            "tags": "noun",
            "meaning": "Sitte = Gewohnheit oder Brauch in einer Gesellschaft / tradition, custom",
            "de_1": "In unserer Familie ist es eine feste Sitte, sonntags gemeinsam zu essen.",
            "en_1": "In our family, it is an established custom to eat together on Sundays.",
            "word_inf": "die Sitte",
            "noun_gender": "die",
            "noun_genetiv": "der Sitte",
            "noun_plural": "Sitten",
            "noun_forms": "-, -n",
        },
        "so auf die Nerven, dass ich wegfahren würde": {
            "tags": "phrase",
            "meaning": "so auf die Nerven gehen = extrem belaestigen und stoeren, dass man fluechten moechte / gets on my nerves so much that I'd drive away",
            "de_1": "Der laute Baulaerm auf der Strasse ging ihm so auf die Nerven, dass er am liebsten weggefahren waere.",
            "en_1": "The loud construction noise on the street got on his nerves so much that he preferred to drive away.",
            "word_inf": "so auf die Nerven gehen",
        },
        "Stille": {
            "tags": "noun",
            "meaning": "Stille = vollkommene Ruhe ohne Geraeusche / quietness, silence",
            "de_1": "In der Bibliothek herrscht eine tiefe Stille, damit man gut lernen kann.",
            "en_1": "There is a deep silence in the library so that you can study well.",
            "word_inf": "die Stille",
            "noun_gender": "die",
            "noun_genetiv": "der Stille",
            "noun_plural": "-",
            "noun_forms": "-, -",
        },
        "Um wieviel Uhr ist die Teambesprechung?": {
            "tags": "phrase",
            "meaning": "Um wie viel Uhr ...? = Frage nach der genauen Zeit eines Ereignisses / At what time is the team meeting?",
            "de_1": "Entschuldigung, um wie viel Uhr ist heute die Teambesprechung angesetzt?",
            "en_1": "Excuse me, at what time is the team meeting scheduled today?",
            "word_inf": "Um wie viel Uhr...?",
        },
        "Urlaubsziel": {
            "tags": "noun",
            "meaning": "Urlaubsziel = Ort, an den man reisen moechte, um seine Ferien zu verbringen / holiday destination",
            "de_1": "Spanien ist in Europa ein sehr beliebtes Urlaubsziel im Sommer.",
            "en_1": "Spain is a very popular holiday destination in Europe in the summer.",
            "word_inf": "das Urlaubsziel",
            "noun_gender": "das",
            "noun_genetiv": "des Urlaubsziels",
            "noun_plural": "Urlaubsziele",
            "noun_forms": "-s, -e",
        },
        "von weit her": {
            "tags": "phrase",
            "meaning": "von weit her = aus grosser persoenlicher oder raeumlicher Distanz / from far away",
            "de_1": "Viele Gaeste auf seiner Hochzeit kamen von weit her angereist.",
            "en_1": "Many guests at his wedding traveled from far away.",
            "word_inf": "von weit her",
        },
        "Wann kommt Frau Dr. Amos?": {
            "tags": "phrase",
            "meaning": "Wann kommt ...? = Frage nach dem Ankunftszeitpunkt / When is Mrs. Dr. Amos coming?",
            "de_1": "Ich habe einen Termin um zwoelf Uhr. Wann kommt Frau Dr. Amos?",
            "en_1": "I have an appointment at twelve o'clock. When is Dr. Amos coming?",
            "word_inf": "Wann kommt...?",
        },
        "wat hier los ist in Berlin": {
            "tags": "phrase",
            "meaning": "wat hier los ist (Berlinerisch) = was hier alles passiert oder wie voll/geschaeftig es ist (umgangssprachlich) / what is going on here in Berlin",
            "de_1": "Manchmal kann man kaum glauben, wat hier los ist in Berlin an einem Samstagabend.",
            "en_1": "Sometimes you can hardly believe what is going on here in Berlin on a Saturday night.",
            "word_inf": "was hier los ist",
        },
        "Weihnachtseinkäufe": {
            "tags": "noun",
            "meaning": "Weihnachtseinkaeufe = Besorgungen, die man speziell fuer das Weihnachtsfest macht / Christmas shopping",
            "de_1": "Am Samstag vor dem Advent waren wir den ganzen Tag Weihnachtseinkaeufe erledigen.",
            "en_1": "On the Saturday before Advent, we spent all day doing Christmas shopping.",
            "word_inf": "die Weihnachtseinkäufe",
            "noun_gender": "die (plural)",
            "noun_genetiv": "der Weihnachtseinkäufe",
            "noun_plural": "Weihnachtseinkäufe",
            "noun_forms": "-",
        },
        "zu erreichen": {
            "tags": "phrase",
            "meaning": "zu erreichen = telefonisch oder persoenlich kontaktierbar sein / reachable, available to contact",
            "de_1": "Herr Schmidt ist momentan telefonisch nicht zu erreichen.",
            "en_1": "Mr. Schmidt is currently not reachable by phone.",
            "word_inf": "erreichen",
            "verb_present": "erreicht",
            "verb_past": "erreichte",
            "verb_perfect": "hat erreicht",
        },
        "über meine Ergebnisse berichten": {
            "tags": "phrase",
            "meaning": "ueber Ergebnisse berichten = dem Team oder Chef Resultate praesentieren / to report on my results",
            "de_1": "Morgen Nachmittag muss ich im kurzen Meeting ueber meine Ergebnisse berichten.",
            "en_1": "Tomorrow afternoon I have to report on my results in the short meeting.",
            "word_inf": "berichten",
        },
        "„Es wird + Adjektiv“": {
            "tags": "phrase",
            "meaning": "Es wird + Adjektiv = Ausdruck, dass sich ein Zustand entwickelt oder aendert / It becomes / It gets + adjective",
            "de_1": "Nimm eine Jacke mit, am Abend wird es schnell sehr kalt.",
            "en_1": "Take a jacket with you, it gets very cold quickly in the evening.",
            "word_inf": "es wird ...",
        },
    }

    ENTRY_OVERRIDES.update({
        "abwesend": {"tags": "adj", "meaning": "abwesend = nicht anwesend oder mit den Gedanken woanders / absent, not present", "de_1": "Heute ist Herr Keller leider abwesend, daher antworte ich.", "en_1": "Mr. Keller is unfortunately absent today, so I will reply.", "word_inf": "abwesend"},
        "angenehm": {"tags": "adj", "meaning": "angenehm = angenehm, freundlich oder als gut empfunden / pleasant, comfortable", "de_1": "Hier sitzt man wirklich angenehm, auch wenn das Meeting lang wird.", "en_1": "It feels really pleasant here, even if the meeting runs long.", "word_inf": "angenehm"},
        "Arbeitsbedingungen": {"tags": "noun", "meaning": "Arbeitsbedingungen = Umstaende, unter denen Menschen arbeiten / working conditions", "de_1": "Die Arbeitsbedingungen sind viel besser geworden, und das merkt man im Alltag.", "en_1": "The working conditions have become much better, and you can feel it every day.", "word_inf": "die Arbeitsbedingungen", "noun_gender": "die (plural)", "noun_genetiv": "der Arbeitsbedingungen", "noun_plural": "Arbeitsbedingungen", "noun_forms": "-"},
        "Art und Weise": {"tags": "phrase", "meaning": "Art und Weise = die Methode oder Form, wie etwas gemacht wird / way, manner", "de_1": "Die Art und Weise, wie Sie das erklaert haben, war echt hilfreich.", "en_1": "The way you explained that was really helpful.", "word_inf": "die Art und Weise"},
        "beanspruchen": {"tags": "verb", "meaning": "beanspruchen = etwas fuer sich verlangen oder viel Zeit/Kraft erfordern / to claim, to take up", "de_1": "Der Antrag beansprucht mehr Zeit, als ich zuerst dachte.", "en_1": "The application takes more time than I first thought.", "word_inf": "beanspruchen", "verb_present": "beansprucht", "verb_past": "beanspruchte", "verb_perfect": "hat beansprucht"},
        "begründen": {"tags": "verb", "meaning": "begründen = einen Grund fuer eine Entscheidung oder Meinung nennen / to justify, give reasons", "de_1": "Koennen Sie kurz begruenden, warum der Termin nicht passt?", "en_1": "Can you briefly explain why the appointment does not work?", "word_inf": "begründen", "verb_present": "begründet", "verb_past": "begründete", "verb_perfect": "hat begründet"},
        "Benefizkonzert": {"tags": "noun", "meaning": "Benefizkonzert = Konzert, dessen Einnahmen fuer einen guten Zweck bestimmt sind / charity concert", "de_1": "Beim Benefizkonzert kommt hoffentlich genug Geld fuer das neue Jugendprojekt zusammen.", "en_1": "At the charity concert, hopefully enough money will be raised for the new youth project.", "word_inf": "das Benefizkonzert", "noun_gender": "das", "noun_genetiv": "des Benefizkonzerts", "noun_plural": "Benefizkonzerte", "noun_forms": "-s, -e"},
        "Bereichen": {"tags": "noun", "meaning": "Bereich = abgegrenztes Thema, Gebiet oder Arbeitsfeld / area, field", "de_1": "In diesen Bereichen fehlt uns noch etwas Erfahrung.", "en_1": "We still lack a bit of experience in these areas.", "word_inf": "der Bereich", "noun_gender": "der", "noun_genetiv": "des Bereichs", "noun_plural": "Bereiche", "noun_forms": "-s, -e"},
        "berichten über": {"tags": "phrase", "meaning": "ueber etwas berichten = Informationen zu einem Thema weitergeben / to report on something", "de_1": "Morgen berichte ich im Team kurz ueber den Stand der Dinge.", "en_1": "Tomorrow I will briefly report to the team on the current status.", "word_inf": "über etwas berichten"},
        "Beschluss": {"tags": "noun", "meaning": "Beschluss = offiziell getroffene Entscheidung, oft in einer Sitzung / resolution, decision", "de_1": "Nach der Diskussion war der Beschluss schnell klar.", "en_1": "After the discussion, the decision was clear quickly.", "word_inf": "der Beschluss", "noun_gender": "der", "noun_genetiv": "des Beschlusses", "noun_plural": "Beschlüsse", "noun_forms": "-es, -¨e"},
        "Brauch": {"tags": "noun", "meaning": "Brauch = traditionelle Gewohnheit in einer Gruppe oder Region / custom, tradition", "de_1": "In unserer Familie ist dieser Brauch immer noch wichtig.", "en_1": "In our family, this custom is still important.", "word_inf": "der Brauch", "noun_gender": "der", "noun_genetiv": "des Brauchs", "noun_plural": "Bräuche", "noun_forms": "-s, -¨e"},
        "Das würden Sie wirklich für mich machen?": {"tags": "phrase", "meaning": "Das wuerden Sie wirklich fuer mich machen? = hoefliche erstaunte Rueckfrage bei einem Hilfsangebot / Would you really do that for me?", "de_1": "Das wuerden Sie wirklich fuer mich machen? Das waere wirklich nett.", "en_1": "Would you really do that for me? That would be really nice.", "word_inf": "Das würden Sie wirklich für mich machen?"},
        "den Überblick behält": {"tags": "phrase", "meaning": "den Ueberblick behalten = trotz vieler Informationen wissen, was wichtig ist / to keep an overview", "de_1": "Bei so vielen Aufgaben ist es wichtig, dass jemand den Ueberblick behaelt.", "en_1": "With so many tasks, it is important that someone keeps track of everything.", "word_inf": "den Überblick behalten"},
        "Distanz": {"tags": "noun", "meaning": "Distanz = raeumlicher oder persoenlicher Abstand / distance", "de_1": "Bitte halten Sie im Gespraech etwas Distanz.", "en_1": "Please keep a little distance in the conversation.", "word_inf": "die Distanz", "noun_gender": "die", "noun_genetiv": "der Distanz", "noun_plural": "Distanzen", "noun_forms": "-, -en"},
        "Entscheidung treffen": {"tags": "phrase", "meaning": "eine Entscheidung treffen = sich nach dem Abwaegen fuer eine Moeglichkeit entscheiden / to make a decision", "de_1": "Wir muessen heute noch entscheiden, wie wir weitermachen.", "en_1": "We still have to decide today how we want to continue.", "word_inf": "eine Entscheidung treffen"},
        "erwähnen": {"tags": "verb", "meaning": "erwaehnen = etwas kurz in einem Gespraech oder Text nennen / to mention", "de_1": "Kannst du im Bericht auch kurz die offenen Punkte erwaehnen?", "en_1": "Can you also briefly mention the open points in the report?", "word_inf": "erwähnen", "verb_present": "erwähnt", "verb_past": "erwähnte", "verb_perfect": "hat erwähnt"},
        "Haben Sie einen Vorschlag?": {"tags": "phrase", "meaning": "Haben Sie einen Vorschlag? = hoefliche Frage nach einer Idee oder Empfehlung / Do you have a suggestion?", "de_1": "Wir kommen gerade nicht weiter. Haben Sie einen Vorschlag?", "en_1": "We are stuck right now. Do you have a suggestion?", "word_inf": "Haben Sie einen Vorschlag?"},
        "hinzuschreiben": {"tags": "verb", "meaning": "hinzuschreiben = etwas zusaetzlich an eine Stelle schreiben / to add in writing", "de_1": "Schreiben Sie Ihre Telefonnummer bitte noch dazu.", "en_1": "Please add your phone number too.", "word_inf": "hinzuschreiben", "verb_present": "schreibt hinzu", "verb_past": "schrieb hinzu", "verb_perfect": "hat hinzugeschrieben"},
        "indirekt zum Punkt kommen": {"tags": "phrase", "meaning": "indirekt zum Punkt kommen = ein Thema vorsichtig ansprechen, ohne es sofort direkt zu sagen / to get to the point indirectly", "de_1": "Er kommt meistens erst indirekt zum Punkt, bevor er es klar sagt.", "en_1": "He usually gets to the point indirectly before saying it clearly.", "word_inf": "indirekt zum Punkt kommen"},
        "Konflikt": {"tags": "noun", "meaning": "Konflikt = Streit oder schwierige Gegensaetze zwischen Personen oder Interessen / conflict", "de_1": "Im Team gibt es gerade einen kleinen Konflikt, den wir ruhig loesen muessen.", "en_1": "There is a small conflict in the team right now that we need to solve calmly.", "word_inf": "der Konflikt", "noun_gender": "der", "noun_genetiv": "des Konflikts", "noun_plural": "Konflikte", "noun_forms": "-s, -e"},
        "Manchem ist nicht klar.": {"tags": "phrase", "meaning": "Manchem ist nicht klar = einigen Personen ist etwas nicht verstaendlich / some people are not clear about it", "de_1": "Manchem ist noch nicht klar, warum die neue Regel sofort gilt.", "en_1": "Some people are still not clear about why the new rule applies right away.", "word_inf": "manchem ist nicht klar"},
        "Mängelerfassung": {"tags": "noun", "meaning": "Maengelerfassung = systematisches Aufnehmen und Dokumentieren von Fehlern oder Schaeden / defect recording", "de_1": "Die Maengelerfassung machen wir direkt nach der Besichtigung.", "en_1": "We do the defect recording right after the inspection.", "word_inf": "die Mängelerfassung", "noun_gender": "die", "noun_genetiv": "der Mängelerfassung", "noun_plural": "Mängelerfassungen", "noun_forms": "-, -en"},
        "Mir ist nicht klar.": {"tags": "phrase", "meaning": "Mir ist nicht klar = ich verstehe etwas noch nicht oder bin unsicher / it is not clear to me", "de_1": "Mir ist noch nicht klar, welche Unterlagen ich zuerst pruefen soll.", "en_1": "I am still not clear on which documents I should check first.", "word_inf": "mir ist nicht klar"},
        "Monatsbericht": {"tags": "noun", "meaning": "Monatsbericht = Bericht, der die wichtigsten Informationen eines Monats zusammenfasst / monthly report", "de_1": "Der Monatsbericht muss bis Freitag an die Leitung geschickt werden.", "en_1": "The monthly report must be sent to management by Friday.", "word_inf": "der Monatsbericht", "noun_gender": "der", "noun_genetiv": "des Monatsberichts", "noun_plural": "Monatsberichte", "noun_forms": "-s, -e"},
        "Oh je!": {"tags": "interjection", "meaning": "Oh je! = Ausruf bei Sorge, Ueberraschung oder einem kleinen Problem / oh dear", "de_1": "Oh je! Ich habe den Termin im Kalender falsch eingetragen.", "en_1": "Oh dear! I entered the appointment incorrectly in the calendar.", "word_inf": "Oh je!"},
        "restlich": {"tags": "adj", "meaning": "restlich = uebrig oder noch verbleibend / remaining", "de_1": "Die restlichen Unterlagen schicken wir Ihnen morgen zu.", "en_1": "We will send you the remaining documents tomorrow.", "word_inf": "restlich"},
        "sich mit jmd. in Verbindung setzen": {"tags": "phrase", "meaning": "sich mit jemandem in Verbindung setzen = Kontakt zu einer Person aufnehmen / to get in touch with someone", "de_1": "Ich setze mich morgen mit der zustaendigen Kollegin in Verbindung.", "en_1": "I will get in touch with the responsible colleague tomorrow.", "word_inf": "sich mit jemandem in Verbindung setzen"},
        "treffen": {"tags": "verb", "meaning": "treffen = einer Person begegnen oder eine Entscheidung/Vereinbarung machen / to meet; to make", "de_1": "Morgen trifft sich das Team, um eine Entscheidung zu treffen.", "en_1": "Tomorrow the team meets to make a decision.", "word_inf": "treffen", "verb_present": "trifft", "verb_past": "traf", "verb_perfect": "hat getroffen"},
        "um Hilfe bitte + AKK": {"tags": "phrase", "meaning": "um Hilfe bitten = eine Person hoeflich um Unterstuetzung fragen / to ask for help", "de_1": "Wenn ich die Aufgabe nicht verstehe, bitte ich meine Kollegin um Hilfe.", "en_1": "If I do not understand the task, I ask my colleague for help.", "word_inf": "jemanden um Hilfe bitten"},
        "umfangreich": {"tags": "adj", "meaning": "umfangreich = gross im Umfang, mit vielen Teilen oder Details / extensive, comprehensive", "de_1": "Die Dokumentation ist umfangreich, aber gut strukturiert.", "en_1": "The documentation is extensive but well structured.", "word_inf": "umfangreich"},
        "umgekehrt": {"tags": "adv", "meaning": "umgekehrt = in der entgegengesetzten Richtung oder Reihenfolge / vice versa, reversed", "de_1": "Erst pruefen wir die Rechnung, und nicht umgekehrt.", "en_1": "First we check the invoice, and not the other way around.", "word_inf": "umgekehrt"},
        "Umstellung": {"tags": "noun", "meaning": "Umstellung = Aenderung von einem bisherigen Ablauf auf einen neuen Ablauf / changeover, transition", "de_1": "Die Umstellung auf das neue System dauert ein paar Wochen.", "en_1": "The changeover to the new system will take a few weeks.", "word_inf": "die Umstellung", "noun_gender": "die", "noun_genetiv": "der Umstellung", "noun_plural": "Umstellungen", "noun_forms": "-, -en"},
        "Unbestimmt": {"tags": "adj", "meaning": "unbestimmt = nicht genau festgelegt oder nicht eindeutig / indefinite, unspecified", "de_1": "Der Termin ist noch unbestimmt, weil mehrere Rueckmeldungen fehlen.", "en_1": "The date is still unspecified because several responses are missing.", "word_inf": "unbestimmt"},
        "Verantwortung für etwas bekommen": {"tags": "phrase", "meaning": "Verantwortung fuer etwas bekommen = fuer eine Aufgabe zustaendig werden / to be given responsibility for something", "de_1": "Ab naechster Woche bekomme ich Verantwortung fuer den Monatsbericht.", "en_1": "Starting next week, I will be given responsibility for the monthly report.", "word_inf": "Verantwortung für etwas bekommen"},
        "Vereinbarung treffen": {"tags": "phrase", "meaning": "eine Vereinbarung treffen = sich gemeinsam verbindlich auf etwas einigen / to make an agreement", "de_1": "Wir sollten heute eine klare Vereinbarung treffen.", "en_1": "We should make a clear agreement today.", "word_inf": "eine Vereinbarung treffen"},
        "währen": {"tags": "verb", "meaning": "waehren = eine bestimmte Zeit dauern oder andauern / to last, endure", "de_1": "Die Besprechung wird voraussichtlich eine Stunde waehren.", "en_1": "The meeting is expected to last one hour.", "word_inf": "währen", "verb_present": "währt", "verb_past": "währte", "verb_perfect": "hat gewährt"},
        "zugreifen": {"tags": "verb", "meaning": "zugreifen = auf Daten, Unterlagen oder ein Angebot Zugriff nehmen / to access", "de_1": "Auf diese Datei koennen nur Mitarbeitende der Abteilung zugreifen.", "en_1": "Only employees of the department can access this file.", "word_inf": "zugreifen", "verb_present": "greift zu", "verb_past": "griff zu", "verb_perfect": "hat zugegriffen"},
    })

    BAD_OUTPUT_MARKERS = (
        "Ausdruck im Themenkontext",
        "context-specific expression",
        "In diesem Kontext ist",
        "is particularly important",
        "nuetzlicher Ausdruck fuer Kommunikation",
        "useful expression for communication",
        "zentrales Nomen im Lernkontext",
        "key noun in this learning context",
        "Handlung oder Vorgang im Alltag",
        "action or process in everyday life",
        "Ausdruck mit erklaerendem Zusatz",
        "konkrete Bedeutung im aktuellen Themenfeld",
        "konkrete Formulierung im Themenfeld",
        "Nomen im Themenkontext",
        "Verb fuer Handlung im Kontext",
        "Bedeutung als Verb im aktuellen Themenfeld",
        "contextual noun meaning",
        "contextual meaning",
        "verb meaning in this topic",
        "This full phrase is used directly in the example.",
    )

    BAD_LINE_PATTERNS = (
        re.compile(
            r"^meaning:\s*.+?=\s*nuetzlicher Ausdruck fuer Kommunikation\s*/\s*useful expression for communication\s*$", re.IGNORECASE),
        re.compile(
            r"^meaning:\s*.+?=\s*zentrales Nomen im Lernkontext\s*/\s*key noun in this learning context\s*$", re.IGNORECASE),
        re.compile(
            r"^meaning:\s*.+?=\s*Handlung oder Vorgang im Alltag\s*/\s*action or process in everyday life\s*$", re.IGNORECASE),
        re.compile(
            r"^de_1:\s*Wir verwenden .+ oft in alltaeglichen Situationen\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*We often use .+ in everyday situations\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^de_1:\s*Der Begriff .+ ist in diesem Thema besonders wichtig\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*The term .+ is especially important in this topic\.?\s*$", re.IGNORECASE),
        # Generic fallback sentences produced by build_example_de / build_example_en
        re.compile(
            r"^de_1:\s*Im Text kommt .+ mehrmals vor\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*The word .+ appears several times in the text\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^de_1:\s*Im Unterricht besprechen wir .+\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*In class, we discuss .+\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^de_1:\s*Wir setzen das Wort .+ in einem klaren Satz ein\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*We use the word .+ in a clear sentence\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^de_1:\s*.+ taucht in diesem Abschnitt mehrfach auf\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*This term appears several times in this section\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*This sentence pattern is used to describe sequence and timing\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^de_1:\s*Bei diesem Thema spielt .+ eine wichtige Rolle\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^de_1:\s*.+ spielt bei dieser Aufgabe eine wichtige Rolle\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^de_1:\s*Im Arbeitsalltag brauchen wir .+ regelm[aä]ssig\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*.+ plays an important role in this (?:topic|task)\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*We regularly need .+ in everyday work\.?\s*$", re.IGNORECASE),
        re.compile(
            r"^en_1:\s*This full phrase is used directly in the example\.?\s*$", re.IGNORECASE),
    )

    CONTEXT_OVERRIDES = {
        "Abläufe": ("Wir müssen die Abläufe im Team noch besser abstimmen.", "We still need to coordinate the processes in the team better."),
        "Abzug": ("Bei diesem Schaden gibt es keinen Abzug vom Preis.", "In this case there is no deduction from the price."),
        "Aktennotiz": ("Nach dem Gespräch schreibe ich sofort eine Aktennotiz.", "I write a file note right after the conversation."),
        "Aktenstruktur": ("Die Aktenstruktur ist jetzt für alle im Team klar.", "The file structure is now clear to everyone on the team."),
        "Abläufe kennenlernen": ("In den ersten Wochen möchte ich die Abläufe kennenlernen.", "In the first few weeks I want to get to know the processes."),
        "alleine machen": ("Den ersten Bericht möchte ich noch nicht alleine machen.", "I do not want to do the first report on my own yet."),
        "Anrufe bekommen": ("Am Montag bekommen wir besonders viele Anrufe.", "We get especially many calls on Monday."),
        "Arbeitszeiterfassung": ("Die Arbeitszeiterfassung machen wir jetzt digital.", "We handle time tracking digitally now."),
        "Ausschreibung": ("Die Ausschreibung für das Projekt wird nächste Woche veröffentlicht.", "The tender for the project will be published next week."),
        "Bauherren": ("Die Bauherren warten noch auf den aktuellen Kostenplan.", "The clients are still waiting for the current cost plan."),
        "bekäme": ("Wenn ich mehr Zeit hätte, bekäme ich die Aufgabe heute noch fertig.", "If I had more time, I would get the task done today."),
        "bezahlbare": ("Wir suchen noch eine bezahlbare Wohnung in der Nähe.", "We are still looking for an affordable apartment nearby."),
        "Bindestrich": ("Zwischen den beiden Wörtern fehlt ein Bindestrich.", "A hyphen is missing between the two words."),
        "bei der Erstellung von + Dativ helfen": ("Können Sie mir bitte bei der Erstellung des Protokolls helfen?", "Could you please help me prepare the minutes?"),
        "Bleibt es dabei oder passt es Ihnen später besser?": ("Bleibt es dabei oder passt es Ihnen später besser, wenn wir uns um drei treffen?", "Shall we keep it as planned, or would later suit you better if we meet at three?"),
        "Bleibt es dabei?": ("Bleibt es dabei, dass wir uns um zehn Uhr treffen?", "Does it remain the plan that we meet at ten?"),
        "Bronchitis": ("Wegen der Bronchitis bleibt er diese Woche zu Hause.", "He is staying home this week because of bronchitis."),
        "Brückentag": ("Am Brückentag ist das Büro nur vormittags geöffnet.", "On the bridge day the office is only open in the morning."),
        "Börse": ("An der Börse gab es heute starke Schwankungen.", "There were strong fluctuations on the stock exchange today."),
        "dasselbe Datum": ("Auf beiden Formularen steht dasselbe Datum.", "The same date is written on both forms."),
        "den größten Bedarf sehen": ("Im Service sehen wir momentan den größten Bedarf.", "At the moment we see the greatest need in customer service."),
        "Dafür gehe ich zu/zur …": ("Dafür gehe ich zur Personalabteilung, weil nur dort der Antrag bearbeitet wird.", "For that I go to the HR department because only they can process the request."),
        "Deswegen sollte es jetzt unser Ziel sein, dass…": ("Deswegen sollte es jetzt unser Ziel sein, dass alle Termine realistischer geplant werden.", "Therefore our goal now should be that all deadlines are planned more realistically."),
        "dürfte ich mal kurz stören?": ("Dürfte ich Sie mal kurz stören? Ich habe noch eine Frage zur Rechnung.", "May I disturb you for a moment? I still have a question about the invoice."),
        "Einarbeitung": ("Die Einarbeitung der neuen Kollegin dauert noch ein paar Tage.", "The onboarding of the new colleague will take a few more days."),
        "Entfernen": ("Vor dem Streichen müssen wir die alte Farbe entfernen.", "Before painting we need to remove the old paint."),
        "Entsorgung": ("Für die Entsorgung des alten Schranks brauchen wir einen Termin.", "We need an appointment for disposing of the old cabinet."),
        "Erstellung": ("Die Erstellung des Berichts dauert länger als geplant.", "Preparing the report is taking longer than planned."),
        "Erteilung": ("Die Erteilung der Genehmigung kann noch einige Tage dauern.", "Granting the permit may still take a few days."),
        "Erzählen Sie doch mal.": ("Erzählen Sie doch mal, wie Ihr erster Arbeitstag war.", "Tell me a bit about how your first day at work went."),
        "es freut mich": ("Es freut mich, dass Sie heute Zeit gefunden haben.", "I'm glad that you found time today."),
        "es ist gut bei Stress": ("Eine klare To-do-Liste ist gut bei Stress, weil man den Überblick behält.", "A clear to-do list is good when you're stressed because it helps you keep track of everything."),
        "es nicht schaffen": ("Ich werde es heute nicht schaffen, alles zu erledigen.", "I will not manage to finish everything today."),
        "etwas für das Protokoll notieren": ("Ich notiere den Beschluss gleich für das Protokoll, damit nichts verloren geht.", "I am noting the decision down for the minutes right away so nothing gets lost."),
        "etwas ablegen": ("Bitte legen Sie die Rechnung im richtigen Ordner ab.", "Please file the invoice in the correct folder."),
        "extra bezahlt": ("Die zusätzlichen Stunden werden extra bezahlt.", "The extra hours are paid separately."),
        "fachgerecht": ("Die Heizung wurde fachgerecht eingebaut.", "The heating system was installed properly."),
        "Fertigstellung": ("Die Fertigstellung des Hauses ist für Juli geplant.", "The completion of the house is planned for July."),
        "früher nach Hause gehen": ("Ich muss heute früher nach Hause gehen, weil mein Kind krank ist.", "I have to go home earlier today because my child is sick."),
        "Für einen/ein/eine … sollte man …": ("Für eine längere Dienstreise sollte man früh genug ein Hotel buchen.", "For a longer business trip, you should book a hotel early enough."),
        "Gefühl haben": ("Ich habe das Gefühl, dass wir eine Frist übersehen haben.", "I have the feeling that we have overlooked a deadline."),
        "Genauigkeit": ("Bei dieser Messung ist Genauigkeit besonders wichtig.", "Accuracy is especially important for this measurement."),
        "Gewährleistung": ("Für das Gerät gilt noch zwei Jahre Gewährleistung.", "The device is still covered by warranty for two years."),
        "gleich alleine": ("Den nächsten Anruf können Sie gleich alleine übernehmen.", "You can handle the next call on your own right away."),
        "Geräte gehen manchmal nach … kaputt. Deshalb lohnt es sich, …": ("Geräte gehen manchmal nach zwei oder drei Jahren kaputt. Deshalb lohnt es sich, die Garantiebedingungen genau zu prüfen.", "Devices sometimes break after two or three years, so it is worth checking the warranty terms carefully."),
        "Grundriss": ("Im Grundriss sieht man sofort, wo die Küche liegt.", "In the floor plan you can immediately see where the kitchen is."),
        "Handwerker": ("Der Handwerker kommt morgen um acht Uhr vorbei.", "The tradesman is coming by tomorrow at eight."),
        "Händler": ("Der Händler hat uns ein neues Angebot geschickt.", "The dealer sent us a new offer."),
        "Ich finde es sinnvoll/praktisch, …, weil …": ("Ich finde es sinnvoll, die Daten zentral zu speichern, weil dann alle darauf zugreifen können.", "I think it makes sense to store the data centrally because then everyone can access it."),
        "Ich habe Kritik von Ihnen bekommen.": ("Ich habe Kritik von Ihnen bekommen und möchte den Punkt gern verbessern.", "I received criticism from you and would like to improve that point."),
        "Ich schließe immer/nie … ab, weil …": ("Ich schließe meinen Schreibtisch immer ab, weil dort vertrauliche Unterlagen liegen.", "I always lock my desk because confidential documents are kept there."),
        "Ich weiß oft nicht, wie es hier gemacht wird.": ("Ich weiß oft nicht, wie es hier gemacht wird, weil ich noch neu im Team bin.", "I often don't know how things are done here because I am still new to the team."),
        "im Moment am wichtigsten sein": ("Für uns wird im Moment am wichtigsten sein, die offenen Aufgaben zu sortieren.", "For us, the most important thing at the moment will be to sort the open tasks."),
        "Ist es sinnvoll, eine Garantieverlängerung zu kaufen? Für welche Geräte? Diskutieren Sie.": ("Ist es sinnvoll, eine Garantieverlängerung zu kaufen? Für teure Geräte würde ich eher ja sagen.", "Is it worth buying an extended warranty? For expensive devices, I would be more likely to say yes."),
        "Kritik bekommen": ("Am Anfang ist es nicht leicht, Kritik zu bekommen.", "At the beginning it is not easy to receive criticism."),
        "Das habe ich wohl falsch verstanden.": ("Das habe ich wohl falsch verstanden. Können Sie es bitte noch einmal erklären?", "I must have misunderstood that. Could you please explain it once again?"),
        "Das ist schwierig für mich.": ("Das ist schwierig für mich, weil ich mit dem Programm noch keine Erfahrung habe.", "That is difficult for me because I do not have any experience with the program yet."),
        "eine Lösung finden": ("Wir müssen heute noch eine Lösung finden.", "We still need to find a solution today."),
        "Maß": ("Wir müssen das Maß noch einmal genau prüfen.", "We need to check the measurement carefully again."),
        "Mangel": ("Den Mangel müssen wir dem Händler sofort melden.", "We need to report the defect to the dealer right away."),
        "Meiner Meinung nach ist es nötig, … zu …, denn …": ("Meiner Meinung nach ist es nötig, die Abläufe zu vereinfachen, denn wir verlieren im Moment zu viel Zeit.", "In my opinion, it is necessary to simplify the processes because we are losing too much time at the moment."),
        "Mitteilungen": ("Wichtige Mitteilungen schicken wir immer per E-Mail.", "We always send important notices by email."),
        "momentan": ("Momentan haben wir besonders viele Anfragen.", "At the moment we have an especially high number of inquiries."),
        "nicht so genaue Regeln": ("In diesem Bereich gibt es noch nicht so genaue Regeln.", "There are not very precise rules in this area yet."),
        "ohne Abzug": ("Wenn alles pünktlich fertig ist, zahlen wir ohne Abzug.", "If everything is finished on time, we will pay in full."),
        "pauschal": ("Das kann man nicht pauschal für alle Fälle sagen.", "You cannot say that as a blanket statement for all cases."),
        "Priorität haben": ("Diese Aufgabe hat heute klare Priorität.", "This task clearly has priority today."),
        "Protokoll führen": ("Während des Meetings muss jemand Protokoll führen.", "Someone has to take minutes during the meeting."),
        "Rechnungen prüfen": ("Am Monatsende muss ich viele Rechnungen prüfen.", "At the end of the month I have to check many invoices."),
        "Rennen": ("Beim Rennen hat sie den zweiten Platz gemacht.", "She took second place in the race."),
        "schnell reagieren": ("Bei Beschwerden müssen wir schnell reagieren.", "We have to react quickly to complaints."),
        "sehr viel Arbeit machen": ("Die Umstellung wird am Anfang sehr viel Arbeit machen.", "The changeover will create a lot of work at the beginning."),
        "Schön, dass Sie da sind.": ("Schön, dass Sie da sind. Dann können wir direkt mit der Besprechung anfangen.", "Nice to have you here. Then we can start the meeting right away."),
        "selbstständig erledigen": ("Diese Aufgabe können Sie bald selbstständig erledigen.", "You will soon be able to handle this task independently."),
        "sich mit jmd. in Verbindung setzen": ("Ich setze mich morgen mit der zuständigen Kollegin in Verbindung.", "I will get in touch with the responsible colleague tomorrow."),
        "sich in Verbindung setzen": ("Bitte setzen Sie sich noch heute mit dem Kunden in Verbindung.", "Please get in touch with the customer today."),
        "Sie/Er hat mich kritisiert.": ("Er hat mich gestern wegen des Fehlers deutlich kritisiert.", "He criticized me clearly yesterday because of the mistake."),
        "Tannen": ("Hinter dem Haus stehen mehrere alte Tannen.", "There are several old fir trees behind the house."),
        "termingerecht": ("Die Unterlagen müssen termingerecht eingereicht werden.", "The documents must be submitted on time."),
        "um Hilfe bitte + AKK": ("Wenn ich die Aufgabe nicht verstehe, bitte ich meine Kollegin um Hilfe.", "If I do not understand the task, I ask my colleague for help."),
        "um Unterstützung bitten": ("Wenn es zu viel wird, sollten Sie um Unterstützung bitten.", "If it becomes too much, you should ask for support."),
        "unangenehme Situation": ("Das war für alle eine unangenehme Situation.", "That was an unpleasant situation for everyone."),
        "Unterstützung bekommen": ("Bei der Einarbeitung habe ich viel Unterstützung bekommen.", "I received a lot of support during onboarding."),
        "Urlaub nehmen": ("Im August möchte ich eine Woche Urlaub nehmen.", "I want to take a week off in August."),
        "Urlaubsantrag ausfüllen": ("Den Urlaubsantrag fülle ich heute noch aus.", "I will fill out the vacation request today."),
        "Urlaubsvertretung": ("Für nächste Woche brauchen wir noch eine Urlaubsvertretung.", "We still need someone to cover the vacation next week."),
        "Vereinbarungen": ("Alle Vereinbarungen stehen jetzt schriftlich im Protokoll.", "All agreements are now recorded in writing in the minutes."),
        "Verantwortung geben": ("Die Chefin will ihm bald mehr Verantwortung geben.", "The boss wants to give him more responsibility soon."),
        "Verträge": ("Die Verträge liegen schon zur Unterschrift bereit.", "The contracts are already ready to be signed."),
        "vorgeht": ("Im Handbuch steht genau, wie man dabei vorgeht.", "The manual explains exactly how to proceed."),
        "Vorlagen": ("Für diese Briefe haben wir schon gute Vorlagen.", "We already have good templates for these letters."),
        "Voraussetzung": ("Gute Deutschkenntnisse sind eine wichtige Voraussetzung für die Stelle.", "Good German skills are an important requirement for the position."),
        "wöchentlich berichten": ("Im Projekt müssen wir wöchentlich berichten.", "In the project we have to report weekly."),
        "zu tun haben": ("Mit diesem Fall habe ich heute den ganzen Tag zu tun.", "I am dealing with this case all day today."),
        "Zuständigkeiten": ("Die Zuständigkeiten im Team sind jetzt klar verteilt.", "The responsibilities in the team are now clearly assigned."),
        "Überstunden machen": ("Diese Woche muss unser Team leider Überstunden machen.", "Unfortunately our team has to work overtime this week."),
        "Übertrag": ("Den Übertrag tragen wir auf die nächste Seite ein.", "We enter the carryover on the next page."),
        "übrig": ("Nach dem Termin bleibt kaum noch Zeit übrig.", "There is hardly any time left after the appointment."),
        "Wenn ich besser wüsste, … könnte ich …": ("Wenn ich besser wüsste, wie das System funktioniert, könnte ich schneller reagieren.", "If I knew better how the system works, I could react more quickly."),
        "90 mal 90": ("Die Fliesen im Bad sind 90 mal 90 Zentimeter groß.", "The tiles in the bathroom are 90 by 90 centimeters."),
        "Das würden Sie wirklich für mich machen?": ("Das würden Sie wirklich für mich machen? Das hilft mir sehr.", "Would you really do that for me? That helps me a lot."),
        "\"Ja, das ist ein guter Vorschlag.\"": ("Ja, das ist ein guter Vorschlag. Lassen Sie uns das so machen.", "Yes, that's a good suggestion. Let's do it that way."),
        "\"Können Sie sich bitte um [etwas] kümmern?\"": ("Koennen Sie sich bitte um die Unterlagen kuemmern?", "Could you please take care of the documents?"),
        "Aktionstag": ("Am Aktionstag gibt es kleine Geschenke und Aktionen im Laden.", "On the promotional day there are small gifts and activities in the store."),
        "Anspruch auf...": ("Ich habe Anspruch auf drei Tage Sonderurlaub.", "I am entitled to three days of special leave."),
        "Bitte nehmen Sie doch Platz.": ("Bitte nehmen Sie doch Platz, ich bin gleich fuer Sie da.", "Please take a seat, I'll be with you in a moment."),
        "Damit haben wir … besprochen.": ("Damit haben wir alle wichtigen Punkte besprochen.", "With that, we've discussed all the important points."),
        "Der Vorteil wäre, dass …": ("Der Vorteil waere, dass wir dadurch Zeit sparen.", "The advantage would be that we save time as a result."),
        "Die meisten von + Dativ + Verb": ("Die meisten von unseren Kunden kommen aus Berlin.", "Most of our customers come from Berlin."),
        "Im Tourismus": ("Im Tourismus sind gute Sprachkenntnisse oft sehr wichtig.", "In tourism, good language skills are often very important."),
        "Kartonaufsteller": ("Der Kartonaufsteller steht vorne am Eingang und faellt sofort auf.", "The cardboard standee is at the entrance and stands out immediately."),
        "Obwohl": ("Obwohl es regnet, gehen wir spazieren.", "Although it's raining, we are going for a walk."),
        "Todesfall": ("Nach dem Todesfall musste die Familie viele Dinge organisieren.", "After the death, the family had to organize many things."),
        "Trotzdem": ("Es ist spaet, trotzdem bleiben wir noch ein bisschen.", "It's late; nevertheless, we're staying a bit longer."),
        "Unabhängigkeit": ("Unabhaengigkeit ist ihm im Leben sehr wichtig.", "Independence is very important to him in life."),
        "Urlaubsanspruch": ("Wie hoch ist dein Urlaubsanspruch in diesem Jahr?", "How much vacation entitlement do you have this year?"),
        "vereinbart": ("Wir haben einen Termin fuer Montag vereinbart.", "We arranged an appointment for Monday."),
        "Verteilung": ("Die Verteilung der Aufgaben machen wir morgen im Meeting.", "We'll do the allocation of tasks tomorrow in the meeting."),
        "Vorrang haben": ("Sicherheit muss immer Vorrang haben.", "Safety must always take priority."),
        "Werbegeschenk": ("Als Werbegeschenk bekommen die Kunden heute einen Kugelschreiber.", "As a promotional gift, customers get a pen today."),
        "würden … passen": ("Wuerde Ihnen Dienstag um 10 Uhr passen?", "Would Tuesday at 10 a.m. work for you?"),
        "Zwar..., aber...": ("Zwar ist es teuer, aber die Qualitaet ist sehr gut.", "Admittedly it's expensive, but the quality is very good."),
        "abgelehnt": ("Der Antrag wurde abgelehnt, weil Unterlagen fehlen.", "The application was rejected because documents are missing."),
        "dieselbe": ("Wir benutzen dieselbe Vorlage wie letztes Mal.", "We use the same template as last time."),
        "derselbe": ("Das ist derselbe Fehler wie gestern.", "That's the same mistake as yesterday."),
        "dasselbe": ("Das ist dasselbe Problem wie letzte Woche.", "That's the same problem as last week."),
        "entschieden für": ("Ich habe mich fuer die guenstigere Option entschieden.", "I decided in favor of the cheaper option."),
        "erhebliche": ("Es gibt erhebliche Unterschiede zwischen den Angeboten.", "There are significant differences between the offers."),
        "etwas festhalten": ("Ich moechte das kurz festhalten, damit wir es nicht vergessen.", "I want to note this briefly so we don't forget it."),
        "genau so": ("Ja, genau so meinte ich das.", "Yes, that's exactly what I meant."),
        "genehmigt": ("Der Urlaub wurde genehmigt.", "The vacation was approved."),
        "Geheimdienst": ("Der Geheimdienst sammelt Informationen ueber Bedrohungen.", "The intelligence agency gathers information about threats."),
        "nachvollziehbar": ("Deine Entscheidung ist fuer mich nachvollziehbar.", "Your decision is understandable to me."),
        "unerwartete": ("Das war eine unerwartete Nachricht.", "That was unexpected news."),
        "Zusatz": ("Im Vertrag gibt es einen Zusatz mit neuen Regeln.", "There is an addendum in the contract with new rules."),
        "einen Termin vereinbaren": ("Wir muessen noch einen Termin vereinbaren, am besten fuer naechste Woche.", "We still need to arrange an appointment, ideally for next week."),
        "etwas anbieten": ("Wir koennen Ihnen zwei Loesungen anbieten: Standard oder Premium.", "We can offer you two solutions: standard or premium."),
        "etwas durchsprechen": ("Lass uns das Problem kurz durchsprechen, bevor wir entscheiden.", "Let's briefly talk through the problem before we decide."),
        "etwas machen gehen": ("Wollen wir nach der Arbeit etwas machen gehen, zum Beispiel ins Kino?", "Do you want to go do something after work, for example go to the cinema?"),
        "Etwas mehr Marketing wäre sicher gut für uns.": ("Etwas mehr Marketing waere sicher gut fuer uns, damit mehr Leute uns kennen.", "A bit more marketing would surely be good for us so more people know us."),
        "Geht man nach links, kommt man zum Bahnhof.": ("Geht man nach links, kommt man zum Bahnhof und dann weiter zur Innenstadt.", "If you go left, you get to the station and then on to the city center."),
        "Ich finde, wir sollten das jetzt wirklich machen.": ("Ich finde, wir sollten das jetzt wirklich machen, sonst bleibt es wieder liegen.", "I think we should really do that now, otherwise it will be left undone again."),
        "Ich habe mir notiert, dass …": ("Ich habe mir notiert, dass wir bis Freitag eine Entscheidung brauchen.", "I noted down that we need a decision by Friday."),
        "Ich möchte Ihnen zuerst … vorstellen.": ("Ich moechte Ihnen zuerst unser neues Konzept vorstellen und dann die Zahlen zeigen.", "I'd like to introduce our new concept first and then show the numbers."),
        "Kompetenz zeigen": ("Im Gespraech muss man Kompetenz zeigen und ruhig bleiben.", "In the conversation you need to show competence and stay calm."),
        "eine Meinung vertreten": ("In der Diskussion muss jeder seine Meinung vertreten und gute Gruende nennen.", "In the discussion, everyone has to stand by their opinion and give good reasons."),
        "mit etwas anfangen": ("Mit diesem Text kann ich nichts anfangen, kannst du es erklaeren?", "I can't make sense of this text; can you explain it?"),
        "Sieht man genauer hin, erkennt man den Unterschied.": ("Sieht man genauer hin, erkennt man den Unterschied zwischen den beiden Materialien.", "If you look more closely, you see the difference between the two materials."),
        "Und schließlich …": ("Und schliesslich kommen wir zum letzten Punkt auf der Liste.", "And finally, we come to the last item on the list."),
        "wann sie wollen": ("Sie koennen morgen vorbeikommen, wann sie wollen.", "You can drop by tomorrow whenever you like."),
        "Wir haben gehört, dass …": ("Wir haben gehoert, dass es naechste Woche eine Aenderung geben soll.", "We heard that there will be a change next week."),
        "Wir haben ja schon einmal darüber nachgedacht.": ("Wir haben ja schon einmal darueber nachgedacht, aber damals hatten wir keine Zeit.", "We already thought about it once, but back then we had no time."),
        "Wir müssen etwas machen.": ("Wir muessen etwas machen, sonst wird das Problem groesser.", "We need to do something, otherwise the problem will get bigger."),
        "übrig bleiben": ("Nach dem Essen bleibt oft noch etwas Brot uebrig.", "After the meal, there is often some bread left over."),
        "… die speziell für junge Leute gedacht sind": ("Wir suchen Angebote, die speziell fuer junge Leute gedacht sind.", "We are looking for offers that are specifically intended for young people."),
    }

    def __init__(self, requirement_file: Path, output_file: Path):
        self.requirement_file = requirement_file
        self.output_file = output_file
        self.existing_words = set()

    def load_existing_words(self) -> None:
        """Load existing words from output file to avoid duplicates."""
        if self.output_file.exists():
            content = self.output_file.read_text(encoding='utf-8')
            # Extract all word: entries (case-insensitive)
            word_pattern = re.compile(
                r'^word:\s*(.+?)$', re.MULTILINE | re.IGNORECASE)
            for match in word_pattern.finditer(content):
                word = match.group(1).strip().lower()
                self.existing_words.add(word)

    def extract_word_list(self) -> List[str]:
        """Extract word list and reorder according to step 3."""
        content = self.requirement_file.read_text(encoding='utf-8')

        # Prefer inline Word List section if present (legacy format).
        word_list_pattern = re.compile(r'## Word List\s*\n(.*)', re.DOTALL)
        match = word_list_pattern.search(content)

        if match:
            word_list_text = match.group(1)
        else:
            # New workflow stores source list in Inputs/Word List (DE).md.
            word_list_file = self.requirement_file.parent.parent / \
                "Inputs" / "Word List (DE).md"
            if not word_list_file.exists():
                raise ValueError(
                    "Word List section not found in requirement file and Inputs/Word List (DE).md is missing"
                )
            word_list_text = word_list_file.read_text(encoding='utf-8')

        # Extract lines (with or without bullet points)
        lines = []
        for line in word_list_text.split('\n'):
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Remove leading "-" if present
            if line.startswith('-'):
                line = line[1:].strip()

            line = re.sub(r'\s*\([^\)]*\)', '', line).strip()

            # Add non-empty lines
            if line:
                lines.append(line)

        # Step 3: Reorder entries
        # Separate single words from phrases
        single_words = []
        phrases = []

        for word in lines:
            if self.is_single_word(word):
                single_words.append(word)
            else:
                phrases.append(word)

        # Sort each group alphabetically (ignoring articles)
        single_words.sort(key=self.get_sort_key)
        phrases.sort(key=self.get_sort_key)

        # Combine: single words first, then phrases
        return single_words + phrases

    def parse_entry(self, line: str) -> Tuple[str, Optional[str]]:
        """Parse a word entry and extract word and meaning."""
        normalized_line = line.replace("**", "").strip()

        # Split on " - ", " – ", " — ", or " = "
        parts = re.split(r'\s+[-–—=]\s+', normalized_line, maxsplit=1)
        raw_word = parts[0].strip()

        meaning: Optional[str]
        if len(parts) > 1:
            word = re.sub(r'\s*\([^\)]*\)', '', raw_word).strip()
            meaning = parts[1].strip()
        else:
            gloss_match = re.fullmatch(r'(.+?)\s*\(([^)]+)\)\s*', raw_word)
            if gloss_match:
                word = gloss_match.group(1).strip()
                meaning = gloss_match.group(2).strip()
            else:
                word = raw_word
                meaning = None
        return word, meaning

    def get_override(self, word: str) -> Optional[dict]:
        """Return lexical override data for known words."""
        # Try exact match first
        if word in self.ENTRY_OVERRIDES:
            return self.ENTRY_OVERRIDES[word]

        # Try without article
        cleaned = self.strip_leading_article(word)
        if cleaned in self.ENTRY_OVERRIDES:
            return self.ENTRY_OVERRIDES[cleaned]

        return None

    def strip_leading_article(self, word: str) -> str:
        """Remove a leading noun article from a display word."""
        cleaned = word.strip()
        for article in ['der ', 'die ', 'das ']:
            if cleaned.lower().startswith(article):
                return cleaned[len(article):].strip()
        return cleaned

    def build_override_entry(self, word: str, override: dict) -> str:
        """Build a complete block from lexical override data."""
        tags = override["tags"]
        meaning_text = override["meaning"]
        de_1 = override["de_1"]
        en_1 = override["en_1"]
        word_inf = override["word_inf"]
        display_word = self.strip_leading_article(
            word) if tags == "noun" else word

        if tags == "noun":
            return f"""SSTART
%VOCAB (German) ver 3
word: {display_word}
meaning: {meaning_text}
de_1: {de_1}
en_1: {en_1}
word_inf: {word_inf}
noun_gender: {override['noun_gender']}
noun_genetiv: {override['noun_genetiv']}
noun_plural: {override['noun_plural']}
noun_forms: {override['noun_forms']}
Tags: noun
EEND"""

        if tags == "verb":
            return f"""SSTART
%VOCAB (German) ver 3
word: {word}
meaning: {meaning_text}
de_1: {de_1}
en_1: {en_1}
word_inf: {word_inf}
verb_present: {override['verb_present']}
verb_past: {override['verb_past']}
verb_perfect: {override['verb_perfect']}
Tags: verb
EEND"""

        return f"""SSTART
%VOCAB (German) ver 3
word: {word}
meaning: {meaning_text}
de_1: {de_1}
en_1: {en_1}
word_inf: {word_inf}
Tags: {tags}
EEND"""

    def enrich_phrase(self, word: str) -> str:
        """Enrich minimal phrases to be more idiomatic and clear."""
        enrichments = {
            'dabei haben': 'dabei etwas haben',
            'Hausaufgaben machen': 'seine Hausaufgaben machen',
            'ausgeben für': 'Geld ausgeben für etwas',
            'den Geburtstag feiern': 'seinen Geburtstag feiern',
            'mit der Arbeit fertig sein': 'mit der Arbeit völlig fertig sein',
        }
        return enrichments.get(word, word)

    def detect_pos(self, word: str) -> str:
        """Detect part of speech."""
        # Long entries and sentence-like inputs are treated as phrases.
        if any(ch in word for ch in [".", ",", ";", ":", "(", ")", "?", "!", "…"]) or len(word.split()) > 3:
            return 'other'

        parts = word.split()
        if len(parts) > 1 and any(token and token[0].islower() for token in parts[1:]):
            return 'other'

        # Check if it's a noun (capitalized first word, may have article)
        # Remove articles if present
        if parts[0].lower() in ['der', 'die', 'das', 'ein', 'eine']:
            if len(parts) > 1:
                first_word = parts[1]
            else:
                return 'noun'
        else:
            first_word = parts[0]

        # If first word starts with capital and isn't sentence start, it's likely a noun
        if first_word[0].isupper():
            return 'noun'

        # Check for verb infinitives
        if word.endswith('en') or word.endswith('ern') or word.endswith('ln'):
            return 'verb'

        # Check for common verb phrases
        verb_keywords = ['werden', 'sein', 'haben']
        if any(kw in word for kw in verb_keywords):
            return 'verb'

        return 'other'

    def build_meaning_text(self, word: str, meaning: Optional[str]) -> str:
        """Build a clearer meaning line with a natural German gloss first."""
        raw_word = word.strip()
        raw_meaning = (meaning or "").strip()

        override = self.MEANING_OVERRIDES.get(raw_word)
        if override:
            return override

        # Reuse provided English gloss when available.
        if raw_meaning:
            return f"{raw_word} = {raw_meaning}"

        # If no gloss is provided, extract hints from parenthetical notes.
        parenthetical = re.search(r"\(([^\)]+)\)", raw_word)
        if parenthetical:
            english_hint = parenthetical.group(1).strip()
            base = re.sub(r"\s*\([^\)]+\)", "", raw_word).strip()
            return f"{raw_word} = Ausdruck mit erklaerendem Zusatz / {base}: {english_hint}"

        raise ValueError(
            f"Missing LLM-authored meaning for '{raw_word}'. "
            "Add override data instead of using code-generated fallback."
        )

    def build_example_de(self, word: str) -> str:
        """Build a more natural B1-level German example sentence."""
        token = word.strip()
        lower = token.lower()
        override = self.CONTEXT_OVERRIDES.get(token)
        if override:
            return override[0]

        if lower.startswith("nachdem"):
            return token if token.endswith(".") else f"{token}."

        if lower.endswith(("en", "ern", "eln")) and " " not in token:
            return f"Wir müssen {token} heute noch sorgfältig planen."

        if token[0].isupper() and " " not in token:
            raise ValueError(
                f"Missing LLM-authored German example for '{token}'. "
                "Add override data instead of using code-generated fallback."
            )

        if lower.startswith(("der ", "die ", "das ")):
            return f"{token} liegt schon auf dem Tisch."

        raise ValueError(
            f"Missing LLM-authored German example for '{token}'. "
            "Add override data instead of using code-generated fallback."
        )

    def build_example_en(self, word: str) -> str:
        """Build an English translation matching the generated German example."""
        token = word.strip()
        lower = token.lower()
        override = self.CONTEXT_OVERRIDES.get(token)
        if override:
            return override[1]

        if lower.startswith("nachdem"):
            return "After I had completed the first action, I did the second action."

        if lower.endswith(("en", "ern", "eln")) and " " not in token:
            return f"We still need to plan {token} carefully today."

        if token[0].isupper() and " " not in token:
            raise ValueError(
                f"Missing LLM-authored English example for '{token}'. "
                "Add override data instead of using code-generated fallback."
            )

        if lower.startswith(("der ", "die ", "das ")):
            return f"{token} is already lying on the table."

        raise ValueError(
            f"Missing LLM-authored English example for '{token}'. "
            "Add override data instead of using code-generated fallback."
        )

    def validate_entry_quality(self, entry: str) -> list[str]:
        """Return quality issues for one generated block."""
        issues: list[str] = []
        for marker in self.BAD_OUTPUT_MARKERS:
            if marker in entry:
                issues.append(f"contains generic marker: '{marker}'")

        for raw_line in entry.splitlines():
            line = raw_line.strip()
            for pattern in self.BAD_LINE_PATTERNS:
                if pattern.match(line):
                    issues.append(f"contains generic fallback line: '{line}'")
                    break
        return issues

    def print_quality_examples(self) -> None:
        """Print concrete quality guidance with bad vs good examples."""
        print(
            "\n[QUALITY CHECK] Generic outputs detected. Refusing to write bad entries.")
        print("[QUALITY CHECK] Unacceptable example:")
        print("  meaning: haltbar = nuetzlicher Ausdruck fuer Kommunikation / useful expression for communication")
        print("  de_1: Wir verwenden haltbar oft in alltaeglichen Situationen.")
        print("  en_1: We often use haltbar in everyday situations.")
        print("[QUALITY CHECK] Acceptable example:")
        print("  meaning: haltbar = lange nutzbar, nicht schnell kaputt / durable, long-lasting")
        print("  de_1: Die Dose ist sehr haltbar und bleibt mehrere Monate frisch.")
        print("  en_1: The can is very durable and stays fresh for several months.")
        print("[QUALITY CHECK] Please refine lexical mappings before rerunning NW1.\n")

    def guess_noun_forms(self, article: str, noun: str) -> Tuple[str, str, str]:
        """Return improved fallback noun forms without placeholders."""
        noun_clean = noun.strip()
        lower = noun_clean.lower()

        def ending_suffix(base: str, inflected: str) -> str:
            if inflected == base:
                return "-"
            if inflected.startswith(base):
                return f"-{inflected[len(base):]}"
            return "-"

        if article == 'die':
            gen = f"der {noun_clean}"
        else:
            if lower.endswith(("s", "ss", "x", "z", "tz")):
                gen_base = noun_clean
            elif lower.endswith(("nis", "tum")) or len(noun_clean) <= 4:
                gen_base = f"{noun_clean}es"
            else:
                gen_base = f"{noun_clean}s"
            gen = f"des {gen_base}"

        if lower.endswith('e'):
            plural = f"{noun_clean}n"
        elif lower.endswith(("ung", "heit", "keit", "schaft", "ion", "tat", "ik", "ur")):
            plural = f"{noun_clean}en"
        elif lower.endswith('nis'):
            plural = f"{noun_clean}se"
        elif lower.endswith('er') or lower.endswith('el'):
            plural = noun_clean
        elif lower.endswith('ent'):
            plural = f"{noun_clean}en"
        else:
            plural = f"{noun_clean}e"

        gen_suffix = '-'
        if article != 'die':
            gen_base = gen.split(' ', 1)[1]
            gen_suffix = ending_suffix(noun_clean, gen_base)
        plural_suffix = ending_suffix(noun_clean, plural)
        forms = f"{gen_suffix}, {plural_suffix}"

        return gen, plural, forms

    def guess_verb_forms(self, infinitive: str) -> Tuple[str, str, str]:
        """Return improved fallback verb forms without placeholders."""
        cleaned = infinitive.strip()
        cleaned = re.sub(r"\s*\([^\)]*\)", "", cleaned).strip()
        verb = cleaned.split()[0] if cleaned else infinitive.strip().split()[0]

        irregular: dict[str, Tuple[str, str, str]] = {
            'sein': ('ist', 'war', 'ist gewesen'),
            'haben': ('hat', 'hatte', 'hat gehabt'),
            'werden': ('wird', 'wurde', 'ist geworden'),
            'geben': ('gibt', 'gab', 'hat gegeben'),
            'kommen': ('kommt', 'kam', 'ist gekommen'),
            'gehen': ('geht', 'ging', 'ist gegangen'),
            'schreiben': ('schreibt', 'schrieb', 'hat geschrieben'),
            'denken': ('denkt', 'dachte', 'hat gedacht'),
            'streichen': ('streicht', 'strich', 'hat gestrichen'),
            'aufstehen': ('steht auf', 'stand auf', 'ist aufgestanden'),
            'schlafen': ('schlaeft', 'schlief', 'hat geschlafen'),
        }
        if verb in irregular:
            return irregular[verb]

        stem = verb
        if verb.endswith('en') and len(verb) > 3:
            stem = verb[:-2]
        elif verb.endswith('n') and len(verb) > 2:
            stem = verb[:-1]

        if stem.endswith(('t', 'd')):
            present = f"{stem}et"
            past = f"{stem}ete"
        else:
            present = f"{stem}t"
            past = f"{stem}te"

        inseparable_prefixes = ('be', 'emp', 'ent', 'er',
                                'ge', 'miss', 'ver', 'zer')
        if verb.endswith('ieren') or verb.startswith(inseparable_prefixes):
            participle = f"{stem}t"
        else:
            participle = f"ge{stem}t"

        sein_verbs = {'gehen', 'kommen', 'fahren',
                      'fallen', 'steigen', 'aufstehen', 'werden'}
        aux = 'ist' if verb in sein_verbs else 'hat'
        perfect = f"{aux} {participle}"
        return present, past, perfect

    def is_single_word(self, word: str) -> bool:
        """Determine if entry is a single lexical item or a phrase/sentence."""
        # Remove articles for checking
        cleaned = word
        for article in ['der ', 'die ', 'das ', 'ein ', 'eine ']:
            if cleaned.lower().startswith(article):
                cleaned = cleaned[len(article):]
                break

        # Count words (excluding simple modifiers)
        words = cleaned.split()

        # Single word or compound noun
        if len(words) == 1:
            return True

        # Two words could be adjective + noun (single lexical item)
        if len(words) == 2 and words[1][0].isupper():
            return True

        # Otherwise it's a phrase
        return False

    def get_sort_key(self, word: str) -> str:
        """Get sorting key, ignoring articles."""
        # Remove articles for sorting
        word_lower = word.lower()
        for article in ['der ', 'die ', 'das ', 'ein ', 'eine ']:
            if word_lower.startswith(article):
                return word_lower[len(article):]
        return word_lower

    def generate_noun_entry(self, word: str, meaning: Optional[str]) -> str:
        """Generate entry for a noun."""
        # This is a simplified version - in production, you'd want proper linguistic analysis
        # For now, providing templates that need to be filled

        display_word = self.strip_leading_article(word)

        # Extract base noun without article
        parts = word.split()
        if parts[0].lower() in ['der', 'die', 'das']:
            article = parts[0]
            noun = ' '.join(parts[1:])
        else:
            noun = word
            noun_lower = noun.lower()
            if noun_lower.endswith(("ung", "heit", "keit", "schaft", "ion", "tät", "ik", "ur", "ei", "enz", "anz", "itis")):
                article = 'die'
            elif noun_lower.endswith(("chen", "lein")) or noun.endswith("en"):
                article = 'das'
            else:
                article = 'der'

        meaning_text = self.build_meaning_text(word, meaning)
        context_de = self.build_example_de(word)
        context_en = self.build_example_en(word)
        noun_genetiv, noun_plural, noun_forms = self.guess_noun_forms(
            article, noun)

        entry = f"""SSTART
%VOCAB (German) ver 3
    word: {display_word}
meaning: {meaning_text}
de_1: {context_de}
en_1: {context_en}
word_inf: {article} {noun}
noun_gender: {article}
noun_genetiv: {noun_genetiv}
noun_plural: {noun_plural}
noun_forms: {noun_forms}
Tags: noun
EEND"""
        return entry

    def generate_verb_entry(self, word: str, meaning: Optional[str]) -> str:
        """Generate entry for a verb."""
        # Extract infinitive
        parts = word.split()
        infinitive = parts[-1] if len(parts) > 1 else word

        meaning_text = self.build_meaning_text(word, meaning)
        context_de = self.build_example_de(word)
        context_en = self.build_example_en(word)
        verb_present, verb_past, verb_perfect = self.guess_verb_forms(
            infinitive)

        entry = f"""SSTART
%VOCAB (German) ver 3
word: {word}
meaning: {meaning_text}
de_1: {context_de}
en_1: {context_en}
word_inf: {infinitive}
verb_present: {verb_present}
verb_past: {verb_past}
verb_perfect: {verb_perfect}
Tags: verb
EEND"""
        return entry

    def generate_other_entry(self, word: str, meaning: Optional[str], pos: str = 'phrase') -> str:
        """Generate entry for other parts of speech."""
        meaning_text = self.build_meaning_text(word, meaning)
        context_de = self.build_example_de(word)
        context_en = self.build_example_en(word)

        entry = f"""SSTART
%VOCAB (German) ver 3
word: {word}
meaning: {meaning_text}
de_1: {context_de}
en_1: {context_en}
word_inf: {word}
Tags: {pos}
EEND"""
        return entry

    def process(self) -> Tuple[int, int, int]:
        """Process the word list and generate vocabulary entries."""
        # Rebuild output from scratch; only deduplicate within this run.
        self.existing_words = set()

        # Extract word list
        word_list = self.extract_word_list()

        # Process each word
        entries: list[str] = []
        quality_issues: list[str] = []
        unresolved: list[str] = []
        processed = 0
        added = 0
        skipped = 0

        for line in word_list:
            processed += 1

            # Parse entry
            word, meaning = self.parse_entry(line)

            # Enrich phrase if needed
            enriched_word = self.enrich_phrase(word)

            # Check for duplicates
            if enriched_word.lower() in self.existing_words:
                skipped += 1
                continue

            try:
                override = self.get_override(enriched_word)
                if override is not None:
                    entry = self.build_override_entry(enriched_word, override)
                else:
                    # Detect POS
                    pos = self.detect_pos(enriched_word)

                    # Generate entry based on POS
                    if pos == 'noun':
                        entry = self.generate_noun_entry(enriched_word, meaning)
                    elif pos == 'verb':
                        entry = self.generate_verb_entry(enriched_word, meaning)
                    else:
                        entry = self.generate_other_entry(enriched_word, meaning)
            except ValueError as exc:
                msg = str(exc)
                if "Missing LLM-authored" in msg:
                    llm_override = self.try_llm_enrich_override(
                        term=enriched_word,
                        meaning_hint=meaning,
                    )
                    if llm_override is not None:
                        entry = self.build_override_entry(enriched_word, llm_override)
                    else:
                        unresolved.append(enriched_word)
                        self.existing_words.add(enriched_word.lower())
                        continue
                else:
                    raise

            entry_issues = self.validate_entry_quality(entry)
            if entry_issues:
                joined = "; ".join(entry_issues)
                quality_issues.append(f"word '{enriched_word}': {joined}")

            entries.append(entry)
            added += 1
            self.existing_words.add(enriched_word.lower())

        if quality_issues:
            self.print_quality_examples()
            details = "\n".join(f"- {issue}" for issue in quality_issues[:10])
            raise ValueError(
                "Generated entries failed quality checks:\n"
                f"{details}\n"
                "(showing first 10 issues)"
            )

        # Write to file
        self.write_entries(entries, processed, added, skipped, unresolved)

        return processed, added, skipped

    def write_entries(self, entries: List[str], processed: int, added: int, skipped: int, unresolved: list[str]) -> None:
        """Write entries to output file."""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        with self.output_file.open('w', encoding='utf-8', newline='\n') as f:
            f.write("TARGET DECK: TEST\n\n")

            for entry in entries:
                f.write(entry)
                f.write('\n\n')

            # Add summary comment
            summary = f"<!-- processed: {processed} | added: {added} | skipped (duplicates): {skipped} -->\n"
            f.write(summary)
            if unresolved:
                uniq = []
                seen = set()
                for w in unresolved:
                    k = w.casefold()
                    if k in seen:
                        continue
                    seen.add(k)
                    uniq.append(w)
                f.write(f"<!-- UNRESOLVED: {', '.join(uniq)} -->\n")

    def try_llm_enrich_override(self, *, term: str, meaning_hint: Optional[str]) -> Optional[dict]:
        """LLM enrich term into override dict; returns None if disabled/unavailable."""
        if os.environ.get("GNW_ENABLE_NW1_LLM_ENRICH", "1") != "1":
            return None
        try:
            from gnw_pipeline.nw1_llm_enrich import llm_enrich_term
        except Exception:
            return None
        try:
            enriched = llm_enrich_term(term=term, meaning_hint=meaning_hint or None)
        except Exception:
            return None
        data = enriched.model_dump()
        data["tags"] = data.pop("tags")
        return data


def main() -> int:
    """Main entry point."""
    # Define paths
    base_dir = Path(__file__).resolve().parent.parent.parent

    preferred_requirement_file = base_dir / "Requirement" / \
        "Requirement NW1 - German new words prompt.md"
    legacy_requirement_file = base_dir / "Requirement" / \
        "Requirement 1 - German new words prompt.md"

    if preferred_requirement_file.exists():
        requirement_file = preferred_requirement_file
    elif legacy_requirement_file.exists():
        requirement_file = legacy_requirement_file
        print(
            f"⚠️  Path drift detected: using legacy requirement file {legacy_requirement_file}")
    else:
        print(
            f"❌ Requirement file not found. Expected: {preferred_requirement_file}")
        print(f"   Legacy path also missing: {legacy_requirement_file}")
        return 1

    output_file = base_dir / "Outputs" / "01_words.md"

    # Process
    processor = GermanVocabProcessor(requirement_file, output_file)
    try:
        processed, added, skipped = processor.process()
    except Exception as exc:
        print(f"Processing failed: {exc}")
        return 1

    print(f"Processing complete!")
    print(f"  Processed: {processed}")
    print(f"  Added: {added}")
    print(f"  Skipped (duplicates): {skipped}")
    print(f"\nOutput written to: {output_file}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
