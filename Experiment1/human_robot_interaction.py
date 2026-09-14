import time
from enum import Enum, auto

from geometry_msgs.msg import PoseStamped
from thefuzz import fuzz, process

from mission_control.missions.mission import Mission
from mission_control.pose import BoundingBox


class HumanRobotInteraction(Mission):
    class Steps(Enum):
        START = auto()
        GO_TO_RECEPTION = auto()
        ASK_FOR_NAME = auto()
        HEAR_NAME = auto()
        ASK_NAME_AGAIN = auto()
        REGISTER_GUEST = auto()
        ASK_FOR_DRINK = auto()
        HEAR_DRINK = auto()
        ASK_DRINK_AGAIN = auto()
        INFO_REGISTER_GUEST = auto()
        COME_WITH_ME = auto()
        GO_TO_MEETING_ROOM = auto()
        RECOGNIZE_EMPTY_SEAT = auto()
        POINT_TO_EMPTY_SEAT = auto()
        INTRODUCE_GUESTS = auto()
        INTRODUCE_GUESTS_RELATIVE_POSITION = auto()
        INTRODUCE_GUESTS_SPEAK = auto()
        PICK_UP_BAG = auto()
        ASK_FOR_BAG = auto()
        ASK_FOLLOW_HOST = auto()
        FOLLOW_HOST = auto()
        GO_TO_ROOM = auto()
        PUT_BAG_DOWN = auto()
        END = auto()

    @property
    def required_services(self) -> list[str]:
        return [
            "speak",
            "go_to_location",
            "hear",
            "recognize_empty_seat",
            "recognize_object_position",
            "recognize_empty_seat",
            "execute_b26_trajectory",
            # 'recognize_object_position',
            "recognize_faces",
            "register_face",
            "recognize_pose",
            "follow_person",
            "recognize_relative_position",
        ]

    def __init__(self, logger, node):
        super().__init__(logger=logger, node=node)
        self.current_step = self.Steps.START
        self.finished = False
        self.count_guests = 0
        self.guest_names = []
        self.recognized_faces = []
        self.has_spoken_confirmation = False
        self.guest_drinks = []
        self.introduce_text = ""
        self.recognized_empty_seats = None
        self.pointed_empty_seat = False
        self.has_asked_to_sit = False

        # Variables needed by the host-following flow
        self.current_operator_bbox = None
        self.current_target_pose = None

        self.known_names = [
            "Miguel",
            "Alice",
            "Arthur",
            "Helena",
            "Heitor",
            "Laura",
            "Davi",
            "Maria Alice",
            "Gabriel",
            "Maria Eduarda",
            "Bernardo",
            "Maria Clara",
            "Gael",
            "Valentina",
            "Enzo Gabriel",
            "Maria Cecília",
            "Samuel",
            "Maria Julia",
            "Theo",
            "Heloisa",
        ]
        self.known_drinks = [
            "water",
            "soda",
            "juice",
            "coffee",
            "tea",
        ]

    def execute(self):
        if self.finished:
            return True

        match self.current_step:

            case self.Steps.START:
                if self.skills_manager.execute("Speak", text="Hello, my name is Bill. I will go to the reception desk"):
                    self.current_step = self.Steps.GO_TO_RECEPTION

            case self.Steps.GO_TO_RECEPTION:
                if self.skills_manager.execute("GoToLocation", location_name="reception"):
                    self.count_guests += 1
                    self.current_step = self.Steps.ASK_FOR_NAME

            case self.Steps.ASK_FOR_NAME:
                if self.skills_manager.execute("Speak", text="What is your name?"):
                    self.current_step = self.Steps.HEAR_NAME

            case self.Steps.HEAR_NAME:
                if self.skills_manager.execute("Hear", context=self.known_names):
                    heard_text = self.skills_manager.get_skill_object("Hear").get_heard_text()

                    best_match = process.extractOne(heard_text, self.known_names, scorer=fuzz.WRatio)

                    self.get_logger().info(f"Heard '{heard_text}', best match is " f"'{best_match[0] if best_match else None}' " f"with score {best_match[1] if best_match else 0}")

                    if best_match and best_match[1] > 75:
                        self.guest_names.append(best_match[0])
                        self.current_step = self.Steps.ASK_FOR_DRINK
                    else:
                        self.current_step = self.Steps.ASK_NAME_AGAIN

            case self.Steps.ASK_NAME_AGAIN:
                if self.skills_manager.execute("Speak", text="Sorry, I did not understand. Could you please repeat it?"):
                    self.current_step = self.Steps.HEAR_NAME

            case self.Steps.ASK_FOR_DRINK:
                if self.skills_manager.execute("Speak", text="What would you like to drink?"):
                    self.current_step = self.Steps.HEAR_DRINK

            case self.Steps.HEAR_DRINK:
                if self.skills_manager.execute("Hear", context=self.known_drinks):
                    heard_text = self.skills_manager.get_skill_object("Hear").get_heard_text()

                    best_match = process.extractOne(heard_text, self.known_drinks, scorer=fuzz.WRatio)

                    self.get_logger().info(f"Heard '{heard_text}', best match is " f"'{best_match[0] if best_match else None}' " f"with score {best_match[1] if best_match else 0}")

                    if best_match and best_match[1] > 75:
                        self.guest_drinks.append(best_match[0])
                        self.current_step = self.Steps.INFO_REGISTER_GUEST
                    else:
                        self.current_step = self.Steps.ASK_DRINK_AGAIN

            case self.Steps.ASK_DRINK_AGAIN:
                if self.skills_manager.execute("Speak", text="Sorry, I did not understand. Could you please repeat it?"):
                    self.current_step = self.Steps.HEAR_DRINK

            case self.Steps.INFO_REGISTER_GUEST:
                if self.skills_manager.execute(
                    "Speak", text=f"Thank you {self.guest_names[-1]}, I will register your face and remember that you like {self.guest_drinks[-1]}. Please look at the camera."
                ):
                    self.current_step = self.Steps.REGISTER_GUEST

            case self.Steps.REGISTER_GUEST:
                guest_name = self.guest_names[-1] if self.guest_names else "Guest"
                if self.skills_manager.execute("RegisterFace", name=guest_name):
                    self.current_step = self.Steps.COME_WITH_ME

            case self.Steps.COME_WITH_ME:
                if self.skills_manager.execute("Speak", text="Please follow me to the meeting room."):
                    self.current_step = self.Steps.GO_TO_MEETING_ROOM

            case self.Steps.GO_TO_MEETING_ROOM:
                if self.skills_manager.execute("GoToLocation", location_name="meeting_room"):
                    self.current_step = self.Steps.RECOGNIZE_EMPTY_SEAT

            case self.Steps.RECOGNIZE_EMPTY_SEAT:
                if self.skills_manager.execute("RecognizeEmptyPlace"):
                    self.current_step = self.Steps.POINT_TO_EMPTY_PLACE

            case self.Steps.POINT_TO_EMPTY_SEAT:
                recognized_empty_seats = self.skills_manager.get_skill_object("RecognizeEmptyPlace").get_recognized_empty_seats()
                if recognized_empty_seats:
                    empty_seat = recognized_empty_seats[0]
                    seat_type = empty_seat["type"]
                    position = empty_seat["position"]
                    self.get_logger().info(f"Recognized empty seat of type '{seat_type}' at position {position}")
                    if self.skills_manager.execute("Point", position=position):
                        if self.count_guests < 2:
                            self.current_step = self.Steps.GO_TO_RECEPTION
                        else:
                            self.current_step = self.Steps.INTRODUCE_GUESTS

            case self.Steps.INTRODUCE_GUESTS:
                time.sleep(3)  # Wait for a moment before starting face recognition
                if not self.skills_manager.execute("RecognizeFaces"):
                    return

                self.recognized_faces = self.skills_manager.get_skill_object("RecognizeFaces").get_recognized_faces()
                self.get_logger().info(f"Recognized {len(self.recognized_faces)} face(s) in meeting room.")

                if self.recognized_faces:
                    self.current_step = self.Steps.INTRODUCE_GUESTS_RELATIVE_POSITION
                else:
                    guest_info = ", ".join([f"{name} who likes {drink}" for name, drink in zip(self.guest_names, self.guest_drinks)])
                    self.introduce_text = f"Welcome to the meeting room. We have {self.count_guests} guests: {guest_info}."
                    self.current_step = self.Steps.INTRODUCE_GUESTS_SPEAK

            case self.Steps.INTRODUCE_GUESTS_RELATIVE_POSITION:
                if not self.skills_manager.execute("RecognizeRelativePosition", objects=self.recognized_faces, target_name="all"):
                    return

                position_text = self.skills_manager.get_skill_object("RecognizeRelativePosition").get_position_text()
                self.get_logger().info(f"Relative position text: {position_text}")

                drink_by_name = {name.lower(): drink for name, drink in zip(self.guest_names, self.guest_drinks)}

                # Sort faces horizontally from robot's left (lower x) to robot's right (higher x)
                sorted_faces = sorted(self.recognized_faces, key=lambda f: f.x_position)
                known_faces = [f for f in sorted_faces if f.name.casefold() != "unknown"]

                if len(sorted_faces) == 2:
                    left_f = sorted_faces[0]  # Person on the robot's left
                    right_f = sorted_faces[1]  # Person on the robot's right

                    left_is_known = left_f.name.casefold() != "unknown"
                    right_is_known = right_f.name.casefold() != "unknown"

                    if left_is_known and right_is_known:
                        left_drink = drink_by_name.get(left_f.name.lower(), "a drink")
                        right_drink = drink_by_name.get(right_f.name.lower(), "a drink")
                        self.introduce_text = f"Welcome to the meeting room. To my left is {left_f.name}, who likes {left_drink}. " f"To my right is {right_f.name}, who likes {right_drink}."
                    elif left_is_known and not right_is_known:
                        left_drink = drink_by_name.get(left_f.name.lower(), "a drink")
                        self.introduce_text = f"Welcome to the meeting room. To my left is {left_f.name}, who likes {left_drink}."
                    elif right_is_known and not left_is_known:
                        right_drink = drink_by_name.get(right_f.name.lower(), "a drink")
                        self.introduce_text = f"Welcome to the meeting room. To my right is {right_f.name}, who likes {right_drink}."
                    else:
                        self.introduce_text = "Welcome to the meeting room. I could not recognize any known faces in front of me."
                elif len(known_faces) == 1:
                    known = known_faces[0]
                    idx = sorted_faces.index(known)
                    if len(sorted_faces) == 1:
                        center_x = known.x_position + getattr(known, "width", 0) / 2.0
                        pos = "to my left" if center_x < 640 / 3.0 else ("in front of me" if center_x < 2.0 * 640 / 3.0 else "to my right")
                    else:
                        pos = f"number {idx + 1} from my left to my right"

                    drink = drink_by_name.get(known.name.lower(), "a drink")
                    self.introduce_text = f"Welcome to the meeting room. {known.name}, who likes {drink}, is {pos}."
                elif len(known_faces) > 1:
                    introductions = []
                    for face in known_faces:
                        idx = sorted_faces.index(face) + 1
                        drink = drink_by_name.get(face.name.lower(), "a drink")
                        introductions.append(f"{face.name} who likes {drink} is number {idx} from my left to my right")
                    self.introduce_text = f"Welcome to the meeting room. I recognized: {', and '.join(introductions)}."
                else:
                    self.introduce_text = "Welcome to the meeting room. I could not recognize any known faces in front of me."

                self.current_step = self.Steps.INTRODUCE_GUESTS_SPEAK

            case self.Steps.INTRODUCE_GUESTS_SPEAK:
                if self.skills_manager.execute("Speak", text=self.introduce_text):
                    self.has_spoken_confirmation = True
                    self.current_step = self.Steps.ASK_FOR_BAG

            case self.Steps.ASK_FOR_BAG:
                if self.skills_manager.execute("Speak", text="Could you please hand me the bag?"):
                    time.sleep(5)  # Wait for the guest to hand over the bag
                    self.current_step = self.Steps.ASK_FOLLOW_HOST

            case self.Steps.ASK_FOLLOW_HOST:
                if self.skills_manager.execute("Speak", text="Please host stand up so I can follow you."):
                    time.sleep(2)  # Wait for the host to stand up
                    self.current_step = self.Steps.FOLLOW_HOST

            case self.Steps.FOLLOW_HOST:
                if not self.skills_manager.execute("RecognizePose"):
                    return

                pose = self.skills_manager.get_skill_object("RecognizePose").get_recognized_pose()

                if not pose:
                    return

                if pose.name == "stop":
                    self.current_step = self.Steps.PUT_BAG_DOWN
                    return

                if pose.name == "no detections":
                    self.get_logger().info("[MISSION] Nenhuma pessoa detectada enquanto procurava o host.")
                    return

                if pose.x1 == 0 and pose.y1 == 0 and pose.x2 == 0 and pose.y2 == 0:
                    self.get_logger().warn("[MISSION] Recebido BBOX zerado (0,0,0,0) — ignorando frame.")
                    return

                self.current_operator_bbox = BoundingBox(x1=int(pose.x1), y1=int(pose.y1), x2=int(pose.x2), y2=int(pose.y2), name="host")

                if not self.skills_manager.execute("RecognizeObjectPosition", bboxes=[self.current_operator_bbox]):
                    return

                positions = self.skills_manager.get_skill_object("RecognizeObjectPosition").get_recognized_object_positions()

                if not positions:
                    self.get_logger().warn("[MISSION] Lista de posições do host vazia.")
                    return

                pos = positions[0]

                if pos.x == 0 and pos.y == 0 and pos.z == 0:
                    self.get_logger().warn("[MISSION] Posição 3D do host inválida (0, 0, 0).")
                    return

                self.current_target_pose = PoseStamped()
                self.current_target_pose.header.frame_id = "base_footprint"
                self.current_target_pose.header.stamp = self.skills_manager.node.get_clock().now().to_msg()

                self.current_target_pose.pose.position.x = float(pos.x)
                self.current_target_pose.pose.position.y = -float(pos.y)
                self.current_target_pose.pose.position.z = 0.0
                self.current_target_pose.pose.orientation.w = 1.0

                self.current_step = self.Steps.GO_TO_ROOM

            case self.Steps.GO_TO_ROOM:
                if self.skills_manager.execute("FollowPerson", target_pose=self.current_target_pose):
                    # Keep updating the host position while following.
                    self.current_step = self.Steps.FOLLOW_HOST

            case self.Steps.PUT_BAG_DOWN:
                if self.skills_manager.execute("Speak", text="Please put the bag off the table."):
                    time.sleep(5)  # Wait for the guest to put down the bag
                    self.current_step = self.Steps.END

            case self.Steps.END:
                if self.skills_manager.execute("Speak", text="mission finished"):
                    self.finished = True
