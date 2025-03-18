# ==============================================================================
# interfacciaConUtente.py
#
# Questo modulo gestisce l'interazione con l'utente: richiede input per
# i dati meteo (sia online che manuale) e per le preferenze dell'attività.
#
# Le variabili globali memorizzano i dati inseriti, che vengono poi usati
# per effettuare inferenze tramite le reti bayesiane.
# ==============================================================================

import requests
from owlready2 import *
from geopy.geocoders import Nominatim
from datetime import datetime, timezone, timedelta

# --------------------------------------------------------------------------
# Dichiarazione delle variabili globali
# --------------------------------------------------------------------------
nome_citta = ""
temp = -1000          # Temperatura (inizialmente un valore placeholder)
vento = ""            # Velocità del vento (inserita dall'utente)
indoor = ""           # Flag per indicare se l'utente ha accesso a strutture indoor
tipo = ""             # Tipo di condizione meteo ("caldo", "freddo", "normale")
meteo = ""            # Condizioni meteo testuali (es. "nuvoloso", "scoperto", "rovesci")
fascia = ""           # Fascia oraria ("mattina" o "sera")
rete = ""             # Scelta della rete bayesiana da utilizzare
reteAggiornata = None # Rete bayesiana aggiornata dopo apprendimento
pioggia = 0           # Intensità della pioggia (0-4)
DEBUG = False          # Flag per abilitare/disabilitare alcuni output di debug

# ==============================================================================
# Funzione: chiedi_online()
# Chiede all'utente se desidera cercare i dati meteo online o utilizzare dati offline.
# ==============================================================================
def chiedi_online():
    while True:
        scelta = input("Vuoi effettuare la ricerca online con il nome della tua città? (si/no) ")
        if scelta.lower() == "si":
            return "trovareInformazioniOnline"
        elif scelta.lower() == "no":
            return "trovareInformazioniOffline"
        else:
            print("Hai effettuato una scelta sbagliata!")

# ==============================================================================
# Funzione: risultati_previsioni()
# Ottiene le previsioni meteo online utilizzando il servizio di geocoding e l'API di OpenWeatherMap.
# ==============================================================================
def risultati_previsioni():
    global nome_citta
    nome_citta = input("Dove ti trovi? ")
    try:
        # Usa un user_agent personalizzato e un timeout per una ricerca affidabile
        geolocator = Nominatim(user_agent="ProgettoAcarrisi", timeout=10)
        address = geolocator.geocode(nome_citta)
    except Exception as e:
        print("Errore durante la ricerca della città:", e)
        return "trovareInformazioniOffline"
    if address is None:
        return "trovareInformazioniOffline"
    # Estrae le coordinate dalla risposta del geolocator
    lat = address.latitude
    lon = address.longitude
    api_key = "2fbee3e1111e3bbc6482a8263d59d1e5" # API Key di openerathermap.org
    try:
        informazioni = ricerca_previsioni_online(lat, lon, api_key)
    except Exception as e:
        print("Errore nel recupero dei dati meteo online:", e)
        return "trovareInformazioniOffline"
    return informazioni

