# ==============================================================================
# sistemaEsperto.py
#
# Questo modulo implementa il motore del sistema esperto usando la libreria
# experta. Esso gestisce l'interazione con l'utente tramite l'ontologia e le
# regole basate sui dati meteo e sull'attività scelta.
# ==============================================================================
from experta import *
from src.ClassiSupporto import interfacciaConUtente

# ==============================================================================
# Classe ConsigliAttivita
# Implementa il motore del sistema esperto che guida l'interazione con l'utente.
# ==============================================================================
class ConsigliAttivita(KnowledgeEngine):

    # --------------------------------------------------------------------------
    # Definizione dei fatti iniziali
    # --------------------------------------------------------------------------
    @DefFacts()
    def _initial_action(self):
        yield Fact(azione="chiedereOnline")

    # --------------------------------------------------------------------------
    # Definizione delle regole
    # --------------------------------------------------------------------------

    # Regola per la richiesta della modalità di ricerca (online)
    @Rule(Fact(azione="chiedereOnline"), salience=1)
    def chiedere_online(self):
        # Chiede all'utente se vuole cercare i dati meteo online e dichiara il fatto
        # corrispondente.
        self.declare(Fact(azione=interfacciaConUtente.chiedi_online()))

    # Regola per la ricerca delle informazioni meteo online
    @Rule(Fact(azione='trovareInformazioniOnline'),
          NOT(Fact(risultato=W())), salience=1)
    def ricerca_informazioni(self):
        # Se l'azione è quella di trovare informazioni online, effettua la ricerca
        # ed estrae il risultato.
        self.declare(Fact(risultato=interfacciaConUtente.risultati_previsioni()))

    # Gestione dell'errore: città non trovata
    @Rule(Fact(risultato="trovareInformazioniOffline"), salience=0)
    def errore_citta_non_trovata(self):
        # Se non si trovano informazioni online, chiede all'utente se vuole inserire
        # manualmente i dati.
        self.declare(Fact(scelta=interfacciaConUtente.chiedi_inserimento_manuale()))

    # Regola per passare alle informazioni offline se non ci sono dati online
    @Rule(AND(NOT(Fact(risultato="trovareInformazioniOffline"))),
          Fact(risultato=MATCH.risultato), salience=0)
    def greet(self, risultato):
        # Se i dati online sono stati trovati, estrae fascia oraria, meteo e temperatura
        # e passa all'azione successiva.
        self.declare(Fact(fascia_oraria=risultato[0]))
        self.declare(Fact(meteo=risultato[1]))
        self.declare(Fact(temperatura=risultato[2]))
        self.declare(Fact(azione="chiediAttivita"))

    # Regola per terminare il sistema se l'utente decide di non procedere
    @Rule(Fact(scelta="no"), salience=0)
    def fine_elaborazione(self):
        self.declare(Fact(azione="terminaAnalisi"))
        print("Fine del sistema esperto")

    # Regola per acquisire informazioni in modalità offline
    @Rule(OR(Fact(scelta="si"), Fact(azione="trovareInformazioniOffline")), salience=0)
    def chiedere_informazioni_offline(self):
        # Chiede all'utente la fascia oraria
        fascia = interfacciaConUtente.chiedi_fascia_oraria()
        # Chiede all'utente le condizioni del meteo
        meteo = interfacciaConUtente.chiedi_meteo()
        self.declare(Fact(fascia_oraria=fascia))
        self.declare(Fact(meteo=meteo))
        # Se le condizioni meteo sono "rovesci", chiede anche l'intensità della pioggia.
        if meteo.strip().lower() == "rovesci":
            self.declare(Fact(pioggia=interfacciaConUtente.chiedi_pioggia()))
        # Chiede all'utente la temperatura
        self.declare(Fact(temperatura=interfacciaConUtente.chiedi_temperatura()))
        # Chiede all'utente il vento
        self.declare(Fact(vento=interfacciaConUtente.chiedi_vento()))
        # Passa all'azione successiva, cioè la richiesta del tipo di attività.
        self.declare(Fact(azione="chiediAttivita"))

    # Regola per acquisire il tipo di attività e l'accesso a strutture indoor,
    # quindi valutare l'allerta meteo tramite rete bayesiana.
    @Rule(Fact(azione="chiediAttivita"), salience=0)
    def chiedere_attivita(self):
        # Chiede al'utente il tipo di attività preferita
        attivita = interfacciaConUtente.chiedi_attivita()
        self.declare(Fact(attivita=attivita))
        # Chiede all'utente se ha accesso a strutture indoor
        indoor_risposta = interfacciaConUtente.chiedi_indoor()
        self.declare(Fact(indoor=indoor_risposta))
        # Valuta il rischio meteo attraverso la rete bayesiana.
        rischio_alto = interfacciaConUtente.stampa_allerta_meteo()
        if rischio_alto:
            # Se viene rilevata un'anomalia meteo, chiede all'utente di scegliere la rete bayesiana.
            self.declare(Fact(azione="chiediTipoRete"))
        else:
            # Altrimenti, passa direttamente alla stampa dell'attività consigliata.
            self.declare(Fact(azione="stampaAttivita"))

    # Regola per la scelta della rete bayesiana da utilizzare in caso di allerta meteo.
    @Rule(Fact(azione="chiediTipoRete"), salience=1)
    def chiedere_tipo_rete(self):
        rete_choice = input("Rilevata anomalia meteorologica, seleziona il tipo di rete bayesiana da utilizzare:\n(1) Rete bayesiana data\n(2) Rete bayesiana con apprendimento dal dataset\nRisposta: ")
        self.declare(Fact(rete=rete_choice))
        # Dopo la scelta, si stampa il rischio finale utilizzando la rete aggiornata.
        from src.ClassiSupporto import interfacciaConUtente
        interfacciaConUtente.rete = rete_choice
        interfacciaConUtente.stampa_rischio_finale()
        self.declare(Fact(azione="stampaAttivita"))

    # Regola per stampare le attività consigliate in base alle informazioni raccolte.
    @Rule(Fact(azione="stampaAttivita"),
          Fact(attivita=MATCH.attivita),
          Fact(indoor=MATCH.indoor),
          Fact(fascia_oraria=MATCH.fascia_oraria),
          Fact(temperatura=MATCH.temperatura),
          Fact(meteo=MATCH.meteo),
          salience=0)
    def stampare_attivita(self, attivita, indoor, fascia_oraria, temperatura, meteo):
        # Chiamata alla funzione di stampa dei risultati
        interfacciaConUtente.stampa_risultato(attivita, indoor, fascia_oraria, temperatura, meteo)
        # Dopo la stampa, passa all'azione finale per evitare di ripetere l'inferenza.
        self.declare(Fact(azione="stampaAccessorio"))

    # Regola finale per terminare il sistema, stampando un separatore e terminando l'esecuzione.
    @Rule(Fact(azione="stampaAccessorio"), salience=0)
    def stampare_accessorio(self):
        print("\n============ !!! ESECUZIONE TERMINATA CON SUCCESSO !!! =============")
        exit(0)

# ==============================================================================
# Funzione per avviare il sistema esperto.
# ==============================================================================
def avvia_sistema_esperto():
    sistema = ConsigliAttivita()
    sistema.reset()
    sistema.run()
