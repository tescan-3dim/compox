"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import sys
import subprocess
import importlib
import zipfile
import weakref
import os
import functools
import pytest

import compox
from compox.server_utils import (weak_lru, algorithm_cache, data_cache, check_and_create_database_collections, 
                                     get_subprocess_fn, ZipImporter, check_system_gpu_availability, check_mps_availability)
import compox.server_utils

if os.name == "nt":
    from compox.internal.JobPOpen import JobPOpen

class Dummy:
    """
    A simple dummy class to demonstrate the behavior of the `weak_lru` decorator.
    """

    def __init__(self):
        """
        Initialize the Dummy instance with a zeroed call counter.

        Parameters
        ----------
        count: int 
            Tracks how many times the `add` method actually executes.   
        """
        self.count = 0

    @weak_lru(maxsize=1)
    def add(self, x):
        """
        Return x + 1, incrementing the call counter on a cache miss.

        Parameters
        ----------
        x : int 
            The input value.

        Returns
        -------
        int
            `x + 1`.
        """
        self.count += 1
        return x + 1


# Test 1 - Check Cuda
def test_check_cuda(monkeypatch):
    """
    Verify 'check_system_gpu_availability' in different states:
        - No torch + nvidia-smi error      → (None, None)
        - No torch + nvidia-smi success    → (True, GPU count)
        - Torch present + cuda unavailable → (True, GPU count)
        - Torch present + cuda available   → (True, GPU count)
    """
    class DummyCuda:
        @staticmethod
        def is_available(): return False 
        def device_count(): return 2
    class DummyTorch:
        cuda = DummyCuda

    class DummyProcess:
        def __init__(self, output="", error="", returncode=0, raise_exc=False):
            self.output = output
            self.error = error
            self.returncode = returncode
            self.raise_exc = raise_exc

        def communicate(self):
            if self.raise_exc:
                raise RuntimeError("Simulated subprocess error")
            return (self.output, self.error)

    def dummy_subprocess_fn_factory(output="", error="", returncode=0, raise_exc=False):
        def _subprocess_fn(*args, **kwargs):
            return DummyProcess(output, error, returncode, raise_exc)
        return _subprocess_fn
    # 1, Torch=None + Cuda unavailable + Exception
        
    monkeypatch.setattr(importlib.util, 'find_spec', lambda name: None)
    monkeypatch.setattr(compox.server_utils, 'get_subprocess_fn', lambda *args, **kwargs: dummy_subprocess_fn_factory(
        output="0, GPU0, 1024\n1, GPU1, 2048",
        error="",
        returncode=0,
        raise_exc=True
    ))
    avail, count = check_system_gpu_availability()
    assert avail is None, (f"Expected 'None' on Error, got {avail!r}")
    assert count is None, (f"Expected 'None' on error, got {count!r}")

    # 2) Torch=None + Cuda unavailable + Check_output
    monkeypatch.setattr(importlib.util, 'find_spec', lambda name: None)
    monkeypatch.setattr(compox.server_utils, 'get_subprocess_fn', lambda *args, **kwargs: dummy_subprocess_fn_factory(
        output="0, GPU0, 1024\n1, GPU1, 2048",
        error="",
        returncode=0,
        raise_exc=False
    ))
    avail, count = check_system_gpu_availability()
    assert avail is True, (f"Expected 'True' when nvidia-smi succeeds, got {avail!r}")
    assert count == 2, (f"Expected '2' GPUs, got {count!r}")
    
    # 3) Torch=True + Cuda unavailable + Check_output
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: True)
    monkeypatch.setattr(compox.server_utils, 'get_subprocess_fn', lambda *args, **kwargs: dummy_subprocess_fn_factory(
        output="0, GPU0, 1024\n1, GPU1, 2048\n2, GPU2, 4096",
        error="",
        returncode=0,
        raise_exc=False
    ))
    sys.modules["torch"] = DummyTorch
    avail, count = check_system_gpu_availability()
    assert avail is True, (f"Expected True when falling back to nvidia-smi, got {avail!r}") 
    assert count == 3, (f"Expected '3' GPUs, got {count!r}")
    
    # 4) Torch=True + Cuda available
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: True)
    monkeypatch.setattr(compox.server_utils, 'get_subprocess_fn', lambda *args, **kwargs: dummy_subprocess_fn_factory(
        output="0, GPU0, 1024\n1, GPU1, 2048",
        error="",
        returncode=0,
        raise_exc=False
    ))
    DummyCuda.is_available = staticmethod(lambda: True)
    sys.modules["torch"] = DummyTorch
    avail, count = check_system_gpu_availability()
    assert avail is True, (f"Expected 'True' when CUDA available, got {avail!r}") 
    assert count == 2, (f"Expected '2' GPUs, got {count!r}")


