import time
from enum import Enum, auto

from geometry_msgs.msg import PoseStamped

from mission_control.capabilities.capability import Capability
from mission_control.pose import BoundingBox


class _FollowStep(Enum):
    ASK_TO_FOLLOW = auto()
    WAIT_STAND_UP = auto()
    FOLLOW_PERSON = auto()
    FOLLOW_EXECUTE = auto()
    STOPPED = auto()


class FollowCapability(Capability):

    @property
    def required_services(self) -> list[str]:
        return ["speak", "follow_person", "recognize_pose", "recognize_object_position"]

    def __init__(self, logger, node, skills_manager, context=None):
        super().__init__(logger, node, skills_manager, context)
        self._step = _FollowStep.ASK_TO_FOLLOW
        self._wait_start = None
        self._target_pose = None

    def reset(self) -> None:
        self._step = _FollowStep.ASK_TO_FOLLOW
        self._wait_start = None
        self._target_pose = None

    def follow(self, reset: bool) -> bool:
        
        if reset:
            self.reset()

        match self._step:
            case _FollowStep.ASK_TO_FOLLOW:
                if self.skills_manager.execute("Speak", text="Please stand up so I can follow you."):
                    self._wait_start = time.time()
                    self._step = _FollowStep.WAIT_STAND_UP

            case _FollowStep.WAIT_STAND_UP:
                if time.time() - self._wait_start >= 2.0:
                    self._wait_start = None
                    self._step = _FollowStep.FOLLOW_PERSON

            case _FollowStep.FOLLOW_PERSON:
                if not self.skills_manager.execute("RecognizePose"):
                    return False

                pose = self.skills_manager.get_skill_object("RecognizePose").get_recognized_pose()
                if not pose:
                    return False

                if pose.name == "stop":
                    self._step = _FollowStep.STOPPED
                    return False

                if pose.name == "no detections":
                    self.get_logger().info("[FollowPersonCapability] Nenhuma pessoa detectada enquanto procurava o host.")
                    return False

                if pose.x1 == 0 and pose.y1 == 0 and pose.x2 == 0 and pose.y2 == 0:
                    self.get_logger().warn("[FollowPersonCapability] Recebido BBOX zerado (0,0,0,0) — ignorando frame.")
                    return False

                bbox = BoundingBox(x1=int(pose.x1), y1=int(pose.y1), x2=int(pose.x2), y2=int(pose.y2), name="host")

                if not self.skills_manager.execute("RecognizeObjectPosition", bboxes=[bbox]):
                    return False

                positions = self.skills_manager.get_skill_object("RecognizeObjectPosition").get_recognized_object_positions()
                if not positions:
                    self.get_logger().warn("[FollowPersonCapability] Lista de posições do host vazia.")
                    return False

                pos = positions[0]
                if pos.x == 0 and pos.y == 0 and pos.z == 0:
                    self.get_logger().warn("[FollowPersonCapability] Posição 3D do host inválida (0, 0, 0).")
                    return False

                self._target_pose = PoseStamped()
                self._target_pose.header.frame_id = "base_footprint"
                self._target_pose.header.stamp = self.node.get_clock().now().to_msg()
                self._target_pose.pose.position.x = float(pos.x)
                self._target_pose.pose.position.y = -float(pos.y)
                self._target_pose.pose.position.z = 0.0
                self._target_pose.pose.orientation.w = 1.0

                self._step = _FollowStep.FOLLOW_EXECUTE

            case _FollowStep.FOLLOW_EXECUTE:
                if self.skills_manager.execute("FollowPerson", target_pose=self._target_pose):
                    self._step = _FollowStep.FOLLOW_PERSON

            case _FollowStep.STOPPED:
                return True

        return False