# shots.json — keyframes and clips

```json
{
  "style": "Vertical cinematic live-action ad, shallow depth of field, night city, realistic.",
  "ratio": "9:16",
  "resolution": "768p",
  "seeds": [1, 2],
  "shots": [
    {
      "id": "01",
      "duration": 5,
      "refs": ["actor_leo", "product"],
      "voices": ["leo"],
      "frame": {
        "prompt": "Medium close-up, night street after rain. The man from <Picture 1> walks toward camera holding the trading device from <Picture 2> at mouth height, slightly forward, thumb on the glass, speaking into it. The screen faces him; the camera sees the device's back, as in the back view of <Picture 2>.",
        "take": 1,
        "model": "gpt-image-2"
      },
      "first_frame": "frames/01_t1.png",
      "prompt": "The man from <Picture 1> walks slowly along the wet street, holding the device from <Picture 2> near his mouth, and says clearly, like a radio call, in the voice of <Audio 1>: \"Long SOL, five x, five hundred USDC.\" The screen faces him the whole time. Rain, distant traffic."
    }
  ]
}
```

| Field | Notes |
|---|---|
| `style` | Prepended to every keyframe and clip prompt. Look and place, not story. |
| `ratio` | Main ratio of the ad (`9:16`, `16:9`, `1:1`). Keyframes and clips use it; other export ratios are derived in the cut. |
| `resolution` | `768p` (US$0.01/s) or `480p` (US$0.007/s). |
| `effort` | Optional, `1x` (default) / `1.5x` / `2x` — more sampling steps, per shot or as a default. At 4 steps H3 sometimes ignores a cut the prompt specifies and close-up skin can look waxy; higher tiers fix that, cost 1.2x / 1.4x and **render ~1.4x / ~1.9x slower** (more when demand is high). 480p / 768p only. An ad's hero close-up may be worth it; a 3-second product shot is not. |
| `seeds` | Takes per shot. 2 is the sweet spot. |
| `shots[].id` | Short, unique, e.g. `01`. Takes are saved as `takes/<id>_a.mp4`, `_b`. |
| `refs` | Images in `refs/` by name (`product`, `product_detail`, `actor_<id>`) → `<Picture 1>`, `<Picture 2>`… in this order, for both the keyframe and the clip. ≤ 9. |
| `voices` | `refs/voice_<name>.mp3` → `<Audio 1>`… (voice timbre). ≤ 3. |
| `frame` | Keyframe for this shot (`gen_frames.py`). `take` = try number; `note` = a correction appended to the prompt; `model` = image model. |
| `first_frame` | Set by `gen_frames.py --approve`. The clip starts exactly on this image (ref_mode "okay"); duration must then be 5–15 s. |
| `prompt` | The clip prompt. A shot without `prompt` is not rendered (use it for planning only). |
| `duration` | Seconds, 5–15 with a keyframe; 5–8 is typical for ads. |
