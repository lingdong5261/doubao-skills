#!/usr/bin/env python3
"""校验各 skill 目录的 SKILL.md 结构，供 CI 与本地使用。

规则（error 会失败，warn 只提示）：
  E1 SKILL.md 存在，且开头有 YAML front matter（--- 包裹）
  E2 front matter 含 name 与 description，且都不为空
  E3 name 与目录名一致（忽略大小写），且只用小写字母、数字、连字符
  E4 description 不超过 1024 字符
  E5 正文非空
  W1 SKILL.md 超过 500 行
  W2 正文里的相对链接指向的文件不存在
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_FILE = "SKILL.md"
MAX_DESC = 1024
MAX_LINES = 500
NAME_RE = re.compile(r"^[a-z0-9]+(-\w+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#]+?)\)")
IGNORE_DIRS = {"scripts", "github", ".github", ".git", "references", "apis", "lib"}


def parse_front_matter(text: str) -> tuple[dict[str, str], str, str | None]:
    if not text.startswith("---"):
        return {}, text, "缺少 YAML front matter"
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text, "front matter 未闭合（缺少结尾 ---）"
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("'\"")
    body = "\n".join(lines[end + 1:])
    return fields, body, None


def check_skill(skill_dir: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    skill_md = skill_dir / SKILL_FILE
    if not skill_md.is_file():
        return [f"E1 缺少 {SKILL_FILE}"], warns

    text = skill_md.read_text(encoding="utf-8", errors="replace")
    fields, body, fm_error = parse_front_matter(text)
    if fm_error:
        errors.append(f"E1 {fm_error}")
    else:
        for key in ("name", "description"):
            if not fields.get(key):
                errors.append(f"E2 front matter 缺少 {key}")
        name = fields.get("name", "")
        if name and name.lower() != skill_dir.name.lower():
            errors.append(f"E3 name『{name}』与目录名『{skill_dir.name}』不一致")
        if name and not NAME_RE.match(name.lower()):
            errors.append(f"E3 name『{name}』只能用小写字母、数字、连字符")
        desc = fields.get("description", "")
        if len(desc) > MAX_DESC:
            errors.append(f"E4 description {len(desc)} 字符，超过 {MAX_DESC}")

    if not body.strip():
        errors.append("E5 正文为空")

    line_count = len(text.splitlines())
    if line_count > MAX_LINES:
        warns.append(f"W1 {SKILL_FILE} {line_count} 行，建议拆分到 references/")

    for target in LINK_RE.findall(body):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if not (skill_dir / target).exists():
            warns.append(f"W2 相对链接失效：{target}")

    return errors, warns


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    skills = [
        d for d in sorted(root.iterdir())
        if d.is_dir() and d.name not in IGNORE_DIRS and not d.name.startswith(".")
    ]
    if not skills:
        print("未找到任何 skill 目录")
        return 1

    failed = 0
    for skill_dir in skills:
        errors, warns = check_skill(skill_dir)
        for msg in warns:
            print(f"[warn] {skill_dir.name}: {msg}")
        for msg in errors:
            print(f"[error] {skill_dir.name}: {msg}")
        if errors:
            failed += 1
        else:
            print(f"[ok] {skill_dir.name}")

    print(f"\n检查 {len(skills)} 个 skill，失败 {failed} 个")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
