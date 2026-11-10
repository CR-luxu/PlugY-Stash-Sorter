# Third-party notices

This project contains no Diablo II game binaries, images, sounds, or MPQ data.

## d2itemreader

The item bit-layout was implemented with reference to
[squeek502/d2itemreader](https://github.com/squeek502/d2itemreader), which is
released into the public domain (Unlicense). The small `plugy14.sss` fixture in
`tests/fixtures/` comes from that project's public test data.

## PlugY

Stash page and BigStash layout information was taken from
[ChaosMarc/PlugY](https://github.com/ChaosMarc/PlugY). PlugY is distributed
under its own license; this project only reads/writes save files and does not
include PlugY code or binaries.

## Diablo II data

`data/items.json`, `data/stat_desc.json`, `data/zh_items.json`,
`data/affixes.json`, `data/skills.json` and `data/names.json` contain item codes,
inventory sizes, English names and Chinese translations derived from Diablo II /
Diablo II: Resurrected text data and from the MIT-licensed
[awdrrawd/D2R-storehouse](https://github.com/awdrrawd/D2R-storehouse)
translation dataset. They are included solely so the tool can interpret a
locally installed game's save files. Diablo II and all related names are
trademarks of Blizzard Entertainment, Inc. This project is not affiliated with
or endorsed by Blizzard Entertainment.

The English string table used during data generation comes from
[fabd/diablo2](https://github.com/fabd/diablo2).
