# Prompting keyframes and clips for ads

These rules hold for any product. Product specifics come from the brief (`ad.json`) and the
user's images, never from habit: a rule that fixed one product must not be copied to the next.

## Keyframes (images)

- Refer to references by position: "the woman from <Picture 1>", "the bottle from <Picture 2>",
  in the shot's `refs` order.
- Say **what the actor does with the product** in this moment, and therefore **which side of the
  product the camera sees**. Image models turn the "nice" side (screen, label, logo) toward the
  camera unless told otherwise, even when the actor is looking at it. Describe the visible side
  from the matching view of the product sheet ("the back, as in the back view of <Picture 2>").
- Give the product its real size against the body ("fits in her palm", "as tall as her forearm").
  `gen_frames.py` adds the brief's `size` and a fidelity sentence to every prompt.
- Controls swap sides when seen from the back: check left/right on every frame.
- Framing: the product big enough to read (close-up or medium close-up) in most shots; one wider
  shot for place is enough.
- Write what you want to see, positively ("a clean frame with only the scene"); naming unwanted
  things ("no text") tends to summon them.
- Generated screens and labels are approximate. Real ones go in as stills in the cut.
- Image models: `gpt-image-2` is the default and follows orientation notes well; try
  `nano-banana-2.1` or `gpt-image-2.5` when a frame keeps missing.

## Clips (MiniMax H3)

- The clip starts on the approved keyframe; the prompt describes only what happens next:
  movement, the line, the sound. Repeat the orientation ("the screen faces her the whole time").
- Keep product handling simple: hold, lift, press, pour, put down. Rotating the product in the
  hand, opening it or fast motion is where products mutate; show those with stills instead.
- Dialogue in double quotes, ≤ 14 words per 6 s, with the voice described ("calm, low American
  voice"); with a voice reference, say "in the voice of <Audio 1>".
- Other voices can come from the product itself ("from the device's speaker, a Japanese woman
  answers: …"); write their lines in their language and put the translation in the captions.
- Sound last: place ambience, a click, a pour.
- Keep `optimize_prompt` on (the scripts do): okaypic rewrites plain English into H3's structured
  format using your references, free.
- Two takes per shot. Reject a take when the product changes shape, flips side, or the face drifts,
  even if the acting is better.