# Test 2 - check MPS
def test_check_mps(monkeypatch):
    """
    Verify 'check_mps_availability' in different states:
        - No torch                        → False
        - Torch present + mps available   → True
        - Torch present + mps unavailable → False
    """
    class DummyMps:
        @staticmethod
        def is_available(): return True
    class DummyBackends:
        mps = DummyMps
    class DummyTorch:
        backends = DummyBackends

    # 1) Torch=None
    monkeypatch.setattr(importlib.util, 'find_spec', lambda name: None)
    mps_avail = check_mps_availability()
    assert mps_avail is False, (f"Expected 'false' when torch is missing, got {mps_avail!r}")

    # 2) Torch=True + Available Mps
    monkeypatch.setattr(importlib.util, 'find_spec', lambda name: True)
    sys.modules["torch"] = DummyTorch
    mps_avail = check_mps_availability()
    assert mps_avail is True, (f"Expected 'true' when MPS is available, got {mps_avail!r}")

    # 3) Torch=True + Unavailable Mps 
    DummyMps.is_available = staticmethod(lambda: False)
    monkeypatch.setattr(importlib.util, 'find_spec', lambda name: True)
    sys.modules["torch"] = DummyTorch
    mps_avail = check_mps_availability()
    assert mps_avail is False, (f"Expected 'false' when MPS is unavailable, got {mps_avail!r}")


# Test 3 - weak lru
def test_weak_lru():
    """
    Verify that the @weak_lru decorator:
        - Caches the first result and increments count on a cache miss.
        - Returns the cached value on a repeated call with the same argument (no further increments).
        - Treats a new argument as a cache miss (increments count again).
        - Maintains separate caches per instance.
        - Uses a weak reference so deleting the object frees it from the cache.    
    """
    d1 = Dummy()
    result = d1.add(5)
    assert result == 6, (f"Expected '6' on first call, got {result!r}")
    assert d1.count == 1, (f"Expected count to be '1' on first call, got {d1.count!r}")

    # 1) Create same item
    result = d1.add(5)
    assert result == 6, (f"Expected '6' when cache hit, got {result!r}")
    assert d1.count == 1, (f"Expected count to be '1' when cache hit, got {d1.count!r}")

    # 2) Try to add another item
    assert d1.add(1) == 2, (f"Expected '2' when adding a new item, got {result!r}")
    assert d1.count == 2, (f"Expected count to be '2' after adding a new item, got {d1.count!r}")

    # 3) Test isolation of instances
    d2, d3 = Dummy(), Dummy()
    d2.add(2)
    d3.add(2)
    assert d2.count == 1, (f"Instance d2 should have its own cache; count should be 1, got {d2.count!r}")
    assert d3.count == 1, (f"Instance d3 should have its own cache; count should be 1, got {d3.count!r}")

    # 4) delete item
    d4 = Dummy()
    ref = weakref.ref(d4)
    d4.add(7)
    assert ref() == d4, ("Weakref should point to d4 before deletion")

    del d4
    import gc
    gc.collect()
    assert ref() is None, (f"After deletion and GC, weakref should be 'None', got {ref()!r}")


# Test 4 - algorithm Cache
def test_algorithm_cache():
    """
    Verify that @algorithm_cache(maxsize=2):
        - Caches the first result (no duplicate calls).
        - Returns cached result on repeated args.
        - Evicts the least recently used entry when exceeding maxsize.
    """
    class Calculator:
        def __init__(self):
            self.calls = []

        @algorithm_cache(maxsize=2)
        def add(self, a, b):
            self.calls.append((a, b))
            return a + b

    calc = Calculator()
    # first call → real
    result = calc.add(1, 2)
    assert result == 3, (f"First call: expected '3', got {result!r}")
    assert calc.calls == [(1, 2)], (f"After first miss: expected calls to be '[(1,2)]', got {calc.calls!r}")

    # cache hit → no new call
    result = calc.add(1, 2)
    assert result == 3, (f"Cache hit: expected '3' again, got {result!r}")
    assert calc.calls == [(1, 2)], (f"Cache hit should not append: got {calc.calls!r}")

    # fill cache with two new keys
    assert calc.add(2, 3) == 5, (f"Second unique key: expected '5', got {calc.calls[-1]!r}")
    assert calc.add(3, 4) == 7, (f"Third unique key: expected '7', got {calc.calls[-1]!r}")
    assert calc.calls == [(1, 2), (2, 3), (3, 4)], (f"Expected call log to be '[(1,2),(2,3),(3,4)]', got {calc.calls!r}")

    # eviction of (1,2)
    result = calc.add(1, 2)
    assert result == 3, (f"After eviction, expected add(1,2) to return 3, got {result!r}")
    assert calc.calls[-1] == (1, 2), (f"Expected last call to be '(1,2)' after eviction, got {calc.calls[-1]!r}")


