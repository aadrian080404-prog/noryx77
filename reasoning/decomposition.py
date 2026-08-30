from __future__ import annotations

from core.state import NORYXState


class TaskDecomposer:
    """Decomponi un obiettivo in sottoattività concrete e deterministiche."""

    def decompose(self, state: NORYXState) -> list[str]:
        goal = (state.goal or "").strip().lower()

        if "viaggio" in goal or "trip" in goal:
            subtasks = [
                "Definire budget, date e destinazione del viaggio",
                "Verificare opzioni di trasporto e alloggio",
                "Prenotare i servizi principali del viaggio",
                "Preparare documenti, agenda e dettagli finali",
            ]
        elif "presentazione" in goal or "presentation" in goal:
            subtasks = [
                "Definire obiettivo, pubblico e messaggio principale",
                "Raccontare e strutturare il contenuto",
                "Preparare materiali, slide e dettagli finali",
            ]
        else:
            subtasks = [
                "Definire l'obiettivo e i requisiti principali",
                "Strutturare i passi necessari per completare il lavoro",
                "Preparare il risultato finale e verificarne la completezza",
            ]

        state.subtasks = subtasks
        return list(subtasks)
