from statscard.card import render_svg

_FIELDS = {
    "os": "Linux / Windows 11 / Android",
    "host": "Presidência da República — DSIC",
    "kernel": "Engenharia de Software @ UnB",
    "ide": "VS Code + Claude Code",
    "uptime": "1 ano, 7 meses",
    "hobbies": "Leitura, Viagens, Natação",
    "contact": "linkedin.com/in/christopherparaizo · github.com/wChrstphr",
}
_STATS = {"repos": 12, "stars": 34, "commits": 567, "followers": 8, "additions": 9000, "deletions": 1200}
_ART_CELLS = [{"row": 0, "col": 0, "char": "█", "color": "#a1b2c3"}]


def test_render_svg_is_well_formed_and_correct_size():
    svg = render_svg("dark", _ART_CELLS, _FIELDS, _STATS)
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg" width="985" height="530"')
    assert svg.rstrip().endswith("</svg>")


def test_render_svg_dark_theme_uses_dark_background():
    svg = render_svg("dark", _ART_CELLS, _FIELDS, _STATS)
    assert 'fill="#161b22"' in svg


def test_render_svg_light_theme_uses_light_background():
    svg = render_svg("light", _ART_CELLS, _FIELDS, _STATS)
    assert 'fill="#fffefe"' in svg


def test_render_svg_emits_one_art_cell_element_per_cell():
    cells = [
        {"row": 0, "col": 0, "char": "█", "color": "#ff0000"},
        {"row": 1, "col": 2, "char": "▒", "color": "#00ff00"},
    ]
    svg = render_svg("dark", cells, _FIELDS, _STATS)
    assert svg.count('class="art-cell"') == 2
    assert "#ff0000" in svg
    assert "#00ff00" in svg


def test_render_svg_includes_all_fields_and_stats():
    svg = render_svg("dark", _ART_CELLS, _FIELDS, _STATS)
    assert "uptime.software" in svg
    assert "1 ano, 7 meses" in svg
    assert "Leitura, Viagens, Natação" in svg
    assert "Repos: 12" in svg
    assert "Stars: 34" in svg
    assert "Commits: 567" in svg
    assert "Followers: 8" in svg
    assert "+9000" in svg
    assert "-1200" in svg


def test_render_svg_escapes_special_characters_in_field_values():
    fields = dict(_FIELDS)
    fields["hobbies"] = "A & B <test>"
    svg = render_svg("dark", _ART_CELLS, fields, _STATS)
    assert "A &amp; B &lt;test&gt;" in svg
    assert "A & B <test>" not in svg
