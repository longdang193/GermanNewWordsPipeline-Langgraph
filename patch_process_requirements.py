import re

OVERRIDES = {
    "Angelegenheit": {
        "tags": "noun",
        "meaning": "Angelegenheit = Thema, Problem oder Aufgabe, um die man sich kuemmern muss / matter, issue, affair",
        "de_1": "Diese private Angelegenheit moechte ich nicht im Buero besprechen.",
        "en_1": "I don't want to discuss this private matter in the office.",
        "word_inf": "die Angelegenheit",
        "noun_gender": "die",
        "noun_genetiv": "der Angelegenheit",
        "noun_plural": "Angelegenheiten",
        "noun_forms": "-, -n"
    },
    "aufkommen": {
        "tags": "verb",
        "meaning": "aufkommen = entstehen oder ploetzlich in Erscheinung treten / to arise, come up",
        "de_1": "Waehrend des Meetings sind einige neue Fragen aufgekommen.",
        "en_1": "Some new questions came up during the meeting.",
        "word_inf": "aufkommen",
        "verb_present": "kommt auf",
        "verb_past": "kam auf",
        "verb_perfect": "ist aufgekommen"
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
        "noun_forms": "-s, ⸚"
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
        "noun_forms": "-, -n"
    },
    "diejenigen": {
        "tags": "pronoun",
        "meaning": "diejenigen = genau die genannten Personen oder Dinge / those (specific ones)",
        "de_1": "Diejenigen, die zu spaet kommen, muessen draussen warten.",
        "en_1": "Those who arrive late have to wait outside.",
        "word_inf": "diejenigen"
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
        "noun_forms": "-s, -"
    },
    "festgestellt": {
        "tags": "verb",
        "meaning": "feststellen = etwas erkennen, bemerken oder bestaetigen / to note, find, establish",
        "de_1": "Der Arzt hat festgestellt, dass ich voellig gesund bin.",
        "en_1": "The doctor has confirmed that I am completely healthy.",
        "word_inf": "feststellen",
        "verb_present": "stellt fest",
        "verb_past": "stellte fest",
        "verb_perfect": "hat festgestellt"
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
        "noun_forms": "-s, -"
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
        "noun_forms": "-s, -"
    },
    "hergekommen": {
        "tags": "verb",
        "meaning": "herkommen = an den Ort kommen, wo der Sprecher ist / to come here",
        "de_1": "Ich weiss nicht, wie dieses kaputte Fahrrad hergekommen ist.",
        "en_1": "I don't know how this broken bicycle got here.",
        "word_inf": "herkommen",
        "verb_present": "kommt her",
        "verb_past": "kam her",
        "verb_perfect": "ist hergekommen"
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
        "noun_forms": "-, -en"
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
        "noun_forms": "-es, ⸚e"
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
        "noun_forms": "-s, -"
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
        "noun_forms": "-, -n"
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
        "noun_forms": "-s, -"
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
        "noun_forms": "-, -n"
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
        "noun_forms": "-s, -"
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
        "noun_forms": "-es, ⸚e"
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
        "noun_forms": "-s, -"
    },
    "unbeschreiblich": {
        "tags": "adj",
        "meaning": "unbeschreiblich = so schoen, so stark oder so besonders, dass man es nicht in Worte fassen kann / indescribable",
        "de_1": "Die Aussicht oben vom Berg war einfach unbeschreiblich schoen.",
        "en_1": "The view from the top of the mountain was simply indescribably beautiful.",
        "word_inf": "unbeschreiblich"
    },
    "vermitteln": {
        "tags": "verb",
        "meaning": "vermitteln = einen Kontakt herstellen, einen Kompromiss finden oder etwas beibringen / to convey, mediate, arrange",
        "de_1": "Die Lehrerin moechte den Schuelern Freude am Lesen vermitteln.",
        "en_1": "The teacher wants to convey the joy of reading to the students.",
        "word_inf": "vermitteln",
        "verb_present": "vermittelt",
        "verb_past": "vermittelte",
        "verb_perfect": "hat vermittelt"
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
        "noun_forms": "-, -en"
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
        "noun_forms": "-es, ⸚e"
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
        "noun_forms": "-s, -e"
    },
    '"wer möchte, hat auch…"': {
        "tags": "phrase",
        "meaning": "wer möchte, hat auch... = wer ein bestimmtes Ziel anstrebt, findet oft auch eine Loesung oder die Mittel dazu / where there's a will, there's a way",
        "de_1": "Er ist sehr zielstrebig und glaubt immer: Wer moechte, hat auch eine Moeglichkeit.",
        "en_1": "He is very goal-oriented and always believes: Where there's a will, there's a way.",
        "word_inf": '"wer möchte, hat auch…"'
    },
    "abbrechen": {
        "tags": "verb",
        "meaning": "abbrechen = etwas unerwartet frueh beenden oder stoppen / to break off, cancel, abort",
        "de_1": "Wegen des starken Sturms mussten wir unsere Wanderung abbrechen.",
        "en_1": "Because of the severe storm, we had to abort our hike.",
        "word_inf": "abbrechen",
        "verb_present": "bricht ab",
        "verb_past": "brach ab",
        "verb_perfect": "hat abgebrochen"
    },
    "Am Samstag anfangs Regen": {
        "tags": "phrase",
        "meaning": "Am Samstag anfangs Regen = Typische und verkuerzte Wetterprognose: Am Samstag gibt es am Anfang Regen / Initally rain on Saturday",
        "de_1": "Der Wetterbericht meldet: Am Samstag anfangs Regen, spaeter heiter.",
        "en_1": "The weather report says: Initially rain on Saturday, later clear.",
        "word_inf": "Am Samstag anfangs Regen"
    },
    "Aufenthalt planen": {
        "tags": "phrase",
        "meaning": "Aufenthalt planen = organisieren, wo und wie man seine Zeit waehrend einer Reise verbringt / to plan a stay",
        "de_1": "Wenn wir nach Paris reisen, muessen wir den Aufenthalt planen.",
        "en_1": "When we travel to Paris, we have to plan the stay.",
        "word_inf": "Aufenthalt planen"
    },
    "ausgerechnet": {
        "tags": "adv",
        "meaning": "ausgerechnet = ein unerwarteter, oft aergerlicher Zufall (genau das, genau jetzt) / of all things, ironicaly, precisely",
        "de_1": "Es regnet ausgerechnet heute, wo wir draussen feiern wollten.",
        "en_1": "It's raining today of all days, when we wanted to celebrate outside.",
        "word_inf": "ausgerechnet"
    },
    "bei der Wahl": {
        "tags": "phrase",
        "meaning": "bei der Wahl = waehrend eines Auswahlverfahrens oder einer politischen Abstimmung / during the election, at the choice",
        "de_1": "Bei der Wahl am Sonntag lag die Beteiligung bei ueber siebzig Prozent.",
        "en_1": "At the election on Sunday, turnout was over seventy percent.",
        "word_inf": "bei der Wahl"
    },
    "beibehalten": {
        "tags": "verb",
        "meaning": "beibehalten = etwas nicht aendern, weiter so machen wie bisher / to maintain, keep, retain",
        "de_1": "Trotz der Kritik moechte die Firma ihren bisherigen Kurs beibehalten.",
        "en_1": "Despite the criticism, the company wants to maintain its current course.",
        "word_inf": "beibehalten",
        "verb_present": "behält bei",
        "verb_past": "behielt bei",
        "verb_perfect": "hat beibehalten"
    },
    "Dimensionen annehmen": {
        "tags": "phrase",
        "meaning": "Dimensionen annehmen = eine bestimmte (oft unerwartete) Groesse oder ein Ausmass erreichen / to take on dimensions",
        "de_1": "Das Problem koennte sonst voellig neue Dimensionen annehmen.",
        "en_1": "The problem could otherwise take on completely new dimensions.",
        "word_inf": "Dimensionen annehmen"
    },
    "fünfköpfig": {
        "tags": "adj",
        "meaning": "fuenfkoepfig = aus fuenf Personen bestehend / five-member, five-strong",
        "de_1": "Die fuenfkoepfige Familie zog am Wochenende in ein neues Haus.",
        "en_1": "The five-member family moved into a new house over the weekend.",
        "word_inf": "fünfköpfig"
    },
    "Geben Sie sofort Ihre Bestellung auf": {
        "tags": "phrase",
        "meaning": "Geben Sie sofort Ihre Bestellung auf = Aufforderung, schnell etwas zu kaufen oder zu ordern / Place your order immediately",
        "de_1": "Geben Sie sofort Ihre Bestellung auf, solange der Artikel noch auf Lager ist.",
        "en_1": "Place your order immediately while the item is still in stock.",
        "word_inf": "Geben Sie sofort Ihre Bestellung auf"
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
        "noun_forms": "-s, ⸚e"
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
        "noun_forms": "-s, -"
    },
    "heiter": {
        "tags": "adj",
        "meaning": "heiter = sonnig und freundlich, ohne dichte Wolken (Wetter) / fair, clear, bright",
        "de_1": "Morgen wird das Wetter ueberwiegend heiter und trocken.",
        "en_1": "Tomorrow the weather will be mostly fair and dry.",
        "word_inf": "heiter"
    },
    "herumtelefonieren": {
        "tags": "verb",
        "meaning": "herumtelefonieren = viele Personen nacheinander anrufen, um etwas herauszufinden / to phone around",
        "de_1": "Um einen Handwerker zu finden, musste ich den ganzen Vormittag herumtelefonieren.",
        "en_1": "To find a craftsman, I had to phone around all morning.",
        "word_inf": "herumtelefonieren",
        "verb_present": "telefoniert herum",
        "verb_past": "telefonierte herum",
        "verb_perfect": "hat herumtelefoniert"
    },
    "immer schwieriger": {
        "tags": "phrase",
        "meaning": "immer schwieriger = mit der Zeit zusaetzlich herausfordernd / increasingly difficult",
        "de_1": "Es wird immer schwieriger, in dieser Stadt eine bezahlbare Wohnung zu finden.",
        "en_1": "It is becoming increasingly difficult to find an affordable apartment in this city.",
        "word_inf": "immer schwieriger"
    },
    "in ein Flugzeug zwängen": {
        "tags": "phrase",
        "meaning": "in ein Flugzeug zwaengen = sich mit wenig Platz in die Kabine eines Flugzeugs druecken / to squeeze into an airplane",
        "de_1": "Waehrend der Ferienzeit muessen sich viele Menschen in ein Flugzeug zwaengen.",
        "en_1": "During holiday season, many people have to squeeze into a plane.",
        "word_inf": "in ein Flugzeug zwängen"
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
        "noun_forms": "-, -n"
    },
    "niederschlagsfrei": {
        "tags": "adj",
        "meaning": "niederschlagsfrei = ohne Regen oder Schnee / precipitation-free, dry",
        "de_1": "Am Wochenende bleibt es voraussichtlich niederschlagsfrei.",
        "en_1": "The weekend is expected to remain precipitation-free.",
        "word_inf": "niederschlagsfrei"
    },
    "sich beschäftigen mit": {
        "tags": "phrase",
        "meaning": "sich beschaeftigen mit = sich einem Thema oder einer Aufgabe intensiv widmen / to deal with, to occupy oneself with",
        "de_1": "In meiner Freizeit beschaeftige ich mich gern mit Fotografie.",
        "en_1": "In my free time, I enjoy occupying myself with photography.",
        "word_inf": "sich beschäftigen mit"
    },
    "sich drehen um": {
        "tags": "phrase",
        "meaning": "sich drehen um = im Mittelpunkt stehen, das Hauptthema sein / to revolve around, to be about",
        "de_1": "In diesem Film dreht sich alles um die Liebe zweier Menschen.",
        "en_1": "Everything in this movie revolves around the love of two people.",
        "word_inf": "sich drehen um"
    },
    "sich herausstellen": {
        "tags": "verb",
        "meaning": "sich herausstellen = nach einer Weile klar oder deutlich werden / to turn out, become apparent",
        "de_1": "Spaeter stellte sich heraus, dass der Fehler gar nicht bei mir lag.",
        "en_1": "Later it turned out that the mistake wasn't mine at all.",
        "word_inf": "herausstellen",
        "verb_present": "stellt sich heraus",
        "verb_past": "stellte sich heraus",
        "verb_perfect": "hat sich herausgestellt"
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
        "noun_forms": "-, -n"
    },
    "so auf die Nerven, dass ich wegfahren würde": {
        "tags": "phrase",
        "meaning": "so auf die Nerven gehen = extrem belaestigen und stoeren, dass man fluechten moechte / gets on my nerves so much that I'd drive away",
        "de_1": "Der laute Baulaerm auf der Strasse ging ihm so auf die Nerven, dass er am liebsten weggefahren waere.",
        "en_1": "The loud construction noise on the street got on his nerves so much that he preferred to drive away.",
        "word_inf": "so auf die Nerven gehen"
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
        "noun_forms": "-, -"
    },
    "Um wieviel Uhr ist die Teambesprechung?": {
        "tags": "phrase",
        "meaning": "Um wie viel Uhr ...? = Frage nach der genauen Zeit eines Ereignisses / At what time is the team meeting?",
        "de_1": "Entschuldigung, um wie viel Uhr ist heute die Teambesprechung angesetzt?",
        "en_1": "Excuse me, at what time is the team meeting scheduled today?",
        "word_inf": "Um wie viel Uhr...?"
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
        "noun_forms": "-s, -e"
    },
    "von weit her": {
        "tags": "phrase",
        "meaning": "von weit her = aus grosser persoenlicher oder raeumlicher Distanz / from far away",
        "de_1": "Viele Gaeste auf seiner Hochzeit kamen von weit her angereist.",
        "en_1": "Many guests at his wedding traveled from far away.",
        "word_inf": "von weit her"
    },
    "Wann kommt Frau Dr. Amos?": {
        "tags": "phrase",
        "meaning": "Wann kommt ...? = Frage nach dem Ankunftszeitpunkt / When is Mrs. Dr. Amos coming?",
        "de_1": "Ich habe einen Termin um zwoelf Uhr. Wann kommt Frau Dr. Amos?",
        "en_1": "I have an appointment at twelve o'clock. When is Dr. Amos coming?",
        "word_inf": "Wann kommt...?"
    },
    "wat hier los ist in Berlin": {
        "tags": "phrase",
        "meaning": "wat hier los ist (Berlinerisch) = was hier alles passiert oder wie voll/geschaeftig es ist (umgangssprachlich) / what is going on here in Berlin",
        "de_1": "Manchmal kann man kaum glauben, wat hier los ist in Berlin an einem Samstagabend.",
        "en_1": "Sometimes you can hardly believe what is going on here in Berlin on a Saturday night.",
        "word_inf": "was hier los ist"
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
        "tags": "noun"
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
        "word_inf": "berichten"
    },
    "„Es wird + Adjektiv“": {
        "tags": "phrase",
        "meaning": "Es wird + Adjektiv = Ausdruck, dass sich ein Zustand entwickelt oder aendert / It becomes / It gets + adjective",
        "de_1": "Nimm eine Jacke mit, am Abend wird es schnell sehr kalt.",
        "en_1": "Take a jacket with you, it gets very cold quickly in the evening.",
        "word_inf": "es wird ..."
    }
}

