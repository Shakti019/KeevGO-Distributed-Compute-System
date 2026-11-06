from abc import ABC, abstractmethod

class Transport(ABC):
    @abstractmethod
    async def connect(self,address):
        pass
    @abstractmethod
    def send(self, data: bytes) -> None:
        pass

    @abstractmethod
    def receive(self) -> bytes:
        pass
    @abstractmethod
    def close(self) -> None:
        pass