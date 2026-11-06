import secrets
import time
import base64
import json


class Channel:

    def __init__(
        self,
        channel_id,
        credential,
        transport_type="auto",
        endpoint=None
    ):

        self.channel_id = channel_id

        self.credential = credential

        self.transport_type = transport_type

        self.endpoint = endpoint

        self.created_at = time.time()

        self.active = True

    @classmethod
    def create(
        cls,
        transport_type="auto",
        endpoint=None
    ):

        channel_id = cls._generate_channel_id()

        credential = cls._generate_credential()

        return cls(
            channel_id=channel_id,
            credential=credential,
            transport_type=transport_type,
            endpoint=endpoint
        )

    @staticmethod
    def _generate_channel_id():

        random_part = secrets.token_hex(4).upper()

        return f"SWARM-{random_part}"

    @staticmethod
    def _generate_credential():

        return secrets.token_urlsafe(32)

    def create_connection_string(self):

        data = {
            "channel_id": self.channel_id,
            "credential": self.credential,
            "transport": self.transport_type,
            "endpoint": self.endpoint
        }

        json_data = json.dumps(
            data,
            separators=(",", ":")
        )

        encoded = base64.urlsafe_b64encode(
            json_data.encode("utf-8")
        ).decode("utf-8")

        return f"SWARM1.{encoded}"

    @staticmethod
    def parse_connection_string(
        connection_string
    ):

        if not connection_string.startswith(
            "SWARM1."
        ):

            raise ValueError(
                "Invalid swarm connection string."
            )

        encoded = connection_string[
            len("SWARM1.") :
        ]

        try:

            json_data = base64.urlsafe_b64decode(
                encoded.encode("utf-8")
            ).decode("utf-8")

            data = json.loads(json_data)

        except Exception:

            raise ValueError(
                "Invalid connection string."
            )

        required_fields = [
            "channel_id",
            "credential",
            "transport",
            "endpoint"
        ]

        for field in required_fields:

            if field not in data:

                raise ValueError(
                    f"Missing field: {field}"
                )

        return data

    def invalidate(self):

        self.active = False

        self.credential = None

    def is_active(self):

        return self.active

    def __str__(self):

        return (
            f"Channel("
            f"id={self.channel_id}, "
            f"transport={self.transport_type}, "
            f"active={self.active}"
            f")"
        )