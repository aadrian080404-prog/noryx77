from core.state import NORYXState


class NORYXOrchestrator:
    """
    Coordinatore centrale di NORYX7.

    Per ora gestisce soltanto il ciclo fondamentale:
    input → stato → elaborazione → risposta.
    """

    def __init__(self):
        self.state = NORYXState()

    def receive(self, user_input: str):
        """Riceve un nuovo input e aggiorna lo stato."""
        self.state.user_input = user_input
        self.state.status = "processing"
        return self.state

    def set_goal(self, goal: str):
        """Imposta l'obiettivo del compito."""
        self.state.goal = goal

    def complete(self, answer: str):
        """Conclude il compito e aggiorna lo stato."""
        self.state.final_answer = answer
        self.state.status = "completed"
        return self.state

