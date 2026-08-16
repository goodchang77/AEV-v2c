#!/usr/bin/env bash
# 匯入 Claude 風格 skill ZIP 到 DSH
# 用法:
#   bash scripts/import_skills.sh <zip1> [zip2 ...]
#   bash scripts/import_skills.sh ~/Downloads/skills/*.zip
# 行為:
#   - ZIP 內有 SKILL.md   → 以 frontmatter 的 name 命名資料夾搬入 ~/.dsh/skills/
#   - ZIP 內沒有 SKILL.md → 自動挑主要 md/txt 當本體，補上 name/description frontmatter
#   - 只有腳本/資源、沒有文字檔 → 跳過並警告（DSH 無法把它當 skill）
set -u

DEST="${DSH_SKILLS_DIR:-$HOME/.dsh/skills}"
mkdir -p "$DEST"

slug() { echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'; }

# 從 SKILL.md 讀 frontmatter 的 name
frontmatter_name() {
  awk '/^---[[:space:]]*$/{c++; next} c==1 && /^name:[[:space:]]*/{sub(/^name:[[:space:]]*/,""); print; exit}' "$1"
}

import_one() {
  local z="$1" tmp f name dir rel body desc
  [ -f "$z" ] || { echo "❌ 找不到 $z"; return; }
  tmp=$(mktemp -d)
  unzip -q "$z" -d "$tmp" 2>/dev/null || { echo "❌ $z：解壓失敗（不是有效 zip？）"; rm -rf "$tmp"; return; }

  f=$(find "$tmp" -name SKILL.md -print -quit)

  if [ -n "$f" ]; then
    # 有 SKILL.md：用 frontmatter name（缺則用 zip 檔名）
    name=$(frontmatter_name "$f")
    [ -z "$name" ] && name=$(slug "$(basename "$z" .zip)")
    name=$(slug "$name")
    dir="$DEST/$name"
    rm -rf "$dir"
    mv "$(dirname "$f")" "$dir"
    find "$dir" \( -name __MACOSX -o -name .DS_Store \) -exec rm -rf {} + 2>/dev/null
    echo "✅ $z → $dir（沿用 SKILL.md，name=$name）"
  else
    # 沒有 SKILL.md：挑主要 md/txt 當本體
    body=$(find "$tmp" -type f \( -iname "instructions.md" -o -iname "*.md" -o -iname "*.txt" \) \
             -not -iname "readme*" 2>/dev/null | sort | head -1)
    [ -z "$body" ] && body=$(find "$tmp" -type f \( -iname "*.md" -o -iname "*.txt" \) -print -quit)
    if [ -z "$body" ]; then
      echo "⚠️ $z：沒有文字檔，無法轉成 skill（DSH 需要指令文字），已跳過"
      rm -rf "$tmp"; return
    fi

    name=$(slug "$(basename "$z" .zip)")
    desc=$(grep -m1 -E '^#+ ' "$body" | sed -E 's/^#+[[:space:]]*//' | cut -c1-200)
    [ -z "$desc" ] && desc="由 $(basename "$z") 自動匯入的 skill"
    desc=$(printf '%s' "$desc" | tr '\n' ' ' | sed "s/\"/'/g")

    dir="$DEST/$name"
    rm -rf "$dir"; mkdir -p "$dir"
    cp -a "$tmp"/. "$dir"/
    {
      printf -- '---\nname: %s\ndescription: %s\n---\n\n' "$name" "$desc"
      cat "$body"
    } > "$dir/SKILL.md"
    rel=${body#"$tmp"/}
    [ "$rel" != "SKILL.md" ] && rm -f "$dir/$rel" 2>/dev/null
    find "$dir" \( -name __MACOSX -o -name .DS_Store \) -exec rm -rf {} + 2>/dev/null
    echo "✅ $z → $dir（已自動生成 SKILL.md，name=$name）"
  fi
  rm -rf "$tmp"
}

for z in "$@"; do import_one "$z"; done

echo "--- 目前 $DEST ---"
ls "$DEST"
