"""Logos from the Cricket Captain editor files: the right picture for the right name, in every way the files can
say it, and nothing breaks without them."""
import base64
import io

import numpy as np

from PIL import Image

from ccstats import logos as LG


def png(path, colour):
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGBA", (60, 40), (0, 0, 0, 0))
    im.paste(Image.new("RGBA", (40, 30), colour), (10, 5))
    im.save(path)
    return path


def game_folder(tmp_path):
    g = tmp_path / "Cricket Captain 2026"
    em, cl = g / "editor" / "emblems", g / "editor" / "complogos"
    png(em / "sydneygreenem.png", (40, 220, 60, 255))       # bright green: shown as it is
    png(em / "warwickshireem.png", (10, 20, 80, 255))      # dark blue: on a light coin
    png(em / "myownmumbai.png", (0, 90, 200, 255))         # a name of your own choosing, via the list
    png(cl / "india20overleaguecl.png", (200, 120, 0, 255))
    png(cl / "internationalworldcup20overcl.png", (90, 0, 160, 255))
    (g / "editor" / "editemblems.txt").write_text(
        "# comment\n# === Australia ===\nSydney Green ; sydneygreenem\nSydney Pink\n"
        "# === India ===\nMumbai ; myownmumbai\nChennai ; Mumbai\n# === England ===\nWarwickshire ; warwickshireem\n"
        "Essex ; nosuchfile\n", encoding="utf-8")
    (g / "editor" / "editcomplogos.txt").write_text(
        "India : 20 Over League ; india20overleaguecl\nInternational : World Cup 20 Over ; "
        "internationalworldcup20overcl\nInternational : One Day International\n", encoding="utf-8")
    (g / "Scorecards").mkdir()
    return g


def test_parse_and_key():
    assert LG.parse("# x\nSydney Green ; sydneygreenem\nSydney Pink\nIndia : 20 Over League ; a b\n") == [
        ("Sydney Green", "sydneygreenem"), ("India : 20 Over League", "a b")]
    assert LG.key("Trinidad & Tobago CC") == "trinidadandtobagocc" and LG.key("Mazar-i-Sharif") == "mazarisharif"


def test_finds_the_files_from_the_scorecards_folder(tmp_path):
    g = game_folder(tmp_path)
    found = LG.find([g / "Scorecards", g])  # the Scorecards folder itself has nothing; its parent does
    assert found["emblems"] == g / "editor" / "emblems" and found["complogos"] == g / "editor" / "complogos"
    assert found["emblem_list"].name == "editemblems.txt" and found["comp_list"].name == "editcomplogos.txt"
    assert LG.find([tmp_path / "nowhere", None]) == {}


def test_the_right_picture_for_each_name(tmp_path):
    b = LG.LogoBook(LG.find([game_folder(tmp_path)]))
    # by the game's name and by the name the site shows
    assert b.team("Sydney Green").name == "sydneygreenem.png" and b.team("Sydney Thunder").name == "sydneygreenem.png"
    assert b.team("Mumbai Indians").name == "myownmumbai.png"  # a file named your own way, from the list
    assert b.team("Chennai Super Kings").name == "myownmumbai.png"  # borrowing another team's emblem
    assert b.team("Warwickshire").name == "warwickshireem.png"
    assert b.team("Sydney Sixers") is None and b.team("Essex") is None  # no picture: no logo (never a wrong one)
    assert b.comp("Indian Premier League").name == "india20overleaguecl.png"
    assert b.comp("T20 World Cup").name == "internationalworldcup20overcl.png"
    assert b.comp("ODIs") is None and b.comp("T20 Blast") is None


