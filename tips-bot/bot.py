import asyncio
import base64
import json
import logging
import re
import struct
from decimal import Decimal
from typing import Optional

from telegram import Bot, Update, ChatMemberOwner, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply, MessageEntity
from telegram.constants import ParseMode
from telegram.error import TimedOut

import entities as e
import lang
import ton

logger = logging.getLogger(__name__)
bot: Optional[Bot] = None
updates_task: Optional[asyncio.Task] = None

TON_URL = 'ton://transfer/{address}?amount={amount}&text={text}'
TON_URL_CUSTOM = 'ton://transfer/{address}?text={text}'
TIPS = []
CUSTOM_TIP = False
HELP_URL = ''


async def run(token):
    global bot, updates_task
    bot = Bot(token=token)
    await shutdown()
    updates_task = asyncio.create_task(updates_loop())
    logger.info('Bot is running')


async def shutdown():
    if not isinstance(updates_task, asyncio.Task):
        return
    updates_task.cancel()
    await updates_task
    logger.info('Bot is terminated')


async def updates_loop():
    offset = None
    while True:
        try:
            updates = await bot.get_updates(offset=offset, timeout=60, allowed_updates=[
                Update.CHANNEL_POST, Update.MESSAGE, Update.CALLBACK_QUERY
            ])
            for update in updates:
                offset = update.update_id + 1
                if update.channel_post:
                    await handle_channel_post(update.channel_post)
                elif update.message:
                    await handle_message(update.message)
                elif update.callback_query:
                    await handle_callback_query(update.callback_query)
                    await bot.answer_callback_query(update.callback_query.id)
        except TimedOut:
            pass
        except asyncio.CancelledError:
            break
        except Exception as err:
            logger.exception('updates_loop exception: %r', err)
            await asyncio.sleep(1)


async def get_chat_owner(chat_id):
    admins = await bot.get_chat_administrators(chat_id)
    return [admin.user.id for admin in admins if isinstance(admin, ChatMemberOwner)][0]


async def handle_channel_post(channel_post):
    invoice_id = await ton.gen_invoice_id(channel_post.chat.id, channel_post.message_id)
    entities = json.dumps([entity.to_dict() for entity in channel_post.entities])
    await e.objects.execute(
        e.Invoice.update(message=channel_post.text, entities=entities).where(e.Invoice.id == invoice_id)
    )
    await update_funded(invoice_id)


async def update_funded(invoice_id):
    invoice = await e.objects.get(e.Invoice.select().where(e.Invoice.id == invoice_id))
    wallet = await e.objects.scalar(e.Wallet.select(e.Wallet.address))
    buttons = [
        InlineKeyboardButton(text, TON_URL.format(address=wallet, amount=amount, text=invoice_id))
        for text, amount in TIPS
    ]
    if CUSTOM_TIP:
        buttons += [InlineKeyboardButton(lang.CUSTOM_TIP, TON_URL_CUSTOM.format(address=wallet, text=invoice_id))]
    if HELP_URL:
        buttons += [InlineKeyboardButton(lang.HELP_BUTTON, HELP_URL)]
    markup = InlineKeyboardMarkup([buttons])
    bottom_text = lang.TIPS_TEXT_BOTTOM.format(amount=ton.int_to_ton(invoice.funded))
    await bot.edit_message_text(
        text=f'{invoice.message}\n\n{bottom_text}',
        entities=MessageEntity.de_list(json.loads(invoice.entities), bot),
        parse_mode=ParseMode.MARKDOWN,
        chat_id=invoice.chat_id,
        message_id=invoice.message_id,
        reply_markup=markup,
    )


async def handle_message(message):
    if message.reply_to_message:
        return await handle_reply(message)
    if message.text.startswith('/start'):
        await bot.send_message(
            text=lang.START_MESSAGE,
            parse_mode=ParseMode.MARKDOWN,
            chat_id=message.chat.id,
        )
    elif message.text.startswith('/balance'):
        balance = await ton.get_user_available_balance(message.from_user.id)
        await bot.send_message(
            text=lang.BALANCE_MESSAGE.format(amount=balance),
            parse_mode=ParseMode.MARKDOWN,
            chat_id=message.chat.id,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(lang.WITHDRAW_BUTTON, callback_data=WithdrawButton(None).data)
            ]])
        )


async def handle_reply(message):
    if ' ' not in message.text:
        await bot.send_message(
            text=lang.WRONG_MESSAGE,
            parse_mode=ParseMode.MARKDOWN,
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
        )
        return
    address, amount = message.text.split(' ', 1)
    re_amount = re.compile(r'^\d+(\.\d+)?$')
    if re_amount.match(address):
        address, amount = amount, address
    if not re_amount.match(amount):
        await bot.send_message(
            text=lang.INCORRECT_AMOUNT,
            parse_mode=ParseMode.MARKDOWN,
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
        )
        return
    amount = Decimal(amount)
    if amount < ton.MIN_WITHDRAW:
        await bot.send_message(
            text=lang.INCORRECT_AMOUNT,
            parse_mode=ParseMode.MARKDOWN,
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
        )
        return
    if amount > await ton.get_user_available_balance(message.from_user.id):
        await bot.send_message(
            text=lang.NOT_ENOUGH_FUNDS,
            parse_mode=ParseMode.MARKDOWN,
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
        )
        return
    wait_message = await bot.send_message(
        text=lang.SENDING,
        parse_mode=ParseMode.MARKDOWN,
        chat_id=message.chat.id,
        reply_to_message_id=message.message_id,
    )
    await ton.withdraw(user_id=message.from_user.id, address=address, amount=amount)
    await bot.edit_message_text(
        text=lang.WITHDRAW_EXECUTED,
        parse_mode=ParseMode.MARKDOWN,
        chat_id=wait_message.chat.id,
        message_id=wait_message.message_id,
    )


class Button:
    @classmethod
    def from_data(cls, data):
        data = base64.b64decode(data)
        button_id, = struct.unpack('<B', data[:1])
        button_cls = BUTTONS[button_id]
        return button_cls(data[1:])

    def __init__(self, data):
        raise NotImplementedError

    async def click(self, callback_query):
        raise NotImplementedError

    @property
    def data(self):
        raise NotImplementedError


class WithdrawButton(Button):
    def __init__(self, data):
        pass

    async def click(self, callback_query):
        await bot.send_message(
            text=lang.WITHDRAW_MESSAGE,
            parse_mode=ParseMode.MARKDOWN,
            chat_id=callback_query.message.chat.id,
            reply_markup=ForceReply(input_field_placeholder=lang.WITHDRAW_PLACEHOLDER),
        )

    @property
    def data(self):
        return base64.b64encode(struct.pack('<B', 0)).decode()


BUTTONS = [WithdrawButton]


async def handle_callback_query(callback_query):
    data = base64.b64decode(callback_query.data)
    button_id = data[0]
    if button_id >= len(BUTTONS):
        await bot.send_message(
            text=lang.UNKNOWN_BUTTON,
            parse_mode=ParseMode.MARKDOWN,
            chat_id=callback_query.message.chat.id,
            reply_to_message_id=callback_query.message.message_id,
        )
        return
    button = BUTTONS[button_id](data[1:])
    await button.click(callback_query)
