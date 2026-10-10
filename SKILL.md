---
name: okaypic-ads
description: Make short video ads for a product with AI video through the okaypic.com API — an on-camera actor holding and using the product, real product shots as inserts, supers, captions and an end card, exported 9:16, 16:9 and 1:1. Use when the user wants an ad, promo, product video, UGC-style spot or commercial for something they sell, starting from a product description and product photos. Covers interviewing the user about the product, picking key features, taglines and a story, preset AI actors with voices, keyframes the user approves, MiniMax H3 clips, and the final cut.
---

# okaypic ads skill

You are making a 15–40 s product ad with the okaypic.com API: images (gpt-image-2) for keyframes,
MiniMax H3 for clips with generated dialogue and sound, ffmpeg for the cut. The scripts in
`scripts/` do the mechanical work. Your job is to understand the product, help the user choose
what the ad says, write the shots, and check every image and take before the user sees it.

What makes this better than a template or a render-only tool: a person on camera who holds and
uses the product, talking, in a real-looking place. Use that.

## Setup (once)

- `OKAYPIC_API_KEY` in the environment or a `.env` file in the project (never print it, never
  commit it). Keys: https://okaypic.com/api-docs . Prices: https://okaypic.com/pricing .
- `ffmpeg` and `ffprobe` on PATH, Python 3.9+ (stdlib only).
- Fonts: `python scripts/fetch_fonts.py <project>/assets` (Noto Sans, Noto Sans SC; OFL).
- One folder per ad (layout in `scripts/ad_project.py`): `ad.json`, `product/`, `refs/`,
  `shots.json`, `frames/`, `takes/`, `cut.json`, `out/`.

## How to ask

Ask one thing at a time. Whenever there is a choice, offer 2–4 concrete options **and** let the
user write their own. In Claude Code use the AskUserQuestion tool (it always adds "Other" for a
custom answer; use multiSelect for features). In other agents, number the options and add
"or tell me your own". Recommend one option when you have a reason, and say the reason in a few
words. Don't ask what you can see in the images or read in the description.

## Workflow

Costs are small but real: an image is about US$0.03, a 5 s H3 clip at 768p US$0.05. Tell the
user the cost before every paid step and wait for their OK. A typical 30 s ad is 4–5 keyframes and
4–5 shots × 2 takes: about US$0.60–0.80.

### 1. Product: description and images

Ask for **a description of the product** (what it is, who it's for, price if they want it in the
ad) and **one or more product images**. Copy the images into `product/`, never edit the originals.
Nothing else is needed: no website, deck or PDF.

Look at every image yourself. With several images, work out what each one is and label it in
`ad.json` (`product.images[]`, see `docs/ad-format.md`):

- **views of the whole product**: front, back, left/right side, top, three-quarter
- **details**: a close-up of one part (a control, a label, a texture, a connector)
- **in use / lifestyle**: the product held, worn, installed, on a table
- **screens / UI, packaging, logo**: good as inserts in the cut, exactly as they are
- **variants**: other colours or sizes — ask which one the ad shows

The user does not prepare a brief; you work it out and ask. First take everything you can from
the images and the description, then ask about whatever is still unclear and matters for the ad,
until you can answer all of these (ask only the missing ones, with options to pick):

1. What exactly is it, in one sentence a stranger understands?
2. Real size (cm / in, or "fits in one hand", "the size of a coffee mug"). Video models get scale
   wrong without it.
3. How is it used: held, worn, placed, poured, plugged in? Which hand, which part do you touch?
4. What is on each side (screen, buttons, lights, label, logo), and which side faces the user
   while it's in use?
5. Are the images the real product, or renders/mockups? Anything in them that is not part of it?
6. Anything that must not be shown or claimed (regulated claims, competitor names, prices that
   may change, regions)?

Price, offer and what's in the box only matter for a sales video: ask them after the purpose
(step 2), and only if the goal is to sell.

Write the answers into `ad.json` (`product.summary`, `size`, `usage`, `sides`, `avoid`). Read
them back to the user in five lines and fix what's wrong. Mark the images for the product sheet
(`"sheet": true` for up to 4 whole-product views, `"sheet": "detail"` for close-ups) and run
`python scripts/product_sheet.py <ad>`; look at `refs/product.png`.

### 2. The purpose of the video

Before features, ask what the video is for — never assume it is a sales ad. Typical answers:

- **sell now**: offer, price, a clear call to action (shop link, "order today")
- **lifestyle / recommendation** (种草): show the product in everyday life so people want it; no
  price, no hard sell, it should feel like a real person's post
- **launch / brand**: introduce something new, build recognition; tagline and name, maybe a date
- **explain / demo**: show how it works, step by step

Ask where it will be posted too if it changes the tone (TikTok/Reels feed, a product page, an
ad account). Store it in `ad.json` `goal`. It decides everything after it: which features lead,
the tone of the taglines, whether there is a price or CTA, what the end card says. Leave out
whatever the goal doesn't need (a lifestyle video carries no price even if the user mentioned one).

### 3. The most important feature

