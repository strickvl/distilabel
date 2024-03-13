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

from enum import Enum

_base = """I want you to act as a Response Rewriter
Your goal is to enhance the quality of the response given by an AI assistant
to the #Given Prompt# through rewriting.
But the rewritten response must be reasonable and must be understood by humans.
Your rewriting cannot omit the non-text parts such as the table and code in
#Given Prompt# and #Given Response#. Also, please do not omit the input
in #Given Prompt#.
You Should enhance the quality of the response using the following method:
"""

_end = """
You should try your best not to make the #Rewritten Response# become verbose,
#Rewritten Response# can only add 10 to 20 words into #Given Response#.
'#Given Response#', '#Rewritten Response#', 'given response' and 'rewritten response'
are not allowed to appear in #Rewritten Response#
#Given Prompt#:
<PROMPT>
#Given Response#:
<RESPONSE>
#Rewritten Response#:
"""


class MutationTemplates(str, Enum):
    HELPFULLNESS = f"{_base}Please make the Response more helpful to the user.{_end}"
    RELEVANCE = (
        f"{_base}Please make the Response more relevant to #Given Prompt#.{_end}"
    )
    DEPTH = f"{_base}Please make the Response more in-depth.{_end}"
    CREATIVITY = f"{_base}Please increase the creativity of the response.{_end}"
    DETAILS = f"{_base}Please increase the detail level of Response.{_end}"