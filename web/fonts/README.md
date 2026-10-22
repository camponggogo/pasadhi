# Open-source fonts

The PASADHI website serves these fonts locally. The White Paper builder embeds Noto fonts in the PDFs.
Thai text uses the original TH Sarabun New (SIPA, v1.35); prose uses Noto Serif; headings and page numbers use Noto Sans;
code uses Noto Sans Mono; the website and SVG diagrams use Nunito.

All five families are distributed under the SIL Open Font License 1.1 (OFL).
They retain copyright and may be used, embedded and redistributed, including commercially, under that license.
Keep the adjacent copyright and OFL notices when distributing the fonts. Fonts are not sold on their own here.
See the unmodified `*-OFL.txt` files and `sources.json` for the exact upstream commit, URLs and SHA-256 digests.

Existing raster experiment charts use Matplotlib's default DejaVu fonts; these allow redistribution and embedding.
See https://github.com/dejavu-fonts/dejavu-fonts/blob/master/LICENSE.
Raster images do not contain embedded font programs. The two architecture/install figures are rebuilt with bundled Nunito.

This project does not bundle or select Georgia, Times New Roman, Arial, Segoe UI, Consolas or Helvetica.
Generic browser fallbacks may be chosen by the viewer only when a glyph is missing or a font fails to load.
The README itself is rendered using the hosting site's font settings.

## Thai and mathematical fallback

TH Sarabun New is distributed unmodified under GPL 2.0 or later with the font embedding exception.
See THSarabunNew-LICENSE.txt (copyright and permission copied from the font's name table) and GPL-2.0.txt.
Original source: https://www.f0nt.com/release/th-sarabun-new/.
The included original ZIP preserves the exact upstream distribution. DejaVu Sans is the mathematical
fallback for arrows and inequality symbols; its full license is in DejaVu-LICENSE.txt.
Noto Sans Thai is retained as an unused OFL asset; the active Thai face is TH Sarabun New.
