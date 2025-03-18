# ==============================================================================
# retiBayesiane.py
#
# Questo modulo definisce due classi per l'inferenza tramite reti bayesiane:
#
# 1. BayesianaInsoddisfazione:
#    - Utilizzata per il ramo "freddo".
#    - Usa le evidenze: Vento, Freddo, Pioggia per inferire il nodo target "Consiglio".
#
# 2. BayesianaTempoLibero:
#    - Utilizzata per il ramo "caldo".
#    - Usa le evidenze: Attività, Vento, Pioggia per inferire il nodo target "Consiglio".
#
# Inoltre, è fornita la funzione ottieni_risultato_query per formattare l'output
# dell'inferenza in una struttura pandas.DataFrame.
# ==============================================================================

from pgmpy.factors.discrete import TabularCPD
import bnlearn
import pandas

# ==============================================================================
# Classe BayesianaInsoddisfazione (Ramo Freddo)
# ==============================================================================
class BayesianaInsoddisfazione:
    def __init__(self):
        """
        Crea una rete bayesiana per il ramo "freddo" con le seguenti evidenze:
          - Vento (0-4)
          - Freddo (0-4)
          - Pioggia (0-4)
        e il nodo target "Consiglio" (0-4).
        """
        # Definizione degli archi (Bordi) del DAG: ciascuna evidenza influenza "Consiglio"
        self.Bordi = [
            ('Vento', 'Consiglio'),
            ('Freddo', 'Consiglio'),
            ('Pioggia', 'Consiglio')
        ]

        # ----------------------------------------------------------------------
        # CPD per Vento: rappresenta la distribuzione a priori dei livelli di vento.
        # I livelli più alti (valore 4) sono più probabili.
        # ----------------------------------------------------------------------
        self.CPD_vento = TabularCPD(
            variable='Vento', variable_card=5,
            values=[
                [0.05],
                [0.10],
                [0.20],
                [0.25],
                [0.40]
            ],
            state_names={'Vento': [0, 1, 2, 3, 4]}
        )

        # ----------------------------------------------------------------------
        # CPD per Freddo: distribuzione a priori aggiornata per la variabile "Freddo".
        # ----------------------------------------------------------------------
        self.CPD_freddo = TabularCPD(
            variable='Freddo', variable_card=5,
            values=[
                [0.18],
                [0.18],
                [0.18],
                [0.18],
                [0.28]
            ],
            state_names={'Freddo': [0, 1, 2, 3, 4]}
        )

        # ----------------------------------------------------------------------
        # CPD per Pioggia: distribuzione a priori per la variabile "Pioggia".
        # Valori maggiori indicano condizioni di pioggia più intense.
        # ----------------------------------------------------------------------
        self.CPD_pioggia = TabularCPD(
            variable='Pioggia', variable_card=5,
            values=[
                [0.50],
                [0.20],
                [0.15],
                [0.10],
                [0.05]
            ],
            state_names={'Pioggia': [0, 1, 2, 3, 4]}
        )

        # ------------------------------------------------------------------
        # CPD per Consiglio: definisce la probabilità di ciascun livello di "Consiglio"
        # in base a combinazioni delle evidenze Vento, Freddo e Pioggia.
        # La logica applicata:
        # - Si considera il massimo tra Vento, Freddo e Pioggia come indicatore di rischio.
        # - In base al valore massimo si determina un "rischio" (0.0, 0.25, 0.40, 0.60, 0.80).
        # - Il rischio viene poi distribuito: metà sui livelli 3 e 4 (stati critici), il resto
        #   equamente distribuito tra 0, 1 e 2.
        # ----------------------------------------------------------------------
        def genera_cpd_consiglio():
            values = [[], [], [], [], []]  # liste per p(Consiglio=0..4)
            # Cicla su tutte le possibili combinazioni delle evidenze (5x5x5 = 125 combinazioni)
            for vento in range(5):
                for freddo in range(5):
                    for pioggia in range(5):
                        massimo = max(vento, freddo, pioggia)
                        if massimo == 0: rischio = 0.0    # condizioni ottimali: rischio 0%
                        elif massimo == 1: rischio = 0.25   # condizioni lievemente sfavorevoli: 25%
                        elif massimo == 2: rischio = 0.40   # condizioni moderate: 40%
                        elif massimo == 3: rischio = 0.60   # condizioni difficili: 60%
                        else: rischio = 0.80   # condizioni estreme: 80%
                        # Suddivide il rischio: metà per lo stato 3, metà per lo stato 4.
                        p3 = rischio / 2
                        p4 = rischio / 2
                        restante = 1 - rischio
                        if restante < 0:
                            restante = 0.0
                        p0 = p1 = p2 = restante / 3 if restante > 0 else 0.0
                        # Aggiunge le probabilità per questa combinazione
                        values[0].append(p0); values[1].append(p1); values[2].append(p2)
                        values[3].append(p3); values[4].append(p4)
            return values

        self.CPD_consiglio = TabularCPD(
            variable='Consiglio', variable_card=5,
            values=genera_cpd_consiglio(),
            evidence=['Vento', 'Freddo', 'Pioggia'],
            evidence_card=[5, 5, 5],
            state_names={
                'Consiglio': [0, 1, 2, 3, 4],
                'Vento': [0, 1, 2, 3, 4],
                'Freddo': [0, 1, 2, 3, 4],
                'Pioggia': [0, 1, 2, 3, 4]
            }
        )

        # ----------------------------------------------------------------------
        # Costruisce il DAG iniziale combinando i CPD definiti
        # ----------------------------------------------------------------------
        self.DAG = bnlearn.make_DAG(
            self.Bordi,
            CPD=[self.CPD_vento, self.CPD_freddo, self.CPD_pioggia, self.CPD_consiglio],
            verbose=0
        )

    # --------------------------------------------------------------------------
    # Metodo inferenza: esegue l'inferenza sul nodo "Consiglio" dato un dizionario di evidenze.
    # --------------------------------------------------------------------------
    def inferenza(self, dati):
        return bnlearn.inference.fit(self.DAG,
                                     variables=['Consiglio'],
                                     evidence=dati,
                                     verbose=0)

    # --------------------------------------------------------------------------
    # Metodo impara_dataset: aggiorna i parametri della rete utilizzando un dataset
    # Se il dataset contiene la colonna 'Attività' (ramo caldo) la usa, altrimenti usa 'Freddo' (ramo freddo).
    # --------------------------------------------------------------------------
    def impara_dataset(self, dataset, metodo="bayes"):
        if 'Attività' in dataset.columns:
            dataset = dataset[['Attività', 'Vento', 'Pioggia', 'Consiglio']]
        else:
            dataset = dataset[['Vento', 'Freddo', 'Pioggia', 'Consiglio']]
        self.DAG = bnlearn.make_DAG(self.Bordi, verbose=0)
        # MODIFICA: utilizza il metodo bayesiano con smoothing (Laplace smoothing, α=1)
        self.DAG = bnlearn.parameter_learning.fit(
            self.DAG, dataset,
            methodtype=metodo,
            verbose=0
        )

