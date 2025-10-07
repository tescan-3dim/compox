"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import toml
import pytest
import json
from unittest.mock import call
import hashlib
import shutil

from compox.algorithm_utils.AlgorithmDeployer import AlgorithmDeployer


@pytest.fixture
def valid_alg_dir(tmp_path):
    """
    Create a temporary algorithm directory with a valid pyproject.toml and Runner.py.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Base temporary directory fixture provided by pytest.

    Returns
    -------
    str
        Path to the created algorithm directory containing:
          - pyproject.toml with valid data
          - Runner.py file
    """
    directory = tmp_path / "alg"
    directory.mkdir()
    content = {
        "project": {"name": "my_algo", "version": "1.2"},
        "tool": {"compox": {
            "check_importable": False,
            "obfuscate": False,
            "hash_module": False,
            "hash_assets": False,
            "algorithm_type": "Generic",
            "tags": ["denoising"],
            "description": "denoising algorithm",
            "supported_devices": ["cpu"],
            "default_device": "cpu",
            "additional_parameters": []
            }}
    }

    toml_path = directory / "pyproject.toml"
    toml_path.write_text(toml.dumps(content))
    (directory / "Runner.py").write_text("class Runner: pass")
    return str(directory)


@pytest.fixture
def invalid_alg_dir(tmp_path):
    """
    Create a temporary algorithm directory with an invalid pyproject.toml and Runner.py.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Base temporary directory fixture provided by pytest.

    Returns
    -------
    str
        Path to the created algorithm directory containing:
          - pyproject.toml with invalid data
          - Runner.py file
    """
    d = tmp_path / "invalid"
    d.mkdir()
    (d / "pyproject.toml").write_text(
        toml.dumps({"project": {"name": "foo", "version": "0.1"}})
    )
    (d / "Runner.py").write_text("class Runner: pass")
    return str(d)


# Test 1 - parse valid pyproject
def test_parse_pyproject(valid_alg_dir):
    """
    Verify that AlgorithmDeployer extracts the correct metadata from pyproject.toml.
    """
    deployer = AlgorithmDeployer(valid_alg_dir)

    assert deployer.algorithm_name == "my_algo", (f"Expected algorithm_name to be 'my_algo', got {deployer.algorithm_name!r}")
    assert deployer.algorithm_major_version == "1", (f"Expected algorithm_major_version to be '1', got {deployer.algorithm_major_version!r}")
    assert deployer.algorithm_minor_version == "2", (f"Expected algorithm_minor_version to be '2', got {deployer.algorithm_minor_version!r}")
    assert deployer.algorithm_type == "Generic", (f"Expected algorithm_type to be 'Generic', got {deployer.algorithm_type!r}")


# Test 2 - parse invalid pyproject
@pytest.mark.filterwarnings("ignore:.*Algorithm type is set to.*:UserWarning")
@pytest.mark.filterwarnings("ignore:.*description.*:UserWarning")
@pytest.mark.filterwarnings("ignore:.*tags.*:UserWarning")
@pytest.mark.filterwarnings("ignore:.*supported_devices.*:UserWarning")
def test_parse_invalid_pyproject(invalid_alg_dir):
    """
    Verify that AlgorithmDeployer raises Exception for invalid input.
    """
    with pytest.raises(KeyError):
        AlgorithmDeployer(invalid_alg_dir)

    with pytest.raises(FileNotFoundError):
        AlgorithmDeployer("invalid_path")


# Test 3 - find py files
def test_find_py_files(valid_alg_dir):
    """
    Verify that find_py_files returns all .py files.
    """

    deployer = AlgorithmDeployer(valid_alg_dir)
    files = deployer.find_py_files(valid_alg_dir)
    assert any(f.endswith(".py") for f in files), (f"Expected to find 'Runner.py' in the list of Python files, got {files!r}")


