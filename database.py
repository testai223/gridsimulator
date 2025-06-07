"""Simple SQLite database layer for storing grid data."""

import sqlite3
from typing import List, Tuple


class GridDatabase:
    """Manage grid data using an SQLite database."""

    def __init__(self, path: str = "grid.db") -> None:
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                vn_kv REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS line (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_bus INTEGER NOT NULL,
                to_bus INTEGER NOT NULL,
                length_km REAL NOT NULL,
                r_ohm_per_km REAL NOT NULL,
                x_ohm_per_km REAL NOT NULL,
                c_nf_per_km REAL NOT NULL,
                max_i_ka REAL NOT NULL,
                FOREIGN KEY(from_bus) REFERENCES bus(id),
                FOREIGN KEY(to_bus) REFERENCES bus(id)
            )
            """
        )
        self.conn.commit()

    def add_bus(self, name: str, vn_kv: float) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO bus (name, vn_kv) VALUES (?, ?)", (name, vn_kv))
        self.conn.commit()
        return cur.lastrowid

    def add_line(
        self,
        from_bus: int,
        to_bus: int,
        length_km: float,
        r_ohm_per_km: float,
        x_ohm_per_km: float,
        c_nf_per_km: float,
        max_i_ka: float,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO line (
                from_bus, to_bus, length_km, r_ohm_per_km,
                x_ohm_per_km, c_nf_per_km, max_i_ka
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                from_bus,
                to_bus,
                length_km,
                r_ohm_per_km,
                x_ohm_per_km,
                c_nf_per_km,
                max_i_ka,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_buses(self) -> List[Tuple[int, str, float]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, vn_kv FROM bus")
        return cur.fetchall()

    def get_lines(
        self,
    ) -> List[Tuple[int, int, int, float, float, float, float, float]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, from_bus, to_bus, length_km, r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka FROM line"
        )
        return cur.fetchall()
