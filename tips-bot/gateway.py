import json
import logging
from decimal import Decimal

import aiohttp
from aiohttp import FormData

import entities as e
import ton

ENTRYPOINT = ''
TRACKING_ENTRYPOINT = ''

logger = logging.getLogger(__name__)


async def _request(session, url, method, *, query=None, form=None, data=None, bearer=None):
    if form is not None:
        form = FormData(form)
    params = {
        'params': query,
        'json' if isinstance(data, dict) else 'data': data or form,
    }
    if bearer is not None:
        params['headers']['Authorization'] = f'Bearer {bearer}'
    async with session.request(method.upper(), url, **params) as resp:
        if resp.status != 200:
            raise RuntimeError(f'{resp.status} {resp.reason}')
        return await resp.text()


async def start_tracking():
    wallets = await e.objects.execute(e.Wallet.select())
    for wallet in wallets:
        await track_wallet(wallet)


async def track_wallet(wallet):
    async with aiohttp.ClientSession() as session:
        url = f'{ENTRYPOINT}/startPaymentTracking'
        data = {
            'address': wallet.address,
            'callbackUrl': TRACKING_ENTRYPOINT,
            'trackingState': json.loads(wallet.state) or 'current',
        }
        result = await _request(session, url, 'post', data=data)
        logging.info('Tracking wallet %s: %s', wallet.address, result)
        return result


async def send(*, from_address, private_key, to_address, amount, text=None):
    if isinstance(amount, Decimal):
        amount = ton.ton_to_int(amount)
    async with aiohttp.ClientSession() as session:
        url = f'{ENTRYPOINT}/send'
        data = {
            'sourceAddress': from_address,
            'sourceKey': private_key,
            'destinationAddress': to_address,
            'amount': amount,
            'senderPaysFees': False,
        }
        if text is not None:
            data['message'] = text
        return json.loads(await _request(session, url, 'post', data=data))
