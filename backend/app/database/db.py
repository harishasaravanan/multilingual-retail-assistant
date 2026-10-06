"""SQLite loader and product lookup for the retail data (SAD section 8).

Build a database from the CSV seed files:
    cd backend && python -m app.database.db            # writes ../retail.db (git-ignored)
"""
import csv
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_DIR = REPO_ROOT / "database"


def _rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            yield {k.strip(): (v or "").strip() for k, v in row.items()}


def _num(value):
    """249.0 -> 249 so JSON matches the API examples."""
    return int(value) if value is not None and float(value) == int(value) else value


def build_db(db_path=":memory:", db_dir=DB_DIR):
    """Create the schema and load every seed file. Returns an open connection."""
    db_dir = Path(db_dir)
    # The web layer runs on a different thread than the one that builds the DB.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript((db_dir / "schema" / "schema.sql").read_text(encoding="utf-8"))
    seed = db_dir / "seed"

    conn.executemany(
        "INSERT INTO map_nodes (node, x, y) VALUES (?, ?, ?)",
        [(r["node"], float(r["x"]), float(r["y"])) for r in _rows(seed / "map_nodes.csv")],
    )
    # Tier 1: each row is one undirected walkable link.
    conn.executemany(
        "INSERT INTO map_edges (a, b, cost) VALUES (?, ?, ?)",
        [(r["a"], r["b"], float(r["cost"])) for r in _rows(seed / "map_edges.csv")],
    )
    conn.executemany(
        "INSERT INTO products (product_id, name, category, price, currency, stock,"
        " aisle, shelf, x, y, node) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (r["product_id"], r["name"], r["category"], float(r["price"]), r["currency"],
             int(r["stock"]), int(r["aisle"]), int(r["shelf"]), float(r["x"]), float(r["y"]),
             r["node"])
            for r in _rows(db_dir / "sample_products.csv")
        ],
    )
    conn.executemany(
        "INSERT INTO aliases (product_id, alias, script, language) VALUES (?,?,?,?)",
        [(r["product_id"], r["alias"], r["script"], r["language"])
         for r in _rows(seed / "aliases.csv")],
    )
    conn.commit()
    return conn


def get_product(conn, product_id):
    """Return the /find-product fields (without the route), or None if unknown."""
    row = conn.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()
    if row is None:
        return None
    return {
        "product_id": row["product_id"],
        "product": row["name"],
        "available": row["stock"] > 0,
        "stock": row["stock"],
        "price": _num(row["price"]),
        "currency": row["currency"],
        "aisle": row["aisle"],
        "shelf": row["shelf"],
        "x": _num(row["x"]),
        "y": _num(row["y"]),
        "node": row["node"],
    }


if __name__ == "__main__":
    out = REPO_ROOT / "retail.db"
    if out.exists():
        sys.exit(f"{out} already exists; delete it first if you want to rebuild.")
    c = build_db(out)
    n = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    a = c.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
    print(f"Built {out}: {n} products, {a} aliases")
