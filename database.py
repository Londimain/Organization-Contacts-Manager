# database.py
import sqlite3
import logging
from datetime import datetime

log = logging.getLogger('db')

SORT_RP = {
    'name': 'full_name', 'city': 'city', 'position': 'position', 'phone': 'phone',
}
SORT_ORG = {
    'name': 'name', 'city': 'contract_number', 'date': 'contract_date',
    'address': 'address', 'phone': 'phone',
}
SORT_STORE = {
    'name': 'name', 'address': 'unloading_address', 'phone': 'phone',
}
SORT_CONTACT = {
    'name': 'full_name', 'position': 'position', 'phone': 'phone',
}

def _dir(d):
    return 'DESC' if str(d).upper() == 'DESC' else 'ASC'

def _ts():
    return datetime.now().isoformat(timespec='seconds')


class Database:
    def __init__(self, db_name='contacts.db'):
        self.db_name = db_name

    def connect(self):
        # Создаем таблицы при старте программы (вызывается один раз из app.py)
        self._create_tables()

    def close(self):
        # Так как мы открываем/закрываем БД в каждой функции, этот метод больше не нужен,
        # но оставлен для совместимости с app.py
        pass

    def get_data_version(self):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute("PRAGMA data_version")
            return c.fetchone()[0]
        finally:
            conn.close()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        c = conn.cursor()
        try:
            c.execute('''
                CREATE TABLE IF NOT EXISTS responsible_persons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL, city TEXT, position TEXT, phone TEXT,
                    deleted_at TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS organizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rp_id INTEGER, name TEXT NOT NULL, address TEXT, phone TEXT,
                    contract_number TEXT, contract_date TEXT, deleted_at TEXT,
                    FOREIGN KEY(rp_id) REFERENCES responsible_persons(id) ON DELETE CASCADE
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS stores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    org_id INTEGER, name TEXT NOT NULL, unloading_address TEXT,
                    phone TEXT, deleted_at TEXT,
                    FOREIGN KEY(org_id) REFERENCES organizations(id) ON DELETE CASCADE
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_id INTEGER, contact_type TEXT, full_name TEXT,
                    position TEXT, phone TEXT, deleted_at TEXT,
                    FOREIGN KEY(store_id) REFERENCES stores(id) ON DELETE CASCADE
                )
            ''')

            migrations = [
                ('responsible_persons', 'position',     'TEXT'),
                ('responsible_persons', 'phone',        'TEXT'),
                ('responsible_persons', 'deleted_at',   'TEXT'),
                ('organizations',       'address',      'TEXT'),
                ('organizations',       'phone',        'TEXT'),
                ('organizations',       'contract_number', 'TEXT'),
                ('organizations',       'contract_date',   'TEXT'),
                ('organizations',       'deleted_at',   'TEXT'),
                ('stores',              'phone',        'TEXT'),
                ('stores',              'deleted_at',   'TEXT'),
                ('contacts',            'deleted_at',   'TEXT'),
            ]
            for table, col, typedef in migrations:
                c.execute(f"PRAGMA table_info({table})")
                cols = [col_info[1] for col_info in c.fetchall()]
                if col not in cols:
                    log.info(f"Migration: ADD COLUMN {table}.{col}")
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")

            c.execute("PRAGMA table_info(organizations)")
            org_cols = [col_info[1] for col_info in c.fetchall()]
            if 'rp_id' not in org_cols and 'responsible_person_id' in org_cols:
                log.info("Migration: rename organizations.responsible_person_id → rp_id")
                c.execute("ALTER TABLE organizations RENAME COLUMN responsible_person_id TO rp_id")

            c.execute("PRAGMA table_info(stores)")
            st_cols = [col_info[1] for col_info in c.fetchall()]
            if 'org_id' not in st_cols and 'organization_id' in st_cols:
                log.info("Migration: rename stores.organization_id → org_id")
                c.execute("ALTER TABLE stores RENAME COLUMN organization_id TO org_id")

            conn.commit()
        finally:
            conn.close()

    # ---------- Responsible Persons ----------
    def get_responsible_persons(self, sort_key='name', sort_dir='ASC', include_deleted=False):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            col = SORT_RP.get(sort_key, 'full_name')
            where = '' if include_deleted else 'WHERE deleted_at IS NULL'
            c.execute(f"SELECT * FROM responsible_persons {where} ORDER BY {col} {_dir(sort_dir)}")
            return c.fetchall()
        finally:
            conn.close()

    def get_rp(self, rp_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM responsible_persons WHERE id=?", (rp_id,))
            return c.fetchone()
        finally:
            conn.close()

    def add_responsible_person(self, full_name, city, position, phone):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO responsible_persons (full_name, city, position, phone) VALUES (?,?,?,?)",
                (full_name, city, position, phone))
            conn.commit()
            return c.lastrowid
        finally:
            conn.close()

    def update_responsible_person(self, rp_id, full_name, city, position, phone):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE responsible_persons SET full_name=?, city=?, position=?, phone=? WHERE id=?",
                (full_name, city, position, phone, rp_id))
            conn.commit()
        finally:
            conn.close()

    def delete_responsible_person(self, rp_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            c = conn.cursor()
            now = _ts()
            c.execute("SELECT id FROM organizations WHERE rp_id=? AND deleted_at IS NULL", (rp_id,))
            for org in c.fetchall():
                self._soft_delete_org(conn, c, org['id'], now)
            c.execute("UPDATE responsible_persons SET deleted_at=? WHERE id=?", (now, rp_id))
            conn.commit()
        finally:
            conn.close()

    def restore_responsible_person(self, rp_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute("SELECT id FROM organizations WHERE rp_id=?", (rp_id,))
            for org in c.fetchall():
                self._restore_org(conn, c, org['id'])
            c.execute("UPDATE responsible_persons SET deleted_at=NULL WHERE id=?", (rp_id,))
            conn.commit()
        finally:
            conn.close()

    def purge_responsible_person(self, rp_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            c = conn.cursor()
            c.execute("DELETE FROM responsible_persons WHERE id=?", (rp_id,))
            conn.commit()
        finally:
            conn.close()

    # ---------- Organizations ----------
    def get_organizations(self, rp_id, sort_key='name', sort_dir='ASC', include_deleted=False):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            col = SORT_ORG.get(sort_key, 'name')
            where = '' if include_deleted else 'AND deleted_at IS NULL'
            c.execute(
                f"SELECT * FROM organizations WHERE rp_id=? {where} ORDER BY {col} {_dir(sort_dir)}",
                (rp_id,))
            return c.fetchall()
        finally:
            conn.close()

    def get_org(self, org_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM organizations WHERE id=?", (org_id,))
            return c.fetchone()
        finally:
            conn.close()

    def add_organization(self, rp_id, name, address, phone, contract_number, contract_date):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO organizations (rp_id, name, address, phone, contract_number, contract_date) "
                "VALUES (?,?,?,?,?,?)",
                (rp_id, name, address, phone, contract_number, contract_date))
            conn.commit()
            return c.lastrowid
        finally:
            conn.close()

    def update_organization(self, org_id, name, address, phone, contract_number, contract_date):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE organizations SET name=?, address=?, phone=?, contract_number=?, contract_date=? "
                "WHERE id=?",
                (name, address, phone, contract_number, contract_date, org_id))
            conn.commit()
        finally:
            conn.close()

    def _soft_delete_org(self, conn, c, org_id, now):
        c.execute("SELECT id FROM stores WHERE org_id=? AND deleted_at IS NULL", (org_id,))
        for st in c.fetchall():
            self._soft_delete_store(conn, c, st['id'], now)
        c.execute("UPDATE organizations SET deleted_at=? WHERE id=?", (now, org_id))

    def _restore_org(self, conn, c, org_id):
        c.execute("SELECT id FROM stores WHERE org_id=?", (org_id,))
        for st in c.fetchall():
            self._restore_store(conn, c, st['id'])
        c.execute("UPDATE organizations SET deleted_at=NULL WHERE id=?", (org_id,))

    def delete_organization(self, org_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            c = conn.cursor()
            now = _ts()
            self._soft_delete_org(conn, c, org_id, now)
            conn.commit()
        finally:
            conn.close()

    def restore_organization(self, org_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            self._restore_org(conn, c, org_id)
            conn.commit()
        finally:
            conn.close()

    def purge_organization(self, org_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            c = conn.cursor()
            c.execute("DELETE FROM organizations WHERE id=?", (org_id,))
            conn.commit()
        finally:
            conn.close()

    # ---------- Stores ----------
    def get_stores(self, org_id, sort_key='name', sort_dir='ASC', include_deleted=False):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            col = SORT_STORE.get(sort_key, 'name')
            where = '' if include_deleted else 'AND deleted_at IS NULL'
            c.execute(
                f"SELECT * FROM stores WHERE org_id=? {where} ORDER BY {col} {_dir(sort_dir)}",
                (org_id,))
            return c.fetchall()
        finally:
            conn.close()

    def get_store(self, store_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM stores WHERE id=?", (store_id,))
            return c.fetchone()
        finally:
            conn.close()

    def add_store(self, org_id, name, address, phone):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO stores (org_id, name, unloading_address, phone) VALUES (?,?,?,?)",
                (org_id, name, address, phone))
            conn.commit()
            return c.lastrowid
        finally:
            conn.close()

    def update_store(self, store_id, name, address, phone):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE stores SET name=?, unloading_address=?, phone=? WHERE id=?",
                (name, address, phone, store_id))
            conn.commit()
        finally:
            conn.close()

    def _soft_delete_store(self, conn, c, store_id, now):
        c.execute("UPDATE contacts SET deleted_at=? WHERE store_id=? AND deleted_at IS NULL", (now, store_id))
        c.execute("UPDATE stores SET deleted_at=? WHERE id=?", (now, store_id))

    def _restore_store(self, conn, c, store_id):
        c.execute("UPDATE contacts SET deleted_at=NULL WHERE store_id=?", (store_id,))
        c.execute("UPDATE stores SET deleted_at=NULL WHERE id=?", (store_id,))

    def delete_store(self, store_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            self._soft_delete_store(conn, c, store_id, _ts())
            conn.commit()
        finally:
            conn.close()

    def restore_store(self, store_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            self._restore_store(conn, c, store_id)
            conn.commit()
        finally:
            conn.close()

    def purge_store(self, store_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            c = conn.cursor()
            c.execute("DELETE FROM stores WHERE id=?", (store_id,))
            conn.commit()
        finally:
            conn.close()

    # ---------- Contacts ----------
    def get_contacts(self, store_id, contact_type=None, sort_key='name', sort_dir='ASC', include_deleted=False):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            col = SORT_CONTACT.get(sort_key, 'full_name')
            extra = ''
            if contact_type:
                extra = "AND contact_type=?"
            if not include_deleted:
                extra += " AND deleted_at IS NULL"
            params = (store_id, contact_type) if contact_type else (store_id,)
            c.execute(
                f"SELECT * FROM contacts WHERE store_id=? {extra} ORDER BY {col} {_dir(sort_dir)}",
                params)
            return c.fetchall()
        finally:
            conn.close()

    def get_all_contacts(self, store_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM contacts WHERE store_id=? AND deleted_at IS NULL", (store_id,))
            return c.fetchall()
        finally:
            conn.close()

    def get_contact(self, contact_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM contacts WHERE id=?", (contact_id,))
            return c.fetchone()
        finally:
            conn.close()

    def add_contact(self, store_id, contact_type, full_name, position, phone):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO contacts (store_id, contact_type, full_name, position, phone) VALUES (?,?,?,?,?)",
                (store_id, contact_type, full_name, position, phone))
            conn.commit()
            return c.lastrowid
        finally:
            conn.close()

    def update_contact(self, contact_id, full_name, position, phone):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE contacts SET full_name=?, position=?, phone=? WHERE id=?",
                (full_name, position, phone, contact_id))
            conn.commit()
        finally:
            conn.close()

    def change_contact_type(self, contact_id, new_type):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute("UPDATE contacts SET contact_type=? WHERE id=?", (new_type, contact_id))
            conn.commit()
        finally:
            conn.close()

    def delete_contact(self, contact_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute("UPDATE contacts SET deleted_at=? WHERE id=?", (_ts(), contact_id))
            conn.commit()
        finally:
            conn.close()

    def restore_contact(self, contact_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute("UPDATE contacts SET deleted_at=NULL WHERE id=?", (contact_id,))
            conn.commit()
        finally:
            conn.close()

    def purge_contact(self, contact_id):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            c = conn.cursor()
            c.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
            conn.commit()
        finally:
            conn.close()

    # ---------- Trash ----------
    def get_deleted_items(self):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            result = []
            c.execute("SELECT id, full_name AS name, deleted_at FROM responsible_persons WHERE deleted_at IS NOT NULL")
            for r in c.fetchall():
                result.append(('rp', r['id'], r['name'], r['deleted_at']))
            c.execute("SELECT id, name, deleted_at FROM organizations WHERE deleted_at IS NOT NULL")
            for r in c.fetchall():
                result.append(('org', r['id'], r['name'], r['deleted_at']))
            c.execute("SELECT id, name, deleted_at FROM stores WHERE deleted_at IS NOT NULL")
            for r in c.fetchall():
                result.append(('store', r['id'], r['name'], r['deleted_at']))
            c.execute("SELECT id, full_name AS name, deleted_at FROM contacts WHERE deleted_at IS NOT NULL")
            for r in c.fetchall():
                result.append(('contact', r['id'], r['name'] or '-', r['deleted_at']))
            result.sort(key=lambda x: x[3] or '', reverse=True)
            return result
        finally:
            conn.close()

    def restore_item(self, node_type, db_id):
        {'rp': self.restore_responsible_person,
         'org': self.restore_organization,
         'store': self.restore_store,
         'contact': self.restore_contact}[node_type](db_id)

    def purge_item(self, node_type, db_id):
        {'rp': self.purge_responsible_person,
         'org': self.purge_organization,
         'store': self.purge_store,
         'contact': self.purge_contact}[node_type](db_id)

    def purge_all_deleted(self):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute("DELETE FROM contacts WHERE deleted_at IS NOT NULL")
            c.execute("DELETE FROM stores WHERE deleted_at IS NOT NULL")
            c.execute("DELETE FROM organizations WHERE deleted_at IS NOT NULL")
            c.execute("DELETE FROM responsible_persons WHERE deleted_at IS NOT NULL")
            conn.commit()
        finally:
            conn.close()

    # ---------- Integrity ----------
    def find_orphans(self):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            orphans = {}
            c.execute("SELECT COUNT(*) c FROM organizations WHERE rp_id NOT IN (SELECT id FROM responsible_persons)")
            orphans['organizations'] = c.fetchone()[0]
            c.execute("SELECT COUNT(*) c FROM stores WHERE org_id NOT IN (SELECT id FROM organizations)")
            orphans['stores'] = c.fetchone()[0]
            c.execute("SELECT COUNT(*) c FROM contacts WHERE store_id NOT IN (SELECT id FROM stores)")
            orphans['contacts'] = c.fetchone()[0]
            return orphans
        finally:
            conn.close()

    def cleanup_orphans(self):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute("DELETE FROM organizations WHERE rp_id NOT IN (SELECT id FROM responsible_persons)")
            c.execute("DELETE FROM stores WHERE org_id NOT IN (SELECT id FROM organizations)")
            c.execute("DELETE FROM contacts WHERE store_id NOT IN (SELECT id FROM stores)")
            conn.commit()
        finally:
            conn.close()

    # ---------- Counts ----------
    def get_counts(self):
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) c FROM responsible_persons WHERE deleted_at IS NULL")
            rp = c.fetchone()[0]
            c.execute("SELECT COUNT(*) c FROM organizations WHERE deleted_at IS NULL")
            org = c.fetchone()[0]
            c.execute("SELECT COUNT(*) c FROM stores WHERE deleted_at IS NULL")
            st = c.fetchone()[0]
            c.execute("SELECT COUNT(*) c FROM contacts WHERE deleted_at IS NULL")
            ct = c.fetchone()[0]
            return {'rp': rp, 'org': org, 'store': st, 'contact': ct}
        finally:
            conn.close()