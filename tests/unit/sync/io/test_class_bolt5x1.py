# Copyright (c) "Neo4j"
# Neo4j Sweden AB [https://neo4j.com]
#
# This file is part of Neo4j.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging

import pytest

import neo4j
import neo4j.exceptions
from neo4j._conf import PoolConfig
from neo4j._sync.io._bolt5 import Bolt5x1
from neo4j.exceptions import ConfigurationError

from ...._async_compat import mark_sync_test


@pytest.mark.parametrize("set_stale", (True, False))
def test_conn_is_stale(fake_socket, set_stale):
    address = neo4j.Address(("127.0.0.1", 7687))
    max_connection_lifetime = 0
    connection = Bolt5x1(address, fake_socket(address),
                              max_connection_lifetime)
    if set_stale:
        connection.set_stale()
    assert connection.stale() is True


@pytest.mark.parametrize("set_stale", (True, False))
def test_conn_is_not_stale_if_not_enabled(fake_socket, set_stale):
    address = neo4j.Address(("127.0.0.1", 7687))
    max_connection_lifetime = -1
    connection = Bolt5x1(address, fake_socket(address),
                              max_connection_lifetime)
    if set_stale:
        connection.set_stale()
    assert connection.stale() is set_stale


@pytest.mark.parametrize("set_stale", (True, False))
def test_conn_is_not_stale(fake_socket, set_stale):
    address = neo4j.Address(("127.0.0.1", 7687))
    max_connection_lifetime = 999999999
    connection = Bolt5x1(address, fake_socket(address),
                              max_connection_lifetime)
    if set_stale:
        connection.set_stale()
    assert connection.stale() is set_stale


@pytest.mark.parametrize(("args", "kwargs", "expected_fields"), (
    (("", {}), {"db": "something"}, ({"db": "something"},)),
    (("", {}), {"imp_user": "imposter"}, ({"imp_user": "imposter"},)),
    (
        ("", {}),
        {"db": "something", "imp_user": "imposter"},
        ({"db": "something", "imp_user": "imposter"},)
    ),
))
@mark_sync_test
def test_extra_in_begin(fake_socket, args, kwargs, expected_fields):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                              PoolConfig.max_connection_lifetime)
    connection.begin(*args, **kwargs)
    connection.send_all()
    tag, is_fields = socket.pop_message()
    assert tag == b"\x11"
    assert tuple(is_fields) == expected_fields


@pytest.mark.parametrize(("args", "kwargs", "expected_fields"), (
    (("", {}), {"db": "something"}, ("", {}, {"db": "something"})),
    (("", {}), {"imp_user": "imposter"}, ("", {}, {"imp_user": "imposter"})),
    (
        ("", {}),
        {"db": "something", "imp_user": "imposter"},
        ("", {}, {"db": "something", "imp_user": "imposter"})
    ),
))
@mark_sync_test
def test_extra_in_run(fake_socket, args, kwargs, expected_fields):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                              PoolConfig.max_connection_lifetime)
    connection.run(*args, **kwargs)
    connection.send_all()
    tag, is_fields = socket.pop_message()
    assert tag == b"\x10"
    assert tuple(is_fields) == expected_fields


@mark_sync_test
def test_n_extra_in_discard(fake_socket):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                              PoolConfig.max_connection_lifetime)
    connection.discard(n=666)
    connection.send_all()
    tag, fields = socket.pop_message()
    assert tag == b"\x2F"
    assert len(fields) == 1
    assert fields[0] == {"n": 666}


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (666, {"n": -1, "qid": 666}),
        (-1, {"n": -1}),
    ]
)
@mark_sync_test
def test_qid_extra_in_discard(fake_socket, test_input, expected):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                              PoolConfig.max_connection_lifetime)
    connection.discard(qid=test_input)
    connection.send_all()
    tag, fields = socket.pop_message()
    assert tag == b"\x2F"
    assert len(fields) == 1
    assert fields[0] == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (777, {"n": 666, "qid": 777}),
        (-1, {"n": 666}),
    ]
)
@mark_sync_test
def test_n_and_qid_extras_in_discard(fake_socket, test_input, expected):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                              PoolConfig.max_connection_lifetime)
    connection.discard(n=666, qid=test_input)
    connection.send_all()
    tag, fields = socket.pop_message()
    assert tag == b"\x2F"
    assert len(fields) == 1
    assert fields[0] == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (666, {"n": 666}),
        (-1, {"n": -1}),
    ]
)
@mark_sync_test
def test_n_extra_in_pull(fake_socket, test_input, expected):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                              PoolConfig.max_connection_lifetime)
    connection.pull(n=test_input)
    connection.send_all()
    tag, fields = socket.pop_message()
    assert tag == b"\x3F"
    assert len(fields) == 1
    assert fields[0] == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (777, {"n": -1, "qid": 777}),
        (-1, {"n": -1}),
    ]
)
@mark_sync_test
def test_qid_extra_in_pull(fake_socket, test_input, expected):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                              PoolConfig.max_connection_lifetime)
    connection.pull(qid=test_input)
    connection.send_all()
    tag, fields = socket.pop_message()
    assert tag == b"\x3F"
    assert len(fields) == 1
    assert fields[0] == expected


