"""Parsing the plan files (format: plan/FORMAT.md)."""
import fnmatch
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDER = ["FILE", "SESSION", "EDIT", "TYPING", "MACRO", "SEARCH", "VIEW", "UI", "L10N", "ENCODING", "LANG",
         "SETTINGS", "TOOLS", "PLUGINS", "MACEXTRA", "COMPARE", "FTP", "RUN", "GIT", "AGENT", "CLI", "WINDOW", "HELP", "VISUAL"]
CASE = re.compile(r"^### ([A-Z0-9]+)-(\d{3}): (.+?)\s*$")
FIELD = re.compile(r"^- (Covers|Channel|Steps|Expect): (.*)$")


def plan_files():
    files = {p.stem: p for p in (ROOT / "plan").glob("*.md") if p.stem not in ("FORMAT",)}
    return [files[a] for a in ORDER if a in files] + sorted(p for a, p in files.items() if a not in ORDER)


def parse(path: Path):
    area_title, cases, group, cur, errors = None, [], None, None, []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if line.startswith("# ") and area_title is None:
            area_title = line[2:].strip()
        elif line.startswith("## "):
            group = line[3:].strip()
        elif m := CASE.match(line):
            cur = {"area": m.group(1), "num": m.group(2), "id": f"{m.group(1)}-{m.group(2)}", "title": m.group(3),
                   "group": group, "file": path.name, "line": n}
            cases.append(cur)
        elif (m := FIELD.match(line)) and cur is not None:
            cur[m.group(1).lower()] = m.group(2).strip()
        elif line.startswith("  ") and cur is not None and cur.get("_last"):
            pass
    for c in cases:
        for f in ("covers", "channel", "steps", "expect"):
            if f not in c:
                errors.append(f"{c['file']}:{c['line']} {c['id']} lacks {f}")
        c["covers_list"] = [x.strip() for x in c.get("covers", "-").split(",") if x.strip() and x.strip() != "-"]
    return area_title, cases, errors


def all_cases():
    out, errors = [], []
    for p in plan_files():
        title, cases, errs = parse(p)
        out += cases
        errors += errs
    seen = {}
    for c in out:
        if c["id"] in seen:
            errors.append(f"duplicate id {c['id']} ({c['file']} and {seen[c['id']]})")
        seen[c["id"]] = c["file"]
    return out, errors


def commands():
    rows = []
    for line in (ROOT / "plan/commands.tsv").read_text().splitlines()[1:]:
        menu, ident, label = line.split("\t")
        rows.append({"menu": menu, "id": ident, "label": label})
    return rows


def coverage(cases):
    covered = {}
    pats = [(p, c["id"]) for c in cases for p in c["covers_list"]]
    for cmd in commands():
        hits = [cid for p, cid in pats if fnmatch.fnmatchcase(cmd["id"], p)]
        covered[cmd["id"]] = hits
    return covered


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:60].rstrip("_")


def test_name(c) -> str:
    return f"test_{c['area'].lower()}_{c['num']}_{slug(c['title'])}"
