import random

# Telegram Message Effect IDs (Bot API 7.4+ / MTProto)
ANIMATED_EFFECTS = [
    5159385139981059251,  # ❤️ Heart
    5104841245755180586,  # 🔥 Fire
    5046509860389126442,  # 🎉 Celebration / Party
    5107584321108051014,  # 👍 Thumbs Up
]


def get_random_effect() -> int:
    return random.choice(ANIMATED_EFFECTS)
