from network.channel_manager import ChannelManager


class ChannelCommands:

    def __init__(self, channel_manager):
        self.channel_manager = channel_manager

    def create(self, arguments=None):
        """
        Create a new SHAC channel.
        """

        channel = self.channel_manager.create_channel()

        print()
        print("=" * 60)
        print("SHAC CHANNEL CREATED")
        print("=" * 60)
        print()

        print(f"Channel ID : {channel.channel_id}")
        print(f"Transport  : {channel.transport_type}")
        print()

        print("Credential:")
        print(channel.credential)

        print()
        print("Channel is active.")
        print()

    def list(self, arguments=None):
        """
        List all SHAC channels.
        """

        channels = self.channel_manager.list_channels()

        print()
        print("SHAC CHANNELS")
        print("=" * 60)

        if not channels:
            print()
            print("No channels found.")
            print()
            return

        print()

        for channel in channels:

            status = (
                "ACTIVE"
                if channel.is_active()
                else "INACTIVE"
            )

            print(
                f"{channel.channel_id:<20}"
                f"{channel.transport_type:<10}"
                f"{status}"
            )

        print()

    def show(self, arguments=None):
        """
        Show detailed information about a channel.
        """

        if not arguments:
            print()
            print(
                "Usage: shac channel show <channel_id>"
            )
            print()
            return

        channel_id = arguments[0]

        try:
            channel = self.channel_manager.get_channel(
                channel_id
            )

        except ValueError as error:
            print()
            print(f"[ERROR] {error}")
            print()
            return

        print()
        print("SHAC CHANNEL")
        print("=" * 60)
        print()

        print(f"Channel ID : {channel.channel_id}")
        print(f"Transport  : {channel.transport_type}")
        print(f"Endpoint   : {channel.endpoint}")
        print(
            f"Status     : "
            f"{'ACTIVE' if channel.is_active() else 'INACTIVE'}"
        )
        print()

    def revoke(self, arguments=None):
        """
        Revoke an active channel.
        """

        if not arguments:
            print()
            print(
                "Usage: shac channel revoke <channel_id>"
            )
            print()
            return

        channel_id = arguments[0]

        try:
            self.channel_manager.invalidate_channel(
                channel_id
            )

        except ValueError as error:
            print()
            print(f"[ERROR] {error}")
            print()
            return

        print()
        print(
            f"Channel {channel_id} has been revoked."
        )
        print()