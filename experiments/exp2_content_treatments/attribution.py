"""Five-arm attribution follow-up specified 10 November 2026, before queries."""
import re
from collections import defaultdict

ATTRIBUTION = ["attr_B", "attr_S0", "attr_S1", "attr_Q0", "attr_Q1"]
# Separate-site follow-up: the outside reviewer's sentence on the brand's own page (Q) or, word for word, at the end of
# the buyer's guide (T); B is a fresh baseline. Specified on 10 November 2026; see the experiment README.
SITE = ["site_B", "site_Q0", "site_Q1", "site_T0", "site_T1"]
SITE_STANCE = {"site_Q0": "attr_Q0", "site_Q1": "attr_Q1", "site_T0": "attr_Q0", "site_T1": "attr_Q1"}
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


def site_bodies(sc, target_core, arm, target_baseline, guide_baseline):
    """(target page, guide page) for a separate-site arm."""
    if arm == "site_B":
        return target_baseline, guide_baseline
    sentence = statement(sc, target_core, SITE_STANCE[arm])
    if arm.startswith("site_Q"):
        return target_baseline + "\n" + sentence, guide_baseline
    return target_baseline, guide_baseline + "\n" + sentence


def check_site_templates():
    """Q and T add the identical sentence (one target mention) at the end of the brand page or of the guide."""
    from build_corpus import build
    original = {i["trial_id"]: i for i in build(3, ["baseline"])}
    grouped = defaultdict(dict)
    for item in build(3, SITE):
        grouped[item["trial_id"]][item["condition"]] = item
    for trial, arms in grouped.items():
        base = original[trial]
        assert arms["site_B"]["user"] == base["user"], trial
        before = base["user"].split("\n\n")
        added = {}
        for arm in SITE[1:]:
            after = arms[arm]["user"].split("\n\n")
            changed = [i for i, (x, y) in enumerate(zip(before, after)) if x != y]
            page = base["target_index"] if arm.startswith("site_Q") else base["guide_index"]
            assert len(before) == len(after) and changed == [page], (trial, arm)
            block = after[page]
            assert block.startswith(before[page] + "\n"), (trial, arm)
            added[arm] = block[len(before[page]) + 1:]
            assert len(re.findall(r"(?<!\w)" + re.escape(base["target"]) + r"(?!\w)", added[arm])) == 1
            evaluator = arms[arm]["attribution_evaluator"]
            assert evaluator not in base["user"] and arms[arm]["user"].count(evaluator) == 1
        assert added["site_Q0"] == added["site_T0"] and added["site_Q1"] == added["site_T1"], trial
    print(f"{len(grouped)} trials: site_B equals the baseline; Q and T add the identical sentence on the brand page "
          f"or the guide page, with one target mention.")
    return grouped


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
    check_site_templates()
