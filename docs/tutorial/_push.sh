#!/usr/bin/env bash
# 把 docs/tutorial 的 12 个部分 + 附录按树状结构推入飞书知识库
set -u
export PATH="C:/Users/EDY/.workbuddy-ai/binaries/node/versions/22.22.2-2:$PATH"
cd "C:/Users/EDY/Documents/ChatGPT/rag/docs/tutorial" || exit 1

SPACE=7694577680926215348
LOG="push-log.txt"
: > "$LOG"

# 第一部分父节点已建、且已建过一个 00-说明 子节点
KNOWN_01_PARENT="A1NtwbdpEi0AxWkBTqycbf1AnG3"
SKIP_CHILD_DIR="01-项目总览"
SKIP_CHILD_BASE="00-说明"

new_parent() {
  lark-cli wiki +node-create --space-id "$SPACE" --title "$1" --as user --jq '.data.node_token' 2>/dev/null
}

new_child() {
  lark-cli docs +create --parent-token "$1" --title "$2" --content "@./$3" \
    --doc-format markdown --as user --jq '.data.document.document_id' 2>/dev/null
}

parts=(
  "01-项目总览|第一部分 · 项目总览|$KNOWN_01_PARENT"
  "02-向量表示|第二部分 · 向量表示|"
  "03-索引构建|第三部分 · 索引构建|"
  "04-召回|第四部分 · 召回|"
  "05-融合精排|第五部分 · 融合精排|"
  "06-查询改写|第六部分 · 查询改写|"
  "07-上下文与记忆|第七部分 · 上下文与记忆|"
  "08-意图与路由|第八部分 · 意图与路由|"
  "09-工作流与工具|第九部分 · 工作流与工具|"
  "10-安全护栏|第十部分 · 安全护栏|"
  "11-评测体系|第十一部分 · 评测体系|"
  "12-工程化与上线|第十二部分 · 工程化与上线|"
  "13-附录|附录|"
)

for entry in "${parts[@]}"; do
  IFS='|' read -r dir title known <<< "$entry"
  if [ -n "$known" ]; then
    node="$known"
    echo "PARENT_EXIST|$dir|$title|$node" >> "$LOG"
  else
    node="$(new_parent "$title")"
    echo "PARENT|$dir|$title|$node" >> "$LOG"
  fi
  for f in "$dir"/*.md; do
    base="$(basename "$f" .md)"
    if [ "$dir" = "$SKIP_CHILD_DIR" ] && [ "$base" = "$SKIP_CHILD_BASE" ]; then
      echo "CHILD_SKIP|$dir|$base" >> "$LOG"
      continue
    fi
    docid="$(new_child "$node" "$base" "$dir/$base.md")"
    echo "CHILD|$dir|$base|$docid" >> "$LOG"
  done
done

echo "ALL_DONE" >> "$LOG"
