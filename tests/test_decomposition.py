import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.state import NORYXState
from reasoning.decomposition import TaskDecomposer


def test_trip_goal_is_split_into_concrete_subtasks():
    state = NORYXState()
    state.goal = "Organizzare il viaggio"

    decomposer = TaskDecomposer()
    decomposer.decompose(state)

    assert state.subtasks == [
        "Definire budget, date e destinazione del viaggio",
        "Verificare opzioni di trasporto e alloggio",
        "Prenotare i servizi principali del viaggio",
        "Preparare documenti, agenda e dettagli finali",
    ]


def test_generic_goal_falls_back_to_general_steps():
    state = NORYXState()
    state.goal = "Preparare una presentazione"

    decomposer = TaskDecomposer()
    decomposer.decompose(state)

    assert state.subtasks == [
        "Definire obiettivo, pubblico e messaggio principale",
        "Raccontare e strutturare il contenuto",
        "Preparare materiali, slide e dettagli finali",
    ]