@mark_sync_test
def test_n_and_qid_extras_in_pull(fake_socket):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                              PoolConfig.max_connection_lifetime)
    connection.pull(n=666, qid=777)
    connection.send_all()
    tag, fields = socket.pop_message()
    assert tag == b"\x3F"
    assert len(fields) == 1
    assert fields[0] == {"n": 666, "qid": 777}


@mark_sync_test
def test_hello_passes_routing_metadata(fake_socket_pair):
    address = neo4j.Address(("127.0.0.1", 7687))
    sockets = fake_socket_pair(address,
                               packer_cls=Bolt5x1.PACKER_CLS,
                               unpacker_cls=Bolt5x1.UNPACKER_CLS)
    sockets.server.send_message(b"\x70", {"server": "Neo4j/4.4.0"})
    sockets.server.send_message(b"\x70", {})
    connection = Bolt5x1(
        address, sockets.client, PoolConfig.max_connection_lifetime,
        routing_context={"foo": "bar"}
    )
    connection.hello()
    tag, fields = sockets.server.pop_message()
    assert tag == b"\x01"
    assert len(fields) == 1
    assert fields[0]["routing"] == {"foo": "bar"}


def _assert_logon_message(sockets, auth):
    tag, fields = sockets.server.pop_message()
    assert tag == b"\x6A"  # LOGON
    assert len(fields) == 1
    keys = ["scheme", "principal", "credentials"]
    assert list(fields[0].keys()) == keys
    for key in keys:
        assert fields[0][key] == getattr(auth, key)


@mark_sync_test
def test_hello_pipelines_logon(fake_socket_pair):
    auth = neo4j.Auth("basic", "alice123", "supersecret123")
    address = neo4j.Address(("127.0.0.1", 7687))
    sockets = fake_socket_pair(address,
                               packer_cls=Bolt5x1.PACKER_CLS,
                               unpacker_cls=Bolt5x1.UNPACKER_CLS)
    sockets.server.send_message(
        b"\x7F", {"code": "Neo.DatabaseError.General.MadeUpError",
                  "message": "kthxbye"}
    )
    connection = Bolt5x1(
        address, sockets.client, PoolConfig.max_connection_lifetime, auth=auth
    )
    with pytest.raises(neo4j.exceptions.Neo4jError):
        connection.hello()
    tag, fields = sockets.server.pop_message()
    assert tag == b"\x01"  # HELLO
    assert len(fields) == 1
    assert list(fields[0].keys()) == ["user_agent"]
    assert auth.credentials not in repr(fields)
    _assert_logon_message(sockets, auth)


@mark_sync_test
def test_logon(fake_socket_pair):
    auth = neo4j.Auth("basic", "alice123", "supersecret123")
    address = neo4j.Address(("127.0.0.1", 7687))
    sockets = fake_socket_pair(address,
                               packer_cls=Bolt5x1.PACKER_CLS,
                               unpacker_cls=Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, sockets.client,
                              PoolConfig.max_connection_lifetime, auth=auth)
    connection.logon()
    connection.send_all()
    _assert_logon_message(sockets, auth)


@mark_sync_test
def test_re_auth(fake_socket_pair, mocker, static_auth):
    auth = neo4j.Auth("basic", "alice123", "supersecret123")
    auth_manager = static_auth(auth)
    address = neo4j.Address(("127.0.0.1", 7687))
    sockets = fake_socket_pair(address,
                               packer_cls=Bolt5x1.PACKER_CLS,
                               unpacker_cls=Bolt5x1.UNPACKER_CLS)
    sockets.server.send_message(
        b"\x7F", {"code": "Neo.DatabaseError.General.MadeUpError",
                  "message": "kthxbye"}
    )
    connection = Bolt5x1(address, sockets.client,
                              PoolConfig.max_connection_lifetime)
    connection.pool = mocker.MagicMock()
    connection.re_auth(auth, auth_manager)
    connection.send_all()
    with pytest.raises(neo4j.exceptions.Neo4jError):
        connection.fetch_all()
    tag, fields = sockets.server.pop_message()
    assert tag == b"\x6B"  # LOGOFF
    assert len(fields) == 0
    _assert_logon_message(sockets, auth)
    assert connection.auth is auth
    assert connection.auth_manager is auth_manager


@mark_sync_test
def test_logoff(fake_socket_pair):
    address = neo4j.Address(("127.0.0.1", 7687))
    sockets = fake_socket_pair(address,
                               packer_cls=Bolt5x1.PACKER_CLS,
                               unpacker_cls=Bolt5x1.UNPACKER_CLS)
    sockets.server.send_message(b"\x70", {})
    connection = Bolt5x1(address, sockets.client,
                              PoolConfig.max_connection_lifetime)
    connection.logoff()
    assert not sockets.server.recv_buffer  # pipelined, so no response yet
    connection.send_all()
    assert sockets.server.recv_buffer  # now!
    tag, fields = sockets.server.pop_message()
    assert tag == b"\x6B"  # LOGOFF
    assert len(fields) == 0


