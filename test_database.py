# test_database.py
import unittest
import os
import tempfile
from database import Database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.mktemp(suffix='.db')
        self.db = Database(self.db_file)
        self.db.connect()

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_file):
            os.unlink(self.db_file)

    def _chain(self):
        rp = self.db.add_responsible_person('Иванов', 'Москва', 'Директор', '101')
        org = self.db.add_organization(rp, 'ООО Ромашка', 'ул. Ленина 1',
                                       '202', '№1', '2026-01-01')
        st = self.db.add_store(org, 'Магазин №1', 'склад', '303')
        dm = self.db.add_contact(st, 'decision_maker', 'Петров', 'Менеджер', '404')
        pay = self.db.add_contact(st, 'payment', 'Сидоров', 'Бухгалтер', '505')
        return rp, org, st, dm, pay

    # ---------- базовая работа ----------
    def test_crud_rp(self):
        rp = self.db.add_responsible_person('Иванов', 'Мск', 'Дир', '1')
        self.assertEqual(self.db.get_rp(rp)['full_name'], 'Иванов')
        self.db.update_responsible_person(rp, 'Петров', 'СПб', 'Мен', '2')
        self.assertEqual(self.db.get_rp(rp)['full_name'], 'Петров')

    def test_foreign_keys_enabled(self):
        """PRAGMA foreign_keys должен быть включён после connect()."""
        cur = self.db.conn.execute("PRAGMA foreign_keys")
        self.assertEqual(cur.fetchone()[0], 1)

    # ---------- мягкое удаление (корзина) ----------
    def test_cascade_soft_delete(self):
        rp, org, st, dm, pay = self._chain()
        self.db.delete_responsible_person(rp)
        self.assertEqual(len(self.db.get_responsible_persons()), 0)
        self.assertEqual(len(self.db.get_organizations(rp)), 0)
        self.assertEqual(len(self.db.get_stores(org)), 0)
        self.assertEqual(len(self.db.get_contacts(st)), 0)

    def test_restore(self):
        rp, org, st, dm, pay = self._chain()
        self.db.delete_responsible_person(rp)
        self.db.restore_responsible_person(rp)
        self.assertEqual(len(self.db.get_responsible_persons()), 1)
        self.assertEqual(len(self.db.get_organizations(rp)), 1)
        self.assertEqual(len(self.db.get_stores(org)), 1)
        self.assertEqual(len(self.db.get_contacts(st)), 2)

    def test_purge(self):
        rp, org, st, dm, pay = self._chain()
        self.db.delete_responsible_person(rp)
        self.db.purge_responsible_person(rp)
        # После purge физического удаления родителя каскад FK не должен
        # оставить «сирот» в БД (PRAGMA foreign_keys=ON).
        self.assertEqual(self.db.find_orphans()['organizations'], 0)

    def test_change_contact_type(self):
        rp, org, st, dm, pay = self._chain()
        self.db.change_contact_type(dm, 'payment')
        self.assertEqual(self.db.get_contact(dm)['contact_type'], 'payment')

    # ---------- «сироты» из старых БД ----------
    def test_orphans(self):
        """
        Имитируем СТАРУЮ БД, созданную до включения PRAGMA foreign_keys:
        удаляем родителя при выключенных FK — в результате появляются «сироты»,
        которые должны ловиться find_orphans() и убираться cleanup_orphans().
        """
        rp, org, st, dm, pay = self._chain()

        # 1. Симулируем старое поведение: FK выключены
        self.db.cursor.execute("PRAGMA foreign_keys = OFF")
        self.db.cursor.execute(
            "DELETE FROM responsible_persons WHERE id=?", (rp,))
        self.db.conn.commit()
        self.db.cursor.execute("PRAGMA foreign_keys = ON")

        # 2. Проверяем, что «сироты» действительно есть
        orphans = self.db.find_orphans()
        self.assertEqual(orphans['organizations'], 1,
                         "Ожидалась одна «сиротская» организация")
        # Магазины и контакты остались привязаны к существующей организации,
        # поэтому они не «сироты».
        self.assertEqual(orphans['stores'], 0)
        self.assertEqual(orphans['contacts'], 0)

        # 3. Чистим и проверяем, что «сирот» больше нет
        self.db.cleanup_orphans()
        self.assertEqual(self.db.find_orphans()['organizations'], 0)

    def test_orphans_deep(self):
        """Глубокая сирота: удалён родитель, есть вложенные магазины и контакты."""
        rp, org, st, dm, pay = self._chain()

        self.db.cursor.execute("PRAGMA foreign_keys = OFF")
        self.db.cursor.execute(
            "DELETE FROM responsible_persons WHERE id=?", (rp,))
        self.db.cursor.execute(
            "DELETE FROM organizations WHERE id=?", (org,))
        self.db.conn.commit()
        self.db.cursor.execute("PRAGMA foreign_keys = ON")

        orphans = self.db.find_orphans()
        self.assertEqual(orphans['organizations'], 0)
        self.assertEqual(orphans['stores'], 1,
                         "Ожидался один «сиротский» магазин")
        self.assertEqual(orphans['contacts'], 0)

        self.db.cleanup_orphans()
        orphans = self.db.find_orphans()
        self.assertEqual(sum(orphans.values()), 0)

    # ---------- корзина ----------
    def test_trash(self):
        rp, org, st, dm, pay = self._chain()
        self.db.delete_contact(dm)
        items = self.db.get_deleted_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0], 'contact')
        self.db.restore_item('contact', dm)
        self.assertEqual(len(self.db.get_deleted_items()), 0)

    def test_trash_purge_all(self):
        rp, org, st, dm, pay = self._chain()
        self.db.delete_contact(dm)
        self.db.delete_contact(pay)
        self.assertEqual(len(self.db.get_deleted_items()), 2)
        self.db.purge_all_deleted()
        self.assertEqual(len(self.db.get_deleted_items()), 0)


if __name__ == '__main__':
    unittest.main()