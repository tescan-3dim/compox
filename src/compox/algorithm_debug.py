import json, typer
from typing import Optional, Annotated

from compox.algorithm_utils.LocalDebugSession import LocalDebugSession

app = typer.Typer(help="Commands for local debugging of algorithms")

def parse_params(value: Optional[str]) -> Optional[dict]:
    """
    Parse a JSON string of algorithm parameters from the command line.

    Parameters
    ----------
    value : str | None
        A JSON string containing algorithm parameters.

    Returns
    -------
    dict | None
        Parsed dictionary of parameters, or ``None`` if no input was provided.

    Raises
    ------
    typer.BadParameter
        If the string cannot be parsed as valid JSON.
    """

    if value is None or value == "":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"--params must be valid JSON: {e}")

@app.command("run")
def debug_run(
    algo: str = typer.Option(".", help="Path to algorithm folder"),
    data: str = typer.Option(..., help="Path to dataset folder (e.g. PNG/TIF stack)"),
    device: str = typer.Option("cpu", help="Device to run on (cpu/cuda)"),
    params: Annotated[Optional[str], typer.Option("--params", callback=parse_params, help="Algorithm params (JSON)")] = None,
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