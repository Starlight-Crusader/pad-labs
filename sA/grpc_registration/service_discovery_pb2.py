# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: service_discovery.proto
# Protobuf Python Version: 5.27.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    27,
    2,
    '',
    'service_discovery.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x17service_discovery.proto\x12\tdiscovery\"2\n\x0fRegisterRequest\x12\x13\n\x0bserviceType\x18\x01 \x01(\t\x12\n\n\x02ip\x18\x02 \x01(\t\"4\n\x10RegisterResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t2W\n\x10ServiceDiscovery\x12\x43\n\x08Register\x12\x1a.discovery.RegisterRequest\x1a\x1b.discovery.RegisterResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'service_discovery_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_REGISTERREQUEST']._serialized_start=38
  _globals['_REGISTERREQUEST']._serialized_end=88
  _globals['_REGISTERRESPONSE']._serialized_start=90
  _globals['_REGISTERRESPONSE']._serialized_end=142
  _globals['_SERVICEDISCOVERY']._serialized_start=144
  _globals['_SERVICEDISCOVERY']._serialized_end=231
# @@protoc_insertion_point(module_scope)
