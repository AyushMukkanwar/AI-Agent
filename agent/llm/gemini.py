from agent.llm.base import LLMClient
from google.genai import Client
from google.genai import types
from agent.types import LLMResponse, Message, ToolCall, ToolSpec
import uuid


class GeminiClient(LLMClient):

    def __init__(self, model: str, config: dict | None = None):
        self.model = model
        self.config = config
        self.client = Client(
            enterprise=True, project='ai-agent-1-512407', location='global'
        )

    def _to_gemini_contents(self, messages: list[Message]) -> list[types.Content]:
        contents: list[types.Content] = []

        for msg in messages:
            if isinstance(msg.provider_data, types.Content):
                contents.append(msg.provider_data)
                continue

            parts: list[types.Part] = []

            if msg.text is not None:
                parts.append(types.Part.from_text(text=msg.text))

            for call in msg.tool_calls:
                parts.append(types.Part(
                    function_call=types.FunctionCall(
                        id=call.id, name=call.name, args=call.args
                    )
                ))

            for result in msg.tool_results:
                parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        id=result.call_id,
                        name=result.name,
                        response={'error': result.output} if result.is_error
                                else {'result': result.output},
                    )
                ))

            contents.append(types.Content(
                role='model' if msg.role == 'assistant' else msg.role,
                parts=parts,
            ))

        return contents

    def _get_tools(self, tool_specs: list[ToolSpec]):
        if len(tool_specs) == 0:
            return None
        
        func_dec = []

        for spec in tool_specs:
            function = types.FunctionDeclaration(
                name=spec.name,
                description=spec.description,
                parameters_json_schema=spec.parameters
            )

            func_dec.append(function)
        
        tools = types.Tool(function_declarations=func_dec) 
        return tools

    def _parse_response(self, response: types.GenerateContentResponse) -> LLMResponse:
        text_chunks: list[str] = []
        tool_calls: list[ToolCall] = []

        if not response.candidates or not response.candidates[0].content:
            return LLMResponse(text=None, tool_calls=[], provider_data=None)

        content = response.candidates[0].content

        for part in content.parts or []:
            if part.text:
                text_chunks.append(part.text)

            if part.function_call:
                fc = part.function_call
                if not fc.name:
                    raise ValueError("Gemini returned a function call with no name")

                tool_calls.append(
                    ToolCall(
                        id=fc.id or str(uuid.uuid4()),
                        name=fc.name,
                        args=dict(fc.args or {}),
                    )
                )

        return LLMResponse(
            text="".join(text_chunks) or None,
            tool_calls=tool_calls,
            provider_data=content,
        )
   
    def generate(self, messages: list[Message], tool_specs: list[ToolSpec], sys_prompt: str | None = None) -> LLMResponse:
        response = self.client.models.generate_content(
            model=self.model, contents= self._to_gemini_contents(messages),
            config=types.GenerateContentConfig(
                system_instruction=sys_prompt,
                temperature=0.3,
                tools=[self._get_tools(tool_specs)]
            )
        )

        llm_res=self._parse_response(response)

        return llm_res