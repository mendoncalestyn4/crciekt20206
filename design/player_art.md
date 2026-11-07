# Player art (stage 6): the look you picked

Picked from mock-ups on 6 and 7 November: **India** (Kohli, on My team) and **Australia** (Smith walking out in his
Test whites, on My team and on S Smith's player page). Build it exactly like this. The photos themselves are yours and
belong to whoever took them, so they never go into this repository: the site reads them from a folder on your PC,
named after the player or the team, the way it reads the game's logos.

## The recipe (the same on every team's page)

1. **The picture is recoloured to match the page**: its own colours kept at 45% strength, then mixed 38% with the
   page's colour (navy `#0f2557` on India's page, yellow `#e7e245` on Australia's). In Python (Pillow):
   `Image.blend(ImageEnhance.Color(photo).enhance(0.45), Image.new("RGB", photo.size, page), 0.38)`.
   Done by the server when it hands the picture over, as it already does for logos, so it suits any team's colours.
2. **Behind the whole screen**, fixed while the page scrolls, with a fade of the page's colour over it from the left:
   70% at the left edge, 25% by the middle, 5% at the right.
3. **Every tile is see-through glass**: the tile colour at 26%, a 2px blur behind it, a faint light edge
   (`rgba(255,255,255,.14)`).
4. **The menu is see-through too**: its colour at 42%, a 6px blur behind it.
5. **Unpicked buttons and the search box**: the page's colour at 35%.
6. **The words**: on dark pages (India) a soft dark shadow (`0 1px 3px rgba(0,0,0,.85), 0 0 14px rgba(0,0,0,.45)`);
   on light pages (Australia) **none** (your pick: a glow made the numbers look smudged).
7. **Placement**: set for each picture so the player sits clear (the picture covers the screen; only where its middle
   sits changes).

## Where it shows

My team (a team picture) and the Player page (the player's own picture). How strong it shows is to be set on screen
when it's built (the mock-ups went from very faint to the strength above, which is the one picked).

## To check when it's built

- Small coloured words on light pages over the picture (the green date at the top, the red "won by" label, the red
  arrows): make sure each still reads.
- Every page's fit check, dark and light, with and without a picture, and a page whose team has no picture.

## The mock-up tool

`design/mockups/player_art_mock.js` lays the picture on the real pages in the browser only (the site unchanged), as
the mock-ups were made: `node player_art_mock.js <port> <folder with the recoloured pictures> <folder for the shots>`.
