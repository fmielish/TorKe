"""Offline tests for the theme button and each person's saved look."""

import re

import pytest

import torke
from test_torke import USER, body, run, tool, use_homebox  # noqa: F401


def look(html):
    m = re.search(r'<html lang="en" data-mode="(\w+)" data-accent="(\w+)">', html)
    return (m.group(1), m.group(2)) if m else None


def card_html(result):
    return body(result)[0]


def test_default_look_is_dark_cyan(tool):
    html = card_html(run(tool.open_project("Shop vac", __user__=USER)))
    assert look(html) == ("dark", "cyan")


def test_every_card_has_the_theme_button_and_the_saved_look(tool, monkeypatch):
    hb = use_homebox(tool, monkeypatch)
    me = {"id": "alice", "valves": torke.Tools.UserValves()}
    assert "Saved: light, green" in run(tool.set_theme("Light", "GREEN", __user__=me))
    cards = [run(tool.open_project("2012 Honda Civic", "brakes", "vehicle", __user__=me)),
             run(tool.find_videos("civic brakes", __user__=me)),
             run(tool.check_tools(["10 mm socket"], "brakes", "2012 Honda Civic", __user__=me)),
             run(tool.shopping_list(__user__=me)),
             run(tool.complete_job("2012 Honda Civic", "brakes", __user__=me, __chat_id__="c1"))]
    assert len(cards) == 5
    for c in cards:
        html = card_html(c)
        assert look(html) == ("light", "green")
        assert 'class="themebtn"' in html and "toggleTheme()" in html and "saveTheme()" in html
        assert html.count('<button type="button" data-m="') == 2 and html.count('<button type="button" data-a="') == 4
    # someone else still gets the default
    other = {"id": "bob", "valves": torke.Tools.UserValves()}
    assert look(card_html(run(tool.open_project("Shop vac", __user__=other)))) == ("dark", "cyan")


def test_set_theme_validates_and_keeps_the_other_half(tool):
    assert "can be dark or light" in run(tool.set_theme("neon", __user__=USER))
    assert "can be dark or light" in run(tool.set_theme("dark", "pink", __user__=USER))
    assert "Ask which look" in run(tool.set_theme(__user__=USER))
    assert torke._theme(USER) == {"mode": "dark", "accent": "cyan"}  # nothing was saved
    run(tool.set_theme("light", __user__=USER))
    run(tool.set_theme(accent="violet", __user__=USER))
    assert torke._theme(USER) == {"mode": "light", "accent": "violet"}
    run(tool.set_theme("dark", __user__=USER))
    assert torke._theme(USER) == {"mode": "dark", "accent": "violet"}


def test_a_damaged_saved_look_falls_back_and_cannot_inject_markup(tool):
    torke._write_store("theme", USER, {"mode": '"><script>x</script>', "accent": 5})
    assert torke._theme(USER) == {"mode": "dark", "accent": "cyan"}
    torke._write_store("theme", USER, ["not", "a", "dict"])
    assert torke._theme(USER) == {"mode": "dark", "accent": "cyan"}
    assert look(card_html(run(tool.open_project("Drill", __user__=USER)))) == ("dark", "cyan")


def test_save_failure_is_reported(tool, monkeypatch):
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(torke, "_write_store", boom)
    assert "couldn't be saved" in run(tool.set_theme("light", __user__=USER))


def test_save_button_sends_the_phrase_the_model_expects():
    # the card's script sends this text; set_theme's docstring tells the model to act on it
    assert "ask('Save my TorKe theme: '+S.m+', '+S.a)" in torke._SIZER
    assert "Save my TorKe theme" in torke.Tools.set_theme.__doc__


def test_every_theme_has_the_variables_the_cards_use():
    css = torke._HUD_CSS
    for name in torke.THEME_ACCENTS:
        if name != "cyan":  # cyan is the default, so it needs no override
            assert f'html[data-accent="{name}"]' in css
            assert f'html[data-mode="light"][data-accent="{name}"]' in css
    assert 'html[data-mode="light"]' in css
    # no leftover hard-coded dark-only colors in any card stylesheet
    everything = "".join(getattr(torke, n) for n in dir(torke) if n.endswith("_CSS"))
    for old in ("rgba(92,225,255,", "rgba(255,179,71,", "rgba(4,16,26,"):
        assert old not in everything
    assert everything.count("#071827") == 1  # only the dark theme's own definition