# ==============================================================================
# Funzione: ricerca_previsioni_online()
# Costruisce l'URL per l'API "/weather" e processa la risposta per
# estrarre le informazioni meteo essenziali.
# ==============================================================================
def ricerca_previsioni_online(lat, lon, api_key):
    global temp, vento, tipo, fascia, pioggia
    # Costruisce l'URL dell'API usando le coordinate e l'API key
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"

    if DEBUG:
        print("DEBUG: URL chiamato ->", url)
    response = requests.get(url)
    if DEBUG:
        print("DEBUG: Response status code ->", response.status_code)
    if response.status_code != 200:
        raise Exception("Errore HTTP: " + str(response.status_code))
    data = response.json()
    if DEBUG:
        print("DEBUG: JSON response ->", data)
    # Controlla la presenza dei dati essenziali
    if 'main' not in data or 'weather' not in data or 'temp' not in data['main']:
        raise Exception("Dati meteo non disponibili per la posizione richiesta")

    # Estrae l'orario (usa UTC; se necessario, adattare con data['timezone'])
    hour = datetime.fromtimestamp(data['dt'], timezone.utc).strftime('%H')

    # Estrae e mappa le condizioni meteo (da inglese a etichette italiane)
    raw_meteo = data['weather'][0]['main']
    if raw_meteo.lower() == "clouds":
        meteo_online = "nuvoloso"
    elif raw_meteo.lower() == "clear":
        meteo_online = "scoperto"
    else:
        meteo_online = "rovesci"    # Mappa tutte le altre condizioni a "rovesci"

    informazioni = [
        hour,
        meteo_online,
        data['main']['temp'],
        ""
    ]
    if DEBUG:
        print("DEBUG: Informazioni grezze estratte ->", informazioni)

    # Determina la fascia oraria
    if int(informazioni[0]) > 14 or int(informazioni[0]) < 3:
        informazioni[0] = "sera"
        fascia = "sera"
    else:
        informazioni[0] = "mattina"
        fascia = "mattina"

    temp = informazioni[2]
    # Determina il tipo in base alla temperatura, con forzatura del ramo "freddo"
    if int(temp) > 26:
        tipo = "caldo"
        informazioni[2] = "caldo"
        converti_temperatura_caldo()
    elif int(temp) >= 15:
        informazioni[2] = "normale"
        # Se le condizioni sono critiche (meteo "rovesci" o pioggia intensa), forza il ramo "freddo"
        if meteo_online == "rovesci" or int(pioggia) >= 3:
            tipo = "freddo"
            informazioni[2] = "freddo"
            converti_temperatura_freddo()
        else:
            tipo = "normale"
    else:
        tipo = "freddo"
        informazioni[2] = "freddo"
        converti_temperatura_freddo()

    # Converte la velocità del vento (da m/s a km/h) e la normalizza
    vento = data['wind']['speed'] * 3.6
    converti_vento()

    print("")
    print("---------------------- DATI METEO RECUPERATI -----------------------")
    print("Città ->", nome_citta)
    print("Fascia oraria ->", fascia)
    print("Temperatura (grezza) ->", informazioni[2])
    print("Vento (km/h) ->", vento)
    print("Pioggia ->", pioggia)
    print("--------------------------------------------------------------------")
    print("")

    # Valuta le condizioni critiche per attivare un'allerta meteo
    controlla_situazione_meteorologica(informazioni)
    return informazioni

# ==============================================================================
# Funzione: controlla_situazione_meteorologica()
# Imposta il flag di allerta meteo (nella posizione 3 delle informazioni)
# in base a condizioni critiche: meteo "rovesci" o intensità di pioggia elevata.
# ==============================================================================
def controlla_situazione_meteorologica(informazioni):
    global tipo, meteo, pioggia
    if meteo.lower() == "rovesci" or int(pioggia) >= 3:
        informazioni[3] = "allerta_meteo"
    elif tipo in ["caldo", "freddo"]:
        informazioni[3] = "allerta_meteo"
    else:
        informazioni[3] = ""        # Nessuna allerta

# ==============================================================================
# Funzione: chiedi_inserimento_manuale()
# Chiede all'utente se vuole inserire manualmente i dati in caso di città non trovata.
# ==============================================================================
def chiedi_inserimento_manuale():
    while True:
        scelta = input("Città non trovata, vuoi inserire manualmente i dati? (si/no) ")
        if scelta.lower() in ["si", "no"]:
            return scelta.lower()
        else:
            print("Hai inserito una scelta sbagliata!")

# ==============================================================================
# Funzione: chiedi_fascia_oraria()
# Richiede all'utente di scegliere la fascia oraria (mattina/sera).
# ==============================================================================
def chiedi_fascia_oraria():
    global fascia
    while True:
        fascia_oraria = input("Scegli la fascia oraria (mattina/sera): ")
        if fascia_oraria.lower() in ["mattina", "sera"]:
            fascia = fascia_oraria.lower()
            return fascia_oraria.lower()
        else:
            print("Hai inserito una scelta sbagliata!")

