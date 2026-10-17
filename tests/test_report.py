import pytest
from tabacos.report import DraftError, publish, render

REPO = "https://github.com/OrsM/tabacos"

DOC = """# A title

<!-- description: One line for the home page. -->

## In one paragraph

See [the stockpiling report](../analyses/stockpiling/report.md), [the site](https://example.org)
and [below](#limits).

![Curve](../analyses/taxshock/curve.png)

## Limits

Few.
"""


def test_title_and_description_come_from_the_document():
    page = render(DOC, "docs/learnings.md", REPO)
    assert page.title == "A title"
    assert page.description == "One line for the home page."
    assert "<title>A title</title>" in page.html
    assert '<meta name="description" content="One line for the home page.">' in page.html


def test_a_document_without_a_description_is_refused():
    with pytest.raises(ValueError, match="description"):
        render("# T\n\nBody.\n", "docs/x.md", REPO)


def test_relative_links_point_into_the_repo_and_others_are_left_alone():
    html = render(DOC, "docs/learnings.md", REPO).html
    assert f'href="{REPO}/blob/main/analyses/stockpiling/report.md"' in html
    assert 'href="https://example.org"' in html
    assert 'href="#limits"' in html


def test_relative_images_are_copied_beside_the_page():
    page = render(DOC, "docs/learnings.md", REPO)
    assert page.images == ["analyses/taxshock/curve.png"]
    assert 'src="curve.png"' in page.html


def test_the_page_cites_the_source_as_the_licence_requires():
    html = render(DOC, "docs/learnings.md", REPO).html
    assert "Comisionado para el Mercado de Tabacos" in html
    assert "Ley 37/2007" in html


def test_a_draft_is_refused_unless_asked_for(tmp_path):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "d.md").write_text("# T\n\n<!-- description: D -->\n\n*Draft for the website.*\n\nBody.\n")
    with pytest.raises(DraftError):
        publish(root, "docs/d.md", tmp_path / "out")
    publish(root, "docs/d.md", tmp_path / "out", draft=True)
    assert (tmp_path / "out" / "index.html").exists()


def test_publish_copies_the_images(tmp_path):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "analyses" / "taxshock").mkdir(parents=True)
    (root / "analyses" / "taxshock" / "curve.png").write_bytes(b"png")
    (root / "docs" / "learnings.md").write_text(DOC)
    publish(root, "docs/learnings.md", tmp_path / "out")
    assert (tmp_path / "out" / "curve.png").read_bytes() == b"png"
