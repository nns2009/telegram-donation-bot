#!/usr/bin/env python3
import argparse
import asyncio
import json
import logging
import signal
import sys

import async_timeout

import bot
import entities as e
import gateway
import server

CONFIG = 'config.json'

toolbox = None
logger = logging.getLogger(__name__)


async def run(cfg_file):
    try:
        with open(cfg_file) as file:
            config = json.load(file)
        e.database.init(config['database'])
        if not e.database.get_tables():
            e.database.create_tables([e.Invoice, e.Wallet, e.Transaction, e.User])
        gateway.ENTRYPOINT = config['ton_gateway']
        gateway.TRACKING_ENTRYPOINT = f'http://{config["host"]}:{config["port"]}/tracking'
        await bot.run(config['bot_token'])
        await server.run(config['host'], config['port'])
        await gateway.start_tracking()
    except Exception:
        await stop()
        raise


async def stop():
    try:
        await server.shutdown()
        await bot.shutdown()
        await e.objects.close()
        logger.info('Goodbye')
        tasks = [t for t in asyncio.all_tasks() if not t.done() and t != asyncio.current_task()]
        logger.info('Remaining tasks: %r', tasks)
        async with async_timeout.timeout(5):
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as err:
        logger.exception('Exception during stopping bot: %r', err)
    finally:
        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str, default=CONFIG, nargs='?')
    parser.add_argument('log_file', type=str, nargs='?')
    args = parser.parse_args()
    logger_options = {
        'level': logging.INFO,
        'format': '%(asctime)s %(levelname)-8s %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
    }
    if args.log_file:
        logger_options.update({
            'filename': args.log_file,
            'filemode': 'a',
        })
        sys.stderr = sys.stdout = open(args.log_file, 'a')
    logging.basicConfig(**logger_options)
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(run(args.config))
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame), lambda: asyncio.ensure_future(stop()))
    loop.run_forever()
    loop.close()
