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

import sys

from distilabel.steps.base import RuntimeParameter

if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

if sys.version_info < (3, 11):
    from enum import EnumMeta as EnumType
else:
    from enum import EnumType

from functools import cached_property
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np
from pydantic import Field, PrivateAttr
from typing_extensions import override

from distilabel.steps.task.base import GeneratorTask
from distilabel.steps.task.evol_instruct.utils import (
    GenerationMutationTemplatesEvolInstruct,
)

if TYPE_CHECKING:
    from distilabel.steps.task.typing import ChatType
    from distilabel.steps.typing import GeneratorStepOutput


class EvolInstructGenerator(GeneratorTask):
    """WizardLM: Empowering Large Language Models to Follow Complex Instructions

    Reference:
        - https://arxiv.org/abs/2304.12244
        - https://github.com/h2oai/h2o-wizardlm
        - https://github.com/nlpxucan/WizardLM/Evol_Instruct

    Runtime parameters:

    - `min_length`: Defines the length (in bytes) that the generated instruction needs to be higher than, to be considered valid.
    - `max_length`: Defines the length (in bytes) that the generated instruction needs to be lower than, to be considered valid.
    - `seed`: The number of evolutions to be run.

    Columns:

    - `input`: instruction
    - `output`: there's multiple scenarios:
        - `generate_answers=False` -> (instruction, model_name)
        - `generate_answers=True` -> (instruction, model_name, answer)
    """

    num_instructions: int
    generate_answers: bool = False
    mutation_templates: EnumType = Field(
        default=GenerationMutationTemplatesEvolInstruct
    )

    min_length: RuntimeParameter[int] = Field(
        default=512,
        description="Defines the length (in bytes) that the generated instruction needs to be higher than, to be considered valid.",
    )
    max_length: RuntimeParameter[int] = Field(
        default=1024,
        description="Defines the length (in bytes) that the generated instruction needs to be lower than, to be considered valid.",
    )

    seed: RuntimeParameter[int] = Field(
        default=42,
        description="As `numpy` is being used in order to randomly pick a mutation method, then is nice to seed a random seed.",
    )
    _seed_texts: Optional[List[str]] = PrivateAttr(default_factory=list)
    _prompts: Optional[List[str]] = PrivateAttr(default_factory=list)

    def _generate_seed_texts(self) -> List[str]:
        """Generates a list of seed texts to be used as part of the starting prompts for the task.

        It will use the `FRESH_START` mutation template, as it needs to generate text from scratch; and
        a list of English words will be used to generate the seed texts that will be provided to the
        mutation method and included within the prompt.

        Returns:
            A list of seed texts to be used as part of the starting prompts for the task.
        """
        seed_texts = []
        for _ in range(self.num_instructions * 10):
            num_words = np.random.choice([1, 2, 3, 4])
            seed_texts.append(
                self.mutation_templates.FRESH_START.value.replace(  # type: ignore
                    "<PROMPT>",
                    ", ".join(
                        [
                            np.random.choice(self._english_nouns).strip()
                            for _ in range(num_words)
                        ]
                    ),
                )
            )
        return seed_texts

    @override
    def model_post_init(self, __context: Any) -> None:
        """Override this method to perform additional initialization after `__init__` and `model_construct`.
        This is useful if you want to do some validation that requires the entire model to be initialized.
        """
        super().model_post_init(__context)

        np.random.seed(self.seed)

        self._seed_texts = self._generate_seed_texts()
        self._prompts = [
            np.random.choice(self._seed_texts) for _ in range(self.num_instructions)
        ]

    @cached_property
    def _english_nouns(self) -> List[str]:
        """A list of English nouns to be used as part of the starting prompts for the task.

        Reference:
            - https://github.com/h2oai/h2o-wizardlm
        """
        _path = str(
            importlib_resources.files("distilabel")
            / "steps/task/evol_instruct/english_nouns.txt"
        )
        with open(_path, mode="r") as f:
            return [line.strip() for line in f.readlines()]

    @property
    def outputs(self) -> List[str]:
        """The output for the task are the `instruction`, the `answer` if `generate_answers=True`
        and the `model_name`."""
        _outputs = ["instruction", "model_name"]
        if self.generate_answers:
            _outputs.append("answer")
        return _outputs

    def format_output(  # type: ignore
        self, instruction: str, answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """The output for the task is a dict with: `instruction`; `answer` if `generate_answers=True`;
        and, finally, the `model_name`.

        Args:
            instruction: The instruction to be included within the output.
            answer: The answer to be included within the output if `generate_answers=True`.

        Returns:
            If `generate_answers=True` return {"instruction": ..., "answer": ..., "model_name": ...};
            if `generate_answers=False` return {"instruction": ..., "model_name": ...};
        """
        _output = {
            "instruction": instruction,
            "model_name": self.llm.model_name,
        }
        if self.generate_answers and answer is not None:
            _output["answer"] = answer[-1]
        return _output

    @property
    def mutation_templates_names(self) -> List[str]:
        """Returns the names i.e. keys of the provided `mutation_templates` enum."""
        return [
            member.name  # type: ignore
            for member in self.mutation_templates.__members__.values()  # type: ignore
        ]

    def _apply_random_mutation(self, iter_no: int) -> List["ChatType"]:
        """Applies a random mutation from the ones provided as part of the `mutation_templates`
        enum, and returns the provided instruction within the mutation prompt.

        Args:
            iter_no: The iteration number to be used to check whether the iteration is the
                first one i.e. FRESH_START, or not.

        Returns:
            A random mutation prompt with the provided instruction formatted as an OpenAI conversation.
        """
        prompts = []
        for idx in range(self.num_instructions):
            if (
                iter_no == 0
                or "Write one question or request containing" in self._prompts[idx]  # type: ignore
            ):
                mutation = "FRESH_START"
            else:
                mutation = np.random.choice(self.mutation_templates_names)
                if mutation == "FRESH_START":
                    self._prompts[idx] = np.random.choice(self._seed_texts)  # type: ignore

            prompt_with_template = (
                self.mutation_templates[mutation].value.replace(  # type: ignore
                    "<PROMPT>",
                    self._prompts[idx],  # type: ignore
                )  # type: ignore
                if iter_no != 0
                else self._prompts[idx]  # type: ignore
            )
            prompts.append([{"role": "user", "content": prompt_with_template}])
        return prompts

    def _generate_answers(self, instructions: List[List[str]]) -> List[str]:
        """Generates the answer for the last instruction in `instructions`.

        Args:
            instructions: A list of lists where each item is a list with either the last
                evolved instruction if `store_evolutions=False` or all the evolved instructions
                if `store_evolutions=True`.
        Returns:
            A list of answers for the last instruction in `instructions`.
        """
        _formatted_instructions = [
            [{"role": "user", "content": instruction[-1]}]
            for instruction in instructions
        ]
        return self.llm.generate(
            _formatted_instructions,
            **self.generation_kwargs,  # type: ignore
        )

    @override
    def process(self, offset: int = 0) -> "GeneratorStepOutput":  # type: ignore
        """Processes the inputs of the task and generates the outputs using the LLM.

        Args:
            offset: The offset to start the generation from. Defaults to 0.

        Yields:
            A list of Python dictionaries with the outputs of the task, and a boolean
            flag indicating whether the task has finished or not i.e. is the last batch.
        """
        instructions = []
        mutation_no = 0

        iter_no = 0
        while len(instructions) < self.num_instructions:
            prompts = self._apply_random_mutation(iter_no=iter_no)

            generated_prompts = self.llm.generate(
                prompts,
                **self.generation_kwargs,  # type: ignore
            )
            for idx, generated_prompt in enumerate(generated_prompts):
                generated_prompt = generated_prompt[-1]
                generated_prompt = (
                    generated_prompt.split("Prompt#:")[-1].strip()
                    if "Prompt#:" in generated_prompt
                    else generated_prompt.strip()
                )
                if self.max_length >= len(generated_prompt) >= self.min_length:  # type: ignore
                    instructions.append(generated_prompt)
                    self._prompts[idx] = np.random.choice(self._seed_texts)  # type: ignore
                else:
                    self._prompts[idx] = generated_prompt  # type: ignore

            self._logger.info(
                f"🔄 Ran iteration {iter_no} with {len(instructions)} instructions already evolved!"
            )
            iter_no += 1

            if len(instructions) > self.num_instructions:
                instructions = instructions[: self.num_instructions]
            if len(instructions) > mutation_no:
                mutation_no = len(instructions) - mutation_no

            if not self.generate_answers and len(instructions[-mutation_no:]) > 0:
                yield (
                    [
                        self.format_output(mutated_instruction)
                        for mutated_instruction in instructions[-mutation_no:]
                    ],
                    len(instructions) >= self.num_instructions,
                )

        self._logger.info(f"🎉 Finished evolving {len(instructions)} instructions!")

        if self.generate_answers:
            self._logger.info(
                f"🧠 Generating answers for the {len(instructions)} evolved instructions!"
            )

            answers = self._generate_answers(instructions)

            self._logger.info(
                f"🎉 Finished generating answers for the {len(instructions)} evolved instructions!"
            )

            yield (
                [
                    self.format_output(instruction, answer)
                    for instruction, answer in zip(instructions, answers)
                ],
                True,
            )