# Test 5 - Data Cache
def test_data_cache():
    """
    Verify that @data_cache(maxsize=1):
        - Caches the first load.
        - Hits the cache on repeating the same key.
        - Evicts the previous key when a new key is loaded.
    """
    class Loader:
        def __init__(self):
            self.calls = []

        @data_cache(maxsize=1)
        def load(self, key):
            self.calls.append(key)
            return f"value_{key}"

    loader = Loader()
    # first load → real
    result = loader.load("a")
    assert result == "value_a", (f"First load: expected 'value_a', got {result!r}")
    assert loader.calls == ["a"], (f"After first load: expected calls '['a']', got {loader.calls!r}")

    # same key → cache hit
    result = loader.load("a")
    assert result == "value_a", (f"Cache hit: expected 'value_a' again, got {result!r}")
    assert loader.calls == ["a"], (f"Cache hit should not append: got {loader.calls!r}")

    # new key → eviction of "a"
    result = loader.load("b")
    assert result == "value_b", (f"New key load: expected 'value_b', got {result!r}")
    assert loader.calls == ["a", "b"], (f"Expected calls '['a','b']', got {loader.calls!r}")

    # after eviction, "a" 
    result = loader.load("a")
    assert result == "value_a", (f"After eviction, expected 'value_a' for 'a', got {result!r}")
    assert loader.calls[-1] == "a", (f"Expected last call to be 'a', got {loader.calls[-1]}")


# Test 6 - Zip importer
def test_zip_importer(tmp_path):
    """
    Verify that ZipImporter can load a module from bytes of a zip archive.
    """
    code = "VALUE=99"
    modname = "mymod"
    zf = tmp_path/"m.zip"
    with zipfile.ZipFile(zf, "w") as z: 
        z.writestr(f"{modname}.py", code)
    data = zf.read_bytes()

    with ZipImporter(data, modname) as m:
        assert hasattr(m, "VALUE"), ("Expected imported module to have attribute 'VALUE'")
        assert m.VALUE == 99, (f"Expected VALUE to be '99', got {m.VALUE!r}")


# Test 7 - check and create database collections
def test_check_and_create_database_collections():
    """
    Verify that missing collections are created and returned.
    """
    class DB:
        def __init__(self, exists):
            self.exists = exists
            self.created = []
        def check_collections_exists(self, names):
            return [n in self.exists for n in names]
        def create_collections(self, names):
            self.created.extend(names)

    db = DB(exists=["c1"])
    new = check_and_create_database_collections(["c1", "c2"], db)
    assert new == ["c2"], (f"Expected output to be '['c2']', got {new!r}")
    assert db.created == ["c2"], (f"Expected db.created to be '['c2']', got {db.created!r}")


# Test 8 - get_subprocess_fn
def test_get_subprocess_fn_posix(monkeypatch):
    """
    Verify get_subprocess_fn() returns subprocess.Popen on posix.
    """
    monkeypatch.setenv("OS", "") 
    monkeypatch.setattr(os, "name", "posix", raising=False)
    assert get_subprocess_fn() == subprocess.Popen, (f"Expected 'subprocess.Popen' on posix, got {get_subprocess_fn()!r}")


# Test 9 - get_subprocess_fn
@pytest.mark.skipif(os.name != "nt", reason="Windows-only test")
def test_get_subprocess_fn_nt(monkeypatch):
    """
    Verify get_subprocess_fn() returns partial(JobPOpen) on nt.
    """
    monkeypatch.setattr(os, "name", "nt", raising=False)
    fn = get_subprocess_fn()
    assert isinstance(fn, functools.partial), (f"Expected a 'functools.partial' on nt, got {type(fn)!r}")
    assert fn.func == JobPOpen, (f"Expected fn.func to be 'JobPOpen', got {fn.func!r}")


# Test 10 - get_subprocess_fn
def test_get_subprocess_fn_unknown(monkeypatch):
    """
    Verify get_subprocess_fn() raises on unsupported OS.
    """
    monkeypatch.setattr(os, "name", "unknown", raising=False)
    with pytest.raises(ValueError):
        get_subprocess_fn()