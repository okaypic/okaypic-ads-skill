# ad.json — the brief

Written by the agent during the interview (SKILL.md steps 1–5), read by the scripts.

```json
{
  "id": "walkie-3f9a1c",
  "product": {
    "name": "Degen Walkie",
    "description": "The user's own words, unedited.",
    "summary": "A pocket trading terminal you talk to: hold the mic, say the trade, press the key.",
    "size": "about 9 x 6 cm and 1 cm thin, fits in one hand like a deck of cards",
    "usage": "held in one hand; talk into it like a walkie-talkie; the thumb presses the trade key",
    "sides": "front: glass screen; back: camera lens, gold contacts, speaker; right edge: mint trade key, thumb wheel",
    "avoid": ["perps only in eligible regions: say so on the end card"],
    "images": [
      {"file": "product/front.png", "shows": "front view, screen on", "sheet": true},
      {"file": "product/back.png", "shows": "back view", "sheet": true},
      {"file": "product/key.jpg", "shows": "detail: the trade key", "sheet": "detail"},
      {"file": "product/ticket.png", "shows": "UI screenshot: order ticket", "sheet": false}
    ]
  },
  "goal": "sell now | lifestyle | launch | demo (the user's words)",
  "features": ["Trade by voice, anywhere", "Your private key never leaves your wallet"],
  "tagline": "Your trading terminal, in your pocket.",
  "story": {"title": "Anywhere", "logline": "Street, metro, café: he trades by voice in each.", "choice": "B"},
  "format": {"length": 30, "ratio": "9:16", "language": "en", "exports": ["9:16", "16:9", "1:1"]},
  "actor": {"preset": "leo"}
}
```

| Field | Notes |
|---|---|
| `id` | Created by the scripts on first use (`<folder>-<random>`). Part of every request id; never change it. |
| `product.size` | Real-world size in words. The keyframe rules use it to keep scale. |
| `product.usage`, `sides` | How it is held / used and what is on each side. The agent writes keyframe prompts from these. |
| `product.images[].sheet` | `true`: whole-product view for `refs/product.png` (≤ 4). `"detail"`: close-up for `refs/product_detail.png` (≤ 4). `false`: not a reference (UI, packaging, lifestyle — still usable as an insert). |
| `product.images[].shows` | What the image shows, in words. Ask the user when unsure. |
| `actor` | `{"preset": "<id>"}`, `{"custom": "<name>"}` or `null`. |
