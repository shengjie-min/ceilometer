# -*- encoding: utf-8 -*-
#
# Author: John Tran <jhtran@att.com>
#         Julien Danjou <julien@danjou.info>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Tests for ceilometer/storage/impl_sqlalchemy.py

.. note::
  In order to run the tests against real SQL server set the environment
  variable CEILOMETER_TEST_SQL_URL to point to a SQL server before running
  the tests.

"""

import datetime

from oslo.config import cfg

from ceilometer.storage import models as api_models
from ceilometer.storage.sqlalchemy.models import table_args

from tests.storage import base


class SQLAlchemyEngineTestBase(base.DBTestBase):
    database_connection = 'sqlite://'


class UserTest(base.UserTest, SQLAlchemyEngineTestBase):
    pass


class ProjectTest(base.ProjectTest, SQLAlchemyEngineTestBase):
    pass


class ResourceTest(base.ResourceTest, SQLAlchemyEngineTestBase):
    pass


class MeterTest(base.MeterTest, SQLAlchemyEngineTestBase):
    pass


class RawSampleTest(base.RawSampleTest, SQLAlchemyEngineTestBase):
    pass


class StatisticsTest(base.StatisticsTest, SQLAlchemyEngineTestBase):
    pass


class CounterDataTypeTest(base.CounterDataTypeTest, SQLAlchemyEngineTestBase):
    pass


class EventTest(base.EventTestBase, SQLAlchemyEngineTestBase):
    def test_unique_exists(self):
        u1 = self.conn._get_unique_name("foo")
        self.assertTrue(u1.id >= 0)
        u2 = self.conn._get_unique_name("foo")
        self.assertEqual(u1, u2)

    def test_new_unique(self):
        u1 = self.conn._get_unique_name("foo")
        self.assertTrue(u1.id >= 0)
        u2 = self.conn._get_unique_name("blah")
        self.assertNotEqual(u1, u2)

    def test_save_events_no_traits(self):
        now = datetime.datetime.utcnow()
        models = [api_models.Event("Foo", now, None),
                  api_models.Event("Zoo", now, [])]

        events = self.conn.record_events(models)
        self.assertEquals(len(events), 2)
        for event, traits in events:
            self.assertEquals(traits, [])
            self.assertTrue(event.id >= 0)
        self.assertNotEqual(events[0][0].id, events[1][0].id)

    def test_string_traits(self):
        model = api_models.Trait("Foo", api_models.Trait.TEXT_TYPE, "my_text")
        trait = self.conn._make_trait(model, None)
        self.assertEquals(trait.t_type, api_models.Trait.TEXT_TYPE)
        self.assertIsNone(trait.t_float)
        self.assertIsNone(trait.t_int)
        self.assertIsNone(trait.t_datetime)
        self.assertEquals(trait.t_string, "my_text")
        self.assertIsNotNone(trait.name)

    def test_int_traits(self):
        model = api_models.Trait("Foo", api_models.Trait.INT_TYPE, 100)
        trait = self.conn._make_trait(model, None)
        self.assertEquals(trait.t_type, api_models.Trait.INT_TYPE)
        self.assertIsNone(trait.t_float)
        self.assertIsNone(trait.t_string)
        self.assertIsNone(trait.t_datetime)
        self.assertEquals(trait.t_int, 100)
        self.assertIsNotNone(trait.name)

    def test_float_traits(self):
        model = api_models.Trait("Foo", api_models.Trait.FLOAT_TYPE, 123.456)
        trait = self.conn._make_trait(model, None)
        self.assertEquals(trait.t_type, api_models.Trait.FLOAT_TYPE)
        self.assertIsNone(trait.t_int)
        self.assertIsNone(trait.t_string)
        self.assertIsNone(trait.t_datetime)
        self.assertEquals(trait.t_float, 123.456)
        self.assertIsNotNone(trait.name)

    def test_datetime_traits(self):
        now = datetime.datetime.utcnow()
        model = api_models.Trait("Foo", api_models.Trait.DATETIME_TYPE, now)
        trait = self.conn._make_trait(model, None)
        self.assertEquals(trait.t_type, api_models.Trait.DATETIME_TYPE)
        self.assertIsNone(trait.t_int)
        self.assertIsNone(trait.t_string)
        self.assertIsNone(trait.t_float)
        self.assertEquals(trait.t_datetime, self.conn._dt_to_float(now))
        self.assertIsNotNone(trait.name)

    def test_save_events_traits(self):
        event_models = []
        for event_name in ['Foo', 'Bar', 'Zoo']:
            now = datetime.datetime.utcnow()
            trait_models = \
                [api_models.Trait(name, dtype, value)
                    for name, dtype, value in [
                        ('trait_A', api_models.Trait.TEXT_TYPE, "my_text"),
                        ('trait_B', api_models.Trait.INT_TYPE, 199),
                        ('trait_C', api_models.Trait.FLOAT_TYPE, 1.23456),
                        ('trait_D', api_models.Trait.DATETIME_TYPE, now)]]
            event_models.append(
                api_models.Event(event_name, now, trait_models))

        events = self.conn.record_events(event_models)
        self.assertEquals(len(events), 3)
        for event, traits in events:
            self.assertEquals(len(traits), 4)

    def test_datetime_to_float(self):
        expected = 1356093296.12
        utc_datetime = datetime.datetime.utcfromtimestamp(expected)
        actual = self.conn._dt_to_float(utc_datetime)
        self.assertEqual(actual, expected)

    def test_float_to_datetime(self):
        expected = 1356093296.12
        expected_datetime = datetime.datetime.utcfromtimestamp(expected)
        actual_datetime = self.conn._float_to_dt(expected)
        self.assertEqual(actual_datetime, expected_datetime)


def test_model_table_args():
    cfg.CONF.database_connection = 'mysql://localhost'
    assert table_args()
