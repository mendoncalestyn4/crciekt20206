"""Logos from the Cricket Captain editor files: the right picture for the right name, in every way the files can
say it, and nothing breaks without them."""
import base64
import io

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


def test_without_the_list_the_games_own_file_names_work(tmp_path):
    g = game_folder(tmp_path)
    (g / "editor" / "editemblems.txt").unlink()
    (g / "editor" / "editcomplogos.txt").unlink()
    b = LG.LogoBook(LG.find([g]))
    assert b.team("Sydney Thunder").name == "sydneygreenem.png"
    assert b.team("Mumbai Indians") is None  # 'myownmumbai' only means Mumbai through the list
    assert b.comp("Indian Premier League").name == "india20overleaguecl.png"


def test_dark_logos_get_a_light_coin_and_keep_their_size(tmp_path):
    g = game_folder(tmp_path)
    sizes = {}
    for name, coin in (("warwickshireem.png", True), ("sydneygreenem.png", False)):
        p = g / "editor" / "emblems" / name
        uri, dark, px = LG._badge(str(p), p.stat().st_mtime_ns, 24, False)
        assert dark is coin
        im = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGBA")
        assert im.size == (px * 2, px * 2)
        # the logo itself: its colour's pixels, as wide as asked for (48 = 24 at twice the size) with or without a coin
        logo_colour = (10, 20, 80) if coin else (40, 220, 60)
        cols = [x for x in range(im.width) if any(im.getpixel((x, y))[:3] == logo_colour for y in range(im.height))]
        sizes[name] = max(cols) - min(cols) + 1
        if coin:  # a coin round it: light, just outside the logo, and the picture is bigger to hold it
            assert px > 24
            assert im.getpixel((min(cols) - 2, im.height // 2))[3] == 255
        else:
            assert px == 24
    assert sizes["warwickshireem.png"] == sizes["sydneygreenem.png"] == 48
    # in a table every picture has the same frame, so the logos come out the same size
    p = g / "editor" / "emblems" / "sydneygreenem.png"
    assert LG._badge(str(p), p.stat().st_mtime_ns, 24, True)[2] == LG._badge(
        str(g / "editor" / "emblems" / "warwickshireem.png"), (g / "editor" / "emblems" / "warwickshireem.png").stat().st_mtime_ns,
        24, True)[2]
    assert LG.badge(None) == "" and LG.badge(tmp_path / "missing.png") == ""


def test_a_see_through_middle_goes_on_the_light_coin(tmp_path):
    """A logo with an enclosed see-through area (a ring, the middle of a shield) shows the page through it; on the
    coin that middle shows light, as in the game. The logo itself is unchanged and keeps its size."""
    from PIL import ImageDraw
    ring = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([5, 5, 95, 95], outline=(230, 180, 20, 255), width=14)  # bright gold ring, hollow
    assert LG.has_holes(ring)
    dot = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(dot).ellipse([5, 5, 95, 95], fill=(230, 180, 20, 255))  # the same, filled in: no middle
    assert not LG.has_holes(dot)
    o = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(o).rectangle([0, 0, 99, 99], fill=(230, 180, 20, 255))
    ImageDraw.Draw(o).rectangle([48, 48, 50, 50], fill=(0, 0, 0, 0))  # a tiny gap, like inside an 'O': not a middle
    assert not LG.has_holes(o)
    p = tmp_path / "ring.png"
    ring.save(p)
    uri, coin, px = LG._badge(str(p), p.stat().st_mtime_ns, 24, False)
    assert coin and px > 24
    im = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGBA")
    c = im.width // 2
    assert im.getpixel((c, c))[3] == 255 and min(im.getpixel((c, c))[:3]) > 200  # the middle shows light
