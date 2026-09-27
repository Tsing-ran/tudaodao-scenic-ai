#!/usr/bin/env bash
# 渲染 docs/diagrams/ 下所有 .puml → PNG（跳过 _ 开头的样式/探针文件）
# 用法：bash tools/render_diagrams.sh            渲染全部
#       bash tools/render_diagrams.sh xxx.puml   渲染单个
set -e
cd "$(dirname "$0")/.."
export GRAPHVIZ_DOT="$HOME/miniconda3/bin/dot"

render() {
  local f="$1"
  local base
  base="$(basename "$f")"
  [[ "$base" == _* ]] && return 0   # 跳过 _style.puml / _probe.puml 等
  echo "渲染 $base ..."
  # dpi=300 下尺寸会超过 PlantUML 默认 4096px 上限被截断，提高限制
  java -DPLANTUML_LIMIT_SIZE=16384 -jar tools/plantuml.jar -tpng "$f"
}

if [[ -n "$1" ]]; then
  render "docs/diagrams/$1"
else
  for f in docs/diagrams/*.puml; do render "$f"; done
fi
echo "完成。产物在 docs/diagrams/*.png"
