"""Render the ad's shots with MiniMax H3 through the okaypic API.

    python gen_clips.py <ad_dir>              # every shot x every seed
    python gen_clips.py <ad_dir> 01 03        # only these shot ids
    python gen_clips.py <ad_dir> --quote      # price what is left to render, submit nothing

Reads <ad_dir>/shots.json (see docs/shots-format.md). Per shot: `refs` are images in refs/
(product, actor_<id>, ...) sent as <Picture 1>, <Picture 2>... in that order; `voices` are
refs/voice_<name>.mp3 sent as <Audio 1>... (voice-timbre references); `first_frame` (an approved
keyframe) locks the opening frame (ref_mode "okay", 5-15 s). Shots without a clip prompt (still
inserts) are skipped.

Resumable: state lives in <ad_dir>/takes/state.json. Re-running skips finished takes and keeps
polling submitted ones (both already paid), and quotes and submits only what is left. Failed
renders are refunded by the API; a retryable failure is resubmitted once under a new
client_request_id. Before submitting, the balance is checked against the remaining cost; on HTTP
402 the script stops submitting, prints the top-up link and keeps polling what is in flight. Each
finished take gets a 5-frame contact sheet (<take>.jpg) and a -16 LUFS copy in takes/leveled/.
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from okaypic_api import TOP_UP_URL, balance_cents, data_uri, download, h3_cost_cents, request, usd  # noqa: E402
from ad_project import load, project_id, ref_path, voice_path  # noqa: E402

MAX_INFLIGHT = 18
POLL_SECONDS = 20
INFLIGHT = ("pending", "processing", "queued", "submitted")


def level_take(mp4):
    """-16 LUFS copy of a take in takes/leveled/ (H3 takes vary by 15 dB); the cut renders from it."""
    out = os.path.join(os.path.dirname(mp4), "leveled", os.path.basename(mp4))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out], check=True)
    return out


def seed_base(sid):
    digits = "".join(c for c in sid if c.isdigit())
    return int(digits) if digits else sum(map(ord, sid))


def contact_sheet(mp4):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf", "fps=1/2,scale=320:-1,tile=5x1",
                    "-frames:v", "1", mp4[:-4] + ".jpg"])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quote_only = "--quote" in sys.argv
    ep = args[0]
    only = set(args[1:])
    spec = load(ep, "shots.json")
    spec = {**spec, "shots": [x for x in spec["shots"] if x.get("prompt")]}  # stills have no clip
    # locked frames (ref_mode "okay") need 5-15 s; catch it here instead of a 400 per take
    short = [s["id"] for s in spec["shots"] if s.get("first_frame")
             and not 5 <= s.get("duration", spec.get("duration", 10)) <= 15]
    if short:
        raise SystemExit(f"shots {', '.join(short)}: with first_frame the duration must be 5-15 s")
    big = [x["id"] for x in spec["shots"] if len(x.get("refs", [])) > 9 or len(x.get("voices", [])) > 3]
    if big:
        raise SystemExit(f"shots {', '.join(big)}: at most 9 reference images and 3 voices per shot")
    takes_dir = os.path.join(ep, "takes")
    os.makedirs(takes_dir, exist_ok=True)
    state_path = os.path.join(takes_dir, "state.json")
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}
    tag = project_id(ep)

    def save():
        json.dump(state, open(state_path, "w", encoding="utf-8"), indent=1)

    work = []
    for shot in spec["shots"]:
        if only and shot["id"] not in only:
            continue
        for i, n in enumerate(spec.get("seeds", [1, 2])):
            work.append((f"{shot['id']}_{'abcdef'[i]}", shot, 1000 + seed_base(shot["id"]) * 10 + n))

    def shot_cost(shot):
        return h3_cost_cents(spec.get("resolution", "768p"), shot.get("duration", spec.get("duration", 10)))

    def to_submit():
        out = []
        for k, shot, _ in work:
            st = state.get(k, {})
            if st.get("status") == "completed" or st.get("status") in INFLIGHT:
                continue
            if st.get("status") == "failed" and (st.get("attempt", 1) >= 2 or st.get("retryable") is False):
                continue
            out.append((k, shot))
        return out

    # quote only what is left: finished and in-flight takes are already paid
    left = to_submit()
    cost = sum(shot_cost(s) for _, s in left)
    done = sum(1 for k, _, _ in work if state.get(k, {}).get("status") == "completed")
    flying = sum(1 for k, _, _ in work if state.get(k, {}).get("status") in INFLIGHT)
    bal = balance_cents()
    print(f"{len(work)} takes: {done} done, {flying} in flight (already paid), {len(left)} to render = {usd(cost)}"
          + (f"; balance {usd(bal)}" if bal is not None else ""), flush=True)
    if quote_only:
        return
    out_of_funds = False
    if left and bal is not None and bal < cost:
        print(f"Not enough balance for the remaining takes ({usd(cost)} needed, {usd(bal)} left). "
              f"Top up from US$2 at {TOP_UP_URL} and re-run; finished takes are kept.", flush=True)
        if not flying:
            return
        out_of_funds = True  # just finish what is in flight

    ref_cache = {}

    def ref(name):
        if name not in ref_cache:
            ref_cache[name] = data_uri(ref_path(ep, name))
        return ref_cache[name]

    def voice(name):
        key = "voice:" + name
        if key not in ref_cache:
            ref_cache[key] = data_uri(voice_path(ep, name), max_px=0)
        return ref_cache[key]

    while True:
        for k in [k for k, s in state.items() if s.get("status") in INFLIGHT]:
            code, r = request("GET", f"/api/video/tasks/{state[k]['taskId']}")
            if code != 200:
                print(f"poll {k}: http {code} {r}", flush=True)
                continue
            if r.get("status") == "completed":
                mp4 = os.path.join(takes_dir, f"{k}.mp4")
                download(r["resultUrls"][0], mp4)
                contact_sheet(mp4)
                try:
                    level_take(mp4)
                except Exception as e:
                    print(f"level {k}: {e}", flush=True)
                state[k].update(status="completed", url=r["resultUrls"][0])
                print(f"done {k}", flush=True)
            elif r.get("status") == "failed":
                state[k].update(status="failed", error=r.get("errorCode"), retryable=r.get("retryable"))
                print(f"FAILED {k}: {r.get('errorCode')} {r.get('errorMessage', '')} retryable={r.get('retryable')}", flush=True)
            else:
                state[k]["status"] = r.get("status") or "pending"
            save()

        inflight = [k for k, s in state.items() if s.get("status") in INFLIGHT]
        for k, shot, seed in ([] if out_of_funds else work):
            st = state.get(k, {})
            if st.get("status") == "completed" or k in inflight:
                continue
            if st.get("status") == "failed" and (st.get("attempt", 1) >= 2 or st.get("retryable") is False):
                continue
            if len(inflight) >= MAX_INFLIGHT:
                break
            attempt = st.get("attempt", 0) + 1
            body = {
                "model": "minimax-h3", "prompt": spec.get("style", "") + " " + shot["prompt"],
                "duration": shot.get("duration", spec.get("duration", 10)),
                "ratio": spec.get("ratio", "9:16"), "resolution": spec.get("resolution", "768p"),
                "ref_mode": "omni", "optimize_prompt": True, "seed": seed,
                "client_request_id": f"{tag}-{k}-{attempt}",
            }
            media = [{"type": "image", "url": ref(n)} for n in shot.get("refs", [])]
            media += [{"type": "audio", "url": voice(n)} for n in shot.get("voices", [])]
            if media:
                body["media"] = media
            ff = shot.get("first_frame")
            if ff:
                body["ref_mode"] = "okay"
                body["first_frame"] = ff if ff.startswith("https://") else data_uri(os.path.join(ep, ff), max_px=0)
            code, r = request("POST", "/api/video/generate", body, body["client_request_id"])
            if code in (200, 201, 202) and r.get("taskId"):
                state[k] = {"status": "submitted", "taskId": r["taskId"], "seed": seed, "attempt": attempt}
                inflight.append(k)
                print(f"submitted {k} seed={seed}", flush=True)
            elif code == 402:
                out_of_funds = True
                print(f"Balance ran out ({usd(r.get('balanceCents', 0))} left, this take costs "
                      f"{usd(r.get('costCents', 0))}). Top up from US$2 at {TOP_UP_URL} and re-run; "
                      "nothing already rendered or in flight is charged again.", flush=True)
                break
            else:
                state[k] = {"status": "failed", "attempt": attempt, "retryable": True, "error": r}
                print(f"SUBMIT ERROR {k}: http {code} {r}", flush=True)
                if code == 429:
                    break
            save()

        inflight = [k for k, s in state.items() if s.get("status") in INFLIGHT]
        remaining = [k for k, _, _ in work if state.get(k, {}).get("status") != "completed"]
        if not inflight:
            print(f"ALL DONE. completed={len(work) - len(remaining)}/{len(work)} failed={remaining}", flush=True)
            break
        print(f"... {len(inflight)} in flight, {len(remaining)} remaining", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
