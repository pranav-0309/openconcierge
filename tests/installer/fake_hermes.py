from __future__ import annotations

import json
import os
import sys
from pathlib import Path

state_path = Path(os.environ["FAKE_HERMES_STATE"])
state = json.loads(state_path.read_text(encoding="utf-8"))
raw_args = sys.argv[1:]
state.setdefault("calls", []).append(raw_args)

args = list(raw_args)
if len(args) >= 2 and args[0] in {"-p", "--profile"}:
    state["last_profile"] = args[1]
    args = args[2:]

if args[:1] == ["doctor"]:
    print("Hermes doctor: healthy")
elif args[:2] == ["profile", "show"]:
    print("Profile: openconcierge\nGateway: stopped\nSkills: openconcierge")
elif args[:2] == ["profile", "list"]:
    print("default\ncoder\nopenconcierge")
elif args[:2] == ["profile", "create"]:
    state["profile_created"] = True
    print("Profile created")
elif args[:2] == ["profile", "install"]:
    state["distribution_installed"] = True
    print("Distribution installed")
elif args[:2] == ["profile", "update"]:
    state["profile_updated"] = True
    print("Profile updated")
elif args[:2] == ["skills", "list"]:
    print("openconcierge")
elif args[:2] == ["tools", "list"]:
    print("web enabled\nmcp_custom_search_search enabled")
elif args[:2] == ["skills", "install"]:
    state["skill_installed"] = True
    print("Skill installed")
elif args[:1] == ["profile"]:
    print("Profile: openconcierge\nGateway: stopped\nSkills: openconcierge")
elif args[:1] == ["desktop"]:
    state["desktop_launched"] = True
    print("Desktop launched")
else:
    print("unsupported fake Hermes command", file=sys.stderr)
    state["unsupported"] = args
    state_path.write_text(json.dumps(state), encoding="utf-8")
    raise SystemExit(3)

state_path.write_text(json.dumps(state), encoding="utf-8")
