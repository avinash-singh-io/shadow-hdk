"""Tool results stay text in chat APIs; the image carrier follows the completed tool batch."""

from typing import Any

from langchain_openai.chat_models.base import _convert_message_to_dict
from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from pydantic import TypeAdapter

from shadow_hdk.adapters.langchain.model import _to_langchain
from shadow_hdk.kernel.ports import Message, ToolCall
from tests.adapters.browser.test_images_reach_the_model_and_wire import PNG


def test_image_carrier_follows_all_tool_results_and_fits_the_native_protocol() -> None:
    messages = (
        Message(
            "assistant", "", tool_calls=(ToolCall("a", "picture", {}), ToolCall("b", "picture", {}))
        ),
        Message("tool", "first caption", "a", images=(PNG,)),
        Message("tool", "second caption", "b", images=(PNG,)),
        Message("assistant", "seen"),
    )
    native = _to_langchain(messages)
    payload: list[Any] = [_convert_message_to_dict(message) for message in native]
    assert [message["role"] for message in payload] == [
        "assistant",
        "tool",
        "tool",
        "user",
        "assistant",
    ]
    assert [
        TypeAdapter(ChatCompletionToolMessageParam).validate_python(message)["content"]
        for message in payload[1:3]
    ] == ["first caption", "second caption"]
    carrier = TypeAdapter(ChatCompletionUserMessageParam).validate_python(payload[3])
    content = carrier["content"]
    assert not isinstance(content, str)
    assert (list(content), PNG.data in str(payload[1:3])) == (
        [
            {"type": "text", "text": "Images returned by tool call a."},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + PNG.data}},
            {"type": "text", "text": "Images returned by tool call b."},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + PNG.data}},
        ],
        False,
    )
