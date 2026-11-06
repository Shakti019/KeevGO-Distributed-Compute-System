from network.channel import Channel

class ChannelManager:

    def __init__(self):
        self.channels = {}

    def create_channel(
        self,
        transport_type="auto",
        endpoint=None
    ):
        """
        Create a new swarm channel.
        """

        channel = Channel.create(
            transport_type=transport_type,
            endpoint=endpoint
        )

        self.channels[channel.channel_id] = channel

        print(
            f"[CHANNEL] Created: {channel.channel_id}"
        )

        return channel

    def get_channel(self, channel_id):
        """
        Retrieve a channel using its ID.
        """

        channel = self.channels.get(channel_id)

        if channel is None:
            raise ValueError(
                f"Channel not found: {channel_id}"
            )

        return channel

    def validate_channel(
        self,
        channel_id,
        credential
    ):
        """
        Validate a channel ID and its credential.
        """

        channel = self.channels.get(channel_id)

        if channel is None:
            return False

        if not channel.is_active():
            return False

        if channel.credential != credential:
            return False

        return True

    def invalidate_channel(self, channel_id):
        """
        Permanently deactivate a channel.
        """

        channel = self.get_channel(channel_id)

        channel.invalidate()

        print(
            f"[CHANNEL] Invalidated: {channel_id}"
        )

    def remove_channel(self, channel_id):
        """
        Remove a channel from the manager.
        """

        if channel_id not in self.channels:
            raise ValueError(
                f"Channel not found: {channel_id}"
            )

        del self.channels[channel_id]

        print(
            f"[CHANNEL] Removed: {channel_id}"
        )

    def list_channels(self):
        """
        Return all channel objects.
        """

        return list(self.channels.values())

    def list_active_channels(self):
        """
        Return only active channels.
        """

        return [
            channel
            for channel in self.channels.values()
            if channel.is_active()
        ]

    def channel_exists(self, channel_id):
        """
        Check whether a channel exists.
        """

        return channel_id in self.channels

    def active_channel_count(self):
        """
        Return number of active channels.
        """

        return len(self.list_active_channels())