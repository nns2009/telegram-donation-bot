import json
import logging

from aiohttp import web

import entities as e
import ton

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()
app = web.Application()
runner = web.AppRunner(app, lingering_time=0)


async def run(host, port):
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)
    await site.start()
    logger.info(f'Web server is running on {host}:{port}')


async def shutdown():
    await runner.cleanup()
    logger.info('Web server is terminated')


@routes.post(r'/tracking')
async def handle_tracking(request):
    data = await request.json()
    async with e.objects.atomic():
        if 'nextTrackingState' in data:
            await e.objects.execute(
                e.Wallet.update(state=json.dumps(data['nextTrackingState'])).where(e.Wallet.address == data['address'])
            )
        for payment in data['payments']:
            await ton.new_tip(
                invoice_id=payment['message'],
                address=data['address'],
                amount=payment['amount'],
            )
    return web.Response(text='ok')


app.add_routes(routes)
