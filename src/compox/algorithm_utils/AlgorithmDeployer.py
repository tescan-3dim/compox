"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import uuid
import json
from datetime import datetime
import os
import shutil
import glob
import tempfile
import zipimport
import sys
import re
import hashlib
import python_minifier
import ast
import toml
import warnings
from loguru import logger

from compox.algorithm_utils.AlgorithmConfigSchema import (
    AlgorithmConfigSchema,
)
from compox.database_connection import BaseConnection


class AlgorithmDeployer:
    """
    The AlgorithmDeployer class is used to deploy an algorithm to the algorithm
    store in the database. The algorithm directory gets automatically separated
    into the algorithm module by detecting all .py files and zipping them as a
    python module and storing them in the module-store collection. Files other than
    .py files are stored as assets in the asset-store collection. The algorithm
    metadata is stored in the algorithm-store collection as a json file. The json file
    contains the algorithm name, major and minor version, the module id, the assets
    dictionary and the timestamp of when the algorithm was stored.

    Parameters
    ----------
    algorithm_directory : str
        The path to the algorithm directory.
    """

    def __init__(
        self,
        algorithm_directory: str,
    ):

        self.logger = logger.bind(log_type="DEPLOYER")
        self.algorithm_id = self.generate_uuid()
        self.algorithm_directory = algorithm_directory

        pyproject_toml = self.parse_pyproject_toml(algorithm_directory)
        self.algorithm_name = pyproject_toml["project"]["name"]
        self.algorithm_major_version = pyproject_toml["project"][
            "version"
        ].split(".")[0]
        self.algorithm_minor_version = pyproject_toml["project"][
            "version"
        ].split(".")[1]

        # check if ["tool"]["compox"] exists in pyproject.toml
        if "tool" in pyproject_toml and "compox" in pyproject_toml["tool"]:
            algorithm_config = pyproject_toml["tool"]["compox"]
            algorithm_config_schema = AlgorithmConfigSchema(**algorithm_config)
            # conver to dict to get the values
            algorithm_config_schema = algorithm_config_schema.model_dump()

            self.algorithm_type = algorithm_config_schema["algorithm_type"]
            self.tags = algorithm_config_schema["tags"]
            self.description = algorithm_config_schema["description"]
            self.device = algorithm_config_schema["supported_devices"]
            self.default_device = algorithm_config_schema["default_device"]
            self.additional_parameters = algorithm_config_schema[
                "additional_parameters"
            ]
        else:
            warnings.warn(
                (
                    "The [tool.compox] section is not found in pyproject.toml."
                    "Setting the algorithm type to Unspecified, tags to an empty list,"
                    "description to an empty string and additional parameters to an empty"
                    "list. If you want to specify the algorithm type, tags, description and"
                    "additional parameters, add the [tool.compox] section to the"
                    "algorithms's pyproject.toml."
                )
            )
            algorithm_config_schema = AlgorithmConfigSchema()
            # conver to dict to get the values
            algorithm_config_schema = algorithm_config_schema.model_dump()
            self.algorithm_type = algorithm_config_schema["algorithm_type"]
            self.tags = algorithm_config_schema["tags"]
            self.description = algorithm_config_schema["description"]
            self.device = algorithm_config_schema["supported_devices"]
            self.default_device = algorithm_config_schema["default_device"]
            self.additional_parameters = algorithm_config_schema[
                "additional_parameters"
            ]

        self.check_importable = pyproject_toml["tool"]["compox"][
            "check_importable"
        ]
        self.obfuscate = pyproject_toml["tool"]["compox"]["obfuscate"]
        self.hash_module = pyproject_toml["tool"]["compox"]["hash_module"]
        self.hash_assets = pyproject_toml["tool"]["compox"]["hash_assets"]

    def parse_pyproject_toml(self, path_to_algorithm_directory: str) -> dict:
        """
        Parse the pyproject.toml file in the algorithm directory to get the
        algorithm name, major version and minor version.

        Parameters
        ----------
        path_to_algorithm_directory : str
            The path to the algorithm directory.

        Returns
        -------
        dict
            The algorithm name, major version and minor version.

        Raises
        ------
        FileNotFoundError
            If pyproject.toml not found in algorithm directory.

        """
        if not os.path.exists(
            os.path.join(path_to_algorithm_directory, "pyproject.toml")
        ):
            raise FileNotFoundError(
                f"pyproject.toml file not found in {path_to_algorithm_directory}."
            )
        with open(
            os.path.join(path_to_algorithm_directory, "pyproject.toml")
        ) as f:
            pyproject_toml = toml.load(f)

        return pyproject_toml

    def store_algorithm(
        self,
        database_connection: BaseConnection.BaseConnection | None = None,
        separate_runner_path: str | None = None,
        algorithm_collection_name: str = "algorithm-store",
        module_collection_name: str = "module-store",
        asset_collection_name: str = "asset-store",
    ) -> str:
        """

        Store the algorithm to the algorithm store.

        Parameters
        ----------
        database_connection : BaseConnection.BaseConnection | None
            The database connection object. Can be None if the algorithm is not
            supposed to be stored in the database (e.g. for local testing and
            development).

        separate_runner_path : str | None , optional
            The path to the runner file. Use this if the runner file is not in
            the root of the algorithm directory. The default is None.

        algorithm_collection_name : str, optional
            The name of the collection to store the algorithm. The default is
            "algorithm-store".

        module_collection_name : str, optional
            The name of the collection to store the module. The default is
            "module-store".

        asset_collection_name : str, optional
            The name of the collection to store the assets. The default is
            "asset-store".

        Returns
        -------
        str
            algorithm id

        Raises
        ------
        Exception
            if algorithm module or assets store failed
        """

        # store the algorithm module
        try:
            algorithm_module_id = self._store_algorithm_module(
                self.algorithm_directory,
                database_connection=database_connection,
                separate_runner_path=separate_runner_path,
                check_importable=self.check_importable,
                obfuscate=self.obfuscate,
                hash_module=self.hash_module,
                collection_name=module_collection_name,
            )
            self.logger.info(
                f"Stored algorithm module with id: {algorithm_module_id}"
            )
        except Exception as e:
            self.logger.error(f"Failed to store algorithm module: {e}")
            raise e

        # store the algorithm assets
        try:
            algorithm_assets_dict = self._store_algorithm_assets(
                self.algorithm_directory,
                database_connection=database_connection,
                hash_assets=self.hash_assets,
                collection_name=asset_collection_name,
            )
            self.logger.info(
                f"Stored algorithm assets: {algorithm_assets_dict}"
            )
        except Exception as e:
            self.logger.error(f"Failed to store algorithm assets: {e}")
            raise e

        # get the timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # compose the algorithm json
        algorithm_json = {
            "algorithm_id": self.algorithm_id,
            "algorithm_name": self.algorithm_name,
            "algorithm_major_version": self.algorithm_major_version,
            "algorithm_minor_version": self.algorithm_minor_version,
            "algorithm_type": self.algorithm_type,
            "algorithm_tags": self.tags,
            "algorithm_description": self.description,
            "supported_devices": self.device,
            "default_device": self.default_device,
            "additional_parameters": self.additional_parameters,
            "module_id": algorithm_module_id,
            "assets": algorithm_assets_dict,
            "timestamp": timestamp,
        }
        algorithm_json = json.dumps(algorithm_json, indent=4)

        # store the algorithm json in the algorithm-store collection
        # check if the collection exists and create it if it does not

        if database_connection is not None:
            if (
                algorithm_collection_name
                not in database_connection.list_collections()
            ):
                database_connection.create_collections(
                    [algorithm_collection_name]
                )
            algorithm_key = f"{self.algorithm_id}~{self.algorithm_name}~{self.algorithm_major_version}~{self.algorithm_minor_version}"
            database_connection.put_objects(
                algorithm_collection_name,
                [algorithm_key],
                [algorithm_json],
            )
        self.logger.info(f"Stored algorithm json: {algorithm_json}")
        return self.algorithm_id

    def _store_algorithm_module(
        self,
        path_to_algorithm_directory: str,
        database_connection: BaseConnection.BaseConnection | None = None,
        separate_runner_path: str | None = None,
        check_importable: bool = False,
        obfuscate: bool = False,
        hash_module: bool = False,
        collection_name: str = "module-store",
    ) -> str | bool:
        """
        Detects all .py files in the algorithm directory, zips them as a python
        module and stores them in the module collection.

        Parameters
        ----------
        path_to_algorithm_directory : str
            The path to the algorithm directory.

        database_connection : BaseConnection.BaseConnection | None
            The database connection object.

        separate_runner_path : str | None, optional
            The path to the runner file. Use this if the runner file is not in
            the root of the algorithm directory. The default is None.

        check_importable : bool, optional
            Whether to check if the module is importable by performing an import
            test. The default is False.

        obfuscate : bool, optional
            Whether to obfuscate the .py files. The default is False.

        hash_module : bool, optional
            Whether to hash the module. Will check if the module already exists
            by comparing the etag hash. If the module already exists, it will
            reuse it instead of uploading. The default is False.

        collection_name : str, optional
            The name of the collection to store the module. The default is
            "module-store".

        Returns
        -------
        str | bool
            The module id.

        Raises
        ------
        ValueError
            if Runner.py not found or import failed
        """

        module_id = self.generate_uuid()

        # get all the .py files in the algorithm directory
        py_files = self.find_py_files(path_to_algorithm_directory)
        py_files_with_relative_path = [
            os.path.relpath(py_file, path_to_algorithm_directory)
            for py_file in py_files
        ]

        # check if Runner.py is in the root of the algorithm directory
        if (
            "Runner.py" not in py_files_with_relative_path
            and separate_runner_path is None
        ):
            raise ValueError(
                "Runner.py not found in the root of the algorithm directory and separate_runner_path is not provided."
            )

        # add the separate runner path to the list of py files if it is not None
        if separate_runner_path is not None:
            py_files.append(separate_runner_path)
            py_files_with_relative_path.append("Runner.py")

        with tempfile.TemporaryDirectory() as temp_dir:
            module_path = os.path.join(temp_dir, "module")
            # copy the .py files to the temporary directory while preserving the directory structure
            for py_file, py_file_with_relative_path in zip(
                py_files, py_files_with_relative_path
            ):
                os.makedirs(
                    os.path.join(
                        module_path, os.path.dirname(py_file_with_relative_path)
                    ),
                    exist_ok=True,
                )
                shutil.copy(
                    py_file,
                    os.path.join(module_path, py_file_with_relative_path),
                )

            # replace file names with uuids and update imports
            import_list = self._rename_folders_and_file_with_unique_ids(
                module_path, mode="uuid"
            )
            runner_path = os.path.join(module_path, "Runner.py")

            # replace the imports in the runner file with random names
            self._replace_imports_in_runner_file(runner_path, import_list)

            # load the .py files again after renaming
            py_files = self.find_py_files(module_path)
            py_files_with_relative_path = [
                os.path.relpath(py_file, module_path) for py_file in py_files
            ]

            if obfuscate:
                # obfuscate the .py files
                # TODO: implement obfuscation
                # for now, minimize the .py files
                self._minimalize_py_files(py_files)

            # create a temporary zip file of the temporary directory
            shutil.make_archive(module_path, "zip", module_path)

            if check_importable:
                importable = self.check_if_zip_is_importable(
                    module_path + ".zip"
                )
                if not importable:
                    raise ValueError("The runner cannot be imported.")

            zip_bytes = open(module_path + ".zip", "rb").read()
            # store the zip file in the module-store collection
            if database_connection is not None:
                if (
                    collection_name
                    not in database_connection.list_collections()
                ):
                    database_connection.create_collections([collection_name])

                if hash_module:
                    module_id = (
                        database_connection.put_objects_with_duplicity_check(
                            collection_name,
                            [module_id],
                            [zip_bytes],
                        )[0]
                    )
                else:
                    database_connection.put_objects(
                        collection_name,
                        [module_id],
                        [zip_bytes],
                    )
        return module_id

    def _replace_imports_in_runner_file(
        self, runner_file_path: str, list_of_imports_to_process: list[str]
    ) -> None:
        """
        This method replaces the imports in runner.py file with random names. e.g.
        from utils import some_function -> from utils import some_function as
        pcb1234567890. This is necessary to avoid conflicts in local dependencies
        when multiple modules with conflicting names are imported during server
        runtime.

        Parameters
        ----------
        runner_file_path : str
            The path to the runner file.

        list_of_imports_to_process : list[str]
            The list of possible imports to process. The imports in the runner file
            that are not in this list will not be processed.

        Returns
        -------
        None
        """

        # read the runner file
        with open(runner_file_path, "r", encoding="utf-8") as f:
            runner_content = f.read()

        # parse the code as an abstract syntax tree
        ast_parsed = ast.parse(runner_content)
        aliases = {}

        # get the imports and their aliases and replace them with randomized aliases
        for node in ast.walk(ast_parsed):
            # get the imports and their aliases
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in list_of_imports_to_process:
                        random_alias = (
                            "pcb_import_"
                            + self.generate_uuid().replace("-", "")
                        )
                        if alias.asname is None:
                            aliases[alias.name] = random_alias
                            alias.asname = random_alias
                        else:
                            aliases[alias.asname] = random_alias
                            alias.asname = random_alias
            # get the imports from a module and their aliases
            if isinstance(node, ast.ImportFrom):
                if node.module in list_of_imports_to_process:
                    for alias in node.names:
                        random_alias = (
                            "pcb_import_"
                            + self.generate_uuid().replace("-", "")
                        )
                        if alias.asname is None:
                            aliases[alias.name] = random_alias
                            alias.asname = random_alias
                        else:
                            aliases[alias.asname] = random_alias
                            alias.asname = random_alias

        # replace the calls with the random names in aliases dict
        for node in ast.walk(ast_parsed):
            if isinstance(node, ast.Call):
                if node.func in aliases:
                    node.func = aliases[node.func]
            if isinstance(node, ast.Name):
                if node.id in aliases:
                    node.id = aliases[node.id]

        # unparsing the ast to get the updated code
        ast_unparsed = ast.unparse(ast_parsed)

        # write the updated code to the runner file
        with open(runner_file_path, "w", encoding="utf-8") as f:
            f.write(ast_unparsed)

    def _rename_folders_and_file_with_unique_ids(
        self, module_path: str, mode: str = "md5"
    ) -> list:
        """
        This method iterates through the py files in the module directory and
        replaces the file names with unique ids. It also updates the relative
        imports in the files. This is necessary to avoid conflicts in local
        dependencies when multiple modules with the same names are imported during
        server runtime. The runner file and special files (e.g. __init__.py) are
        kept unchanged.

        Parameters
        ----------
        module_path : str
            The path to the module directory.

        mode : str, optional
            The mode of the renaming. The default is "md5", which renames the
            files with an md5 hash of the file contents. The other option is "uuid",
            which renames the files with a uuid.

        Returns
        -------
        list
            list of possible imports
        """

        # rename the directories
        original_files = self.find_py_files(module_path)
        original_files_with_rel_path = [
            os.path.relpath(file, module_path) for file in original_files
        ]

        new_files = self._rename_all_subdirectories(
            module_path, original_files, mode=mode
        )
        # files = self.find_py_files(module_path)
        files_with_rel_path = [
            os.path.relpath(file, module_path) for file in new_files
        ]

        # rename the files
        dict_file_name_to_random_filename = self._rename_all_files(
            module_path, files_with_rel_path, mode=mode
        )

        original_to_new_file_name = {}
        for i in range(len(original_files_with_rel_path)):
            original_to_new_file_name[original_files_with_rel_path[i]] = list(
                dict_file_name_to_random_filename.values()
            )[i]

        # get possible imports
        possible_old_import_list = []
        possible_new_import_list = []
        for old_file_name, new_file_name in original_to_new_file_name.items():
            old_modules = old_file_name.split(os.path.sep)
            new_modules = new_file_name.split(os.path.sep)
            # re
            possible_old_imports = [
                ".".join(old_modules[:i])
                for i in range(1, len(old_modules) + 1)
            ]
            possible_new_imports = [
                ".".join(new_modules[:i])
                for i in range(1, len(new_modules) + 1)
            ]

            possible_old_imports += [
                ".".join(old_modules[-i:])
                for i in range(1, len(old_modules) + 1)
            ]
            possible_new_imports += [
                ".".join(new_modules[-i:])
                for i in range(1, len(new_modules) + 1)
            ]
            if len(possible_old_imports) > 0:
                possible_old_import_list.append(possible_old_imports)
                possible_new_import_list.append(possible_new_imports)

        # flatten the lists
        possible_old_import_list = [
            item for sublist in possible_old_import_list for item in sublist
        ]
        possible_new_import_list = [
            item for sublist in possible_new_import_list for item in sublist
        ]

        # remove py file extensions
        possible_old_import_list = [
            item.replace(".py", "") for item in possible_old_import_list
        ]
        possible_new_import_list = [
            item.replace(".py", "") for item in possible_new_import_list
        ]
        # get the unique imports
        possible_old_import_list = list(dict.fromkeys(possible_old_import_list))
        possible_new_import_list = list(dict.fromkeys(possible_new_import_list))

        # update the imports
        for root, _, files in os.walk(module_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                    for old_import, new_import in zip(
                        possible_old_import_list, possible_new_import_list
                    ):
                        # replace typical imports using regex
                        file_content = re.sub(
                            r"(?<=import ){}(?= )".format(old_import),
                            new_import,
                            file_content,
                        )
                        file_content = re.sub(
                            r"(?<=from ){}(?= )".format(old_import),
                            new_import,
                            file_content,
                        )
                        # from . import old_import
                        file_content = re.sub(
                            r"(?<=from \. import ){}(?= )".format(old_import),
                            new_import,
                            file_content,
                        )
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(file_content)

        return possible_new_import_list

    def _store_algorithm_assets(
        self,
        path_to_algorithm_directory: str,
        database_connection: BaseConnection.BaseConnection | None = None,
        hash_assets: bool = False,
        collection_name: str = "asset-store",
    ) -> dict:
        """
        Stores the assets of the algorithm in the asset-store collection.

        Parameters
        ----------
        path_to_algorithm_directory : str
            The path to the algorithm directory.

        database_connection : BaseConnection.BaseConnection | None
            The database connection object.

        hash_assets : bool, optional
            Whether to hash the assets. Will check if the assets already exists
            by comparing the etag hash. If the assets already exists, it will
            reuse them instead of uploading. The default is False.

        collection_name : str, optional
            The name of the collection to store the assets. The default is
            "asset-store".

        Returns
        -------
        dict
            The dictionary of the assets.

        """

        # get all the files other than .py files in the algorithm directory
        other_than_py_files = self.find_other_than_py_files(
            path_to_algorithm_directory
        )
        other_than_py_files_with_relative_path = [
            os.path.relpath(file, path_to_algorithm_directory)
            for file in other_than_py_files
        ]

        # store the assets in the asset-store collection
        assets_dict = {}
        for file, relative_file in zip(
            other_than_py_files, other_than_py_files_with_relative_path
        ):
            file_id = self.generate_uuid()
            with open(file, "rb") as f:
                file_bytes = f.read()

            if database_connection is not None:
                if (
                    collection_name
                    not in database_connection.list_collections()
                ):
                    database_connection.create_collections([collection_name])
                if hash_assets:
                    file_id = (
                        database_connection.put_objects_with_duplicity_check(
                            collection_name,
                            [file_id],
                            [file_bytes],
                        )[0]
                    )
                    assets_dict[
                        self.process_path_to_dict_key(relative_file)
                    ] = file_id
                else:
                    database_connection.put_objects(
                        collection_name,
                        [file_id],
                        [file_bytes],
                    )
                    assets_dict[
                        self.process_path_to_dict_key(relative_file)
                    ] = file_id
        return assets_dict

    @staticmethod
    def process_path_to_dict_key(path: str) -> str:
        """
        This method takes a path to a file specified as directory and substitutes
        any backslashes and double backslashes with forward slashes. It also removes
        the leading forward slash if it exists. This is necessary to store the
        directory structure as a dictionary key which can then be accessed by the
        server independently of the operating system, where the deployment is
        performed.

        Parameters
        ----------
        path : str
            A path to a file.

        Returns
        -------
        str
            The processed path with forward slashes and without the leading forward
            slash.

        """
        if path[0] == "\\":
            path = path[1:]
        path = path.replace("\\", "/")
        return path

    def _minimalize_py_files(self, py_files: list[str]) -> None:
        """
        Minimalize .py files using python_minifier. The minification is performed
        in place.

        Parameters
        ----------
        py_files : list[str]
            The list of paths to the .py files to minimalize.

        Returns
        -------
        None

        """
        for py_file in py_files:
            with open(py_file, "r", encoding="utf-8") as f:
                file_content = f.read()
            minified_content = python_minifier.minify(
                file_content, remove_literal_statements=True
            )
            with open(py_file, "w") as f:
                f.write(minified_content)

    @staticmethod
    def check_if_zip_is_importable(path_to_zip: str) -> bool:
        """
        Check if a a zipped module is importable.
        Parameters
        ----------
        path_to_zip : str
            The path to the zip file.

        Returns
        -------
        bool
            True if the module is importable, False otherwise.

        """
        try:
            sys.path.insert(0, path_to_zip)
            module = zipimport.zipimporter(path_to_zip)
            module.load_module("Runner")
            return True
        except Exception as e:
            return False

    @staticmethod
    def calculate_etag(file: bytes) -> str:
        """
        Calculate the etag hash of a file.

        Parameters
        ----------
        file : bytes
            The file.

        Returns
        -------
        str
            The etag hash.

        """
        import hashlib

        md5s = hashlib.md5(file)
        return '"{}"'.format(md5s.hexdigest())

    @staticmethod
    def find_py_files(directory: str, ignore_pycache: bool = True) -> list[str]:
        """
        Find all the .py files in a directory recursively.

        Parameters
        ----------
        directory : str
            The directory to search.

        ignore_pycache: bool
            Whether to ignore __pycache__ directory

        Returns
        -------
        list[str]
            The list of .py files.

        """
        py_files = []

        for root, _, _ in os.walk(directory):
            py_files.extend(glob.glob(os.path.join(root, "*.py")))

        # remove the __pycache__ directory if it exists
        if ignore_pycache:
            py_files = [
                file
                for file in py_files
                if "__pycache__" not in file.split(os.path.sep)
            ]
        return py_files

    @staticmethod
    def find_other_than_py_files(
        directory: str,
        ignore_pycache: bool = True,
        ignore_gitignore: bool = True,
    ) -> list[str]:
        """
        Find all the files in a directory other than .py files.

        Parameters
        ----------
        directory : str
            The directory to search.

        ignore_pycache : bool, optional
            Whether to ignore the __pycache__ directory. The default is True.

        ignore_gitignore : bool, optional
            Whether to ignore the .gitignore file. The default is True.

        Returns
        -------
        list[str]
            The list of files other than .py files.

        """
        other_than_py_files = []

        # get all the files other than .py files in the algorithm directory
        for root, _, _ in os.walk(directory):
            other_than_py_files.extend(glob.glob(os.path.join(root, "*")))

        # remove the .py files from the list
        other_than_py_files = [
            file for file in other_than_py_files if not file.endswith(".py")
        ]
        # remove paths that are directories
        other_than_py_files = [
            file for file in other_than_py_files if not os.path.isdir(file)
        ]

        # remove the __pycache__ directory if it exists
        if ignore_pycache:
            other_than_py_files = [
                file
                for file in other_than_py_files
                if "__pycache__" not in file.split(os.path.sep)
            ]

        if ignore_gitignore:
            other_than_py_files = [
                file
                for file in other_than_py_files
                if ".gitignore" not in file.split(os.path.sep)
            ]

        return other_than_py_files

    @staticmethod
    def generate_uuid(version: int = 1) -> str:
        """
        Generate a uuid.

        Parameters
        ----------
        version : int, optional
            The version of the uuid. The default is 1.

        Returns
        -------
        str
            The uuid.

        Raises
        ------
        ValueError
            if version of the uuid is not 1 or 4.
        """
        if version == 1:
            return str(uuid.uuid1())
        elif version == 4:
            return str(uuid.uuid4())
        else:
            raise ValueError("uuid version must be 1 or 4")

    def _rename_all_subdirectories(
        self, parent_dir: str, original_files: list, mode: str = "uuid"
    ) -> list:
        """
        Rename all the subdirectories in a directory with either a uuid or an md5
        hash of the directory contents. This is necessary to avoid conflicts in
        local dependencies when multiple modules with the same names are imported
        during server runtime.

        Parameters
        ----------
        parent_dir : str
            The parent directory.

        original_files : list
            The list of file paths in the directory.

        mode : str, optional
            The mode of the renaming. The default is "uuid", which renames the
            subdirectories with a uuid. The other option is "md5", which renames
            the subdirectories with an md5 hash of the directory contents.

        Returns
        -------
        list
            The list of file paths in the directory with the updated relative
            paths.

        """

        # if mode is md5, first compute the hashes before renaming
        if mode == "md5":
            hashes = {}
            for root, dirs, files in os.walk(parent_dir, topdown=False):
                for dir_name in dirs:
                    old_path = os.path.join(root, dir_name)
                    hashes[old_path] = self.hash_directory(old_path)

        for root, dirs, files in os.walk(parent_dir, topdown=False):
            for dir_name in dirs:
                old_path = os.path.join(root, dir_name)
                if mode == "uuid":
                    random_name = "pcb" + self.generate_uuid()
                elif mode == "md5":
                    random_name = "pcb" + hashes[old_path]
                # remove - and _ from the random name
                random_name = random_name.replace("-", "").replace("_", "")
                new_path = os.path.join(root, random_name)
                os.rename(old_path, new_path)

                # add trailing slash to the new path
                # this is necessary to not replace file names with the same prefix
                new_path += os.path.sep
                old_path += os.path.sep
                # update the relative paths
                for i in range(len(original_files)):
                    original_files[i] = original_files[i].replace(
                        old_path, new_path
                    )
        return original_files

    def _rename_all_files(
        self,
        module_path: str,
        files_with_relative_paths: list,
        mode: str = "uuid",
    ) -> dict:
        """
        Rename all the files in a directory with either a uuid or an md5 hash of
        the file contents. This is necessary to avoid conflicts in local
        dependencies when multiple modules with the same names are imported during
        server runtime.

        Parameters
        ----------
        module_path : str
            The path to the module directory.

        files_with_relative_paths : list
            The list of file paths in the directory.

        mode : str, optional
            The mode of the renaming. The default is "uuid", which renames the
            files with a uuid. The other option is "md5", which renames the files
            with an md5 hash of the file contents.

        Returns
        -------
        dict
            A dictionary with the original file names as keys and the new file
            names as values.

        Raises
        ------
        ValueError
            If the mode of the renaming is not supported.
        """
        dict_file_name_to_random_filename = {}
        for py_file_with_relative_path in files_with_relative_paths:
            # skip renaming the runner file and special files (e.g. __init__.py)
            if os.path.basename(py_file_with_relative_path) == "Runner.py":
                dict_file_name_to_random_filename[
                    py_file_with_relative_path
                ] = py_file_with_relative_path
            elif "__" in os.path.basename(py_file_with_relative_path):
                dict_file_name_to_random_filename[
                    py_file_with_relative_path
                ] = py_file_with_relative_path
            else:
                if mode == "uuid":
                    random_name = "pcb" + self.generate_uuid() + ".py"
                    random_name = random_name.replace("-", "").replace("_", "")
                elif mode == "md5":
                    random_name = (
                        "pcb"
                        + self.hash_py_file(
                            os.path.join(
                                module_path, py_file_with_relative_path
                            )
                        )
                        + ".py"
                    )
                    random_name = random_name.replace("-", "").replace("_", "")
                else:
                    raise ValueError(f"Unsupported mode: {mode}")

                dict_file_name_to_random_filename[
                    py_file_with_relative_path
                ] = os.path.join(
                    os.path.dirname(py_file_with_relative_path),
                    random_name,
                )
        # rename the files
        for (
            py_file_with_relative_path,
            random_filename,
        ) in dict_file_name_to_random_filename.items():
            os.rename(
                os.path.join(module_path, py_file_with_relative_path),
                os.path.join(module_path, random_filename),
            )

        return dict_file_name_to_random_filename

    @staticmethod
    def hash_directory(directory: str) -> str:
        """
        Compute the md5 hash of a directory based on its contents.

        Parameters
        ----------
        directory : str
            The path to the directory.

        Returns
        -------
        str
            The md5 hash.

        """
        md5 = hashlib.md5()
        for root, dirs, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                with open(filepath, "rb") as f:
                    while True:
                        data = f.read(65536)  # 64k chunks
                        if not data:
                            break
                        md5.update(data)
        return md5.hexdigest()

    @staticmethod
    def hash_py_file(file: str) -> str:
        """
        Compute the md5 hash of a .py file.

        Parameters
        ----------
        file : str
            The path to the file.

        Returns
        -------
        str
            The md5 hash.

        """
        md5 = hashlib.md5()
        with open(file, "rb") as f:
            while True:
                data = f.read(65536)

                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()


if __name__ == "__main__":

    algorithm_deployer = AlgorithmDeployer(
        "C:/Users/Jan Matula/Work/python-computing-backend/algorithms/sam2_segmentation"
    )
    algorithm_deployer.store_algorithm(database_connection=None)
