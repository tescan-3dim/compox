"""
Copyright 2024 TESCAN 3DIM, s.r.o.
All rights reserved
"""

import json
import os
import subprocess
import pystray
import tkinter as tk
import textwrap
from functools import partial
from tkinter.filedialog import askdirectory, askopenfilename
from PIL import Image
import threading
from loguru import logger

from compox.algorithm_utils.AlgorithmDeployer import AlgorithmDeployer
from compox.algorithm_utils.AlgorithmExporter import AlgorithmExporter
from compox.algorithm_utils.AlgorithmManager import AlgorithmManager


class ServerSystrayInterface(pystray.Icon):
    def __init__(
        self,
        settings,
        app,
        server,
        config,
        title=None,
        menu=None,
    ):
        """
        The class for the system tray interface of the server.

        Parameters
        ----------
        settings : object
            The server settings object.
        app : object
            The FastAPI app object.
        server : object
            The uvicorn server object.
        config : object
            The uvicorn configuration object.

        """
        self.logger = logger.bind(log_type="SYSTRAY")
        self._name = settings.info.product_name

        self._group_name = settings.info.group_name
        self._organization_name = settings.info.organization_name
        self._organization_domain = settings.info.organization_domain
        self._log_path = settings.log_path
        self._is_ssl = settings.ssl.use_ssl
        self._algorithm_add_remove_in_menus = (
            settings.gui.algorithm_add_remove_in_menus
        )
        self._menu = menu
        self._title = settings.info.product_name
        self._displayed_version = server._version
        self.algorithm_manager = AlgorithmManager(
            database_connection=app.state.database_connection
        )
        self.algorithm_exporter = AlgorithmExporter(
            database_connection=app.state.database_connection
        )
        self.__initialize_menu(app, server, config)

        icon_img = Image.open(settings.gui.icon_path)
        super().__init__(self._name, icon_img, self._title, self._menu)

    def set_menu(self, menu):
        self._menu = menu
        self.update_menu()

    def on_restart(self, server):
        server.restart()
        self.stop()

    def on_show_server_log(self):
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.DETACHED_PROCESS
            subprocess.Popen(
                ["notepad.exe", self._log_path],
                startupinfo=startupinfo,
            )

    def get_algorithms(self, app):
        algorithm_ids = app.state.database_connection.list_objects(
            "algorithm-store"
        )
        algorithm_records = []
        if algorithm_ids:
            algorithm_jsons = app.state.database_connection.get_objects(
                "algorithm-store",
                [algorithm_id["Key"] for algorithm_id in algorithm_ids],
            )
            for i, algorithm_json in enumerate(algorithm_jsons):
                algorithm_json = json.loads(algorithm_json)
                algorithm_name = algorithm_json["algorithm_name"]
                algorithm_id = algorithm_json["algorithm_id"]
                algorithm_major = algorithm_json["algorithm_major_version"]
                algorithm_minor = algorithm_json[
                    "latest_algorithm_minor_version"
                ]
                algorithm_description = algorithm_json["algorithm_description"]
                algorithm_tooltip = (
                    f"{algorithm_name} v{algorithm_major}.{algorithm_minor}"
                )
                # make first letter uppercase
                algorithm_tooltip = (
                    algorithm_tooltip[0].upper() + algorithm_tooltip[1:]
                )
                algorithm_key = (
                    f"{algorithm_id}~{algorithm_name}~{algorithm_major}"
                )

                algorithm_records.append(
                    {
                        "tooltip": algorithm_tooltip,
                        "name": algorithm_name,
                        "major_version": algorithm_major,
                        "minor_version": algorithm_minor,
                        "id": algorithm_id,
                        "key": algorithm_key,
                        "description": algorithm_description,
                    }
                )
        return algorithm_records

    def on_get_algorithms(self, app):
        algorithm_records = self.get_algorithms(app)
        pystray_items = []
        pystray_items.append(
            pystray.MenuItem("Refresh", lambda: self.update_menu())
        )
        pystray_items.append(pystray.Menu.SEPARATOR)
        if not algorithm_records:
            pystray_items.append(
                pystray.MenuItem("Empty.", None, enabled=False)
            )
        else:
            if app.state.settings.gui.algorithm_add_remove_in_menus:
                for record in algorithm_records:
                    pystray_items.append(
                        pystray.MenuItem(
                            record["tooltip"],
                            pystray.Menu(
                                pystray.MenuItem(
                                    "Algorithm Info",
                                    partial(
                                        self.on_show_algorithm_info,
                                        record["tooltip"],
                                        record["description"],
                                    ),
                                ),
                                pystray.Menu.SEPARATOR,
                                pystray.MenuItem(
                                    "Export Algorithm",
                                    partial(
                                        self.on_export_algorithm,
                                        record["name"],
                                        record["major_version"],
                                    ),
                                ),
                                pystray.MenuItem(
                                    "Remove Algorithm",
                                    partial(
                                        self.on_remove_algorithm,
                                        record["name"],
                                        record["major_version"],
                                    ),
                                ),
                            ),
                        )
                    )
                pystray_items.append(pystray.Menu.SEPARATOR)
                pystray_items.append(
                    pystray.MenuItem(
                        "Remove All Algorithms",
                        lambda: self.on_remove_all_algorithms(app),
                    )
                )
            else:
                for record in algorithm_records:
                    pystray_items.append(
                        pystray.MenuItem(
                            record["tooltip"],
                            pystray.Menu(pystray.MenuItem(record["id"], None)),
                        )
                    )
        return pystray_items

    def on_add_algorithm(self, app):
        # the clash of the tkiter caused weird behavior, when the dialog was opened
        # but was not responsive to user input, so we need to run it in a separate thread
        # and destroy the root window after the dialog is closed

        @logger.catch
        def add_algorithm():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = askdirectory(initialdir="..")
            root.destroy()

            if not path:
                return
            if not app.state.database_connection:
                self.notify(
                    "Failed to add algorthm: No database connection!",
                    title="Error",
                )
            algorithm_id = ""
            try:
                algorithm_id = AlgorithmDeployer(path).store_algorithm(
                    database_connection=app.state.database_connection,
                )
                self.notify(
                    f"Added algorithm from folder:\n{algorithm_id}",
                    title="Success",
                )
                self.update_menu()
            except Exception as e:
                self.notify(
                    "Failed to add algorithm from folder. Please ensure the selected directory "
                    "contains a valid algorithm. You can check the backend log for more details.",
                    title="Error",
                )
                raise e

        threading.Thread(
            target=add_algorithm,
        ).start()

    def on_add_algorithm_zip(self, app):
        # the clash of the tkiter caused weird behavior, when the dialog was opened
        # but was not responsive to user input, so we need to run it in a separate thread
        # and destroy the root window after the dialog is closed

        @logger.catch
        def add_algorithm_zip():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = askopenfilename(
                initialdir="..",
                filetypes=[("Zip files", "*.zip")],
            )
            root.destroy()

            if not path:
                return
            if not app.state.database_connection:
                self.notify(
                    "Failed to add algorithm: No database connection!",
                    title="Error",
                )
            algorithm_id = ""
            try:
                algorithm_id = AlgorithmDeployer.deploy_from_zip(
                    path,
                    database_connection=app.state.database_connection,
                )
                self.notify(
                    f"Added algorithm from zip:\n{algorithm_id}",
                    title="Success",
                )
                self.update_menu()
            except Exception as e:
                self.notify(
                    "Failed to add algorithm from zip. Please ensure the selected file "
                    "is a valid algorithm package. You can check the backend log for more details.",
                    title="Error",
                )
                raise e

        threading.Thread(
            target=add_algorithm_zip,
        ).start()

    def on_export_algorithm(self, name, major_version, icon=None, item=None):
        # the clash of the tkiter caused weird behavior, when the dialog was opened
        # but was not responsive to user input, so we need to run it in a separate thread
        # and destroy the root window after the dialog is closed

        @self.logger.catch
        def export_algorithm():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = askdirectory(initialdir="..")
            root.destroy()

            if not path:
                return
            try:
                self.algorithm_exporter.export_algorithm_to_zip(
                    algorithm_name=name,
                    algorithm_major_version=major_version,
                    target_zip_path=os.path.join(
                        path, f"{name}_{major_version}.zip"
                    ),
                )
                self.notify(
                    f"Exported algorithm:\n{name} v{major_version}",
                    title="Success",
                )
            except Exception as e:
                self.notify(
                    "Failed to export algorithm. You can check the backend log for more details.",
                    title="Error",
                )
                raise e

        threading.Thread(
            target=export_algorithm,
        ).start()

    def on_remove_algorithm(self, name, major_version, icon=None, item=None):
        # the icon and item are not used, but they are required by pystray
        # to call the function with the correct signature, otherwise it will
        # throw a number of positional arguments error

        self.algorithm_manager.delete_algorithm(
            name=name, major_version=major_version
        )
        self.notify(
            f"Removed algorithm :\n{name} v{major_version}", title="Success"
        )
        self.update_menu()

    def on_show_algorithm_info(
        self, tooltip, description, icon=None, item=None
    ):
        # the icon and item are not used, but they are required by pystray
        # to call the function with the correct signature, otherwise it will
        # throw a number of positional arguments error
        self.notify(
            textwrap.fill(
                description,
                width=50,
            ),
            title=tooltip,
        )

    def on_remove_all_algorithms(self, app):
        # the clash of the tkiter caused weird behavior, when the dialog was opened
        # but was not responsive to user input, so we need to run it in a separate thread
        # and destroy the root window after the dialog is closed
        @self.logger.catch
        def remove_algorithms():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            confirmation = tk.messagebox.askyesno(
                title="Confirm Removal",
                message="Are you sure to remove all algorithms from the backend? This action cannot be undone.",
            )

            root.destroy()

            if confirmation:
                root.update()
                self.logger.info("Removed all algorithms")
                algorithm_records = self.get_algorithms(app)
                for record in algorithm_records:
                    self.algorithm_manager.delete_algorithm(
                        name=record["name"],
                        major_version=record["major_version"],
                    )
                self.notify("Removed all algorithms", title="Success")
                self.update_menu()

        threading.Thread(target=remove_algorithms).start()

    def on_about(self, config):
        version = f"version {self._displayed_version}"
        self.notify(
            self._group_name
            + "\n"
            + version
            + "\nAvailable at: "
            + ("https://" if config.is_ssl else "http://")
            + config.host
            + ":"
            + str(config.port),
        )

    def on_quit(self, server):
        server.should_exit = True
        self.stop()

    def __initialize_menu(self, app, server, config):
        menuItems = (
            pystray.MenuItem(
                "About",
                lambda: self.on_about(config),
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Algorithms",
                pystray.Menu(lambda: self.on_get_algorithms(app)),
            ),
            pystray.MenuItem(
                "Add Algorithm (Folder)",
                lambda: self.on_add_algorithm(app),
                visible=self._algorithm_add_remove_in_menus,
            ),
            pystray.MenuItem(
                "Add Algorithm (ZIP)",
                lambda: self.on_add_algorithm_zip(app),
                visible=self._algorithm_add_remove_in_menus,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Log",
                lambda: self.on_show_server_log(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Restart", lambda: self.on_restart(server)),
            pystray.MenuItem("Quit", lambda: self.on_quit(server)),
        )
        self.set_menu(pystray.Menu(*menuItems))