# ==============================================================================
# Funzione: chiedi_meteo()
# Richiede all'utente di scegliere le condizioni meteo attuali.
# ==============================================================================
def chiedi_meteo():
    global meteo
    while True:
        meteo_input = input("Scegli le condizioni meteo attuali (nuvoloso, scoperto, rovesci): ")
        if meteo_input.lower() in ["nuvoloso", "scoperto", "rovesci"]:
            meteo = meteo_input.lower()  # Salva il valore in variabile globale
            return meteo
        else:
            print("Hai inserito una scelta sbagliata!")

# ==============================================================================
# Funzione: chiedi_pioggia()
# Richiede all'utente l'intensità della pioggia e assegna il valore globale 'pioggia'.
# ==============================================================================
def chiedi_pioggia():
    global pioggia
    while True:
        risposta = input("Inserisci l'intensità della pioggia (assenza, leggera, moderata, intensa, molto intensa) ")
        if risposta.lower() == "assenza":
            pioggia = 0
            return 0
        elif risposta.lower() == "leggera":
            pioggia = 1
            return 1
        elif risposta.lower() == "moderata":
            pioggia = 2
            return 2
        elif risposta.lower() == "intensa":
            pioggia = 3
            return 3
        elif risposta.lower() == "molto intensa":
            pioggia = 4
            return 4
        else:
            print("Risposta errata, riprova!")

# ==============================================================================
# Funzione: chiedi_vento()
# Richiede all'utente una valutazione qualitativa della forza del vento e la converte in un indice (0-4).
# ==============================================================================
def chiedi_vento():
    global vento
    while True:
        vento_input = input("Inserisci quanto forte ti sembra il vento (non presente, moderato, teso, fresco, forte, molto forte): ")
        if vento_input.lower() in ["non presente", "moderato"]:
            vento = 0
            return 0
        elif vento_input.lower() == "teso":
            vento = 1
            return 1
        elif vento_input.lower() == "fresco":
            vento = 2
            return 2
        elif vento_input.lower() == "forte":
            vento = 3
            return 3
        elif vento_input.lower() == "molto forte":
            vento = 4
            return 4
        else:
            print("Hai inserito una risposta errata!")

# ==============================================================================
# Funzione: chiedi_temperatura()
# Richiede all'utente la temperatura in gradi Celsius e determina il ramo (caldo/freddo/normale)
# in base al valore inserito, forzando il ramo "freddo" in presenza di condizioni critiche.
# ==============================================================================
def chiedi_temperatura():
    global temp, tipo, fascia, meteo, pioggia
    while True:
        temperatura = input("Inserisci la temperatura in gradi Celsius: ")
        try:
            float(temperatura)
            # Se la temperatura è superiore a 26, il ramo è "caldo"
            if int(temperatura) > 26:
                tipo = "caldo"
                temp = int(temperatura)
                converti_temperatura_caldo()
                return "caldo"
            # Se la temperatura è inferiore a 15, il ramo è "freddo"
            elif int(temperatura) < 15:
                tipo = "freddo"
                temp = int(temperatura)
                converti_temperatura_freddo()
                return "freddo"
            else:
                # Se la temperatura è "normale" ma le condizioni sono critiche,
                # forza il ramo "freddo"
                if meteo.lower() == "rovesci" or int(pioggia) >= 3:
                    tipo = "freddo"
                    temp = int(temperatura)
                    converti_temperatura_freddo()
                    return "freddo"
                else:
                    tipo = "normale"
                    temp = int(temperatura)
                    return "normale"
        except ValueError:
            print("Hai inserito un valore non valido!")

# ==============================================================================
# Funzione: chiedi_attivita()
# Richiede all'utente il tipo di attività preferita e assegna il valore globale 'attivita'.
# ==============================================================================
def chiedi_attivita():
    global attivita
    while True:
        attivita_input = input("Quale tipo di attività preferisci oggi? (sportiva/culturale/ricreativa) ")
        if attivita_input.lower() in ["sportiva", "culturale", "ricreativa"]:
            attivita = attivita_input.lower()
            return attivita
        else:
            print("Hai inserito una scelta non valida!")

