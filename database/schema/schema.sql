PRAGMA foreign_keys = ON;
CREATE TABLE map_nodes (node TEXT PRIMARY KEY, x REAL, y REAL);
CREATE TABLE map_edges (a TEXT REFERENCES map_nodes(node), b TEXT REFERENCES map_nodes(node),
  cost REAL DEFAULT 1, PRIMARY KEY (a, b));
CREATE TABLE products (
  product_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT,
  price REAL NOT NULL CHECK (price >= 0),
  currency TEXT NOT NULL DEFAULT 'INR',
  stock INTEGER NOT NULL CHECK (stock >= 0),
  aisle INTEGER, shelf INTEGER,
  x REAL, y REAL,
  node TEXT REFERENCES map_nodes(node)
);
CREATE TABLE aliases (
  alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL REFERENCES products(product_id),
  alias TEXT NOT NULL,
  script TEXT NOT NULL,      -- latin | tamil | devanagari
  language TEXT NOT NULL     -- en | ta | hi | ta-en
);
CREATE INDEX idx_alias ON aliases(alias);
