import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

PROVIDERS = [
    ("openai", "OpenAI", "Uses OPENAI_API_KEY"),
    ("openrouter", "OpenRouter", "Uses OPENROUTER_API_KEY"),
    ("anthropic", "Anthropic", "Uses ANTHROPIC_API_KEY"),
    ("groq", "Groq", "Uses GROQ_API_KEY"),
    ("deepseek", "DeepSeek", "Uses DEEPSEEK_API_KEY"),
    ("ollama", "Ollama (local)", "No key needed, local server"),
    ("custom", "Custom model ID", "Model ID must include provider, e.g. openai/gpt-4o"),
]


class AIMessage(bpy.types.PropertyGroup):
    role: StringProperty(default="user")
    content: StringProperty()
    image: StringProperty(subtype="FILE_PATH")


class AIProperties(bpy.types.PropertyGroup):
    oc_provider: bpy.props.EnumProperty(
        name="Provider",
        items=PROVIDERS,
        default="openai",
        description="Model provider configured for the portable OpenCode runtime",
    )
    oc_api_key: StringProperty(
        name="API Key",
        subtype="PASSWORD",
        description="Provider API key, passed to the OpenCode process",
    )
    oc_model: StringProperty(
        name="Model",
        default="gpt-4o",
        description="Model for OpenCode, e.g. gpt-4o, claude-sonnet-4, llava",
    )
    oc_port: IntProperty(
        name="Port",
        default=4096,
        min=1024,
        max=65535,
        description="Port for the local OpenCode server",
    )
    oc_session_id: StringProperty(default="")
    oc_status: StringProperty(default="")
    oc_progress: FloatProperty(default=0.0, min=0.0, max=1.0, subtype="FACTOR")
    oc_auto_fix: BoolProperty(
        name="Auto-fix errors",
        default=True,
        description="Automatically send execution logs back to the agent for fixing",
    )
    auto_run: BoolProperty(
        name="Auto-run",
        default=True,
        description="Automatically execute code returned by the agent",
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
    busy: BoolProperty(default=False, description="Waiting for the agent")
