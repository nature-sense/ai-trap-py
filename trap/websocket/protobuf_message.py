from trap.websocket import protocol_pb2


class ProtobufMessage :
    def __init__(self, identifier, protobuf) :
        self.identifier = identifier
        self.protobuf = protobuf

    def to_protobuf(self):
        prot_msg = protocol_pb2.ProtocolMsg()
        prot_msg.identifier = self.identifier
        prot_msg.protobuf = self.protobuf
        return prot_msg.SerializeToString()

    @staticmethod
    def from_proto(proto):
        prot_msg = protocol_pb2.ProtocolMsg()
        prot_msg.ParseFromString(proto)
        return ProtobufMessage(
            prot_msg.identifier,
            prot_msg.protobuf
        )