# ==============================================================================
# Funzione: chiedi_indoor()
# Richiede all'utente se ha accesso a strutture indoor e assegna il valore globale 'indoor'.
# ==============================================================================
def chiedi_indoor():
    global indoor
    while True:
        accesso = input("Hai accesso a una palestra o a una struttura indoor? (si/no) ")
        if accesso.lower() in ["si", "no"]:
            indoor = accesso.lower()
            return accesso.lower()
        else:
            print("Hai inserito una risposta errata!")

# ==============================================================================
# Funzione: stampa_risultato()
# Costruisce la chiave per la ricerca nell'ontologia in base alle scelte dell'utente e stampa le raccomandazioni.
# Se la chiave non viene trovata, tenta alternative (fallback) modificando meteo o temperatura.
# ==============================================================================
def stampa_risultato(attivita, accesso, fascia_oraria, temperatura, meteo):
    # Costruisce il percorso dell'ontologia
    path = os.path.dirname(os.path.abspath("./src/Ontologia/ontologiaAttivita.owl"))
    path = path.replace("\\", "/")
    path = "file://" + path + "/ontologiaAttivita.owl"
    onto = get_ontology(path).load()

    # Determina se l'utente ha scelto indoor o outdoor
    luogo = "indoor" if accesso.strip().lower() == "si" else "outdoor"
    fallback_used = False
    if luogo == "outdoor" and meteo.strip().lower() == "rovesci":
        print("Avviso: Nessuna attività specifica trovata per condizioni outdoor con rovesci. Verranno fornite raccomandazioni generali.")
        luogo_fallback = "indoor"
        meteo_fallback = "nuvoloso"
        fallback_used = True
    else:
        luogo_fallback = luogo
        meteo_fallback = meteo.strip().lower()

    # Costruisce la chiave per la ricerca nell'ontologia
    chiave = ("attivita_"
              + attivita.strip().lower() + "_"
              + luogo_fallback + "_"
              + fascia_oraria.strip().lower() + "_"
              + temperatura.strip().lower() + "_"
              + meteo_fallback)
    # Cerca l'individuo corrispondente nell'ontologia
    individuo = None
    for ind in onto.individuals():
        if ind.name.strip().lower() == chiave:
            individuo = ind
            break
    if individuo is None:
        # Fallback: tenta alternative modificando meteo e temperatura
        if luogo_fallback == "indoor":
            # 1. Prova a modificare il meteo (es. da 'rovesci' a 'nuvoloso')
            alt_meteo = meteo_fallback
            alt_temp = temperatura.strip().lower()
            if alt_meteo == "rovesci":
                alt_meteo = "nuvoloso"
                chiave_alternativa = "attivita_" + attivita.strip().lower() + "_" + luogo_fallback + "_" + fascia_oraria.strip().lower() + "_" + alt_temp + "_" + alt_meteo
                for ind in onto.individuals():
                    if ind.name.strip().lower() == chiave_alternativa:
                        individuo = ind
                        break
            # 2. Se ancora non trovato, prova a modificare la temperatura (es. da 'freddo' a 'normale')
            if individuo is None:
                if alt_temp == "freddo":
                    alt_temp = "normale"
                elif alt_temp == "caldo":
                    alt_temp = "normale"
                chiave_alternativa = "attivita_" + attivita.strip().lower() + "_" + luogo_fallback + "_" + fascia_oraria.strip().lower() + "_" + alt_temp + "_" + alt_meteo
                for ind in onto.individuals():
                    if ind.name.strip().lower() == chiave_alternativa:
                        individuo = ind
                        break
            if individuo is None:
                print("--------------------------------- !!! AVVISO !!! --------------------------------")
                print("Non sono state trovate alternative.")
                return
        else:
            print("Non è stato possibile trovare l'individuo per la chiave:", chiave)
            return
    # Stampa le proprietà dell'individuo trovato
    print("\n----------------------- ATTIVITÀ CONSIGLIATE -----------------------")
    if hasattr(individuo, "haAttivitaPrincipale") and len(individuo.haAttivitaPrincipale) > 0:
        print("PRINCIPALE:\t" + individuo.haAttivitaPrincipale[0].strip())
    if hasattr(individuo, "haAttivitaSecondaria") and len(individuo.haAttivitaSecondaria) > 0:
        print("SECONDARIA:\t" + individuo.haAttivitaSecondaria[0].strip() + "\n")
    print("--------------------- ATTIVITÀ NON CONSIGLIATE ---------------------")
    if hasattr(individuo, "haAttivitaAlternativa") and len(individuo.haAttivitaAlternativa) > 0:
        print(individuo.haAttivitaAlternativa[0].strip() + "\n")
    print("---------------------- ACCESSORI CONSIGLIATI -----------------------")
    if hasattr(individuo, "haAccessorioConsigliato") and len(individuo.haAccessorioConsigliato) > 0:
        print(individuo.haAccessorioConsigliato[0].strip())

