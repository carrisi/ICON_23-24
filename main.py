# ===================================================================
# main.py
#
# Questo file è il punto di ingresso del sistema esperto.
# Viene importato il modulo del sistema esperto e vengono
# configurati gli avvisi e il logging per le librerie utilizzate.
# ===================================================================

# -------------------------------------------------------------------
# Import
# -------------------------------------------------------------------
import logging

# -------------------------------------------------------------------
# Configurazione dei warning e del logging
# -------------------------------------------------------------------
# Imposta il livello di logging per pgmpy su ERROR per minimizzare l'output
logging.getLogger("pgmpy").setLevel(logging.ERROR)
# Imposta il livello di logging per la libreria experta su WARNING
logging.getLogger('experta').setLevel(logging.WARNING)

# -------------------------------------------------------------------
# Importa il modulo del sistema esperto
# -------------------------------------------------------------------
from src.SistemaEsperto import sistemaEsperto

# -------------------------------------------------------------------
# Funzione per avviare il sistema esperto.
# -------------------------------------------------------------------
def avvia_sistema():
    sistemaEsperto.avvia_sistema_esperto()

# -------------------------------------------------------------------
# Punto di ingresso dell'applicazione.
# -------------------------------------------------------------------
if __name__ == '__main__':
    avvia_sistema()
