"""
Loading Messages
Funny, humorous loading messages for the agentic pipeline
"""
import random

LOADING_MESSAGES = [
    "🤖 Router agent waking up from coffee break...",
    "🧠 Summarizer agent dusting off ancient scrolls...",
    "🔍 Insight agent putting on detective glasses...",
    "🎯 Flaw detector agent sharpening critical eye...",
    "👥 Context agent gathering round table discussion...",
    "❓ QA agent loading brain bleach to forget bad questions...",
    "✨ Personalization agent discovering user vibes...",
    "📊 PPT agent firing up the disco ball graphics...",
    "💼 Application agent connecting dots to real world...",
    "📚 Critic agent preparing harsh but fair review...",
    "🚀 All agents syncing up for coordinated genius...",
    "⚡ LLM processing at 1.21 gigawatts...",
    "🎪 Agents doing a synchronized swimming routine...",
    "🔗 LangGraph weaving silk threads of reasoning...",
    "🧠 Neural pathways firing in exotic patterns...",
    "🎬 Action! Agents, lights, camera, analysis!",
    "🌈 Agents painting the Mona Lisa of responses...",
    "⚙️ Gears turning, hamsters running, sparks flying...",
    "🎸 Agents jamming out a sweet analysis groove...",
    "🏃 Agents in a relay race to wisdom...",
    "🎭 Agents performing Shakespeare's summary act...",
    "🔮 Crystal ball showing insights into the future...",
    "🎨 Agents mixing the perfect color of understanding...",
    "🎯 Agents throwing darts at the bullseye of truth...",
    "🌊 Riding the wave of agentic intelligence...",
    "🍕 Agents ordering thoughts like toppings on pizza...",
    "🎪 Three-ring circus of analysis happening now...",
    "📡 Transmitting wisdom through the aether...",
    "🎪 Agents juggling concepts with expert precision...",
    "🚗 Agents shifting gears into high-performance mode...",
    "🎯 Agents laser-focused on paper excellence...",
    "🌟 Agents channeling their inner genius consultant...",
    "🎢 Buckle up for this intellectual roller coaster...",
    "🎭 Agents rehearsing their finest analytical performance...",
    "🔥 Agents bringing the heat to this analysis...",
    "💎 Polishing your response to diamond-grade quality...",
    "🎪 Agents assembling Voltron of understanding...",
    "🌀 Spinning the golden thread of comprehension...",
    "🎬 Cue the dramatic music, analysis incoming...",
    "🏆 Agents competing for gold medal insight...",
]

def get_random_loading_message() -> str:
    """Get a random funny loading message"""
    return random.choice(LOADING_MESSAGES)

def get_loading_messages_sequence() -> list:
    """Get a sequence of loading messages for streaming"""
    return LOADING_MESSAGES.copy()
