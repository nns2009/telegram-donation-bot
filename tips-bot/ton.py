import base64
import struct
from datetime import datetime, timezone
from decimal import Decimal

from telegram.error import BadRequest

import bot
import entities as e
import gateway

FEE = Decimal('1')
MIN_WITHDRAW = Decimal('0.5')


async def gen_invoice_id(chat_id, message_id):
    data = struct.pack('<qi', chat_id, message_id)
    invoice_id = base64.urlsafe_b64encode(data).decode()
    await e.objects.create(e.Invoice, id=invoice_id, chat_id=chat_id, message_id=message_id)
    return invoice_id


def int_to_ton(value):
    return Decimal(value) / 10 ** 9


def ton_to_int(value):
    return int(Decimal(value) * 10 ** 9)


def now_utc():
    return datetime.now().astimezone(timezone.utc)


async def get_user_available_balance(user_id):
    balance = await e.objects.scalar(e.User.select(e.User.balance).where(e.User.id == user_id)) or 0
    return int_to_ton(balance)


async def new_tip(*, invoice_id, address, amount):
    invoice = await e.objects.get(e.Invoice, id=invoice_id)
    user_id = await bot.get_chat_owner(invoice.chat_id)
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
        user.balance += amount * (1 - FEE / 100)
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
