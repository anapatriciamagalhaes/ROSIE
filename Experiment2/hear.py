from bill_interfaces.srv import HearSrv

from mission_control.skills.skill import Skill


class Hear(Skill):
    def __init__(self, skills_manager):
        super().__init__(skills_manager=skills_manager)
        self._description: str = "Calls ROS hear service and follows its execution"
        self.__done: bool = True
        self.__heard_text: str = None
        self.__db_max: float = 0.0
        self.__db_mean: float = 0.0

    @property
    def description(self) -> str:
        return self._description

    def _done_callback(self, future, request) -> None:
        try:
            response: HearSrv.response = future.result()
            self.__heard_text = response.heard_text
            self.__db_max = float(response.db_max)
            self.__db_mean = float(response.db_mean)
            self.__done = True
            self.get_logger().info("Hearing: " + response.heard_text)
        except Exception as e:
            self.get_logger().error("Call to hear service failed:" + str(e))

    def execute(self, reset: bool, context: list[str] = None) -> bool:
        if reset:
            self.__done = False
            self.__heard_text = None
            self.__db_max = 0.0
            self.__db_mean = 0.0

            # Crie o objeto de requisição e preencha o contexto
            request = HearSrv.Request()
            request.context = context if context is not None else []

            # Chame o serviço com a requisição
            self.node.call_hear(done_callback=self._done_callback, request=request)

        return self.__done

    def is_ready(self) -> bool:
        return self.__done

    def get_heard_text(self):
        return self.__heard_text

    def get_db_max(self) -> float:
        return self.__db_max

    def get_db_mean(self) -> float:
        return self.__db_mean
