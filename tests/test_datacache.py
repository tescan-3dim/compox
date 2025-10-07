"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import pytest

from compox.session.DataCache import DataCache


@pytest.fixture
def datacache():
    """
    Provide a DataCache instance using max_size=3 and max_memory_mb=None.
    """
    return DataCache(max_size=3, max_memory_mb=None)


# Test 1 - test len and __getitem__ with empty datacache
def test_len_contains_and_getitem_empty(datacache):
    """
    Verify that new 'DataCache' is empty and accesing a missing key raises KeyError.
    """
    assert len(datacache) == 0, (f"Expected DataCache to be empty, got {len(datacache)} items")
    assert "key1" not in datacache, (f"Did not expect 'key1' in DataCache, but found it")
    with pytest.raises(KeyError):
        _ = datacache.__getitem__("key1")


# Test 2 - add_item and __getitem__
def test_add_and_get_item(datacache):
    """
    Verify that 'add_item' stores value under the key in DataCache and value can by accessed by using correct key
    """
    datacache.add_item("value1", "key1")
    assert len(datacache) == 1, (f"Expected 1 item in DataCache, got {len(datacache)} items")
    assert "key1" in datacache, (f"Expected 'key1' to be in DataCache")
    assert datacache["key1"] == "value1", (f"Accessing Datacache with 'key1' should return 'value1', got {datacache['key1']!r}")
    assert datacache.__getitem__("key1") == "value1", (f"Accessing Datacache with 'key1' should return 'value1', got {datacache['key1']!r}")


# Test 3 - test max size (remove oldeset item when cache is full)
def test_exceeding_max_size(datacache):
    """
    Verify that DataCache remove oldest item, when max_size is exceeded.
    """
    datacache.add_item(1, "key1")
    datacache.add_item(2, "key2")
    datacache.add_item(3, "key3")
    datacache.add_item(4, "key4") # This should remove key1

    assert "key1" not in datacache, (f"Expected 'key1' to be deleted when exceeding 'DataCache' max_size, but found it")     
    assert "key1" in datacache.removed_keys_len, (f"Expect 'key1' to be in 'DataCache.removed_keys_len' after exceeding DataCache max_size")  
    assert "key2" in datacache, (f"Expected 'key2' to be stored in 'Datache'")
    assert "key3" in datacache, (f"Expected 'key3' to be stored in 'Datache'")
    assert "key4" in datacache, (f"Expected 'key4' to be stored in 'Datache'")     
    assert len(datacache) == 3, (f"DataCache should hold 3 items after eviction, got {len(datacache)} items")


# Test 4 - test usage limit (remove oldest item when memory usage limit is exceeded)
def test_memory_usage_limit(monkeypatch):
    """
    Verify that 'DataCache' remove oldest item when memory usage limit is exceeded.
    """
    datacache = DataCache(max_size=10, max_memory_mb=1)
    seq = [0.5, 2, 2, 0.5]
    monkeypatch.setattr(datacache, "_get_memory_usage", lambda: seq.pop(0))

    datacache.add_item("item1", "key1")
    datacache.add_item("item2", "key2")
    datacache.add_item("item3", "key3") # This should remove key1

    assert "key1" not in datacache, (f"Expected 'key1' to be deleted when exceeding 'DataCache' max_size, but found it")                                            
    assert "key1" in datacache.removed_keys_memory, (f"Expect 'key1' to be in 'DataCache.removed_keys_len' after exceeding DataCache max_size")    
    assert "key2" in datacache, (f"Expected 'key2' to be stored in 'Datache'") 
    assert "key3" in datacache, (f"Expected 'key3' to be stored in 'Datache'")


# Test 5 - remove item from Cache
def test_remove_item(datacache):
    """
    Verify that 'remove_item' correctly delete item from 'DataCache'
    """
    datacache.add_item(1, "key1")
    datacache.remove_item("key1")
    assert "key1" not in datacache, (f"Did not expect 'key1' in DataCache after deleting, but found it")
    datacache.remove_item("key1")


# Test 6 - clear Cache
def test_clear(datacache):
    """
    Verify that 'clear' correctly delete all items from 'DataCache'
    """
    datacache.add_item(1, "key1")
    datacache.add_item(2, "key2")
    datacache.clear()
    assert len(datacache) == 0, (f"Expected 'DataCache' to be empty, got {len(datacache)} items")
    assert datacache.cache == {}, (f"Expected 'DataCache.cache' to be empty, got {datacache.cache!r}")
    assert datacache.cache_keys == [], (f"Expected 'DataCache.cache_keys' to be empty, got {datacache.cache_keys!r}")
    assert len(datacache.removed_keys_memory) == 0, (f"Expected 'DataCache.removed_keys_memory' to be empty, got {len(datacache.removed_keys_memory)} items")
    assert "key1" not in datacache, (f"Did not expect 'key1' in 'DataCache'")
    assert "key2" not in datacache, (f"Did not expect 'key2' in 'DataCache'")