with open(r'c:\Users\HOANG PHI LONG DANG\OneDrive\OBSIDIAN 24 09 01\24 09 01 obsidian-go-obsidian_v.0.3.1\German_New_Words\Tools\scripts\process_requirement1.py', 'r', encoding='utf-8') as f:
    script = f.read()

import re

start_str = "    ENTRY_OVERRIDES = {\n"
start_idx = script.find(start_str)
end_str = "    BAD_OUTPUT_MARKERS = (\n"
end_idx = script.find(end_str)

if start_idx != -1 and end_idx != -1:
    end_of_dict_idx = script.rfind("    }", start_idx, end_idx) + 5
    
    new_overrides = ""
    for k, v in OVERRIDES.items():
        new_overrides += f"        \"{k}\": {{\n"
        for field_key, field_val in v.items():
            new_overrides += f"            \"{field_key}\": \"{field_val}\",\n"
        new_overrides += "        },\n"
        
    with open(r'c:\Users\HOANG PHI LONG DANG\OneDrive\OBSIDIAN 24 09 01\24 09 01 obsidian-go-obsidian_v.0.3.1\German_New_Words\Tools\scripts\process_requirement1.py', 'w', encoding='utf-8') as f:
        f.write(script[:end_of_dict_idx] + "\n" + new_overrides + script[end_of_dict_idx:])

    print("Success: Updated ENTRY_OVERRIDES in process_requirement1.py")
else:
    print("Could not find boundaries for ENTRY_OVERRIDES")
