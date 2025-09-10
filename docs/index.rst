Welcome to the t3dserver documentation!
====================================================

.. include:: ../README.md
    :parser: myst_parser.sphinx_

Algorithms
====================================================

.. include:: ../algorithms/readme.md
    :parser: myst_parser.sphinx_
.. include:: ../algorithms/template_denoising_algorithm/README.md
    :parser: myst_parser.sphinx_
.. include:: ../algorithms/template_segmentation_algorithm/README.md
    :parser: myst_parser.sphinx_
.. include:: ../algorithms/template_registration_algorithm/README.md
    :parser: myst_parser.sphinx_
.. automodule:: algorithm_utils.AlgorithmDeployer
    :members:
.. automodule:: algorithm_utils.AlgorithmManager
    :members:
.. automodule:: algorithm_utils.BaseRunner
    :members:

Tasks
====================================================

.. automodule:: tasks.TaskHandler
    :members:
.. automodule:: tasks.DebuggingTaskHandler
    :members:

Sessions
====================================================
.. automodule:: session.TaskSession
    :members:
.. automodule:: session.DataCache
    :members:

Database Connection
====================================================

.. automodule:: database_connection.BaseConnection
    :members:
.. automodule:: database_connection.S3Connection
    :members:
.. automodule:: database_connection.TempfileConnection
    :members:
.. automodule:: database_connection.database_utils
    :members:

Server Utils
====================================================

.. automodule:: server_utils
    :members:
.. toctree::
   :maxdepth: 2
   :caption: Contents:

Server Endpoints
====================================================
.. automodule:: routers.algorithms_controller
    :members:
.. automodule:: routers.file_controller
    :members:
.. automodule:: routers.execution_controller
    :members:

Pydantic Models
====================================================
.. automodule:: pydantic_models
    :members:

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
