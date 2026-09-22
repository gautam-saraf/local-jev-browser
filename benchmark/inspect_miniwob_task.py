import argparse
import gymnasium as gym
import browsergym.miniwob

from browsergym.utils.obs import flatten_axtree_to_str


parser = argparse.ArgumentParser()

parser.add_argument(
    "--task",
    required=True,
)

parser.add_argument(
    "--seed",
    type=int,
    default=42,
)

args = parser.parse_args()


env = gym.make(
    args.task,
    headless=False,
)

try:
    obs, info = env.reset(
        seed=args.seed
    )

    print()
    print("=" * 80)
    print("MINIWOB TASK INSPECTION")
    print("=" * 80)

    print("Task:")
    print(args.task)

    print()
    print("Seed:")
    print(args.seed)

    print()
    print("Goal:")
    print(obs["goal"])

    print()
    print("URL:")
    print(obs["url"])

    print()
    print("===== ACCESSIBILITY TREE =====")

    print(
        flatten_axtree_to_str(
            obs["axtree_object"],
            extra_properties=obs[
                "extra_element_properties"
            ],
            with_visible=True,
            with_clickable=True,
            filter_visible_only=True,
            skip_generic=False,
        )
    )

    print()
    print("===== RAW AX NODES WITH BIDs =====")

    for node in obs[
        "axtree_object"
    ].get(
        "nodes",
        [],
    ):

        bid = node.get(
            "browsergym_id"
        )

        if not bid:
            continue

        def value(field):
            x = node.get(
                field,
                {}
            )

            if isinstance(x, dict):
                return x.get(
                    "value",
                    ""
                )

            return x

        print({
            "bid":
                bid,
            "role":
                value("role"),
            "name":
                value("name"),
            "value":
                value("value"),
            "properties":
                obs[
                    "extra_element_properties"
                ].get(
                    bid,
                    {},
                ),
        })

    print()
    print("===== INITIAL INFO =====")
    print(info)

    print()
    print(
        "Browser visible for 10 seconds..."
    )

    import time
    time.sleep(10)

finally:
    env.close()
