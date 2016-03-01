# Copyright (c) 2016 Ansible, Inc.
# All Rights Reserved

# Python
import pytest
from dateutil.relativedelta import relativedelta
from datetime import timedelta

# Django
from django.utils import timezone
from django.core.management.base import CommandError

# AWX
from awx.main.management.commands.cleanup_facts import CleanupFacts, Command
from awx.main.models.fact import Fact

@pytest.mark.django_db
def test_cleanup_granularity(fact_scans, hosts):
    epoch = timezone.now()
    hosts(5)
    fact_scans(10, timestamp_epoch=epoch)
    fact_newest = Fact.objects.all().order_by('-timestamp').first()
    timestamp_future = fact_newest.timestamp + timedelta(days=365)
    granularity = relativedelta(days=2)

    cleanup_facts = CleanupFacts()
    deleted_count = cleanup_facts.cleanup(timestamp_future, granularity)
    assert 60 == deleted_count

'''
Delete half of the scans
'''
@pytest.mark.django_db
def test_cleanup_older_than(fact_scans, hosts):
    epoch = timezone.now()
    hosts(5)
    fact_scans(28, timestamp_epoch=epoch)
    qs = Fact.objects.all().order_by('-timestamp')
    fact_middle = qs[qs.count() / 2]
    granularity = relativedelta()

    cleanup_facts = CleanupFacts()
    deleted_count = cleanup_facts.cleanup(fact_middle.timestamp, granularity)
    assert 210 == deleted_count

@pytest.mark.django_db
def test_cleanup_older_than_granularity_module(fact_scans, hosts):
    epoch = timezone.now()
    hosts(5)
    fact_scans(10, timestamp_epoch=epoch)
    fact_newest = Fact.objects.all().order_by('-timestamp').first()
    timestamp_future = fact_newest.timestamp + timedelta(days=365)
    granularity = relativedelta(days=2)

    cleanup_facts = CleanupFacts()
    deleted_count = cleanup_facts.cleanup(timestamp_future, granularity, module='ansible')
    assert 20 == deleted_count

@pytest.mark.django_db
@pytest.mark.skip(reason="Needs implementing. Takes brain power.")
def test_cleanup_logic(fact_scans, hosts):
    pass

@pytest.mark.django_db
def test_parameters_ok(mocker):
    run = mocker.patch('awx.main.management.commands.cleanup_facts.CleanupFacts.run')
    kv = {
        'older_than': '1d',
        'granularity': '1d',
        'module': None,
    }
    cmd = Command()
    cmd.handle(None, **kv)
    run.assert_called_once_with(relativedelta(days=1), relativedelta(days=1), module=None)

@pytest.mark.django_db
def test_string_time_to_timestamp_ok():
    kvs = [
        {
            'time': '2w',
            'timestamp': relativedelta(weeks=2),
            'msg': '2 weeks',
        },
        {
            'time': '23d',
            'timestamp': relativedelta(days=23),
            'msg': '23 days',
        },
        {
            'time': '11m',
            'timestamp': relativedelta(months=11),
            'msg': '11 months',
        },
        {
            'time': '14y',
            'timestamp': relativedelta(years=14),
            'msg': '14 years',
        },
    ]
    for kv in kvs:
        cmd = Command()
        res = cmd.string_time_to_timestamp(kv['time'])
        assert kv['timestamp'] == res

@pytest.mark.django_db
def test_string_time_to_timestamp_invalid():
    kvs = [
        {
            'time': '2weeks',
            'msg': 'weeks instead of w',
        },
        {
            'time': '2days',
            'msg': 'days instead of d',
        },
        {
            'time': '23',
            'msg': 'no unit specified',
        },
        {
            'time': None,
            'msg': 'no value specified',
        },
        {
            'time': 'zigzag',
            'msg': 'random string specified',
        },
    ]
    for kv in kvs:
        cmd = Command()
        res = cmd.string_time_to_timestamp(kv['time'])
        assert res is None

@pytest.mark.django_db
def test_parameters_fail(mocker):
    # Mock run() just in case, but it should never get called because an error should be thrown
    mocker.patch('awx.main.management.commands.cleanup_facts.CleanupFacts.run')
    kvs = [
        {
            'older_than': '1week',
            'granularity': '1d',
            'msg': '--older_than invalid value "1week"',
        },
        {
            'older_than': '1d',
            'granularity': '1year',
            'msg': '--granularity invalid value "1year"',
        }
    ]
    for kv in kvs:
        cmd = Command()
        with pytest.raises(CommandError) as err:
            cmd.handle(None, older_than=kv['older_than'], granularity=kv['granularity'])
        assert kv['msg'] in err.value