def test_a_broken_picture_is_no_picture(tmp_path):
    """Found by the logo stress test: an empty file, text named .png or a picture cut off while being saved was listed
    as a logo the site then couldn't draw. Now it counts as no picture: the team takes its other one, or none."""
    g = game_folder(tmp_path)
    em = g / "editor" / "emblems"
    good = png(em / "Warwickshire.png", (200, 0, 0, 255))
    (em / "warwickshireem.png").write_bytes(good.read_bytes()[:40])          # cut off mid-save
    (em / "essexem.png").write_bytes(b"")                                     # empty
    (em / "Essex.png").write_text("not a picture")                            # text named .png
    jpeg = em / "surreyem.png"                                                # a real picture, saved as JPEG
    Image.new("RGB", (30, 30), (0, 120, 60)).save(jpeg, "JPEG")
    b = LG.LogoBook(LG.find([g]))
    assert b.team("Warwickshire").name == "Warwickshire.png"   # the good one, not the cut-off one
    assert b.team("Essex") is None
    assert b.team("Surrey").name == "surreyem.png" and LG.png(b.team("Surrey"), 48)


def test_without_the_list_the_games_own_file_names_work(tmp_path):
    g = game_folder(tmp_path)
    (g / "editor" / "editemblems.txt").unlink()
    (g / "editor" / "editcomplogos.txt").unlink()
    b = LG.LogoBook(LG.find([g]))
    assert b.team("Sydney Thunder").name == "sydneygreenem.png"
    assert b.team("Mumbai Indians") is None  # 'myownmumbai' only means Mumbai through the list
    assert b.comp("Indian Premier League").name == "india20overleaguecl.png"


def decode(uri):
    return Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGBA")


def seen(uri):
    """The picture as it looks on the dark page."""
    im = decode(uri)
    page = Image.new("RGBA", im.size, (10, 19, 34, 255))
    page.alpha_composite(im)
    return page.convert("RGB")


def test_a_logo_with_no_look_picked_is_shown_as_it_is(tmp_path):
    """Logos outside the IPL, the Hundred, the Big Bash and internationals get nothing added: no line, no white."""
    g = game_folder(tmp_path)
    p = g / "editor" / "emblems" / "warwickshireem.png"
    uri, px = LG.picture(p, 24)
    im = decode(uri)
    assert im.size == (px * 2, px * 2)
    px_ = np.array(im).reshape(-1, 4)
    colours = {tuple(int(v) for v in c) for c in px_[px_[:, 3] > 0]}
    assert colours == {(10, 20, 80, 255)}  # only the logo's own colour: nothing light round it
    cols = [x for x in range(im.width) if any(im.getpixel((x, y))[3] for y in range(im.height))]
    assert max(cols) - min(cols) + 1 == 48  # 24 across, drawn at twice the size
    assert LG.badge(None) == "" and LG.badge(tmp_path / "missing.png") == "" and LG.picture(None) == ("", 0)


def test_every_look_has_the_same_frame_so_logos_line_up(tmp_path):
    g = game_folder(tmp_path)
    p = g / "editor" / "emblems" / "warwickshireem.png"
    assert len({LG.picture(p, 36, look)[1] for look in ("plain", "inside", "whole", "line", "C", "D", "nonsense")}) == 1


def test_the_picked_looks_go_to_the_right_logos(tmp_path):
    """A look is picked for a team or competition by name and follows its picture; everyone else is plain."""
    g = game_folder(tmp_path)
    em, cl = g / "editor" / "emblems", g / "editor" / "complogos"
    png(em / "mumbaiem2.png", (0, 90, 200, 255))
    png(cl / "internationaltestmatchcl.png", (60, 60, 60, 255))
    with open(g / "editor" / "editemblems.txt", "a", encoding="utf-8") as f:
        f.write("# === India ===\nMumbai ; myownmumbai\n")
    with open(g / "editor" / "editcomplogos.txt", "a", encoding="utf-8") as f:
        f.write("International : Test Match ; internationaltestmatchcl\n")
    b = LG.LogoBook(LG.find([g]))
    assert b.style(b.team("Sydney Thunder")) == b.style(b.team("Sydney Green")) == LG.STYLES["Sydney Thunder"] == "inside"
    assert b.style(b.comp("Tests (bilateral series)")) == b.style(b.comp("World Test Championship Final")) == "C"
    assert b.style(b.team("Warwickshire")) == "plain"  # no look picked
    assert b.style(None) == "plain"


