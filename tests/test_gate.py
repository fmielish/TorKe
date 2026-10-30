"""The warning gate: nothing works until the person accepts, and turning it off takes a second warning."""

import inspect
import re
from html import unescape

import pytest

import torke
from test_torke import USER, body, run, tool, use_homebox  # noqa: F401

OTHER = {"id": "u2", "name": "Other", "valves": torke.Tools.UserValves()}


@pytest.fixture(autouse=True)
def gate_on(monkeypatch):
    monkeypatch.setattr(torke, "REQUIRE_WARNING", True)


def said(text):
    return [{"role": "user", "content": text}]


def accept(tool, user=USER):
    return run(tool.accept_warning(__user__=user, __messages__=said(torke.ACCEPT_PHRASE)))


def test_nothing_works_before_the_warning_is_accepted(tool, monkeypatch):
    use_homebox(tool, monkeypatch)
    calls = [
        tool.open_project("2013 Ford F-150", "hub", "vehicle", __user__=USER, __chat_id__="g1"),
        tool.job_picker("2013 Ford F-150", "vehicle", __user__=USER),
        tool.show_procedure("2013 Ford F-150", "hub", ["Do a thing."], "a manual", __user__=USER),
        tool.safety_check("hub", "2013 Ford F-150", "vehicle", __user__=USER),
        tool.find_manuals("2013 Ford F-150", __user__=USER),
        tool.shopping_list(__user__=USER),
        tool.read_scanner(codes=["P0301"], __user__=USER),
        tool.set_theme("light", "red", __user__=USER),
    ]
    for c in calls:
        html, ctx = body(run(c))
        assert "Read this before you start" in html and "STOP." in ctx and "never call accept_warning yourself" in ctx.lower()


def test_every_working_tool_is_behind_the_gate():
    open_ones = {"show_warning", "accept_warning", "turn_off_warning", "confirm_turn_off_warning", "turn_on_warning"}
    for name, fn in vars(torke.Tools).items():
        if name.startswith("_") or not callable(fn) or name in ("Valves", "UserValves"):
            continue
        assert inspect.iscoroutinefunction(fn), name
        assert (name in open_ones) == (not hasattr(fn, "__wrapped__")), name  # gated ones are wrapped
        if name not in open_ones:
            assert "__user__" in inspect.signature(fn).parameters, name  # the gate reads who is asking


def test_wrapping_keeps_what_open_webui_reads_from_a_tool():
    fn = torke.Tools.open_project
    assert fn.__name__ == "open_project" and "Open the project card" in fn.__doc__
    params = inspect.signature(fn).parameters
    assert "item" in params and "__user__" in params and "__chat_id__" in params


def test_the_warning_card_covers_the_risks_and_needs_a_tick(tool):
    html, ctx = body(run(tool.show_warning(__user__=USER)))
    html = unescape(html)
    for must in ("injure or kill you", "can be wrong", "licensed professional", "Check every number", "jack stands",
                 "No warranty", "If you don't agree, don't use TorKe", "DISCLAIMER.md"):
        assert must in html
    assert 'id="go" disabled' in html and 'type="checkbox"' in html  # the button waits for the tick
    assert torke.ACCEPT_PHRASE in html


def test_accepting_needs_the_persons_own_message_and_unlocks_the_tools(tool):
    # the model can't accept for them
    for msgs in (None, [], said("start the job"), [{"role": "assistant", "content": torke.ACCEPT_PHRASE}],
                 [{"role": "tool", "content": torke.ACCEPT_PHRASE}]):
        assert "Not saved" in run(tool.accept_warning(__user__=USER, __messages__=msgs))
    assert "Read this before you start" in body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=USER)))[0]
    # their button message accepts, the latest user message counts
    assert "accepted and saved" in accept(tool)
    html, _ = body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=USER)))
    assert "Pick a job" in html and "Read this before you start" not in html


def test_acceptance_is_per_person_and_asked_again_when_the_warning_changes(tool, monkeypatch):
    accept(tool)
    assert "Read this before you start" in body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=OTHER)))[0]
    assert "Pick a job" in body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=USER)))[0]
    monkeypatch.setattr(torke, "WARNING_VERSION", "2099-01-01")
    assert "Read this before you start" in body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=USER)))[0]


def test_turning_it_off_takes_a_second_warning_and_the_persons_own_message(tool):
    html, ctx = body(run(tool.turn_off_warning(__user__=USER)))
    assert "Turn the warning off?" in html and "second warning" in html and "Everyone who uses this account" in html
    assert 'id="go" disabled' in html and torke.OFF_PHRASE in html and torke.KEEP_PHRASE in html
    assert "Don't turn anything off yet" in ctx
    # nothing turns off without their message, and accepting the first warning isn't enough
    accept(tool)
    for msgs in (None, said("turn it off"), said(torke.ACCEPT_PHRASE), [{"role": "assistant", "content": torke.OFF_PHRASE}]):
        assert "Not turned off" in run(tool.confirm_turn_off_warning(__user__=USER, __messages__=msgs))
    assert "turned off for this person" in run(tool.confirm_turn_off_warning(__user__=USER, __messages__=said(torke.OFF_PHRASE)))
    # and when it is off, other people on the server still get it
    assert "Pick a job" in body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=USER)))[0]
    assert "Read this before you start" in body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=OTHER)))[0]


def test_turning_it_off_works_even_before_accepting_and_turning_it_back_on_asks_again(tool):
    run(tool.confirm_turn_off_warning(__user__=USER, __messages__=said(torke.OFF_PHRASE)))
    assert "Pick a job" in body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=USER)))[0]
    assert "back on" in run(tool.turn_on_warning(__user__=USER))
    assert "Read this before you start" in body(run(tool.job_picker("2013 Ford F-150", "vehicle", __user__=USER)))[0]


def test_phrase_check_ignores_case_punctuation_and_a_wrapper_but_not_other_words(tool):
    for text in (torke.ACCEPT_PHRASE.upper(), "  " + torke.ACCEPT_PHRASE.rstrip(".") + "  ",
                 [{"type": "text", "text": torke.ACCEPT_PHRASE}]):
        msgs = [{"role": "user", "content": text}]
        assert "accepted and saved" in run(tool.accept_warning(__user__=USER, __messages__=msgs))
        run(tool.turn_on_warning(__user__=USER))
    assert "Not saved" in run(tool.accept_warning(__user__=USER, __messages__=said("I do not accept the risk.")))


def test_the_warning_cards_follow_the_theme_and_have_no_stray_characters(tool):
    for fn in (tool.show_warning, tool.turn_off_warning):
        html, _ = body(run(fn(__user__=USER)))
        assert 'data-mode="dark"' in html and "toggleTheme()" in html
        assert not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", html)


def test_text_in_a_message_cannot_inject_into_the_warning_card(tool):
    html, _ = body(run(tool.show_warning(__user__={"id": "<script>x</script>", "valves": torke.Tools.UserValves()})))
    assert "<script>x" not in html