# Test 4 - store algorithm with module-store, asset-store and algorithm-store
def test_store_algorithm(valid_alg_dir, mock_connection):
    """
    Verify that `store_algorithm` writes module, assets, and algorithm metadata
    to the mock database in the correct order and format.
    """
    mock_connection.list_collections.return_value = []
    deployer = AlgorithmDeployer(valid_alg_dir)
    returned_id = deployer.store_algorithm(database_connection=mock_connection)
    calls = mock_connection.put_objects.call_args_list

    expected_calls = [call(["module-store"]), call(["asset-store"]), call(["algorithm-store"])]
    assert returned_id == deployer.algorithm_id, (f"Expected returned_id to be {deployer.algorithm_id!r}, got {returned_id!r}")
    assert mock_connection.create_collections.call_count == 3, (f"Expected create_collections to be called 3 times (module-store, asset-store, algorithm-store)" 
                                                                f"but was called {mock_connection.create_collections.call_count} times")
    assert mock_connection.put_objects.call_count == 3, (f"Expected put_objects to be called 3 times (module-store, asset-store, algorithm-store)" 
                                                         f"but was called {mock_connection.put_objects.call_count} times")
    assert mock_connection.create_collections.call_args_list == expected_calls, (f"Expected call_args_list to be {expected_calls!r}," 
                                                                                 f"got { mock_connection.create_collections.call_args_list!r}")

    # 1) module-store
    bucket1, _, _ = calls[0][0]
    assert bucket1 == "module-store", (f"Expected first put_objects call to be 'module-store', got {bucket1!r}")

    # 2) asset-store
    bucket2, _, _ = calls[1][0]
    assert bucket2 == "asset-store", (f"Expected second put_objects call bucket to be 'asset-store', got {bucket2!r}")

    # 3) algorithm-store, and verify its key + payload
    bucket3, keys3, values3 = calls[2][0]
    payload = json.loads(values3[0])
    expected_key = (f"{returned_id}~{deployer.algorithm_name}~"f"{deployer.algorithm_major_version}~{deployer.algorithm_minor_version}")
    
    assert bucket3 == "algorithm-store", (f"Expected third put_objects call bucket to be 'algorithm-store', got {bucket3!r}")
    assert keys3 == [expected_key], (f"Expected algorithm-store key to be {expected_key!r}, got {keys3!r}")
    assert payload["algorithm_id"] == returned_id, (f"Expected payload['algorithm_id'] == {returned_id!r}, got {payload['algorithm_id']!r}")
    assert payload["algorithm_name"] == "my_algo", (f"Expected payload['algorithm_name'] == 'my_algo', got {payload['algorithm_name']!r}")
    assert payload["algorithm_major_version"] == "1", (f"Expected payload['algorithm_major_version'] == '1', got {payload['algorithm_major_version']!r}")
    assert payload["algorithm_minor_version"] == "2", (f"Expected payload['algorithm_minor_version'] == '2', got {payload['algorithm_minor_version']!r}")
    assert payload.get("module_id"), (f"Expected payload to contain a non-empty 'module_id', got {payload.get('module_id')!r}")
    assert payload.get("timestamp"), (f"Expected payload to contain a non-empty 'timestamp', got {payload.get('timestamp')!r}")

    
# Test 5 - store algorithm and skip algorithm-store
def test_store_algorithm_skips_only_algorithm_store(valid_alg_dir, mock_connection):
    """
    Verify that `store_algorithm` skips creating the "algorithm-store" collection
    when it already exists, but still uploads module and asset data.
    """
    mock_connection.list_collections.return_value = ["algorithm-store"]
    deployer = AlgorithmDeployer(valid_alg_dir)
    deployer.store_algorithm(database_connection=mock_connection)
    created = [args[0] for args, _ in mock_connection.create_collections.call_args_list]

    assert mock_connection.create_collections.call_count == 2, (f"Expected create_collections to be called 2 times (module-store, asset-store)" 
                                                                f"but was called {mock_connection.create_collections.call_count} times")
    assert mock_connection.put_objects.call_count == 3, (f" Expected put_objects to be called 3 times (module-store, asset-store, algorithm-store)" 
                                                         f"but was called {mock_connection.put_objects.call_count} times")
    assert ["module-store"] in created, (f"Expected 'module-store' in created connection, got {created!r}")
    assert ["asset-store"]  in created, (f"Expected 'asset-store' in created connection, got {created!r}")
    assert all(c != ["algorithm-store"] for c in created), (f"Did not expect 'algorithm-store' in created connection, got {created!r}")


