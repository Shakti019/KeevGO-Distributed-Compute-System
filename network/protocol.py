import json
import uuid


PROTOCOL_VERSION = 1
MAX_FRAME_SIZE = 64 * 1024


def make_message(message_type, payload=None, request_id=None):
    return {
        "version": PROTOCOL_VERSION,
        "type": message_type,
        "request_id": request_id or uuid.uuid4().hex,
        "payload": payload or {},
    }


def encode_message(message):
    encoded = json.dumps(message, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > MAX_FRAME_SIZE:
        raise ValueError("Message exceeds the maximum frame size.")
    return encoded.encode("utf-8") + b"\n"


def decode_message(line):
    if len(line) > MAX_FRAME_SIZE:
        raise ValueError("Message exceeds the maximum frame size.")
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid JSON message.") from error
    if not isinstance(message, dict):
        raise ValueError("Message must be a JSON object.")
    if message.get("version") != PROTOCOL_VERSION:
        raise ValueError("Unsupported protocol version.")
    if not isinstance(message.get("type"), str):
        raise ValueError("Message type is required.")
    if not isinstance(message.get("payload"), dict):
        raise ValueError("Message payload must be an object.")
    return message


def reply(message, message_type, payload=None):
    return make_message(message_type, payload, request_id=message.get("request_id"))