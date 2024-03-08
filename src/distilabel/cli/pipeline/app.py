# Copyright 2023-present, Argilla, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from typing import Any, List, Tuple

import typer
from typing_extensions import Annotated

RUNTIME_PARAM_REGEX = re.compile(r"(?P<key>[^.]+(?:\.[^=]+)+)=(?P<value>.+)")

app = typer.Typer(help="Commands to run and inspect Distilabel pipelines.")

ConfigOption = Annotated[
    str, typer.Option(help="Path or URL to the Distilabel pipeline configuration file.")
]


def parse_runtime_param(value: str) -> Tuple[List[str], str]:
    match = RUNTIME_PARAM_REGEX.match(value)
    if not match:
        raise typer.BadParameter(
            "Runtime parameters must be in the format `key.subkey=value` or"
            " `key.subkey.subsubkey=value`"
        )
    return match.group("key").split("."), match.group("value")


@app.command(name="run", help="Run a Distilabel pipeline.")
def run(
    config: ConfigOption,
    # `param` is `List[Tuple[Tuple[str, ...], str]]` after parsing
    param: Annotated[
        List[Any],
        typer.Option(help="", parser=parse_runtime_param, default_factory=list),
    ],
) -> None:
    from distilabel.cli.pipeline.utils import get_pipeline, parse_runtime_parameters

    try:
        pipeline = get_pipeline(config)
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1) from e

    parameters = parse_runtime_parameters(param)
    pipeline.run(parameters=parameters)


@app.command(name="info", help="Get information about a Distilabel pipeline.")
def info(config: ConfigOption) -> None:
    from distilabel.cli.pipeline.utils import get_pipeline, print_pipeline_info

    try:
        pipeline = get_pipeline(config)
        print_pipeline_info(pipeline)
    except Exception as e:
        typer.secho(str(e), fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=1) from e
