# cut.json — the edit

```json
{
  "output": "degen_walkie",
  "colors": {"bg": "0x131518", "accent": "0x3ef0a0", "text": "white"},
  "exports": ["9:16", "16:9", "1:1"],
  "segments": [
    {"clip": "01_a", "in": 0.0, "out": 5.0, "super": "Trade by voice.", "sub": "Anywhere.",
     "captions": [{"start": 0.5, "end": 4.4, "text": "“Long SOL, five x, five hundred USDC.”"}]},
    {"still": "product/ticket.png", "seconds": 2.4, "crop": "502:505:0:0",
     "super": "SEE IT.", "sub": "Every detail on one ticket."},
    {"still": "product/front.png", "seconds": 1.3, "super": "One pocket terminal.", "sub": "Perps · Spot · News"},
    {"still": "product/side.png", "seconds": 1.3, "fade": false, "super": "One pocket terminal.", "sub": "Ask about your book."},
    {"endcard": {"image": "product/front.png", "title": "DEGEN WALKIE",
                 "lines": ["Your trading terminal, in your pocket.", "Pre-order $99 · Fully refundable"],
                 "small": "Perps in eligible regions only", "seconds": 3.5}}
  ]
}
```

| Segment | Fields |
|---|---|
| clip | `clip` = take name (`<shot>_<a|b>`), `in` / `out` seconds inside the take, optional `super`, `sub`, `captions` (times inside the untrimmed take) |
| still | `still` = an image path in the project (the user's screenshots, packaging, product photos), `seconds`, optional `crop` (`w:h:x:y` in source pixels), `super`, `sub` |
| endcard | `image` (the product, edges are feathered into `colors.bg`), `title`, `lines` (first one in the accent colour), `small` (legal / small print), `seconds` |

- `fade: false` keeps a super steady when consecutive segments repeat it.
- Supers sit in the top band (on clips, over a dark band), captions near the bottom; long text is
  fitted or wrapped automatically.
- `colors`: pick from the product / brand (background of the renders, the brand accent).
- Caption timing: `ffmpeg -i takes/leveled/01_a.mp4 -af silencedetect=n=-32dB:d=0.25 -f null -`
  prints the pauses; speech sits between them.
