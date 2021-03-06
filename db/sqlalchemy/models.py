# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
SQLAlchemy models for daisy data
"""

import uuid

from oslo.serialization import jsonutils
from oslo_db.sqlalchemy import models
from oslo_utils import timeutils
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy.orm import backref, relationship
from sqlalchemy import sql
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy import UniqueConstraint


BASE = declarative_base()


@compiles(BigInteger, 'sqlite')
def compile_big_int_sqlite(type_, compiler, **kw):
    return 'INTEGER'


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string"""

    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = jsonutils.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = jsonutils.loads(value)
        return value

class DaisyBase(models.ModelBase, models.TimestampMixin):
    """Base class for Daisy Models."""

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __table_initialized__ = False
    __protected_attributes__ = set([
        "created_at", "updated_at", "deleted_at", "deleted"])

    def save(self, session=None):
        from daisy.db.sqlalchemy import api as db_api
        super(DaisyBase, self).save(session or db_api.get_session())
       
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    created_at = Column(DateTime, default=lambda: timeutils.utcnow(),
                        nullable=False)
    # TODO(vsergeyev): Column `updated_at` have no default value in
    #                  openstack common code. We should decide, is this value
    #                  required and make changes in oslo (if required) or
    #                  in daisy (if not).
    updated_at = Column(DateTime, default=lambda: timeutils.utcnow(),
                        nullable=True, onupdate=lambda: timeutils.utcnow())
    # TODO(boris-42): Use SoftDeleteMixin instead of deleted Column after
    #                 migration that provides UniqueConstraints and change
    #                 type of this column.
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, nullable=False, default=False)

    def delete(self, session=None):
        """Delete this object."""
        self.deleted = True
        self.deleted_at = timeutils.utcnow()
        self.save(session=session)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def to_dict(self):
        d = self.__dict__.copy()
        # NOTE(flaper87): Remove
        # private state instance
        # It is not serializable
        # and causes CircularReference
        d.pop("_sa_instance_state")
        return d

class Host(BASE, DaisyBase):
    """Represents an host in the datastore."""
    __tablename__ = 'hosts'
    __table_args__ = (Index('ix_hosts_deleted', 'deleted'),)

    name = Column(String(255), nullable=False)
    dmi_uuid = Column(String(36))
    description = Column(Text)
    resource_type = Column(String(36))
    ipmi_user=Column(String(36))
    ipmi_passwd=Column(String(36))
    ipmi_addr=Column(String(255))
    status = Column(String(36), default='init', nullable=False)
    root_disk = Column(String(36))
    root_lv_size = Column(Integer())
    swap_lv_size = Column(Integer())
    root_pwd = Column(String(36))
    os_version_id = Column(String(36))
    os_version_file = Column(String(255))
    os_progress = Column(Integer())
    os_status = Column(String(36))
    messages = Column(Text)

class Cluster(BASE, DaisyBase):
    """Represents an clusters in the datastore."""
    __tablename__ = 'clusters'
    __table_args__ = (Index('ix_clusters_deleted', 'deleted'),)
    
    name = Column(String(255), nullable=False)
    owner = Column(String(255))
    description = Column(Text)
    net_l23_provider = Column(String(64))
    base_mac = Column(String(128))
    gre_id_start = Column(Integer())
    gre_id_end = Column(Integer())
    vlan_start = Column(Integer())
    vlan_end = Column(Integer())
    vni_start = Column(BigInteger())
    vni_end = Column(BigInteger())
    public_vip = Column(String(128))
    segmentation_type = Column(String(64))
    auto_scale = Column(Integer(), nullable=False, default=0)

class ClusterHost(BASE, DaisyBase):
    """Represents an cluster host  in the datastore."""
    __tablename__ = 'cluster_hosts'
    __table_args__ = (Index('ix_cluster_hosts_deleted', 'deleted'),)

    cluster_id = Column(String(36),
                            ForeignKey('clusters.id'),
                            nullable=False)
    host_id = Column(String(36),
                            nullable=False)

class HostInterface(BASE, DaisyBase):
    """Represents an host_interfaces in the datastore."""
    __tablename__ = 'host_interfaces'
    __table_args__ = (Index('ix_host_interfaces_deleted', 'deleted'),)

    host_id = Column(String(36),
                            ForeignKey('hosts.id'),
                            nullable=False)
    name = Column(String(64))
    ip = Column(String(256))
    netmask = Column(String(256))
    gateway = Column(String(256))
    mac = Column(String(256))
    pci = Column(String(32))
    type = Column(String(32),nullable=False, default='ether')
    slave1 = Column(String(32))
    slave2 = Column(String(32))
    mode = Column(String(36))
    is_deployment=Column(Boolean(),default=False)

