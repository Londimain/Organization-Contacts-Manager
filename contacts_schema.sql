-- Ответственные лица
CREATE TABLE responsible_persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    city TEXT
);

-- Организации
CREATE TABLE organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    responsible_person_id INTEGER,
    name TEXT NOT NULL,
    FOREIGN KEY (responsible_person_id) REFERENCES responsible_persons(id) ON DELETE CASCADE
);

-- Магазины
CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    name TEXT NOT NULL,
    unloading_address TEXT,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Контакты (ЛПР и Оплаты)
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER,
    contact_type TEXT CHECK(contact_type IN ('decision_maker', 'payment')),
    full_name TEXT,
    position TEXT,
    phone TEXT,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
);