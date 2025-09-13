protoc --python_out=trap/cameras/picam3 proto/picam3.proto
protoc --python_out=trap/sessions proto/sessions.proto
protoc --python_out=trap/settings proto/settings.proto
protoc --python_out=trap/websocket proto/protocol.proto
protoc --python_out=trap/workflow proto/control.proto