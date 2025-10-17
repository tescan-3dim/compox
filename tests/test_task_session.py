"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import pytest
from datetime import datetime, timedelta

from t3d_server.session.TaskSession import TaskSession


@pytest.fixture
def task_session():
    """
    Fixture that provides a mocked TaskSession.
    """
    return TaskSession(
        session_token="sess-1",
        max_number_of_data_caches=5,
        max_cache_size=5,
        max_cache_memory_mb=None,
        expire_hours=1,
        not_implemented=False,
    )

# Test 1 - Clean expired Sessions
def test_clean_expired_sessions_removes_old_entries(task_session):
    """
    Evict only sessions older than expire_hours, preserving newer ones.
    """
    now = datetime.now()
    task_session.data_caches.update({
        "sess_1": {"time_created": now - timedelta(hours=5), "data_cache": None},
        "sess_2": {"time_created": now - timedelta(minutes=30), "data_cache": None},
        "sess_3": {"time_created": now - timedelta(hours=4), "data_cache": None}
    })

    task_session._clean_expired_sessions(expire_hours=1)

    assert "sess_1" not in task_session.data_caches, (f"Expected 'sess_1' should have expired and been deleted from 'task_session.data_cache'")
    assert "sess_2" in task_session.data_caches, (f"Expected 'sess_2' to be in 'task_session.data_cache'")
    assert "sess_3" not in task_session.data_caches, (f"Expected 'sess_3' should have expired and been deleted from 'task_session.data_cache'")


# Test 2 - Keep new Sessions
def test_clean_expired_sessions_keeps_recent_entries(task_session):
    """
    Verify that 'data_cache.update' preserves not-expired sessions.
    """
    now = datetime.now()
    task_session.data_caches.update({
        "sess_1": {"time_created": now - timedelta(hours=1), "data_cache": None},
        "sess_2": {"time_created": now - timedelta(hours=2), "data_cache": None},
    })

    task_session._clean_expired_sessions(expire_hours=3)

    assert "sess_1" in task_session.data_caches, (f"Expected 'sess_1' to be in 'task_session.data_cache'")
    assert "sess_2" in task_session.data_caches, (f"Expected 'sess_2' to be in 'task_session.data_cache'")


# Test 3 - add_item and __getitem__
def test_add_and_get_item(task_session):
    """
    Verify that 'add_item' store new object and '__getitem__' returns correct object
    """
    key = "key_1"
    obj = object()
    task_session.add_item(obj, key)
    assert task_session[key] == obj, (f"Expected 'task_session['key_1']' to return {obj!r}, got {task_session[key]!r}")
    assert task_session.__getitem__(key) == obj, (f"Expected '__getitem__('key_1')' to return {obj!r}, got {task_session[key]!r}")


# Test 4 - remove item from cache
def test_remove_item(task_session):
    """
    Verify that 'remove_item' delete object from 'task_session'
    """
    key = "key_2"
    task_session.add_item(123, key)
    task_session.remove_item(key)
    with pytest.raises(KeyError):
        _ = task_session[key]


# Test 5 - Clear cache
def test_clear_cache(task_session):
    """
    Verify that 'clear_cache' delete all objects from 'task_session'
    """
    for i in range(3):
        obj, key = object(), f"key_{i}"
        task_session.add_item(obj, key)

    task_session.clear_cache()
    with pytest.raises(KeyError):
        _ = task_session["key_0"]