import asyncio
import itertools
from typing import Tuple, Dict, List, Iterator, AsyncIterator

from aioetherscan.exceptions import EtherscanClientApiError


class Utils:
    """Helper methods which use the combination of documented APIs."""

    def __init__(self, client):
        self._client = client

    async def token_transfers_generator(
            self,
            contract_address: str,
            be_polite: bool = True,
            block_limit: int = 50,
            offset: int = 3,
            start_block: int = 0,
            end_block: int = None,
    ) -> AsyncIterator[Dict]:
        if not end_block:
            end_block = int(await self._client.proxy.block_number(), 16)

        if be_polite:
            for sblock, eblock in self._generate_intervals(start_block, end_block, block_limit):
                result = await self._parse_by_pages(contract_address, sblock, eblock, offset)
                for t in result:
                    yield t
        else:
            tasks = [
                self._parse_by_pages(contract_address, sblock, eblock, offset)
                for sblock, eblock in self._generate_intervals(start_block, end_block, block_limit)
            ]
            result = await asyncio.gather(*tasks)
            for t in itertools.chain.from_iterable(result):
                yield t

    async def token_transfers(
            self,
            contract_address: str,
            be_polite: bool = True,
            block_limit: int = 50,
            offset: int = 3,
            start_block: int = 0,
            end_block: int = None,
    ) -> List[Dict]:
        kwargs = {k: v for k, v in locals().items() if k != 'self' and not k.startswith('_')}
        return [t async for t in self.token_transfers_generator(**kwargs)]

    async def _parse_by_pages(self, contract_address: str, start_block: int, end_block: int, offset: int) -> List[Dict]:
        page, result = 1, []
        while True:
            try:
                transfers = await self._client.account.token_transfers(
                    contract_address=contract_address,
                    start_block=start_block,
                    end_block=end_block,
                    page=page,
                    offset=offset
                )
            except EtherscanClientApiError as e:
                if e.message == 'No transactions found':
                    break
                raise
            else:
                result.extend(transfers)
                page += 1

        return result

    @staticmethod
    def _generate_intervals(from_number: int, to_number: int, count: int) -> Iterator[Tuple[int, int]]:
        for i in range(from_number, to_number + 1, count):
            yield (i, min(i + count - 1, to_number))
