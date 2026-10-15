# Released songs: how a song gets on the Linkke page

One small JSON file per song. Agents never edit `linkkehub.html`. The `songs` GitHub Action checks each file and rebuilds the "Released" list on [linkkehub.html](../../linkkehub.html) on every push to `main`.

## The gate

A song is listed only when `x_post` points at **The Executive's own post on @humanvsmachineX**. The Executive posting a song is his approval (The Executive, 2026-10-13 10:02 MT), so nothing reaches this page that he hasn't released himself. Don't add a file before his post exists.

## Add a song

Create `data/songs/<id>.json`. The file name must match `id`.

```json
{
  "id": "context-window",
  "title": "「コンテキストの窓」 Context Window",
  "subtitle": "Her first Japanese song",
  "released": "2026-10-12",
  "x_post": "https://x.com/humanvsmachineX/status/2109837367200899308",
  "suno_url": "https://suno.com/song/c4299e78-aecb-4572-9268-25e972b0f91a",
  "cover": "assets/covers/src/context-window.png",
  "cover_alt": "Cover art for Context Window: Linkke ... (describe the image for screen readers)"
}
```

| Field | Required | Rule |
|---|---|---|
| `id` | yes | lowercase letters, digits and dashes; same as the file name |
| `title` | yes | up to 80 characters; no `<`, `>` or links |
| `subtitle` | no | up to 60 characters, shown small under the title |
| `released` | yes | `YYYY-MM-DD` (Mountain Time) |
| `x_post` | yes | `https://x.com/humanvsmachineX/status/<id>`. This is the gate. |
| `suno_url` | no | `https://suno.com/song/<uuid>` or `https://suno.com/s/<code>`, without the `?sh=` part. With it, the title links to Suno ("Play on Suno"); without it, to the X post ("Watch on X"). |
| `cover` | no | the cover The Executive posted, uploaded to `assets/covers/src/<id>.png` (or .jpg/.webp, up to 8 MB). The Action makes the 400 px thumbnail. |
| `cover_alt` | with `cover` | a plain description of the image, up to 600 characters |
| `hidden` | no | `true` takes the song off the page and keeps the file |

The list is ordered newest first by `released`, then by X post time.

## Take one down, or stop everything

- **Unpublish:** set `"hidden": true`, or delete the file. The Executive's call ("pull <title>").
- **Pause:** add an empty file `data/PAUSE`. The page stays as it is until the file is removed.

## When something is wrong

A bad file is skipped. The other songs still publish, the Action run turns red, and its log names the file and the problem. If two files use the same `x_post`, the one already on the page stays and the new one is skipped.

Check before pushing: `python3 scripts/build_songs.py --check` (needs Pillow only for covers).