def test_englands_navy_badge_shows_on_the_dark_pages(tmp_path):
    """England's badge is navy, like the dark-blue pages: it gets the look you picked (a light tint of its own colours),
    which draws it lighter than the page so it can be seen; drawn as it is, it would be as dark as the page."""
    g = game_folder(tmp_path)
    png(g / "editor" / "emblems" / "englandem.png", (18, 36, 96, 255))   # navy
    b = LG.LogoBook(LG.find([g]))
    assert b.style(b.team("England")) == LG.STYLES["England"] == "C"

    def brightest(look):
        a = np.asarray(decode(LG.badge(b.team("England"), 48, look)).convert("RGBA"), float)
        return a[..., :3].mean(axis=2)[a[..., 3] > 128].max()
    assert brightest("plain") < 70 < 150 < brightest(b.style(b.team("England")))


def test_dark_parts_made_visible_and_inside_as_in_the_game(tmp_path):
    """C: navy writing on the page turns a light tint of its colour. inside: a gap cut into the logo shows white,
    as on the game's page, while the page round the logo stays dark."""
    from PIL import ImageDraw
    p = tmp_path / "word.png"
    im = Image.new("RGBA", (200, 60), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([10, 10, 190, 50], outline=(20, 30, 110, 255), width=6)  # a thin navy frame
    im.save(p)
    plain, c = seen(LG.picture(p, 60, "plain")[0]), seen(LG.picture(p, 60, "C")[0])
    stroke = [(x, y) for x in range(plain.width) for y in range(plain.height) if plain.getpixel((x, y))[2] > 80]
    assert stroke and all(sum(c.getpixel(xy)) > sum(plain.getpixel(xy)) + 150 for xy in stroke[::7])  # lighter
    ring = tmp_path / "ring.png"
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([5, 5, 95, 95], outline=(200, 30, 30, 255), width=14)
    im.save(ring)
    inside = seen(LG.picture(ring, 40, "inside")[0])
    mid = inside.width // 2
    assert inside.getpixel((mid, mid)) == (255, 255, 255)  # the middle, as on the game's white page
    assert inside.getpixel((2, 2)) == (10, 19, 34)  # the page round the logo: untouched


def test_pictures_saved_under_each_others_names_are_swapped_back(tmp_path, monkeypatch):
    g = game_folder(tmp_path)
    em = g / "editor" / "emblems"
    png(em / "pamirem.png", (1, 2, 3, 255))
    png(em / "maiwandem.png", (4, 5, 6, 255))
    with open(g / "editor" / "editemblems.txt", "a", encoding="utf-8") as f:
        f.write("# === Afghanistan ===\nMaiwand ; maiwandem\nPamir ; pamirem\n")
    h_pamir_file, h_maiwand_file = LG._md5(em / "pamirem.png"), LG._md5(em / "maiwandem.png")
    # each file holds the other team's logo: swapped back, for the game's names and the real ones
    monkeypatch.setattr(LG, "SWAPPED", [("Pamir Legends", "Maiwand Champions", h_maiwand_file, h_pamir_file)])
    b = LG.LogoBook(LG.find([g]))
    assert b.team("Pamir Legends").name == b.team("Pamir").name == "maiwandem.png"
    assert b.team("Maiwand Champions").name == b.team("Maiwand").name == "pamirem.png"
    # once the files are put right (the pictures no longer match), nothing is swapped
    monkeypatch.setattr(LG, "SWAPPED", [("Pamir Legends", "Maiwand Champions", h_pamir_file, h_maiwand_file)])
    b = LG.LogoBook(LG.find([g]))
    assert b.team("Pamir Legends").name == "pamirem.png" and b.team("Maiwand Champions").name == "maiwandem.png"


def test_a_name_two_teams_answer_to_means_the_team_the_scorecards_print_it_for(tmp_path):
    """'Delhi' is the game's name for the IPL side (printed 'Delhi Capitals') and the printed name of the Ranji side
    ('Delhi CC' in the game). The site shows printed names, so 'Delhi' is always the Ranji side's emblem, and never
    the IPL side's when the Ranji side has no picture. Same for competitions: 'National T20 Cup' is printed by
    Pakistan and Afghanistan, so each is shown with its country and gets its own logo; the bare name gets none."""
    g = game_folder(tmp_path)
    em, cl = g / "editor" / "emblems", g / "editor" / "complogos"
    png(em / "delhiem.png", (200, 30, 30, 255))
    png(em / "delhiccem.png", (30, 30, 200, 255))
    png(cl / "pakistan20overtrophycl.png", (0, 150, 60, 255))
    png(cl / "afghanistandomestic20overcl.png", (0, 60, 150, 255))
    with open(g / "editor" / "editemblems.txt", "a", encoding="utf-8") as f:
        f.write("# === India ===\nDelhi ; delhiem\nDelhi CC ; delhiccem\n")
    with open(g / "editor" / "editcomplogos.txt", "a", encoding="utf-8") as f:
        f.write("Pakistan : 20 Over Trophy ; pakistan20overtrophycl\n"
                "Afghanistan : Domestic 20 Over ; afghanistandomestic20overcl\n")
    for _ in range(2):  # the same answer whatever order the names come in
        b = LG.LogoBook(LG.find([g]))
        assert b.team("Delhi Capitals").name == "delhiem.png" and b.team("Delhi").name == "delhiccem.png"
        assert b.comp("National T20 Cup (Pakistan)").name == "pakistan20overtrophycl.png"
        assert b.comp("National T20 Cup (Afghanistan)").name == "afghanistandomestic20overcl.png"
        assert b.comp("National T20 Cup") is None
    (em / "delhiccem.png").unlink()
    b = LG.LogoBook(LG.find([g]))
    assert b.team("Delhi Capitals").name == "delhiem.png" and b.team("Delhi") is None


def test_where_logos_are_looked_for_and_how_they_are_drawn_on_each_page(tmp_path):
    """Shared by both sites: your folder first, then the game's folder above each Scorecards folder, the Scorecards
    folder, Steam, and the Stats Pack's own 'logos' folder; no place twice. On a light page a logo is drawn as it is,
    apart from the white inside some."""
    from ccstats import local as L
    sc = tmp_path / "Cricket Captain 2026" / "Scorecards"
    got = LG.places(str(tmp_path / "mine"), [str(sc), "", str(sc)], tmp_path / "home")
    assert got[:3] == [tmp_path / "mine", sc.parent, sc]
    assert got[3:-1] == L.game_install_folders() and got[-1] == tmp_path / "home" / "logos"
    assert LG.places("", [], tmp_path)[0] == L.game_install_folders()[0]
    for style in ("plain", "inside", "whole", "line", "C", "D"):
        assert LG.look_on(style, dark=True) == style
        assert LG.look_on(style, dark=False) == (style if style in ("inside", "whole") else "plain")


def test_a_logo_as_a_png_file_and_a_stamp_that_sees_changes(tmp_path):
    g = game_folder(tmp_path)
    found = LG.find([g])
    b = LG.LogoBook(found)
    data = LG.png(b.team("Sydney Thunder"), 40, "plain")
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert np.asarray(Image.open(io.BytesIO(data))).shape[0] == 2 * LG.picture(b.team("Sydney Thunder"), 40)[1]
    assert LG.png(None, 40) == b"" and LG.png(tmp_path / "missing.png", 40) == b""
    before = LG.stamp(found)
    assert before == LG.stamp(LG.find([g]))
    import os
    t = found["emblem_list"].stat().st_mtime_ns + 5_000_000_000
    os.utime(found["emblem_list"], ns=(t, t))
    assert LG.stamp(found) != before   # a file edited in the game: the logos are matched again
