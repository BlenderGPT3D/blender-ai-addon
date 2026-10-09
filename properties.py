import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)


class AIMessage(bpy.types.PropertyGroup):
    role: StringProperty(default="user")
    content: StringProperty()
    image: StringProperty(subtype="FILE_PATH")


class AIProperties(bpy.types.PropertyGroup):
    api_base: StringProperty(
        name="Base URL",
        default="https://api.openai.com/v1",
        description="OpenAI-compatible endpoint base URL",
    )
    api_key: StringProperty(
        name="API Key",
        subtype="PASSWORD",
        description="API key for the provider",
    )
    model: StringProperty(
        name="Model",
        default="gpt-4o",
        description="Model name, must support images for image input",
    )
    temperature: FloatProperty(
        name="Temperature",
        default=0.2,
        min=0.0,
        max=2.0,
        description="Sampling temperature",
    )
    max_tokens: IntProperty(
        name="Max tokens",
        default=2048,
        min=64,
        max=32768,
        description="Maximum tokens in the response",
    )
    auto_run: BoolProperty(
        name="Auto-run",
        default=True,
        description="Automatically execute code returned by the AI",
    )
    input: StringProperty(
        name="Message",
        multiline=True,
        description="Describe what to create or change",
    )
    image_path: StringProperty(
        name="Reference image",
        subtype="FILE_PATH",
        description="Optional image attached to the next message",
    )
    messages: CollectionProperty(type=AIMessage)
    busy: BoolProperty(default=False, description="Waiting for the AI response")
