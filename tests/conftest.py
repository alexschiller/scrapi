import mock
import pytest

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError

from scrapi import settings
from scrapi import database


settings.DEBUG = True
settings.CELERY_ALWAYS_EAGER = True
settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
database._manager.keyspace = 'test'

postgres_exc = None

try:
    con = Elasticsearch(settings.ELASTIC_URI, request_timeout=settings.ELASTIC_TIMEOUT)
    con.cluster.health(wait_for_status='yellow')
    use_es = True
except ConnectionError:
    use_es = False


@pytest.fixture(autouse=True)
def harvester(monkeypatch):
    mock_registry = mock.MagicMock()
    mock_harvester = mock.MagicMock()
    mock_registry.__getitem__.return_value = mock_harvester

    monkeypatch.setattr('scrapi.tasks.registry', mock_registry)

    return mock_harvester


@pytest.fixture(autouse=True)
def timestamp_patch(monkeypatch):
    monkeypatch.setattr('scrapi.tasks.timestamp', lambda: 'TIME')


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'cassandra: Handles setup and teardown for tests using cassandra'
    )
    config.addinivalue_line(
        'markers',
        'elasticsearch: tests that rely on an elasticsearch connection'
    )


def pytest_runtest_setup(item):
    marker = item.get_marker('cassandra')
    if marker is not None:
        if not database.setup():
            pytest.skip('No connection to Cassandra')

    marker = item.get_marker('elasticsearch')
    if marker is not None:
        if not use_es:
            pytest.skip('No connection to Elasticsearch')


def pytest_runtest_teardown(item, nextitem):
    marker = item.get_marker('cassandra')
    if marker is not None:
        database._manager.clear_keyspace(force=True)