# Test 6 - parse pyproject_toml
def test_parse_pyproject_toml_direct(valid_alg_dir):
    """
    Verify that parse_pyproject_toml correctly reads pyproject.toml file and returns dict.
    """
    deployer = AlgorithmDeployer(valid_alg_dir)
    parsed = deployer.parse_pyproject_toml(valid_alg_dir)
    assert isinstance(parsed, dict), (f"'parse_pyproject_toml' should return 'dict', got {type(parsed)!r}")
    assert parsed["project"]["name"] == "my_algo", (f"Expected parsed data 'name' to be 'my_algo', got {parsed['project']['name']!r}")
    assert parsed["project"]["version"] == "1.2", (f"Expected parsed data 'version' to be '1.2', got {parsed['project']['version']!r}")


# Test 7 - process path to dict
def test_process_path_to_dict_key():
    """
    Verify that process_path_to_dict_key: 
        - converts '\\' and '\' to '/'
        - delete leading slashes or backslashes
    """
    raw = r"\foo\bar/baz"
    key = AlgorithmDeployer.process_path_to_dict_key(raw)
    assert key == "foo/bar/baz", (f" Expected 'key' to be 'foo/bar/baz', got {key!r}")


# Test 8 - find other than py files
def test_find_other_than_py_files(tmp_path):
    """
    Verify that find_other_than_py_files returns only non- '.py' files 
    and exclude files in __pycache__ directory.
    """
    d = tmp_path / "dir"
    d.mkdir()
    (d / "a.txt").write_text("1")
    (d / "b.py").write_text("2")
    sub = d / "__pycache__"
    sub.mkdir()
    (sub / "c.txt").write_text("3")

    files = AlgorithmDeployer.find_other_than_py_files(str(d))
    assert any(f.endswith("a.txt") for f in files), (f"Expected 'a.txt' in output files, got {files!r}")
    assert all(not f.endswith(".py") for f in files), (f"Did not expect 'b.py' in output files, got {files!r}")
    assert all("__pycache__" not in f for f in files), (f"Did not expect files in '__pycache__' directory, got {files!r}")


# Test 9 - calculate etag
def test_calculate_etag():
    """
    Verify that 'calculate_etag' returns an MD5-based etag
    """
    data = b"abc"
    etag = AlgorithmDeployer.calculate_etag(data)
    expected = '"' + hashlib.md5(data).hexdigest() + '"'
    assert etag == expected, (f"Expected 'etag' to be {expected!r}, got {etag!r}")


# Test 10 - generate uuid with different versions
def test_generate_uuid_versions():
    """
    Verify that 'generate_uuid': 
        - returns valid uuid for version 1 or 4
        - raise ValueError for any other versions
    """
    u1 = AlgorithmDeployer.generate_uuid(version=1)
    u4 = AlgorithmDeployer.generate_uuid(version=4)
    assert isinstance(u1, str) and len(u1) > 0, (f"'generate_uuid' should return 'str', got {type(u1)!r}. "
                                                 f"Length of returned uuid string should be at least 1, got {len(u1)}")
    assert isinstance(u4, str) and len(u4) > 0, (f"'generate_uuid' should return 'str', got {type(u4)!r}. "
                                                 f"Length of returned uuid string should be at least 1, got {len(u4)}")
    with pytest.raises(ValueError):
        AlgorithmDeployer.generate_uuid(version=2)


