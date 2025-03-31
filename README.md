# ICON_23-24
Progetto per il corso di "Ingegneria della conoscenza" a.a. 2023/2024

## Presentazione

Questa repository contiene il progetto realizzato per l'esame di Ingegneria della Conoscenza.  
Il sistema esperto sviluppato integra due componenti principali:

1. **Motore a Regole:** Utilizza la libreria *experta* per guidare l’interazione con l’utente, raccogliendo informazioni relative alle condizioni meteorologiche e alle preferenze per le attività.
2. **Rete Bayesiana:** Implementata con *pgmpy* e *bnlearn*, la rete calcola, tramite inferenza e apprendimento da dataset, la probabilità di insoddisfazione o rischio dovuto a condizioni climatiche avverse. Il sistema può aggiornare automaticamente le tabelle di probabilità condizionata (CPD) in base a dati reali, garantendo una stima più precisa man mano che vengono integrati nuovi dati.

La documentazione completa del progetto è disponibile nel file:  
```Documentazione_acarrisi.pdf```

Studente:

* Nome: Alessandro
* Cognome: Carrisi
* Matricola: 736830
* Email istituzionale: a.carrisi3@studenti.uniba.it

## Installare i Requisiti

Installa tutte le librerie necessarie elencate nel file **requisiti.txt** eseguendo il comando seguente nella directory del file ```requisiti.txt```:

```pip install -r requisiti.txt```

Se, in ambiente Windows, dovessi ricevere errori, prova ad eseguire:

```python.exe -m pip install -r requisiti.txt```

Nel caso in cui, durante l’installazione, si verifichi il seguente errore:
```
  File "percorsoAlFile/__init__.py", line 16, in <module>
    class frozendict(collections.Mapping):
AttributeError: module 'collections' has no attribute 'Mapping'
```

segui questi passaggi:
1. Apri il file __init__.py del pacchetto indicato.
2. Trova la riga: class frozendict(collections.Mapping)
3. Modificala in: class frozendict(collections.abc.Mapping)

## Avviare il Sistema
Per avviare il sistema esperto, esegui il comando:

```python main.py```

Assicurati di eseguire il comando dalla directory in cui si trova il file ```main.py```.