# ==============================================================================
# Funzione: stampa_allerta_meteo()
# Valuta le condizioni meteo e, tramite la rete bayesiana, determina se c'è un'allerta.
# Gestisce separatamente i casi "freddo" e "caldo" includendo anche le variabili Vento e Pioggia.
# ==============================================================================
def stampa_allerta_meteo():
    global vento, temp, fascia, rete, tipo, indoor, meteo, reteAggiornata
    # --------------------------------------------------------------------------
    # Caso "freddo"
    # --------------------------------------------------------------------------
    if tipo == "freddo":
        # Determina il luogo (indoor/outdoor)
        luogo = "indoor" if indoor.strip().lower() == "si" else "outdoor"
        import pandas as pd
        # Carica il dataset del ramo freddo (il dataset attuale non ha "Pioggia" per il ramo freddo)
        dataset = pd.read_csv("src/ClassiSupporto/dataset_consulente_freddo_ottimale.csv")
        dataset = dataset[['Vento', 'Freddo', 'Consiglio']]
        # Prepara l'evidenza includendo anche la pioggia (per coerenza, sebbene il dataset non la usi)
        evidenza = {'Vento': int(vento), 'Freddo': int(temp), 'Pioggia': int(pioggia)}
        if DEBUG:
            print("Evidenza per inferenza (freddo):", evidenza)
        from src.ReteBayesiana import retiBayesiane as rb
        rete_bayesiana_temp = rb.BayesianaInsoddisfazione()
        risultato_default = rb.ottieni_risultato_query(rete_bayesiana_temp.inferenza(evidenza))
        p_default = risultato_default["p"]
        probabilita_rischio_default = (p_default.iloc[3] + p_default.iloc[4]) * 100
        if probabilita_rischio_default < 35:
            print("\n==========================  BOX ALLERTE  ===========================")
            print("--------------- !!! Nessun'allerta meteo rilevata !!! --------------")
            print("====================================================================")
            return False
        else:
            print("\n==========================  BOX ALLERTE  ===========================")
            print("------------------- !!! Allerta meteo rilevata !!! -----------------")
            print("====================================================================")
            reteAggiornata = rete_bayesiana_temp
            return True

    # --------------------------------------------------------------------------
    # Caso "caldo"
    # --------------------------------------------------------------------------
    elif tipo == "caldo":
        from src.ReteBayesiana import retiBayesiane as rb
        rete_bayesiana_temp = rb.BayesianaTempoLibero()
        import pandas as pd
        dataset = pd.read_csv("src/ClassiSupporto/dataset_consulente_caldo_ottimale.csv")
        dataset = dataset[['Attività', 'Vento', 'Pioggia', 'Consiglio']]
        # Qui, per il ramo caldo, usiamo le variabili Attività, Vento e Pioggia
        evidenza = {'Attività': int(temp), 'Vento': int(vento), 'Pioggia': int(pioggia)}
        if DEBUG:
            print("Evidenza per inferenza (caldo):", evidenza)
        risultato_default = rb.ottieni_risultato_query(rete_bayesiana_temp.inferenza(evidenza))
        p_default = risultato_default["p"]
        probabilita_rischio_default = (p_default.iloc[3] + p_default.iloc[4]) * 100
        if probabilita_rischio_default < 35:
            print("Condizioni ottimali per l'attività proposta. Nessun'allerta meteo rilevata.")
            return False
        else:
            print("\n==========================  BOX ALLERTE  ===========================")
            print("------------------- !!! Allerta meteo rilevata !!! -----------------")
            print("====================================================================")
            reteAggiornata = rete_bayesiana_temp
            return True
    else:
        print("\n==========================  BOX ALLERTE  ===========================")
        print("--------------- !!! Nessun'allerta meteo rilevata !!! --------------")
        print("====================================================================")
        return False

