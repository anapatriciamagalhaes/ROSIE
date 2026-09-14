from mission_control.skills.skill import Skill

from bill_interfaces.srv import SpeakSrv

class Speak(Skill):
    def __init__(self, skills_manager):
        super().__init__(skills_manager=skills_manager)
        self._description = "Calls ROS speak service and follows its execution"
        self.__done = True

    @property
    def description(self) -> str:
        return self._description

    def _done_callback(self, future, request) -> None:
        try:
            response: SpeakSrv.Response = future.result()
            was_successful = response.was_successful
            self.__done = True
            self.get_logger().info(f'Speaking was sucessful' if was_successful else f'Speaking failed')
        except Exception as e:
            self.get_logger().error("Call to speak service failed:" + str(e))

    def execute(self, reset: bool, text: str) -> bool:
        if reset:
            self.__done = False
            self.node.call_speak(done_callback=self._done_callback, text_to_speak=text)
            return False
        return self.__done

    def is_ready(self) -> bool:
        return self.__done