# ==============================================================================
# Funzione di supporto per ottenere i risultati dell'inferenza in formato DataFrame
# ==============================================================================
def ottieni_risultato_query(query) -> pandas.DataFrame:
    return bnlearn.bnlearn.query2df(query, verbose=0)

# ==============================================================================
# Classe BayesianaTempoLibero (Ramo Caldo)
# ==============================================================================
class BayesianaTempoLibero:
    def __init__(self):
        """
        Crea una rete bayesiana per il ramo "caldo" con le seguenti evidenze:
          - Attività (0-4, indice che rappresenta il grado di caldo/attività)
          - Vento (0-4)
          - Pioggia (0-4)
        e il nodo target "Consiglio" (0-4).
        """
        # Definizione degli archi del DAG: Attività, Vento e Pioggia influenzano "Consiglio"
        self.Bordi = [
            ('Attività', 'Consiglio'),
            ('Vento', 'Consiglio'),
            ('Pioggia', 'Consiglio')
        ]

        # ----------------------------------------------------------------------
        # CPD per Attività: distribuzione uniforme
        # ----------------------------------------------------------------------
        self.CPD_attivita = TabularCPD(
            variable='Attività', variable_card=5,
            values=[
                [0.2],
                [0.2],
                [0.2],
                [0.2],
                [0.2]
            ],
            state_names={'Attività': [0, 1, 2, 3, 4]}
        )

        # ----------------------------------------------------------------------
        # CPD per Vento: distribuzione a priori (valori più bassi più frequenti)
        # ----------------------------------------------------------------------
        self.CPD_vento = TabularCPD(
            variable='Vento', variable_card=5,
            values=[
                [0.25],
                [0.30],
                [0.20],
                [0.15],
                [0.10]
            ],
            state_names={'Vento': [0, 1, 2, 3, 4]}
        )

        # ----------------------------------------------------------------------
        # CPD per Pioggia: distribuzione a priori (pioggia intensa meno probabile)
        # ----------------------------------------------------------------------
        self.CPD_pioggia = TabularCPD(
            variable='Pioggia', variable_card=5,
            values=[
                [0.20],
                [0.40],
                [0.20],
                [0.15],
                [0.05]
            ],
            state_names={'Pioggia': [0, 1, 2, 3, 4]}
        )

        # ----------------------------------------------------------------------
        # CPD per Consiglio: calcola la distribuzione in base alle evidenze Attività, Vento e Pioggia.
        # La logica è simile a quella usata per il ramo freddo:
        # si considera il massimo tra Attività, Vento e Pioggia per determinare il rischio.
        # ----------------------------------------------------------------------
        def genera_cpd_consiglio():
            values = [[], [], [], [], []]
            for att in range(5):
                for vento in range(5):
                    for pioggia in range(5):
                        massimo = max(att, vento, pioggia)
                        if massimo == 0:
                            rischio = 0.0
                        elif massimo == 1:
                            rischio = 0.25
                        elif massimo == 2:
                            rischio = 0.40
                        elif massimo == 3:
                            rischio = 0.60
                        else:
                            rischio = 0.80
                        p3 = rischio / 2
                        p4 = rischio / 2
                        restante = 1 - rischio
                        if restante < 0:
                            restante = 0.0
                        p0 = p1 = p2 = restante / 3 if restante > 0 else 0.0
                        values[0].append(p0); values[1].append(p1); values[2].append(p2)
                        values[3].append(p3); values[4].append(p4)
            return values

        self.CPD_consiglio = TabularCPD(
            variable='Consiglio', variable_card=5,
            values=genera_cpd_consiglio(),
            evidence=['Attività', 'Vento', 'Pioggia'],
            evidence_card=[5, 5, 5],
            state_names={
                'Consiglio': [0, 1, 2, 3, 4],
                'Attività': [0, 1, 2, 3, 4],
                'Vento': [0, 1, 2, 3, 4],
                'Pioggia': [0, 1, 2, 3, 4]
            }
        )

        # ----------------------------------------------------------------------
        # Costruisce il DAG con i CPD definiti
        # ----------------------------------------------------------------------
        self.DAG = bnlearn.make_DAG(
            self.Bordi,
            CPD=[self.CPD_attivita, self.CPD_vento, self.CPD_pioggia, self.CPD_consiglio],
            verbose=0
        )

    # --------------------------------------------------------------------------
    # Metodo inferenza: esegue l'inferenza sul nodo "Consiglio" dato un dizionario di evidenze.
    # --------------------------------------------------------------------------
    def inferenza(self, dati):
        return bnlearn.inference.fit(self.DAG,
                                     variables=['Consiglio'],
                                     evidence=dati,
                                     verbose=0)

    # --------------------------------------------------------------------------
    # Metodo impara_dataset: aggiorna i parametri della rete utilizzando un dataset,
    # applicando Laplace smoothing (α=1) per evitare probabilità estreme.
    # Se il dataset contiene la colonna 'Attività' (ramo caldo), la usa, altrimenti usa 'Freddo' (ramo freddo).
    # --------------------------------------------------------------------------
    def impara_dataset(self, dataset, metodo="bayes"):
        if 'Attività' in dataset.columns:
            dataset = dataset[['Attività', 'Vento', 'Pioggia', 'Consiglio']]
        else:
            dataset = dataset[['Vento', 'Freddo', 'Pioggia', 'Consiglio']]
        self.DAG = bnlearn.make_DAG(self.Bordi, verbose=0)
        self.DAG = bnlearn.parameter_learning.fit(
            self.DAG, dataset,
            methodtype=metodo,
            verbose=0
        )
