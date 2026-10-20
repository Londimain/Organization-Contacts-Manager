import sqlite3

class Database:
    def __init__(self, db_name='contacts.db'):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS responsible_persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                city TEXT,
                position TEXT,
                phone TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rp_id INTEGER,
                name TEXT NOT NULL,
                address TEXT,
                phone TEXT,
                FOREIGN KEY(rp_id) REFERENCES responsible_persons(id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER,
                name TEXT NOT NULL,
                unloading_address TEXT,
                phone TEXT,
                FOREIGN KEY(org_id) REFERENCES organizations(id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id INTEGER,
                contact_type TEXT,
                full_name TEXT,
                position TEXT,
                phone TEXT,
                FOREIGN KEY(store_id) REFERENCES stores(id) ON DELETE CASCADE
            )
        ''')
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()

    # --- Responsible Persons ---
    def get_responsible_persons(self):
        self.cursor.execute("SELECT * FROM responsible_persons ORDER BY full_name")
        return self.cursor.fetchall()

    def get_rp(self, rp_id):
        self.cursor.execute("SELECT * FROM responsible_persons WHERE id=?", (rp_id,))
        return self.cursor.fetchone()

    def add_responsible_person(self, full_name, city, position, phone):
        self.cursor.execute(
            "INSERT INTO responsible_persons (full_name, city, position, phone) VALUES (?, ?, ?, ?)",
            (full_name, city, position, phone)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def update_responsible_person(self, rp_id, full_name, city, position, phone):
        self.cursor.execute(
            "UPDATE responsible_persons SET full_name=?, city=?, position=?, phone=? WHERE id=?",
            (full_name, city, position, phone, rp_id)
        )
        self.conn.commit()

    def delete_responsible_person(self, rp_id):
        self.cursor.execute("DELETE FROM responsible_persons WHERE id=?", (rp_id,))
        self.conn.commit()

    # --- Organizations ---
    def get_organizations(self, rp_id):
        self.cursor.execute("SELECT * FROM organizations WHERE rp_id=? ORDER BY name", (rp_id,))
        return self.cursor.fetchall()

    def get_org(self, org_id):
        self.cursor.execute("SELECT * FROM organizations WHERE id=?", (org_id,))
        return self.cursor.fetchone()

    def add_organization(self, rp_id, name, address, phone):
        self.cursor.execute(
            "INSERT INTO organizations (rp_id, name, address, phone) VALUES (?, ?, ?, ?)",
            (rp_id, name, address, phone)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def update_organization(self, org_id, name, address, phone):
        self.cursor.execute(
            "UPDATE organizations SET name=?, address=?, phone=? WHERE id=?",
            (name, address, phone, org_id)
        )
        self.conn.commit()

    def delete_organization(self, org_id):
        self.cursor.execute("DELETE FROM organizations WHERE id=?", (org_id,))
        self.conn.commit()

    # --- Stores ---
    def get_stores(self, org_id):
        self.cursor.execute("SELECT * FROM stores WHERE org_id=? ORDER BY name", (org_id,))
        return self.cursor.fetchall()

    def get_store(self, store_id):
        self.cursor.execute("SELECT * FROM stores WHERE id=?", (store_id,))
        return self.cursor.fetchone()

    def add_store(self, org_id, name, address, phone):
        self.cursor.execute(
            "INSERT INTO stores (org_id, name, unloading_address, phone) VALUES (?, ?, ?, ?)",
            (org_id, name, address, phone)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def update_store(self, store_id, name, address, phone):
        self.cursor.execute(
            "UPDATE stores SET name=?, unloading_address=?, phone=? WHERE id=?",
            (name, address, phone, store_id)
        )
        self.conn.commit()

    def delete_store(self, store_id):
        self.cursor.execute("DELETE FROM stores WHERE id=?", (store_id,))
        self.conn.commit()

    # --- Contacts ---
    def get_contacts(self, store_id, contact_type=None):
        if contact_type:
            self.cursor.execute("SELECT * FROM contacts WHERE store_id=? AND contact_type=? ORDER BY full_name", (store_id, contact_type))
        else:
            self.cursor.execute("SELECT * FROM contacts WHERE store_id=? ORDER BY full_name", (store_id,))
        return self.cursor.fetchall()

    def get_all_contacts(self, store_id):
        self.cursor.execute("SELECT * FROM contacts WHERE store_id=?", (store_id,))
        return self.cursor.fetchall()

    def get_contact(self, contact_id):
        self.cursor.execute("SELECT * FROM contacts WHERE id=?", (contact_id,))
        return self.cursor.fetchone()

    def add_contact(self, store_id, contact_type, full_name, position, phone):
        self.cursor.execute(
            "INSERT INTO contacts (store_id, contact_type, full_name, position, phone) VALUES (?, ?, ?, ?, ?)",
            (store_id, contact_type, full_name, position, phone)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def update_contact(self, contact_id, full_name, position, phone):
        self.cursor.execute(
            "UPDATE contacts SET full_name=?, position=?, phone=? WHERE id=?",
            (full_name, position, phone, contact_id)
        )
        self.conn.commit()

    def delete_contact(self, contact_id):
        self.cursor.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
        self.conn.commit()