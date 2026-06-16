# Monkeypatch protobuf MessageFactory.GetPrototype to avoid AttributeError in newer protobuf versions
try:
    from google.protobuf import message_factory
    if not hasattr(message_factory.MessageFactory, "GetPrototype"):
        message_factory.MessageFactory.GetPrototype = lambda self, descriptor: self.GetMessageClass(descriptor)
except ImportError:
    pass
