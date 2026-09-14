from abc import ABC, abstractmethod


class Capability(ABC):

    def __init__(self, logger, node, skills_manager, context=None):
        self.logger = logger
        self.get_logger = lambda: self.logger
        self.node = node
        self.skills_manager = skills_manager
        self.context = context

    @property
    @abstractmethod
    def required_services(self) -> list[str]:
        pass
