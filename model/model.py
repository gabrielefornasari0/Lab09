from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # TODO: Aggiungere eventuali altri attributi

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        # Inizializza la soluzione migliore prima di avviare la ricerca ricorsiva:
        # - _pacchetto_ottimo conterrà la lista delle Escursione scelte
        # - _costo conterrà il costo totale del pacchetto migliore trovato
        # - _valore_ottimo parte da 0 così qualsiasi combinazione valida con voto >= 0 possa aggiornarlo
        self._pacchetto_ottimo = []
        self._costo = 0.0
        self._valore_ottimo = 0

        # Filtra dal dizionario self.escursioni_map solo le escursioni appartenenti al parco selezionato (id_parco).
        # In questo modo l'algoritmo esplora esclusivamente le escursioni di quel parco.
        escursioni_parco = [
            esc for esc in self.escursioni_map.values()
            if esc.id_parco == id_parco
        ]

        # Avvia la ricorsione partendo dall'indice 0 della lista filtrata,
        # con pacchetto vuoto, durata 0, costo 0.0, valore 0 e nessun punto di interesse già usato.
        self._ricorsione(
            escursioni=escursioni_parco,
            start_index=0,
            pacchetto_parziale=[],
            durata_corrente=0,
            costo_corrente=0.0,
            valore_corrente=0,
            punti_usati=set(),
            max_giorni=max_giorni,
            max_budget=max_budget
        )

        # Restituisce la tripla attesa dal controller: lista escursioni ottime, costo totale e voto complessivo
        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(
            self,
            escursioni: list,
            start_index: int,
            pacchetto_parziale: list,
            durata_corrente: int,
            costo_corrente: float,
            valore_corrente: int,
            punti_usati: set,
            max_giorni: int,
            max_budget: float
    ):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        # 🟤 A - Istruzioni eseguite a ogni chiamata ricorsiva:
        # Controlla se lo stato parziale corrente ha un voto complessivo (valore_corrente)
        # strettamente maggiore del miglior valore trovato finora (_valore_ottimo).
        # Se sì, salva una copia superficiale (.copy()) di pacchetto_parziale così future modifiche
        # tramite .append() e .pop() non altereranno la soluzione salvata.
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._costo = costo_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()

        # 🟢 B - Condizione terminale:
        # Non serve un if esplicito di fine corsa perché quando start_index == len(escursioni),
        # range(start_index, len(escursioni)) è vuoto e il ciclo for termina naturalmente,
        # facendo risalire la ricorsione al livello precedente.

        # Cicla sulle escursioni a partire da start_index:
        # partire da i e poi passare i + 1 nella chiamata ricorsiva garantisce di considerare
        # ogni escursione al più una volta (no escursioni duplicate) e di non rivedere combinazioni già provate.
        for i in range(start_index, len(escursioni)):
            # Seleziona l'escursione candidata corrente
            esc = escursioni[i]

            # Calcola la durata e il costo cumulativi qualora si aggiungesse `esc` al pacchetto parziale
            nuova_durata = durata_corrente + esc.durata_giorni
            nuovo_costo = costo_corrente + esc.costo

            # 🟡 C - Controllo dei vincoli prima di scendere in ricorsione:
            # 1) Durata: valida se non c'è limite (max_giorni is None) oppure se nuova_durata <= max_giorni
            ok_durata = (max_giorni is None) or (nuova_durata <= max_giorni)
            # 2) Budget: valido se non c'è limite (max_budget is None) oppure se nuovo_costo <= max_budget
            ok_budget = (max_budget is None) or (nuovo_costo <= max_budget)
            # 3) Punti di interesse unici: isdisjoint() restituisce True se punti_usati e esc.punti_interesse
            #    non hanno alcun elemento in comune (quindi non si visita due volte lo stesso punto).
            ok_punti = punti_usati.isdisjoint(esc.punti_interesse)

            # Procede con la scelta di `esc` solo se tutti e tre i vincoli sono soddisfatti
            if ok_durata and ok_budget and ok_punti:
                # 🔵 D - Aggiornamento parziale ("compute_partial"):
                # Recupera il set di oggetti PuntoInteresse associati all'escursione `esc`
                nuovi_punti = esc.punti_interesse
                # Calcola il voto portato da questa escursione sommando voto_visitatori di ciascun suo punto di interesse
                valore_aggiunto = sum(p.voto_visitatori for p in nuovi_punti)

                # Aggiunge l'escursione alla soluzione parziale corrente
                pacchetto_parziale.append(esc)
                # Registra i nuovi punti di interesse come già visitati nel ramo corrente
                punti_usati.update(nuovi_punti)

                # 🔴 E - Chiamata ricorsiva ("recursion"):
                # Esplora il sotto-albero successivo passando start_index = i + 1,
                # i nuovi totali di durata, costo e valore, e l'insieme punti_usati aggiornato.
                self._ricorsione(
                    escursioni=escursioni,
                    start_index=i + 1,
                    pacchetto_parziale=pacchetto_parziale,
                    durata_corrente=nuova_durata,
                    costo_corrente=nuovo_costo,
                    valore_corrente=valore_corrente + valore_aggiunto,
                    punti_usati=punti_usati,
                    max_giorni=max_giorni,
                    max_budget=max_budget
                )

                # 🟣 F - Backtracking ("back_tracking"):
                # Al ritorno dalla chiamata ricorsiva, annulla la scelta di `esc` per poter provare
                # le altre escursioni successive nel ciclo `for`:
                # - rimuove l'ultima escursione inserita da pacchetto_parziale
                pacchetto_parziale.pop()
                # - rimuove da punti_usati solo i punti appartenenti a `esc` (che avevamo aggiunto al passo D)
                punti_usati.difference_update(nuovi_punti)