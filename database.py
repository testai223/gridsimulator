"""Simple SQLite database layer for storing grid data."""

import sqlite3
import json
import pandapower as pp
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime


class GridDatabase:
    """Manage grid data using an SQLite database."""

    def __init__(self, path: str = "grid.db") -> None:
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self.conn.cursor()
        
        # Create grids table to store different grid configurations
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS grids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_date TEXT NOT NULL,
                modified_date TEXT NOT NULL,
                grid_data TEXT NOT NULL,
                is_example BOOLEAN DEFAULT 0
            )
            """
        )
        
        # Create bus table with grid_id reference
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grid_id INTEGER,
                name TEXT NOT NULL,
                vn_kv REAL NOT NULL,
                FOREIGN KEY(grid_id) REFERENCES grids(id) ON DELETE CASCADE
            )
            """
        )
        
        # Create line table with grid_id reference
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS line (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grid_id INTEGER,
                from_bus INTEGER NOT NULL,
                to_bus INTEGER NOT NULL,
                length_km REAL NOT NULL,
                r_ohm_per_km REAL NOT NULL,
                x_ohm_per_km REAL NOT NULL,
                c_nf_per_km REAL NOT NULL,
                max_i_ka REAL NOT NULL,
                FOREIGN KEY(grid_id) REFERENCES grids(id) ON DELETE CASCADE,
                FOREIGN KEY(from_bus) REFERENCES bus(id),
                FOREIGN KEY(to_bus) REFERENCES bus(id)
            )
            """
        )
        
        # Create analysis_results table to store contingency analysis results
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grid_id INTEGER NOT NULL,
                analysis_type TEXT NOT NULL,
                analysis_date TEXT NOT NULL,
                results_data TEXT NOT NULL,
                FOREIGN KEY(grid_id) REFERENCES grids(id) ON DELETE CASCADE
            )
            """
        )
        
        self.conn.commit()

    def save_grid(self, name: str, net: pp.pandapowerNet, description: str = "", is_example: bool = False) -> int:
        """Save a pandapower network to the database."""
        cur = self.conn.cursor()
        
        # Convert pandapower network to JSON
        grid_data = pp.to_json(net)
        current_time = datetime.now().isoformat()
        
        try:
            cur.execute(
                """
                INSERT INTO grids (name, description, created_date, modified_date, grid_data, is_example)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, description, current_time, current_time, grid_data, is_example)
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            # Grid name already exists, update it
            cur.execute(
                """
                UPDATE grids SET description = ?, modified_date = ?, grid_data = ?, is_example = ?
                WHERE name = ?
                """,
                (description, current_time, grid_data, is_example, name)
            )
            self.conn.commit()
            cur.execute("SELECT id FROM grids WHERE name = ?", (name,))
            return cur.fetchone()[0]

    def load_grid(self, grid_id: int) -> Optional[pp.pandapowerNet]:
        """Load a pandapower network from the database."""
        cur = self.conn.cursor()
        cur.execute("SELECT grid_data FROM grids WHERE id = ?", (grid_id,))
        result = cur.fetchone()
        
        if result:
            try:
                grid_data = result[0]
                net = pp.from_json_string(grid_data)
                
                # Validate the loaded network
                if not hasattr(net, 'bus') or len(net.bus) == 0:
                    raise ValueError("Loaded network has no buses")
                
                return net
            except Exception as e:
                print(f"Error loading grid {grid_id}: {e}")
                raise Exception(f"Failed to deserialize grid data: {e}")
        return None

    def load_grid_by_name(self, name: str) -> Optional[pp.pandapowerNet]:
        """Load a pandapower network by name from the database."""
        cur = self.conn.cursor()
        cur.execute("SELECT grid_data FROM grids WHERE name = ?", (name,))
        result = cur.fetchone()
        
        if result:
            try:
                grid_data = result[0]
                net = pp.from_json_string(grid_data)
                
                # Validate the loaded network
                if not hasattr(net, 'bus') or len(net.bus) == 0:
                    raise ValueError("Loaded network has no buses")
                
                return net
            except Exception as e:
                print(f"Error loading grid '{name}': {e}")
                raise Exception(f"Failed to deserialize grid data: {e}")
        return None

    def get_all_grids(self) -> List[Tuple[int, str, str, str, str, bool]]:
        """Get list of all saved grids."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, description, created_date, modified_date, is_example FROM grids ORDER BY is_example DESC, modified_date DESC"
        )
        return cur.fetchall()

    def delete_grid(self, grid_id: int) -> bool:
        """Delete a grid and all associated data."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM grids WHERE id = ?", (grid_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def save_analysis_results(self, grid_id: int, analysis_type: str, results_data: Dict[str, Any]) -> int:
        """Save contingency analysis results."""
        cur = self.conn.cursor()
        analysis_date = datetime.now().isoformat()
        results_json = json.dumps(results_data)
        
        cur.execute(
            """
            INSERT INTO analysis_results (grid_id, analysis_type, analysis_date, results_data)
            VALUES (?, ?, ?, ?)
            """,
            (grid_id, analysis_type, analysis_date, results_json)
        )
        self.conn.commit()
        return cur.lastrowid

    def get_analysis_results(self, grid_id: int, analysis_type: str = None) -> List[Tuple[int, str, str, Dict[str, Any]]]:
        """Get analysis results for a grid."""
        cur = self.conn.cursor()
        if analysis_type:
            cur.execute(
                "SELECT id, analysis_type, analysis_date, results_data FROM analysis_results WHERE grid_id = ? AND analysis_type = ? ORDER BY analysis_date DESC",
                (grid_id, analysis_type)
            )
        else:
            cur.execute(
                "SELECT id, analysis_type, analysis_date, results_data FROM analysis_results WHERE grid_id = ? ORDER BY analysis_date DESC",
                (grid_id,)
            )
        
        results = []
        for row in cur.fetchall():
            results.append((row[0], row[1], row[2], json.loads(row[3])))
        return results

    def update_grid_description(self, grid_id: int, description: str) -> bool:
        """Update grid description."""
        cur = self.conn.cursor()
        modified_date = datetime.now().isoformat()
        cur.execute(
            "UPDATE grids SET description = ?, modified_date = ? WHERE id = ?",
            (description, modified_date, grid_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def initialize_example_grids(self):
        """Initialize the database with example grids if they don't exist."""
        from examples import create_example_grid, create_ieee_9_bus, create_ieee_39_bus, create_ieee_39_bus_standard
        
        # Check if example grids already exist
        cur = self.conn.cursor()
        
        # Check for each specific example to avoid duplicates
        example_names = [
            "Simple Example Grid",
            "IEEE 9-Bus Test System", 
            "IEEE 39-Bus New England System",
            "IEEE 39-Bus Standard (MATPOWER)"
        ]
        
        # Add example grids if they don't exist
        try:
            # Simple example grid
            cur.execute("SELECT COUNT(*) FROM grids WHERE name = ? AND is_example = 1", ("Simple Example Grid",))
            if cur.fetchone()[0] == 0:
                example_net = create_example_grid()
                self.save_grid("Simple Example Grid", example_net, 
                              "Basic 2-bus system with generator and load", True)
            
            # IEEE 9-bus system
            cur.execute("SELECT COUNT(*) FROM grids WHERE name = ? AND is_example = 1", ("IEEE 9-Bus Test System",))
            if cur.fetchone()[0] == 0:
                ieee9_net = create_ieee_9_bus()
                self.save_grid("IEEE 9-Bus Test System", ieee9_net,
                              "Standard IEEE 9-bus reliability test system", True)
            
            # IEEE 39-bus system  
            cur.execute("SELECT COUNT(*) FROM grids WHERE name = ? AND is_example = 1", ("IEEE 39-Bus New England System",))
            if cur.fetchone()[0] == 0:
                ieee39_net = create_ieee_39_bus()
                self.save_grid("IEEE 39-Bus New England System", ieee39_net,
                              "IEEE 39-bus New England test system for large-scale analysis", True)
            
            # IEEE 39-bus standard system
            cur.execute("SELECT COUNT(*) FROM grids WHERE name = ? AND is_example = 1", ("IEEE 39-Bus Standard (MATPOWER)",))
            if cur.fetchone()[0] == 0:
                ieee39std_net = create_ieee_39_bus_standard()
                self.save_grid("IEEE 39-Bus Standard (MATPOWER)", ieee39std_net,
                              "Standard IEEE 39-bus system based on MATPOWER case39", True)
                          
        except Exception as e:
            print(f"Warning: Could not initialize example grids: {e}")

    # Legacy methods for backward compatibility
    def add_bus(self, name: str, vn_kv: float, grid_id: int = None) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO bus (grid_id, name, vn_kv) VALUES (?, ?, ?)", (grid_id, name, vn_kv))
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
        grid_id: int = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO line (
                grid_id, from_bus, to_bus, length_km, r_ohm_per_km,
                x_ohm_per_km, c_nf_per_km, max_i_ka
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                grid_id,
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

    def get_buses(self, grid_id: int = None) -> List[Tuple[int, str, float]]:
        cur = self.conn.cursor()
        if grid_id:
            cur.execute("SELECT id, name, vn_kv FROM bus WHERE grid_id = ?", (grid_id,))
        else:
            cur.execute("SELECT id, name, vn_kv FROM bus WHERE grid_id IS NULL")
        return cur.fetchall()

    def get_lines(self, grid_id: int = None) -> List[Tuple[int, int, int, float, float, float, float, float]]:
        cur = self.conn.cursor()
        if grid_id:
            cur.execute(
                "SELECT id, from_bus, to_bus, length_km, r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka FROM line WHERE grid_id = ?",
                (grid_id,)
            )
        else:
            cur.execute(
                "SELECT id, from_bus, to_bus, length_km, r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka FROM line WHERE grid_id IS NULL"
            )
        return cur.fetchall()
