import io
import pickle
from typing import Type

from common.packets import Packet
from common.enums import (
    PacketType,
    KeyBoardType,
    KeyBoardEventType,
    MouseEventType,
    MouseButton,
    Status,
)


class SafeDeserializer:

    ALLOWED_CLASSES = {cls.__name__: cls for cls in Packet.__args__}
    ALLOWED_CLASSES[PacketType.__name__] = PacketType
    ALLOWED_CLASSES[KeyBoardType.__name__] = KeyBoardType
    ALLOWED_CLASSES[KeyBoardEventType.__name__] = KeyBoardEventType
    ALLOWED_CLASSES[MouseEventType.__name__] = MouseEventType
    ALLOWED_CLASSES[MouseButton.__name__] = MouseButton
    ALLOWED_CLASSES[Status.__name__] = Status

    class SafeUnpickler(pickle.Unpickler):
        def __init__(self, file, allowed_classes: dict[str, Type]):
            super().__init__(file)
            self.allowed_classes = allowed_classes

        def find_class(self, module: str, name: str) -> Type:
            """
            Override find_class để kiểm tra whitelist
            """
            if name in self.allowed_classes:
                return self.allowed_classes[name]

            raise pickle.UnpicklingError(
                f"Class {module}.{name} is not allowed for deserialization"
            )

    @classmethod
    def safe_loads(cls, data: bytes) -> Packet:
        """
        Deserializes data with whitelist protection
        """
        try:
            unpickler = cls.SafeUnpickler(io.BytesIO(data), cls.ALLOWED_CLASSES)
            packet = unpickler.load()
        except (pickle.PickleError, pickle.UnpicklingError, EOFError) as e:
            raise ValueError(f"Failed to deserialize packet: {e}")

        if not hasattr(packet, "packet_type"):
            raise ValueError("Deserialized object is missing packet_type attribute")

        if not isinstance(packet, (Packet, PacketType)):
            raise ValueError(
                f"Deserialized object is not a valid packet type: {type(packet)}"
            )

        return packet
