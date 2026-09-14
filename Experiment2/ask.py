from enum import Enum, auto

from thefuzz import fuzz, process

from mission_control.capabilities.capability import Capability


class _AskStep(Enum):
    ASK_QUESTION = auto()
    HEAR_ANSWER = auto()
    ASK_AGAIN = auto()


class AskCapability(Capability):

    @property
    def required_services(self) -> list[str]:
        return ["speak", "hear"]

    def __init__(self, logger, node, skills_manager, context=None):
        super().__init__(logger, node, skills_manager, context)
        self._step = _AskStep.ASK_QUESTION
        self._attempts = 0

    def reset(self) -> None:
        self._step = _AskStep.ASK_QUESTION
        self._attempts = 0

    def ask(
        self,
        reset: bool,
        question: str,
        options: list[str],
        retry_text: str = "Sorry, I did not understand. Could you please repeat it?",
        threshold: int = 75,
        max_attempts: int = 2,
        fallback_value: str = "Unknown",
    ) -> tuple[bool, str | None]:
        if reset:
            self.reset()

        match self._step:
            case _AskStep.ASK_QUESTION:
                if self.skills_manager.execute("Speak", text=question):
                    self._step = _AskStep.HEAR_ANSWER

            case _AskStep.HEAR_ANSWER:
                if self.skills_manager.execute("Hear", context=options):
                    heard_text = self.skills_manager.get_skill_object("Hear").get_heard_text()

                    best_match = process.extractOne(heard_text, options, scorer=fuzz.WRatio)

                    self.get_logger().info(f"Heard '{heard_text}', best match is " f"'{best_match[0] if best_match else None}' " f"with score {best_match[1] if best_match else 0}")

                    if best_match and best_match[1] > threshold:
                        return True, best_match[0]

                    self._attempts += 1
                    if self._attempts >= max_attempts:
                        return True, fallback_value

                    self._step = _AskStep.ASK_AGAIN

            case _AskStep.ASK_AGAIN:
                if self.skills_manager.execute("Speak", text="Sorry, I did not understand. Could you please repeat it?"):
                    self._step = _AskStep.HEAR_ANSWER

        return False, None

    def ask_name(self, reset: bool, known_names: list[str]) -> tuple[bool, str | None]:
        return self.ask(
            reset=reset,
            question="What is your name?",
            options=known_names,
            fallback_value="Guest",
        )

    def ask_drink(self, reset: bool, known_drinks: list[str]) -> tuple[bool, str | None]:
        return self.ask(
            reset=reset,
            question="What would you like to drink?",
            options=known_drinks,
            fallback_value="Water",
        )
