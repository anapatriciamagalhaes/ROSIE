from enum import Enum, auto

from mission_control.capabilities.ask import AskCapability
from mission_control.capabilities.follow import FollowCapability
from mission_control.missions.mission import Mission


class CapabilityTestMission(Mission):
    class Steps(Enum):
        START = auto()
        ASK_NAME = auto()
        ASK_DRINK = auto()
        REPORT = auto()
        FOLLOW = auto()
        END = auto()

    @property
    def required_services(self) -> list[str]:
        return ["speak", "hear", "follow_person", "recognize_pose", "recognize_object_position"]

    def __init__(self, logger, node):
        super().__init__(logger=logger, node=node)

        self.ask: AskCapability = self.register_capability(AskCapability(logger=logger, node=node, skills_manager=self.skills_manager))
        self.follow: FollowCapability = self.register_capability(FollowCapability(logger=logger, node=node, skills_manager=self.skills_manager))

        self.known_names = ["Miguel", "Alice", "Arthur", "Helena"]
        self.known_drinks = ["coffee", "coke", "fanta", "tea"]

        self.current_step = self.Steps.START
        self.guest_name: str = None
        self.guest_drink: str = None

    def execute(self):
        just_entered = self._entered_step(self.current_step)

        match self.current_step:
            case self.Steps.START:
                self.current_step = self.Steps.ASK_NAME

            case self.Steps.ASK_NAME:
                finished, name = self.ask.ask_name(reset=just_entered, known_names=self.known_names)
                if finished:
                    self.guest_name = name
                    self.current_step = self.Steps.ASK_DRINK

            case self.Steps.ASK_DRINK:
                finished, drink = self.ask.ask_drink(reset=just_entered, known_drinks=self.known_drinks)
                if finished:
                    self.guest_drink = drink
                    self.current_step = self.Steps.REPORT

            case self.Steps.REPORT:
                text = f"Ok, {self.guest_name}, your favorite drink is {self.guest_drink}"
                if self.skills_manager.execute("Speak", text=text):
                    self.current_step = self.Steps.FOLLOW

            case self.Steps.FOLLOW:
                finished = self.follow.follow(reset=just_entered)
                if finished:
                    self.current_step = self.Steps.END

            case self.Steps.END:
                pass