Ask what matters most about the product to the people who buy it, for this goal. Offer 3–5 candidates you drew
from the description (short, benefit first: "orders by voice, anywhere" rather than "has a
microphone"), multi-select, plus their own. One main feature carries the ad; at most two more
get a beat each. Store them in `ad.json` `features`.

### 4. Tagline

Offer 3–4 taglines built on the main feature, different in tone (plain / bold / playful /
premium; matching the goal: a lifestyle video wants a line a person would say, not a slogan),
≤ 7 words each, plus their own. Store it in `tagline`. It closes the ad on the end card.

### 5. Story

Also ask the format first if not known: length (15 / 30 / 40 s), main ratio (9:16 for
TikTok/Reels/Shorts, 16:9 for YouTube/web), language of the dialogue.

Offer 3 stories, each 2–3 lines: the hook (first 2 s), what the actor does with the product, how
each chosen feature is shown, the close. Make them genuinely different: e.g. a problem/solution
moment, a day-in-the-life montage across places, a direct-to-camera demo, a skit. Plus their own.
Note which shots need an actor. Store the choice in `story`.

Actor (when the story has one): `python scripts/actors.py list` shows okaypic's preset AI actors
(AI-generated people, each with a reference sheet and a fixed voice in en / zh / ja). Show the
user the sheet links of 2–3 that fit, or offer their own photo / voice (`actors.py custom`; only
of people who agreed), or no actor. Then `python scripts/actors.py use <ad> <id> --lang en`.

### 6. Script and shot list

Write `shots.json` (`docs/shots-format.md`) and `cut.json` (`docs/cut-format.md`) together, then
show the user one table: time, picture, spoken line, super (on-screen text). Rules:

- **Hook in the first 2 seconds, with the product in frame.** No logo intro.
- One idea per shot, 5–8 s per H3 shot. Spoken lines ≤ 14 words per 6 s; dialogue in quotes.
- Features are shown, not listed: the actor *does* the thing; a super names it in ≤ 5 words, a
  sub-line explains in ≤ 8.
- Real screens, packaging, labels and close-ups come from the user's images as still inserts
  (1.5–2.5 s), never generated: generated text is unreliable.
- End card: product image, name, tagline; price/CTA only when the goal is to sell; the user's small print.
- Only claims the user gave you. No invented prices, numbers, awards or certifications.

Get the user's OK on the table and the cost estimate before generating anything.

### 7. Keyframes — the user checks and iterates

Every shot where the actor and the product appear together gets a keyframe first: a still the
clip will start from. Products differ too much to get right automatically, so this is a review
step. Write each shot's `frame.prompt` (`docs/prompting.md`), then
`python scripts/gen_frames.py <ad>` and look at `frames/review.jpg` yourself first: is the product
right (shape, colour, controls on the correct side, the side that should face the camera, real
size in the hand), is the actor the same person, is the moment readable? Fix obvious misses
yourself before showing it. Then show the user each frame and offer:

- approve
- try again (same idea, new try: bump `frame.take`)
- a correction in their words (`frame.note`, e.g. "the label should face the camera"), new try
- another image model (`gpt-image-2` default, `nano-banana-2.1`, `gpt-image-2.5`)
- their own image (save it as `frames/<id>_t<n>.png`)

Each try costs one image. On approval run `python scripts/gen_frames.py <ad> --approve <id>`.
Only approved frames go to video.

### 8. Clips

`python scripts/gen_clips.py <ad> --quote`, tell the user the line it prints, wait for OK, then
`python scripts/gen_clips.py <ad>` (detached; tail `takes/run.log`; 5–15 min per batch). Look at
every take's contact sheet (`takes/<shot>_<take>.jpg`): reject takes where the product changes
shape, flips to the wrong side, or the actor's face drifts; prefer the take where the line is
delivered cleanly (`ffmpeg -i take.mp4 -af silencedetect=n=-32dB:d=0.25 -f null -` shows where
speech sits). Re-render only misfires (`gen_clips.py <ad> 03`), after fixing the prompt.

### 9. Cut

Fill `cut.json` picks, trims and caption times (from silencedetect), set `colors` from the
product's palette, then `python scripts/cut_ad.py <ad>` → `out/<name>_9x16.mp4`, `_16x9`, `_1x1`.
Verify with a frame sheet (`ffmpeg -i out/x.mp4 -vf "fps=1/2,scale=200:-1,tile=8x2" -frames:v 1 sheet.jpg`)
and look at it: supers inside the frame, captions on the right lines, end card readable. You
cannot hear the audio: say so, and ask the user to listen once before posting (caption timing,
voices, a line H3 may have dropped).

## Balance and top-ups

- `gen_clips.py --quote` prints what is done, in flight (already paid) and left, with the cost and
  the current balance. After a stopped run, quote again: a resume only charges for what is left.
- On a low balance or HTTP 402 the scripts stop with a top-up link. Tell the user what it costs,
  what is left, that they can top up from US$2 at https://okaypic.com/billing (card or WeChat
  Pay), and that re-running continues where it stopped.

## Guardrails

- Never put the API key in a prompt, a log, a commit, or a file you did not create for it.
- Before any paid batch, state the number of calls and the cost, and wait for approval.
- Real people: only the user's own photo/voice or people who agreed. The presets are AI-generated.
- Failed tasks are refunded; `content_violation` is never retryable — rewrite the prompt.
- Every request id contains the project id from `ad.json` (`id`), so separate ads never collide;
  never edit or reuse it across projects.
- Don't watch full videos to judge takes; use the contact sheets, then open only the finalists.

## Files

| File | Role |
|---|---|
| `scripts/product_sheet.py` | The product reference sheet from the user's own images |
| `scripts/actors.py` | Preset AI actors (sheet + voice), or a custom actor from a photo / voice |
| `scripts/gen_frames.py` | Keyframes, tries, review grid, approval |
| `scripts/gen_clips.py` | H3 clips: 2 takes per shot, resumable, `--quote`, contact sheets, levelled copies |
| `scripts/cut_ad.py` | Cut with inserts, supers, captions, end card; 9:16 / 16:9 / 1:1 |
| `scripts/okaypic_api.py`, `ad_project.py`, `fetch_fonts.py` | API client, project helpers, fonts |
| `docs/` | `ad-format.md`, `shots-format.md`, `cut-format.md`, `prompting.md` |
| `examples/degen-walkie/` | A finished 34 s ad: brief, shots, cut and a frame sheet |
