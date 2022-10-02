import base64
import decimal
import struct
from datetime import datetime, timezone
from decimal import Decimal

from telegram.error import BadRequest

import bot
import entities as e
import gateway

FEE = Decimal('0.01')
MIN_AMOUNT = Decimal('0.0')


async def get_wallet():
    return await e.objects.scalar(e.Wallet.select(e.Wallet.address))


async def gen_invoice_id(owner_id, chat_id, message_id):
    data = struct.pack('<qqq', owner_id, chat_id, message_id)
    invoice_id = base64.urlsafe_b64encode(data).decode('ascii')
    await e.objects.create(e.Invoice, id=invoice_id, chat_id=chat_id, message_id=message_id)
    return invoice_id


async def get_invoice_data(invoice_id):
    invoice = await e.objects.get(e.Invoice, id=invoice_id)
    return invoice.chat_id, invoice.message_id
    # data = base64.urlsafe_b64decode(invoice_id)
    # return struct.unpack('<qqq', data)


async def get_invoice_amount(invoice_id):
    return await e.objects.scalar(e.Invoice.select(e.Invoice.funded).where(e.Invoice.id == invoice_id))


def int_to_ton(value):
    return Decimal(value) / 10 ** 9


def ton_to_int(value):
    return int(value * 10 ** 9)


def now_utc():
    return datetime.now().astimezone(timezone.utc)


async def get_wallet_state(address):
    return await e.objects.scalar(e.Wallet.select(e.Wallet.state).where(e.Wallet.address == address))


async def get_user_available_balance(user_id):
    balance = await e.objects.scalar(e.User.select(e.User.balance).where(e.User.id == user_id)) or 0
    return int_to_ton(balance)


async def new_tip(*, invoice_id, address, amount):
    chat_id, _ = await get_invoice_data(invoice_id)
    user_id = await bot.get_chat_owner(chat_id)
    wallet = await e.objects.get(e.Wallet, address=address)
    async with e.objects.atomic():
        await e.objects.create(
            e.Transaction,
            user_id=user_id, date=now_utc(), amount=amount, wallet_id=wallet.id, invoice_id=invoice_id
        )
        await e.objects.execute(e.Invoice.update(
            {e.Invoice.funded: e.Invoice.funded + amount}
        ).where(
            e.Invoice.id == invoice_id
        ))
        user, _ = await e.objects.get_or_create(e.User, id=user_id)
        user.balance += amount * (1 - FEE)
        await e.objects.update(user)
    try:
        await bot.update_funded(invoice_id)
    except BadRequest:
        pass


async def withdraw(*, user_id, address, amount):
    amount = ton_to_int(amount)
    wallet = await e.objects.get(e.Wallet.select().limit(1))
    async with e.objects.atomic():
        transaction = await e.objects.create(
            e.Transaction,
            user_id=user_id,
            date=now_utc(),
            amount=amount,
            wallet_id=wallet.id,
        )
        await e.objects.execute(e.User.update(
            {e.User.balance: e.User.balance - amount}
        ).where(
            e.User.id == user_id
        ))
        sent_result = await gateway.send(
            from_address=wallet.address, private_key=wallet.private_key, to_address=address, amount=amount
        )
        transaction.seqno = sent_result['seqno']
        await e.objects.update(transaction)
