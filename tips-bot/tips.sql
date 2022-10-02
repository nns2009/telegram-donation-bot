BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "wallet" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	"address"	TEXT NOT NULL,
	"private_key"	TEXT,
	"state"	TEXT
);
CREATE TABLE IF NOT EXISTS "invoice" (
	"id"	TEXT NOT NULL,
	"chat_id"	INTEGER NOT NULL,
	"message_id"	INTEGER NOT NULL,
	"funded"	INTEGER NOT NULL DEFAULT 0,
	"message"	TEXT NOT NULL DEFAULT '',
	"entities"	TEXT NOT NULL DEFAULT '',
	PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "user" (
	"id"	INTEGER NOT NULL,
	"balance"	INTEGER NOT NULL DEFAULT 0,
	PRIMARY KEY("id")
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS "transaction" (
	"user_id"	INTEGER NOT NULL,
	"date"	INTEGER NOT NULL,
	"amount"	INTEGER NOT NULL,
	"wallet_id"	INTEGER NOT NULL,
	"invoice_id"	TEXT,
	"seqno"	TEXT,
	FOREIGN KEY("invoice_id") REFERENCES "invoice"("id"),
	FOREIGN KEY("wallet_id") REFERENCES "wallet"("id")
);
CREATE INDEX IF NOT EXISTS "wallet_address" ON "wallet" (
	"address"
);
COMMIT;