# Test 11 - check if zip is importable
@pytest.mark.filterwarnings("ignore:.*zipimport.zipimporter.load_module.*:DeprecationWarning")
def test_check_if_zip_is_importable(tmp_path):
    """
    Verify that 'check_if_zip_is_importable' correctly intentifies importable and corrupt ZIP.
    """
    # good zip
    mod = tmp_path / "mod"
    mod.mkdir()
    (mod / "Runner.py").write_text("class Runner: pass")
    zip_path = shutil.make_archive(str(mod), 'zip', str(mod))
    assert AlgorithmDeployer.check_if_zip_is_importable(zip_path), (f"'check_if_zip_is_importable' should return 'True' for valid ZIP, "
                                                                    f"got {AlgorithmDeployer.check_if_zip_is_importable(zip_path)!r}")

    # bad zip
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip")
    assert not AlgorithmDeployer.check_if_zip_is_importable(str(bad)), (f"'check_if_zip_is_importable' should return 'False' for invalid ZIP, "
                                                                        f"got {AlgorithmDeployer.check_if_zip_is_importable(str(bad))!r}")


# Test 12 - hash py file
def test_hash_py_file_and_directory(tmp_path):
    """
    Verify that 'hash_py_file' and 'hash_directory' calculate correct MD5-based hashes.
    """
    f = tmp_path / "f.py"
    f.write_text("data")
    file_hash = AlgorithmDeployer.hash_py_file(str(f))
    expected = hashlib.md5(b"data").hexdigest()
    assert file_hash == expected, (f"'hash_py_file' should return {expected!r}, got {file_hash!r}")

    d = tmp_path / "d"
    d.mkdir()
    (d / "g.txt").write_text("foo")
    dir_hash = AlgorithmDeployer.hash_directory(str(d))
    expected_dir = hashlib.md5(b"foo").hexdigest()
    assert dir_hash == expected_dir, (f"'hash_directory' should return {expected_dir!r}, got {dir_hash!r}")


# Test 13 - minimalize py file
def test_minimalize_py_files(valid_alg_dir, tmp_path):
    """
    Verify that `_minimalize_py_files` delete comments and blank lines from Python files.
    """
    f = tmp_path / "m.py"
    f.write_text("# comment\n\nx = 1\n")
    deployer = AlgorithmDeployer(valid_alg_dir)
    deployer._minimalize_py_files([str(f)])
    content = f.read_text()
    assert "x=1" in content or "x = 1" in content, (f"Expected code 'x=1' or 'x = 1' in content after minimalization, got {content!r}")
    assert "#" not in content, (f"Did not expect any '#' in content after minimalization, got {content!r}")


# Test 14 rename subfolder
def test_rename_subfolder(tmp_path):
    """
    Verify that `_rename_folders_and_file_with_unique_ids` replaces a single subdirectory
    with exactly one MD5-based 'pcb...' prefixed directory when mode='md5'.
    """
    root = tmp_path / "alg"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()
    (sub / "m.py").write_text("y = 2")

    deployer = AlgorithmDeployer.__new__(AlgorithmDeployer)
    deployer._rename_folders_and_file_with_unique_ids(str(root), mode="md5")
    dirs = [d.name for d in root.iterdir() if d.is_dir()]

    assert len(dirs) == 1, (f"Expected exactly one directory, got {dirs!r}")
    assert dirs[0].startswith("pcb"), (f"Renamed directory should start 'pcb', got {dirs[0]!r}")


# Test 15 replace imports
@pytest.mark.parametrize("fake_uuid", ["deadbeeffeedfacecafebabef00d12345"])
def test_replace_imports_only(tmp_path, monkeypatch, fake_uuid):
    """
    Verify that `_replace_imports_in_runner_file` appends a 'as pcb_import_<uuid>' alias
    to each import that matches the provided module names.
    """
    runner = tmp_path / "Runner.py"
    runner.write_text("from sub.m import y\n")

    monkeypatch.setattr(
        AlgorithmDeployer,
        "generate_uuid",
        lambda self, version=1: fake_uuid
    )

    deployer = AlgorithmDeployer.__new__(AlgorithmDeployer)
    deployer._replace_imports_in_runner_file(str(runner), ["sub.m"])

    text = runner.read_text()
    expected = f"from sub.m import y as pcb_import_{fake_uuid}"
    assert expected in text, (f"Expected import alias '{expected}' in Runner.py, but got {text!r}")