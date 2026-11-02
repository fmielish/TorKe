"""Offline tests for the step-by-step procedure card."""

import re

import torke
from test_torke import USER, body, run, tool, use_homebox  # noqa: F401

STEPS = [
    {"title": "Lift and support the truck", "how": "Set jack stands.", "check": "It doesn't rock.",
     "warn": "Never work under a jack alone."},
    {"title": "Fasten the hub", "how": "Install the new bolts.",
     "torque": [{"what": "Hub bolts (new)", "value": "129 ft-lb", "note": "2 sources agree"},
                {"what": "Axle nut (new)", "value": "30 ft-lb", "note": "From the manual, p. 12", "confirmed": True}]},
    "Test drive at walking speed.",
]
SRC = "GoTech front hub guide; torque from ford-specs.com (not Ford)"


def card(tool, **kw):
    args = dict(item="2013 Ford F-150", job="Replace front hub assembly (4WD)", steps=STEPS, source=SRC)
    args.update(kw)
    return body(run(tool.show_procedure(__user__=USER, **args)))


def test_card_has_every_step_in_both_views(tool):
    html, ctx = card(tool)
    assert len(re.findall(r'<div class="st[ "]', html)) == 3 and html.count('<li data-i=') == 3
    assert "Lift and support the truck" in html and "Test drive at walking speed." in html
    assert "One step at a time" in html and "Full list" in html
    assert "3 steps" in ctx and "one step at a time" in ctx and "Don't repeat the steps" in ctx


def test_tap_right_goes_forward_and_left_goes_back(tool):
    html, _ = card(tool)
    assert 'id="stage"' in html and 'onclick="tap(event)"' in html
    assert "e.clientX<r.left+r.width/2)go(-1);else go(1)" in html  # left half back, right half forward
    assert "closest('a,button,input,textarea,label')" in html  # taps on controls aren't also taps on the step
    assert "ArrowLeft" in html and "ArrowRight" in html  # keyboard works too
    assert "Tap the right side of the step to go forward, the left side to go back." in html
    assert "Back" in html and "Next step" in html  # buttons for anyone who doesn't tap the side


def test_last_step_offers_done_and_closes_the_job_out(tool):
    html, _ = card(tool)
    assert "Done with this job" in html
    assert "The job is done: 2013 Ford F-150, Replace front hub assembly (4WD). Close it out." in html


def test_torque_values_not_confirmed_are_flagged_and_confirmed_are_not(tool):
    html, ctx = card(tool)
    assert '<div class="un"><span>Hub bolts (new)</span>' in html
    assert '<div class=""><span>Axle nut (new)</span>' in html
    assert "From the manual, p. 12" in html and "Amber means not confirmed from a manual." in html
    assert "1 torque value(s) are marked not confirmed" in ctx
    assert html.count("<tr><td>") == 2  # the table lists each value once


def test_source_is_shown_and_a_missing_source_says_so(tool):
    html, ctx = card(tool)
    assert f"Source: {SRC}" in html and f"Source given: {SRC}" in ctx
    html, ctx = card(tool, source="")
    assert "No source was given for these steps." in html and "No source was given" in ctx


def test_view_can_start_as_a_list(tool):
    html, ctx = card(tool, view="list")
    assert '<div id="sv" hidden>' in html and '<div id="lv">' in html and "starting as a list" in ctx
    html, _ = card(tool, view="nonsense")
    assert '<div id="sv">' in html and '<div id="lv" hidden>' in html


def test_nothing_is_made_up_when_there_are_no_steps(tool):
    for steps in ([], None, [{}], [""]):
        out = run(tool.show_procedure("2013 Ford F-150", "x", steps, __user__=USER))
        assert isinstance(out, str) and "Don't make steps up" in out
    assert "Needs the item" in run(tool.show_procedure("", "x", STEPS, __user__=USER))


def test_uses_the_open_project_when_item_and_job_are_left_out(tool):
    run(tool.open_project("2013 Ford F-150", "Front hub", "vehicle", __user__=USER, __chat_id__="c9"))
    html, ctx = body(run(tool.show_procedure(steps=STEPS, source=SRC, __user__=USER, __chat_id__="c9")))
    assert "2013 Ford F-150" in html and "Front hub" in html


def test_text_from_a_page_cannot_inject_markup_or_script(tool):
    evil = [{"title": "<script>alert(1)</script>", "how": '"><img src=x onerror=alert(2)>',
             "torque": [{"what": "<b>x</b>", "value": "</td><script>y</script>"}]}]
    html, _ = card(tool, steps=evil, item="<i>car</i>", job="</script><script>z()</script>", source="<script>s</script>")
    assert "<script>alert" not in html and "<img src=x" not in html and "<b>x</b>" not in html
    assert "<script>y" not in html and "<script>s</script>" not in html and "<script>z" not in html
    assert len(re.findall(r"<script", html)) == 2  # the shared sizer and the card's own, nothing else


def test_long_procedures_and_long_text_are_cut_down(tool):
    many = [{"title": f"Step {i}", "how": "x" * 5000} for i in range(100)]
    html, _ = card(tool, steps=many)
    assert len(re.findall(r'<div class="st[ "]', html)) == torke.MAX_PROC_STEPS
    assert "x" * 601 not in html


def test_the_card_has_no_stray_control_characters(tool):
    html, _ = card(tool)
    assert not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", html)


def test_card_follows_the_saved_theme(tool):
    html, _ = card(tool)
    assert 'data-mode="dark" data-accent="cyan"' in html and "toggleTheme()" in html


def test_readme_opens_with_the_warning_and_the_full_warning_exists():
    import pathlib
    root = pathlib.Path(torke.__file__).parent
    readme = (root / "README.md").read_text()
    assert readme.index("WARNING") < readme.index("TorKe (say")
    assert "DISCLAIMER.md" in readme
    text = (root / "DISCLAIMER.md").read_text()
    for must in ("kill you", "not a lawyer", "as is", "your own risk", "jack stands", "Don't use TorKe"):
        assert must in text
