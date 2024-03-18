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


import pytest
from distilabel.pipeline.local import Pipeline
from distilabel.steps.task.evol_quality.base import (
    EvolQuality,
)
from pydantic import ValidationError

from tests.unit.steps.task.utils import DummyLLM


class TestEvolInstruct:
    def test_with_errors(self) -> None:
        with pytest.raises(
            ValidationError, match="num_evolutions\n  Field required \\[type=missing"
        ):
            EvolQuality(name="task", pipeline=Pipeline())  # type: ignore

        with pytest.raises(ValueError, match="Step 'task' hasn't received a pipeline"):
            EvolQuality(name="task", llm=DummyLLM(), num_evolutions=2)

    def test_process(self) -> None:
        pipeline = Pipeline()
        llm = DummyLLM()
        task = EvolQuality(name="task", llm=llm, num_evolutions=2, pipeline=pipeline)
        assert list(task.process([{"instruction": "test", "response": "mock"}])) == [
            [
                {
                    "instruction": "test",
                    "response": "mock",
                    "evolved_response": "output",
                    "model_name": "test",
                }
            ]
        ]

    def test_process_store_evolutions(self) -> None:
        pipeline = Pipeline()
        llm = DummyLLM()
        task = EvolQuality(
            name="task",
            llm=llm,
            num_evolutions=2,
            store_evolutions=True,
            pipeline=pipeline,
        )
        assert list(task.process([{"instruction": "test", "response": "mock"}])) == [
            [
                {
                    "instruction": "test",
                    "response": "mock",
                    "evolved_responses": ["output", "output"],
                    "model_name": "test",
                }
            ]
        ]

    def test_serialization(self) -> None:
        pipeline = Pipeline()
        llm = DummyLLM()
        task = EvolQuality(name="task", llm=llm, num_evolutions=2, pipeline=pipeline)
        assert task.dump() == {
            "name": "task",
            "input_mappings": task.input_mappings,
            "output_mappings": task.output_mappings,
            "input_batch_size": task.input_batch_size,
            "llm": {
                "type_info": {
                    "module": task.llm.__module__,
                    "name": task.llm.__class__.__name__,
                }
            },
            "llm_kwargs": {},
            "num_evolutions": task.num_evolutions,
            "store_evolutions": task.store_evolutions,
            "mutation_templates": {
                "_type": "enum",
                "_enum_type": "str",
                "_name": task.mutation_templates.__name__,
                "_values": {
                    mutation.name: mutation.value  # type: ignore
                    for mutation in task.mutation_templates.__members__.values()  # type: ignore
                },
            },
            "num_generations": task.num_generations,
            "group_generations": task.group_generations,
            "generation_kwargs": {},
            "seed": task.seed,
            "runtime_parameters_info": [
                {
                    "name": "llm_kwargs",
                    "description": "The kwargs to be propagated to the `LLM` constructor. Note that these kwargs will be specific to each LLM, and while some as `model` may be present on each `LLM`, some others may not, so read the `LLM` constructor signature in advance to see which kwargs are available.",
                    "optional": True,
                },
                {
                    "name": "num_generations",
                    "optional": True,
                    "description": "The number of generations to be produced per input.",
                },
                {
                    "name": "generation_kwargs",
                    "optional": True,
                    "description": "The kwargs to be propagated to either `generate` or `agenerate` methods within each `LLM`. Note that these kwargs will be specific to each LLM, and while some as `temperature` may be present on each `LLM`, some others may not, so read the `LLM.{generate,agenerate}` signatures in advance to see which kwargs are available.",
                },
                {
                    "name": "seed",
                    "optional": True,
                    "description": "As `numpy` is being used in order to randomly pick a mutation method, then is nice to set a random seed.",
                },
            ],
            "type_info": {
                "module": task.__module__,
                "name": task.__class__.__name__,
            },
        }

        with Pipeline() as pipeline:
            new_task = EvolQuality.from_dict(task.dump())
            assert isinstance(new_task, EvolQuality)