class Network(BASE, DaisyBase):
    """Represents an networks in the datastore."""
    __tablename__ = 'networks'
    __table_args__ = (Index('ix_networks_deleted', 'deleted'),)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    cluster_id = Column(String(36))
    cidr = Column(String(255))
    vlan_id = Column(String(36))
    vlan_start = Column(Integer(), nullable=False, default=0)
    vlan_end = Column(Integer(), nullable=False, default=0)
    gateway = Column(String(128))
    ip = Column(String(256))
    type = Column(String(36), nullable=False, default='custom')
    ml2_type = Column(String(36))
    network_type = Column(String(36), nullable=False)
    physnet_name = Column(String(108))
    capability = Column(String(36))
    mtu = Column(Integer(), nullable=False, default=1500)
    
class IpRange(BASE, DaisyBase):
    """Represents an ip_ranges in the datastore."""
    __tablename__ = 'ip_ranges'
    __table_args__ = (Index('ix_ip_ranges_deleted', 'deleted'),)

    start = Column(String(128))
    end = Column(String(128))
    network_id = Column(String(36))    

class HostRole(BASE, DaisyBase):
    """Represents an host_roles in the datastore."""
    __tablename__ = 'host_roles'
    __table_args__ = (Index('ix_host_roles_deleted', 'deleted'),)

    host_id = Column(String(36), 
                            ForeignKey('hosts.id'),
                            nullable=False)
    role_id = Column(String(36),
                             ForeignKey('roles.id'),
                             nullable=False)
    status = Column(String(32), nullable=False, default='init')
    progress = Column(Integer(), default=0)

class Role(BASE, DaisyBase):
    """Represents an roles in the datastore."""
    __tablename__ = 'roles'
    __table_args__ = (Index('ix_roles_deleted', 'deleted'),Index('ix_roles_id', 'id'),)

    name = Column(String(255), 
                            nullable=False)
    description = Column(Text)
    status = Column(String(32), nullable=False, default='init')
    progress = Column(Integer(), default=0)
    config_set_id = Column(String(36), 
                            ForeignKey('config_sets.id'))
    cluster_id = Column(String(36))
    type = Column(String(36), nullable=False, default='custom')
    vip = Column(String(256))
    deployment_backend = Column(String(36))
    messages = Column(Text)
    config_set_update_progress = Column(Integer(), default=0)
    db_lv_size = Column(Integer())
    glance_lv_size = Column(Integer())
    nova_lv_size = Column(Integer(), default=0)
    
class ServiceRole(BASE, DaisyBase):
    """Represents an service_roles in the datastore."""
    __tablename__ = 'service_roles'
    __table_args__ = (Index('ix_service_roles_deleted', 'deleted'),)

    role_id = Column(String(36), ForeignKey('roles.id'), nullable=False)
    service_id = Column(String(36), ForeignKey('services.id'), nullable=False)
    
class Service(BASE, DaisyBase):
    """Represents an services in the datastore."""
    __tablename__ = 'services'
    __table_args__ = (Index('ix_services_deleted', 'deleted'),)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    component_id = Column(String(36), ForeignKey('components.id'), nullable=True)
    backup_type = Column(String(32), nullable=False, default='none')

class Component(BASE, DaisyBase):
    """Represents an components in the datastore."""
    __tablename__ = 'components'
    __table_args__ = (Index('ix_components_deleted', 'deleted'),)

    name = Column(String(255), nullable=False)
    description = Column(Text)

class ConfigSet(BASE, DaisyBase):
    """Represents an config_sets in the datastore."""
    __tablename__ = 'config_sets'
    __table_args__ = (Index('ix_config_sets_deleted', 'deleted'),)

    name = Column(String(255), nullable=False)
    description = Column(Text) 

class Config(BASE, DaisyBase):
    """Represents an configs in the datastore."""
    __tablename__ = 'configs'
    __table_args__ = (Index('ix_configs_deleted', 'deleted'),)

    section = Column(String(255))
    key = Column(String(255), nullable=False)
    value = Column(String(255))
    config_file_id = Column(String(36), ForeignKey('config_files.id'), nullable=False)
    config_version = Column(Integer(),default='0')
    running_version = Column(Integer(),default='0')
    description = Column(Text)

class ConfigFile(BASE, DaisyBase):
    """Represents an config_files in the datastore."""
    __tablename__ = 'config_files'
    __table_args__ = (Index('ix_config_files_deleted', 'deleted'),)

    name = Column(String(255), nullable=False)
    description = Column(Text)       
    
class ConfigSetItem(BASE, DaisyBase):
    """Represents an config_set_items in the datastore."""
    __tablename__ = 'config_set_items'
    __table_args__ = (Index('ix_config_set_items_deleted', 'deleted'),)

    config_set_id = Column(String(36), ForeignKey('config_sets.id'),
                            nullable=False)
    config_id = Column(String(36), ForeignKey('configs.id'), nullable=False)
    