# ==============================================================================
# Funzione: stampa_rischio_finale()
# Aggiorna la rete bayesiana (se necessario) e stampa il rischio finale di insoddisfazione.
# Se l'utente ha accesso a strutture indoor, il rischio viene annullato nel messaggio.
# ==============================================================================
def stampa_rischio_finale():
    global vento, temp, tipo, reteAggiornata, rete, indoor, pioggia
    if reteAggiornata is None:
        print("Nessuna rete aggiornata disponibile.")
        return
    # Aggiorna la rete con il dataset in base alla scelta dell'utente
    if rete == "2":
        import pandas as pd
        if tipo == "freddo":
            dataset = pd.read_csv("src/ClassiSupporto/dataset_consulente_freddo_ottimale.csv")
            dataset = dataset[['Vento', 'Freddo', 'Pioggia', 'Consiglio']]
        elif tipo == "caldo":
            dataset = pd.read_csv("src/ClassiSupporto/dataset_consulente_caldo_ottimale.csv")
            dataset = dataset[['Attività', 'Vento', 'Pioggia', 'Consiglio']]
        reteAggiornata.impara_dataset(dataset, "bayes")

    from src.ReteBayesiana import retiBayesiane as rb
    # Prepara l'evidenza in base al tipo di ramo (freddo/caldo), includendo tutte le variabili
    if tipo == "freddo":
        evidenza = {'Vento': int(vento), 'Freddo': int(temp), 'Pioggia': int(pioggia)}
    elif tipo == "caldo":
        evidenza = {'Attività': int(temp), 'Vento': int(vento), 'Pioggia': int(pioggia)}
    else:
        print("Tipo non riconosciuto per l'inferenza.")
        return

    risultato = rb.ottieni_risultato_query(reteAggiornata.inferenza(evidenza))
    p = risultato["p"]
    probabilita_rischio = (p.iloc[3] + p.iloc[4]) * 100
    print("====================================================================")
    if indoor.strip().lower() == "si":
        print("Avendo accesso ad una struttura indoor il rischio si annulla!")
    else:
        print(f"Il rischio di insoddisfazione è del {round(probabilita_rischio, 2)}% a causa del meteo.")
    print("====================================================================")


# ==============================================================================
# Funzione: safe_int()
# Converte in intero un valore, gestendo errori di conversione.
#
# NOTA BENE: ha 0 Utilizzi perchè serviva per risolvere degli errori in fase di sviluppo
# ==============================================================================
def safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0

# ==============================================================================
# Funzione: converti_temperatura_freddo()
# Converte la temperatura in un indice (0-4) per il ramo "freddo" in base a soglie predefinite.
# ==============================================================================
def converti_temperatura_freddo():
    global temp
    if temp < 5:
        temp = 4
    elif temp < 9:
        temp = 3
    elif temp < 12:
        temp = 2
    elif temp < 15:
        temp = 1
    else:
        temp = 4        # Condizione estrema: forza l'indice massimo


# ==============================================================================
# Funzione: converti_temperatura_caldo()
# Converte la temperatura in un indice (0-4) per il ramo "caldo" in base a soglie predefinite.
# ==============================================================================
def converti_temperatura_caldo():
    global temp
    if temp > 42:
        temp = 4
    elif temp > 38:
        temp = 3
    elif temp > 34:
        temp = 2
    elif temp > 31:
        temp = 1
    elif temp > 26:
        temp = 0

# ==============================================================================
# Funzione: converti_vento()
# Converte il valore del vento in un indice (0-4) in base a soglie predefinite.
# ==============================================================================
def converti_vento():
    global vento
    try:
        vento = float(vento)
    except:
        vento = 0
    if vento <= 16:
        vento = 0
    elif 16 < vento <= 21:
        vento = 1
    elif 21 < vento <= 27:
        vento = 2
    elif 27 < vento <= 31:
        vento = 3
    elif vento > 31:
        vento = 4
