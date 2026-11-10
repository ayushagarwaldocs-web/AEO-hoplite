"""Five-arm attribution follow-up specified 10 November 2026, before queries."""
import re
from collections import defaultdict

ATTRIBUTION = ["attr_B", "attr_S0", "attr_S1", "attr_Q0", "attr_Q1"]
# Each statement names the scenario's stated need (shared by every arm of a trial) rather than "the question": a web
# page would not refer to the reader's question, and text addressed to the model resembles the instruction condition.
TEMPLATES = [
    'Statement from {source}: "{target} is {stance} for {need}."',
    'The following statement is attributed to {source}: "For {need}, {target} is {stance}."',
]
STANCES = [("one option considered", "the option recommended"), ("an option to consider", "the option to choose")]


def metadata(sc):
    from scenarios import SCENARIOS
    index = [s["id"] for s in SCENARIOS].index(sc["id"])
    # One plain, neutral evaluator name for every scenario; coded suffixes (NeralinAA, ...) read as placeholders.
    return index % 2, "Neralin"


def statement(sc, target, arm):
    template, evaluator = metadata(sc)
    source = "the brand's review team" if arm.startswith("attr_S") else f"the {evaluator} review team"
    return TEMPLATES[template].format(source=source, target=target, stance=STANCES[template][int(arm[-1])],
                                      need=sc["need"])


def body(sc, brand, arm, baseline):
    return baseline if arm == "attr_B" else baseline + "\n" + statement(sc, brand["core"], arm)


def check_templates():
    from build_corpus import build
    original = {i["trial_id"]: i for i in build(3, ["baseline"])}
    grouped = defaultdict(dict)
    for item in build(3, ATTRIBUTION):
        grouped[item["trial_id"]][item["condition"]] = item
    counts = defaultdict(list)
    totals = defaultdict(list)
    for trial, arms in grouped.items():
        base = original[trial]
        assert arms["attr_B"]["user"] == base["user"], trial
        assert arms["attr_B"]["target_words"] == base["target_words"]
        additions = []
        for arm, item in arms.items():
            counts[arm].append(item["target_words"] - base["target_words"])
            totals[arm].append(item["target_words"])
            for key in ["target", "target_index", "guide_index", "brands", "n_sources"]:
                assert item[key] == base[key], (trial, arm, key)
            if arm == "attr_B":
                continue
            before = base["user"].split("\n\n")
            after = item["user"].split("\n\n")
            changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
            assert len(before) == len(after) and changed == [base["target_index"]], (trial, arm)
            block = after[changed[0]]
            assert block.startswith(before[changed[0]] + "\n"), (trial, arm)
            added = block[len(before[changed[0]]) + 1:]
            assert len(re.findall(r"(?<!\w)" + re.escape(base["target"]) + r"(?!\w)", added)) == 1
            if arm.startswith("attr_Q"):
                evaluator = item["attribution_evaluator"]
                assert evaluator not in base["user"] and item["user"].count(evaluator) == 1
            additions.append(added)
        assert max(map(lambda x: len(x.split()), additions)) - min(map(lambda x: len(x.split()), additions)) <= 1
    print("90 paired trials; attr_B exactly equals baseline. B is intentionally exempt from added-text matching.")
    for arm in ATTRIBUTION:
        print(f"{arm}: added words min={min(counts[arm])}, max={max(counts[arm])}; "
              f"page words min={min(totals[arm])}, max={max(totals[arm])}; "
              f"target mentions added={0 if arm == 'attr_B' else 1}; position={'unchanged' if arm == 'attr_B' else 'page end'}")
    return counts


if __name__ == "__main__":
    check_templates()
