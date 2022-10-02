from datetime import datetime

from peewee import IntegerField, Model, TextField, AutoField, ForeignKeyField
from peewee_async import Manager

from async_sqlite import SqliteDatabase

database = SqliteDatabase(None)
objects = Manager(database)


class UTCDateTimeField(IntegerField):
    def db_value(self, value):
        if not value:
            return super().db_value(value)
        return datetime.timestamp(value)

    def python_value(self, value):
        if not value:
            return super().python_value(value)
        return datetime.fromtimestamp(value)


class BaseModel(Model):
    class Meta:
        database = database
        only_save_dirty = True


class Invoice(BaseModel):
    id = TextField(primary_key=True)
    chat_id = IntegerField()
    message_id = IntegerField()
    funded = IntegerField()
    message = TextField()
    entities = TextField()

    class Meta:
        db_table = 'invoice'

    def __repr__(self):
        return f'Invoice(id={self.id}, chat_id={self.chat_id}, message_id={self.message_id}), fuded={self.funded}, ' \
               f'message={self.message}), entities={self.entities})'


class Wallet(BaseModel):
    id = TextField(primary_key=True)
    address = TextField()
    private_key = TextField()
    state = TextField(null=True)

    class Meta:
        db_table = 'wallet'

    def __repr__(self):
        return f'Wallet(id={self.id}, address={self.address}, private_key={self.private_key}, state={self.state})'


class Transaction(BaseModel):
    rowid = AutoField(primary_key=True)
    user_id = IntegerField()
    date = UTCDateTimeField()
    amount = IntegerField()
    wallet = ForeignKeyField(model=Wallet, column_name='wallet_id', field='id', index=True)
    invoice = ForeignKeyField(null=True, model=Invoice, column_name='invoice_id', field='id')
    seqno = TextField(null=True)

    class Meta:
        db_table = 'transaction'

    def __repr__(self):
        return f'Transaction(rowid={self.rowid}, user_id={self.user_id}, date={self.date}, amount={self.amount}, ' \
               f'wallet={self.wallet}, invoice={self.invoice}, seqno={self.seqno})'


class User(BaseModel):
    id = IntegerField(primary_key=True)
    balance = IntegerField(default=0)

    class Meta:
        db_table = 'user'

    def __repr__(self):
        return f'User(id={self.id}, balance={self.balance})'
