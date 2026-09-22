import gymnasium as gym
import browsergym.miniwob


TASK = "browsergym/miniwob.click-button"

print("=" * 60)
print("BROWSERGYM MINIWOB SMOKE TEST")
print("=" * 60)
print("Task:", TASK)

env = gym.make(
    TASK,
    headless=False,
)

try:
    obs, info = env.reset(seed=42)

    print()
    print("RESET=OK")

    print()
    print("Goal:")
    print(obs["goal"])

    print()
    print("URL:")
    print(obs["url"])

    print()
    print("Observation keys:")
    for key in obs.keys():
        print("-", key)

    print()
    print(
        "Screenshot shape:",
        getattr(
            obs.get("screenshot"),
            "shape",
            None,
        ),
    )

    print()
    print("Initial task info:")
    print(info)

finally:
    env.close()

print()
print("MINIWOB_SMOKE_TEST=PASS")
