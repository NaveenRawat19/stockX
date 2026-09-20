from abc import ABC, abstractmethod


class ExchangeProvider(ABC):

    @abstractmethod
    async def get_equity_universe(self):
        pass