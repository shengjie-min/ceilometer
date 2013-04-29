# -*- encoding: utf-8 -*-
#
# Author: John Tran <jhtran@att.com>
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

"""
SQLAlchemy models for Ceilometer data.
"""

import json
import urlparse

from oslo.config import cfg
from sqlalchemy import Column, Integer, String, Table, ForeignKey, DateTime, \
    Float, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, VARCHAR

from ceilometer.openstack.common import timeutils

sql_opts = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine')
]

cfg.CONF.register_opts(sql_opts)


def table_args():
    engine_name = urlparse.urlparse(cfg.CONF.database_connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': cfg.CONF.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class JSONEncodedDict(TypeDecorator):
    "Represents an immutable structure as a json-encoded string."

    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class CeilometerBase(object):
    """Base class for Ceilometer Models."""
    __table_args__ = table_args()
    __table_initialized__ = False

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)


Base = declarative_base(cls=CeilometerBase)


sourceassoc = Table('sourceassoc', Base.metadata,
                    Column('meter_id', Integer,
                           ForeignKey("meter.id")),
                    Column('project_id', String(255),
                           ForeignKey("project.id")),
                    Column('resource_id', String(255),
                           ForeignKey("resource.id")),
                    Column('user_id', String(255),
                           ForeignKey("user.id")),
                    Column('source_id', String(255),
                           ForeignKey("source.id")))


class Source(Base):
    __tablename__ = 'source'
    id = Column(String(255), primary_key=True)


class Meter(Base):
    """Metering data."""

    __tablename__ = 'meter'
    id = Column(Integer, primary_key=True)
    counter_name = Column(String(255))
    sources = relationship("Source", secondary=lambda: sourceassoc)
    user_id = Column(String(255), ForeignKey('user.id'))
    project_id = Column(String(255), ForeignKey('project.id'))
    resource_id = Column(String(255), ForeignKey('resource.id'))
    resource_metadata = Column(JSONEncodedDict)
    counter_type = Column(String(255))
    counter_unit = Column(String(255))
    counter_volume = Column(Float(53))
    timestamp = Column(DateTime, default=timeutils.utcnow)
    message_signature = Column(String)
    message_id = Column(String)


class User(Base):
    __tablename__ = 'user'
    id = Column(String(255), primary_key=True)
    sources = relationship("Source", secondary=lambda: sourceassoc)
    resources = relationship("Resource", backref='user')
    meters = relationship("Meter", backref='user')


class Project(Base):
    __tablename__ = 'project'
    id = Column(String(255), primary_key=True)
    sources = relationship("Source", secondary=lambda: sourceassoc)
    resources = relationship("Resource", backref='project')
    meters = relationship("Meter", backref='project')


class Resource(Base):
    __tablename__ = 'resource'
    id = Column(String(255), primary_key=True)
    sources = relationship("Source", secondary=lambda: sourceassoc)
    resource_metadata = Column(JSONEncodedDict)
    user_id = Column(String(255), ForeignKey('user.id'))
    project_id = Column(String(255), ForeignKey('project.id'))
    meters = relationship("Meter", backref='resource')


class UniqueName(Base):
    """Key names should only be stored once.
    """
    __tablename__ = 'unique_name'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    key = Column(String(32), index=True, unique=True)

    def __init__(self, key):
        self.key = key

    def __repr__(self):
        return "<UniqueName: %s>" % self.key


class Event(Base):
    __tablename__ = 'event'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    when = Column(DateTime, index=True)

    unique_name_id = Column(Integer, ForeignKey('unique_name.id'))
    unique_name = relationship("UniqueName", backref=backref('unique_name',
                               order_by=id))

    def __init__(self, event, when):
        self.unique_name = event
        self.when = when

    def __repr__(self):
        return "<Event %d('Event: %s, When: %s')>" % \
               (self.id, self.unique_name, self.when)


class Trait(Base):
    __tablename__ = 'trait'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)

    name_id = Column(Integer, ForeignKey('unique_name.id'))
    name = relationship("UniqueName", backref=backref('name', order_by=id))

    t_type = Column(Integer, index=True)
    t_string = Column(String(32), nullable=True, default=None, index=True)
    t_float = Column(Numeric, nullable=True, default=None, index=True)
    t_int = Column(Integer, nullable=True, default=None, index=True)
    t_datetime = Column(Float, nullable=True, default=None, index=True)

    event_id = Column(Integer, ForeignKey('event.id'))
    event = relationship("Event", backref=backref('event', order_by=id))

    def __init__(self, name, event, t_type, t_string=None, t_float=None,
                 t_int=None, t_datetime=None):
        self.name = name
        self.t_type = t_type
        self.t_string = t_string
        self.t_float = t_float
        self.t_int = t_int
        self.t_datetime = t_datetime
        self.event = event

    def __repr__(self):
        return "<Trait(%s) %d=%s/%s/%s on %s>" % (self.name, self.t_type,
               self.t_string, self.t_float, self.t_int, self.event)