class ConfigHistory(BASE, DaisyBase):
    """Represents an config_historys in the datastore."""
    __tablename__ = 'config_historys'
    __table_args__ = (Index('ix_config_historys_deleted', 'deleted'),)

    config_id = Column(String(36))
    value = Column(String(255))
    version = Column(Integer()) 
    
class Task(BASE, DaisyBase):
    """Represents an tasks in the datastore."""
    __tablename__ = 'tasks'
    __table_args__ = (Index('ix_tasks_deleted', 'deleted'),)

    type = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False)
    owner = Column(String(255), nullable=False)
    expires_at = Column(DateTime())
    
class TaskInfo(BASE, DaisyBase):
    """Represents an task_infos in the datastore."""
    __tablename__ = 'task_infos'
    __table_args__ = (Index('ix_task_infos_deleted', 'deleted'),)

    task_id = Column(String(36))
    input = Column(Text())
    result = Column(Text())
    message = Column(Text())
    
class Repository(BASE, DaisyBase):
    """Represents an repositorys in the datastore."""
    __tablename__ = 'repositorys'
    __table_args__ = (Index('ix_repositorys_deleted', 'deleted'),)

    url = Column(String(255))
    description = Column(Text())
    

class User(BASE, DaisyBase):
    """Represents an users in the datastore."""
    __tablename__ = 'users'
    __table_args__ = (Index('ix_users_deleted', 'deleted'),)

    name = Column(String(256), nullable=False)
    password = Column(String(256))
    email = Column(String(256))
    phone = Column(String(128))
    address = Column(String(256))

class Version(BASE, DaisyBase):
    """Represents an versions in the datastore."""
    __tablename__ = 'versions'
    __table_args__ = (Index('ix_versions_deleted', 'deleted'),)

    name = Column(String(256), nullable=False)
    size = Column(BigInteger())
    status = Column(String(30))
    checksum = Column(String(128))
    owner = Column(String(256))
    version = Column(String(32))
    type = Column(String(30), default='0')
    description = Column(Text())
    
class AssignedNetworks(BASE, DaisyBase):
    """Represents an assigned_networks in the datastore."""
    __tablename__ = 'assigned_networks'
    __table_args__ = (Index('ix_assigned_networks_deleted', 'deleted'),)

    mac = Column(String(128))
    network_id = Column(String(36))
    interface_id = Column(String(36))
    ip = Column(String(256))

class LogicNetwork(BASE, DaisyBase):
    """Represents an logic_networks in the datastore."""
    __tablename__ = 'logic_networks'
    __table_args__ = (Index('ix_logic_networks_deleted', 'deleted'),)
    
    name = Column(String(255), nullable=False)
    type = Column(String(36))
    physnet_name = Column(String(255))
    cluster_id= Column(String(36), ForeignKey('clusters.id'), nullable=False)
    segmentation_id = Column(BigInteger())
    segmentation_type = Column(String(64), nullable=False)
    shared = Column(Boolean(), default=False)

class Subnet(BASE, DaisyBase):
    """Represents an subnets in the datastore."""
    __tablename__ = 'subnets'
    __table_args__ = (Index('ix_subnets_deleted', 'deleted'),)

    cidr = Column(String(128))
    gateway = Column(String(128))
    logic_network_id = Column(String(36), ForeignKey('logic_networks.id'), nullable=False) 
    name = Column(String(255), nullable=False)
    router_id = Column(String(36), ForeignKey('routers.id')) 

class FloatIpRange(BASE, DaisyBase):
    """Represents an float_ip_ranges in the datastore."""
    __tablename__ = 'float_ip_ranges'
    __table_args__ = (Index('ix_float_ip_ranges_deleted', 'deleted'),)

    start = Column(String(128))
    end = Column(String(36))
    subnet_id = Column(String(36), ForeignKey('subnets.id'), nullable=False)

class DnsNameservers(BASE, DaisyBase):
    """Represents an dns_nameservers in the datastore."""
    __tablename__ = 'dns_nameservers'
    __table_args__ = (Index('ix_dns_nameservers_deleted', 'deleted'),)

    dns = Column(String(128))
    subnet_id = Column(String(36), ForeignKey('subnets.id'), nullable=False) 

class Router(BASE, DaisyBase):
    """Represents an routers in the datastore."""
    __tablename__ = 'routers'
    __table_args__ = (Index('ix_routers_deleted', 'deleted'),)

    name = Column(String(255))
    description = Column(Text())
    cluster_id = Column(String(36), ForeignKey('clusters.id'), nullable=False)
    external_logic_network = Column(String(255))
    
def register_models(engine):
    """Create database tables for all models with the given engine."""
    models = (Host,Project)
    for model in models:
        model.metadata.create_all(engine)

def unregister_models(engine):
    """Drop database tables for all models with the given engine."""
    models = (Host,project)
    for model in models:
        model.metadata.drop_all(engine)