@pytest.mark.parametrize(("hints", "valid"), (
    ({"connection.recv_timeout_seconds": 1}, True),
    ({"connection.recv_timeout_seconds": 42}, True),
    ({}, True),
    ({"whatever_this_is": "ignore me!"}, True),
    ({"connection.recv_timeout_seconds": -1}, False),
    ({"connection.recv_timeout_seconds": 0}, False),
    ({"connection.recv_timeout_seconds": 2.5}, False),
    ({"connection.recv_timeout_seconds": None}, False),
    ({"connection.recv_timeout_seconds": False}, False),
    ({"connection.recv_timeout_seconds": "1"}, False),
))
@mark_sync_test
def test_hint_recv_timeout_seconds(
    fake_socket_pair, hints, valid, caplog, mocker
):
    address = neo4j.Address(("127.0.0.1", 7687))
    sockets = fake_socket_pair(address,
                               packer_cls=Bolt5x1.PACKER_CLS,
                               unpacker_cls=Bolt5x1.UNPACKER_CLS)
    sockets.client.settimeout = mocker.Mock()
    sockets.server.send_message(
        b"\x70", {"server": "Neo4j/4.3.4", "hints": hints}
    )
    sockets.server.send_message(b"\x70", {})
    connection = Bolt5x1(
        address, sockets.client, PoolConfig.max_connection_lifetime
    )
    with caplog.at_level(logging.INFO):
        connection.hello()
    if valid:
        if "connection.recv_timeout_seconds" in hints:
            sockets.client.settimeout.assert_called_once_with(
                hints["connection.recv_timeout_seconds"]
            )
        else:
            sockets.client.settimeout.assert_not_called()
        assert not any("recv_timeout_seconds" in msg
                       and "invalid" in msg
                       for msg in caplog.messages)
    else:
        sockets.client.settimeout.assert_not_called()
        assert any(repr(hints["connection.recv_timeout_seconds"]) in msg
                   and "recv_timeout_seconds" in msg
                   and "invalid" in msg
                   for msg in caplog.messages)


CREDENTIALS = "+++super-secret-sauce+++"


@pytest.mark.parametrize("auth", (
    ("user", CREDENTIALS),
    neo4j.basic_auth("user", CREDENTIALS),
    neo4j.kerberos_auth(CREDENTIALS),
    neo4j.bearer_auth(CREDENTIALS),
    neo4j.custom_auth("user", CREDENTIALS, "realm", "scheme"),
    neo4j.Auth("scheme", "principal", CREDENTIALS, "realm", foo="bar"),
))
@mark_sync_test
def test_credentials_are_not_logged(auth, fake_socket_pair, caplog):
    address = neo4j.Address(("127.0.0.1", 7687))
    sockets = fake_socket_pair(address,
                               packer_cls=Bolt5x1.PACKER_CLS,
                               unpacker_cls=Bolt5x1.UNPACKER_CLS)
    sockets.server.send_message(b"\x70", {"server": "Neo4j/4.3.4"})
    sockets.server.send_message(b"\x70", {})
    connection = Bolt5x1(
        address, sockets.client, PoolConfig.max_connection_lifetime, auth=auth
    )
    with caplog.at_level(logging.DEBUG):
        connection.hello()

    if isinstance(auth, tuple):
        auth = neo4j.basic_auth(*auth)
    for field in ("scheme", "principal", "realm", "parameters"):
        value = getattr(auth, field, None)
        if value:
            assert repr(value) in caplog.text
    assert CREDENTIALS not in caplog.text


@pytest.mark.parametrize(("method", "args"), (
    ("run", ("RETURN 1",)),
    ("begin", ()),
))
@pytest.mark.parametrize("kwargs", (
    {"notifications_min_severity": "WARNING"},
    {"notifications_disabled_categories": ["HINT"]},
    {"notifications_disabled_categories": []},
    {
        "notifications_min_severity": "WARNING",
        "notifications_disabled_categories": ["HINT"]
    },
))
def test_does_not_support_notification_filters(fake_socket, method,
                                               args, kwargs):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(address, socket,
                            PoolConfig.max_connection_lifetime)
    method = getattr(connection, method)
    with pytest.raises(ConfigurationError, match="Notification filtering"):
        method(*args, **kwargs)


@mark_sync_test
@pytest.mark.parametrize("kwargs", (
    {"notifications_min_severity": "WARNING"},
    {"notifications_disabled_categories": ["HINT"]},
    {"notifications_disabled_categories": []},
    {
        "notifications_min_severity": "WARNING",
        "notifications_disabled_categories": ["HINT"]
    },
))
def test_hello_does_not_support_notification_filters(
    fake_socket, kwargs
):
    address = neo4j.Address(("127.0.0.1", 7687))
    socket = fake_socket(address, Bolt5x1.UNPACKER_CLS)
    connection = Bolt5x1(
        address, socket, PoolConfig.max_connection_lifetime,
        **kwargs
    )
    with pytest.raises(ConfigurationError, match="Notification filtering"):
        connection.hello()
