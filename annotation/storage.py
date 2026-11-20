"""Persistência das anotações em SQLite (biblioteca padrão do Python).

Observação para o Heroku: o sistema de arquivos dos dynos é efêmero, então o
arquivo .db é recriado a cada reinício. Use os botões de exportação (CSV/JSON)
para guardar o trabalho, ou aponte ANNOTATION_DB para um volume persistente.
"""
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "ANNOTATION_DB",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance", "annotations.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS annotations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    domain      TEXT NOT NULL,          -- 'classical' | 'quantum'
    item_id     TEXT NOT NULL,
    annotator   TEXT NOT NULL,
    label       TEXT NOT NULL,          -- rótulo humano
    model_label TEXT NOT NULL,          -- pré-anotação automática
    gold_label  TEXT NOT NULL,          -- gabarito (ground truth)
    seconds     REAL,                   -- tempo gasto na anotação
    created_at  TEXT NOT NULL,
    UNIQUE(domain, item_id, annotator)
);
"""


def _connect():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)


def save(domain, item_id, annotator, label, model_label, gold_label, seconds=None):
    """Insere ou atualiza (re-anotação) o rótulo de um item."""
    with _connect() as conn:
        conn.execute(
            """INSERT INTO annotations
               (domain, item_id, annotator, label, model_label, gold_label, seconds, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(domain, item_id, annotator) DO UPDATE SET
                   label=excluded.label, seconds=excluded.seconds,
                   created_at=excluded.created_at""",
            (domain, item_id, annotator, label, model_label, gold_label, seconds,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )


def fetch(domain, annotator=None):
    sql = "SELECT * FROM annotations WHERE domain = ?"
    args = [domain]
    if annotator:
        sql += " AND annotator = ?"
        args.append(annotator)
    sql += " ORDER BY id"
    with _connect() as conn:
        return [dict(r) for r in conn.execute(sql, args)]


def done_ids(domain, annotator):
    return {r["item_id"] for r in fetch(domain, annotator)}


def clear(domain, annotator=None):
    sql = "DELETE FROM annotations WHERE domain = ?"
    args = [domain]
    if annotator:
        sql += " AND annotator = ?"
        args.append(annotator)
    with _connect() as conn:
        conn.execute(sql, args)
