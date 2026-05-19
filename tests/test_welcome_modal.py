from __future__ import annotations

from app.components.welcome_modal import (
    _MODAL_CSS,
    WelcomeStep,
    clamp_step,
    get_epiphany_html,
    get_steps,
)


def test_get_steps_returns_four_entries() -> None:
    steps = get_steps()
    assert len(steps) == 4


def test_get_steps_are_welcome_step_instances() -> None:
    for step in get_steps():
        assert isinstance(step, WelcomeStep)


def test_get_steps_have_nonempty_fields() -> None:
    for step in get_steps():
        assert step.tag.strip()
        assert step.icon.strip()
        assert step.title.strip()
        assert step.body.strip()


def test_welcome_step_is_immutable() -> None:
    step = WelcomeStep(tag="x", icon="🔍", title="t", body="b")
    try:
        step.tag = "y"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("WelcomeStep should be immutable (NamedTuple)")


def test_clamp_step_negative_returns_zero() -> None:
    assert clamp_step(-5) == 0


def test_clamp_step_above_max_returns_last_index() -> None:
    last = len(get_steps()) - 1
    assert clamp_step(99) == last


def test_clamp_step_in_range_returns_self() -> None:
    for i in range(len(get_steps())):
        assert clamp_step(i) == i


def test_step_titles_are_unique() -> None:
    titles = [s.title for s in get_steps()]
    assert len(set(titles)) == len(titles)


def test_step_tags_mention_fr_codes() -> None:
    tags = [s.tag for s in get_steps()]
    assert any("FR-01" in t for t in tags)
    assert any("FR-02" in t for t in tags)
    assert any("FR-03" in t for t in tags)
    assert any("FR-05" in t for t in tags)


def test_epiphany_html_includes_prd_core_numbers() -> None:
    html = get_epiphany_html()
    assert "387,000" in html
    assert "92.1" in html


def test_epiphany_html_uses_welcome_epiphany_class() -> None:
    assert 'class="welcome-epiphany"' in get_epiphany_html()


def test_every_step_has_nonempty_example() -> None:
    for step in get_steps():
        assert step.example.strip(), f"step {step.tag} missing example"


def test_roi_step_example_mentions_helicity_numbers() -> None:
    roi = next(s for s in get_steps() if "FR-03" in s.tag)
    assert "387,000" in roi.example
    assert "7,740" in roi.example


def test_welcome_step_example_defaults_to_empty() -> None:
    step = WelcomeStep(tag="x", icon="✨", title="t", body="b")
    assert not step.example


def test_modal_card_has_hover_state_with_primary_accent() -> None:
    assert ".welcome-feature-card:hover" in _MODAL_CSS
    assert "border-color:#0071E3" in _MODAL_CSS
    # Design.md: 카드 lift 금지 — text-transform(대문자 변환) 외에 CSS transform 속성 금지.
    css_without_text_transform = _MODAL_CSS.replace("text-transform:", "")
    assert "transform:" not in css_without_text_transform
