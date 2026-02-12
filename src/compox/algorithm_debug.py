import json, typer
from typing import Optional, Annotated, Dict, Any, List

from compox.algorithm_utils.LocalDebugSession import LocalDebugSession

app = typer.Typer(help="Commands for local debugging of algorithms")


def build_params_dict(items: Optional[List[str]]) -> Optional[Dict[str, Any]]:
    """
    Convert repeated --param key=value options into a dict.

    Parameters
    ----------
    items : list of str | None
        List of strings in the form "key=value".

    Returns
    -------
    dict | None
        Dictionary of parameters, or ``None`` if no items were provided.

    Raises
    ------
    typer.BadParameter
        If any item is not in the form "key=value".
    """
    if not items:
        return None

    params: Dict[str, Any] = {}

    for item in items:
        key, sep, value = item.partition("=")
        if not sep:
            raise typer.BadParameter(
                f"--param '{item}' must be in the form key=value"
            )

        key = key.strip()
        value = value.strip()

        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value 

        params[key] = parsed

    return params


@app.command("run")
def debug_run(
    algo: str = typer.Option(".", help="Path to algorithm folder"),
    data: str = typer.Option(..., help="Path to dataset folder (e.g. PNG/TIF stack)"),
    device: str = typer.Option("cpu", help="Device to run on (cpu/cuda)"),
    param: Annotated[
        Optional[List[str]],
        typer.Option(
            "--param",
            "-p",
            help="Algorithm parameter 'key=value'. Can be used multiple times."
        )
    ] = None,
):
    """
    Run an algorithm locally in debug mode (without Compox backend).

    Parameters
    ----------
    algo : str
        Path to the algorithm directory.
    data : str
        Path to the folder containing image slices.
    device : str
        Target device to execute the algorithm on.
    params : dict | None
        Algorithm parameters.
    """
    params = build_params_dict(param)

    debug(algo_dir=algo, data=data, params=params, device=device)


def debug(algo_dir=".", data=".", params=None, device="cpu"):
    """
    Run a local debugging session. The function initializes a `LocalDebugSession`, 
    loads an image stack from the specified folder, uploads it into the temporary 
    database, and executes the algorithm in the given directory.

    Parameters
    ----------
    algo_dir : str, optional
        Path to the algorithm folder. Default is the current directory (".").
    data : str, optional
        Path to the dataset folder (e.g. a directory with PNG/TIF slices).
    params : dict, optional
        Dictionary of algorithm parameters.
    device : str, optional
        Target device for execution. Default is "cpu".

    Returns
    -------
    Any
        Output returned by the algorithm’s ``run()`` method.
    """

    sess = LocalDebugSession(device=device)
    input_ids = sess.load_data(data)
    out = sess.run(algo_dir, {"input_dataset_ids": input_ids}, args=params or {})
    print(out)
    return out

if __name__ == "__main__":
    app()