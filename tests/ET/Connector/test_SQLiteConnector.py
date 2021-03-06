import os
import sqlite3
import unittest
from six.moves import configparser

from aup.ET.Connector.SQLiteConnector import SQLiteConnector
from aup.setupdb import sqlite


class SQLiteConnectorTestCase(unittest.TestCase):
    db_file = os.path.join("tests", "data", "sqlite3.db")
    config = configparser.ConfigParser()
    config.add_section("Auptimizer")
    config.set("Auptimizer", "SQLITE_FILE", db_file)
    config.set("Auptimizer", "gpu_mapping", """{"1": 0, "2": 1}""")
    username = "test"
    name = "unittest"

    def setUp(self):
        sqlite.create_database(self.config, [self.name], 1, self.username)

    def tearDown(self):
        os.remove(self.db_file)

    def test_resource(self):
        """Test resource allocation"""
        connector = SQLiteConnector(self.db_file)
        self.assertListEqual(connector.get_resource_type(), [u'gpu', u'cpu', u'passive'])

        rids = connector.get_available_resource(self.username, 'gpu')
        self.assertEqual({1, 2}, set(rids))

        connector.take_available_resource(1)
        rids = connector.get_available_resource(self.username, 'gpu')
        self.assertEqual({2}, set(rids))

        connector.free_used_resource(1)
        rids = connector.get_available_resource(self.username, 'gpu')
        self.assertEqual({1, 2}, set(rids))

        connector.take_available_resource(2)
        connector.take_available_resource(1)
        rids = connector.get_available_resource(self.username, 'gpu')
        self.assertEqual(set([]), set(rids))

        connector.free_used_resource(1)
        connector.free_used_resource(2)
        rids = connector.get_available_resource(self.username, 'gpu')
        self.assertEqual({1, 2}, set(rids))
        connector.close()

    def test_experiment(self):
        """test experiment start and stop"""
        connector = SQLiteConnector(self.db_file)
        eid1 = connector.start_experiment(self.name, "exp1")
        eid2 = connector.start_experiment(self.name, "exp2")
        connector.end_experiment(eid1)
        connector.end_experiment(eid2)

        eids = connector.get_all_experiment(username=self.name)
        self.assertListEqual(eids, [1, 2])

        eids = connector.get_all_experiment()
        self.assertListEqual(eids, [1, 2])

        self.assertRaises(ValueError, connector.get_all_experiment, "not-exist")

    def test_job(self):
        """test job start and stop"""
        connector = SQLiteConnector(self.db_file)
        eid = connector.start_experiment(self.name, 'exp1')
        rid = 1
        jid1 = connector.job_started(eid, rid, "job1")
        jid2 = connector.job_started(eid, rid, "job1")

        self.assertListEqual(connector.get_running_job(eid), [jid1, jid2])

        connector.job_finished(eid, jid2, -100.)
        connector.job_finished(eid, jid1, 100.)

        self.assertRaises(sqlite3.IntegrityError, connector.job_started,1, 20, "job2")
        self.assertListEqual(connector.get_best_result(1, maximize=True), [jid1, 100.])
        self.assertListEqual(connector.get_best_result(1, maximize=False), [jid2, -100.])
        connector.close()

    def test_reset(self):
        connector = SQLiteConnector(self.db_file)
        eid = connector.start_experiment(self.name, 'exp1')
        rids = connector.get_available_resource(self.username, 'gpu')
        self.assertEqual({1, 2}, set(rids))
        jid = connector.job_started(eid, 1, "job1")
        connector.get_available_resource(self.username, "gpu")
        sqlite.reset(self.config)
        self.assertEqual({1, 2}, set(rids))
        r_jid = connector.get_all_history(1)[0][0]
        self.assertEqual(r_jid, jid)
