import io
import pickle
from typing import Type, Union

from common.packet import (
    AssignIdPacket,
    SendPasswordPacket,
    ImagePacket,
    KeyBoardPacket,
    MousePacket,
    PacketType,
    RequestConnectionPacket,
    RequestPasswordPacket,
    ResponseConnectionPacket,
)


class SafeDeserializer:

    ALLOWED_PACKET_CLASSES = {
        "ImagePacket": ImagePacket,
        "KeyBoardPacket": KeyBoardPacket,
        "MousePacket": MousePacket,
        "AssignIdPacket": AssignIdPacket,
        "SendPasswordPacket": SendPasswordPacket,
        "RequestPasswordPacket": RequestPasswordPacket,
        "RequestConnectionPacket": RequestConnectionPacket,
        "ResponseConnectionPacket": ResponseConnectionPacket,
        "PacketType": PacketType,
    }

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
    def safe_loads(cls, data: bytes) -> Union[
        ImagePacket,
        KeyBoardPacket,
        MousePacket,
        AssignIdPacket,
        SendPasswordPacket,
        RequestConnectionPacket,
        ResponseConnectionPacket,
        RequestPasswordPacket,
    ]:
        """
        Deserializes data with whitelist protection
        """
        try:
            unpickler = cls.SafeUnpickler(io.BytesIO(data), cls.ALLOWED_PACKET_CLASSES)
            packet = unpickler.load()
        except (pickle.PickleError, pickle.UnpicklingError, EOFError) as e:
            raise ValueError(f"Failed to deserialize packet: {e}")

        if not hasattr(packet, "packet_type"):
            raise ValueError("Deserialized object is missing packet_type attribute")

        if not isinstance(
            packet,
            (
                ImagePacket,
                KeyBoardPacket,
                MousePacket,
                AssignIdPacket,
                SendPasswordPacket,
                RequestConnectionPacket,
                ResponseConnectionPacket,
                RequestPasswordPacket,
            ),
        ):
            raise ValueError(
                f"Deserialized object is not a valid packet type: {type(packet)}"
            )

        return packet
