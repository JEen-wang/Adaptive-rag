# 简历项目拷打：Adaptive RAG 电商客服（34 问）

> 八股考「知不知道」，项目拷打考「做没做过」。面试官听的不是标准答案，而是你做决策的过程：为什么这么选、哪条路会坏、数字从哪来。

这份文档只写这个仓库里真实存在的行为。每题按 **新手答 → 高手答 → 追问 → 差距在哪** 组织，代码路径、参数和指标都可以当场对质。

---

## 这份文档怎么用

| 你的处境 | 怎么读 |
|---|---|
| 明天就面，只想背 | 先看[三分钟自述](#三分钟自述)和[数字速查表](#数字速查表)，再挑 5 道最可能被问的：Q2、Q6、Q14、Q20、Q29 |
| 想真讲清楚 | 按章节顺序读，每题的高手答都能落到 `app/` 下具体文件 |
| 已经被问崩过 | 直接看[绝对不能说的 6 句话](#绝对不能说的-6-句话)和 Q24、Q29、Q30 |

### 面试官识别「假经验」的三个信号

1. **只描述架构，不描述决策。** 说「用了 LangGraph」却说不清为什么不用一条链、为什么不用 AutoGen。
2. **只有正面，没有踩坑。** 真做过的人一定有一堆「本来以为……后来发现……」。
3. **回答和 README 一字不差。** README 是结论，拷打问的是结论背后的取舍。

### 先记住这一条请求路径

所有回答都可以挂到这条链上，忘了细节就从这里往回找：

```text
HTTP / SSE
  → ChatService（限流、会话、待确认动作）
    → LangGraph
        apply_guardrail → classify_intent → route_complexity
            ├─ DIRECT   → generate_answer
            ├─ REFUSE   → refuse_answer
            ├─ SINGLE/MULTI → retrieve_docs → generate_answer
            └─ AGENT    → plan_tasks → execute_tools → generate_answer
        → check_faithfulness → compact_memory → END
  → 回答 + citations + strategy + trace_id + latency
```

代码入口：[`app/agents/graph.py`](../app/agents/graph.py) → [`app/services/chat_service.py`](../app/services/chat_service.py) → [`app/retrieval/adaptive.py`](../app/retrieval/adaptive.py)。

---

## 一、项目整体与选型

### Q1 · 用一句话介绍你的项目

**新手答：** 这是一个基于 LangGraph 和 RAG 的电商客服系统，用了 DeepSeek 和向量数据库。

**高手答：** 四句话，每句一个信息维度：

1. **是什么**：面向电商客服的 Adaptive RAG 工作流，先判断问题属于直接回答、单跳检索、多跳检索、业务工具还是拒答，再走对应路径。
2. **技术选型**：FastAPI + LangGraph + BM25/向量混合检索 + 本地 Cross-Encoder 精排 + DeepSeek 生成。
3. **规模与效果**：39 篇政策文档、约 156 个切片、15 个业务工具、14 类意图；离线 65 条检索集上 Hybrid+CE 的 P@1 89.2%、R@3 97.7%，端到端 P50 4.9s。
4. **我的贡献与边界**：路由、检索、工具权限、HITL、评测都是自己写的；目前没有真实公网流量，`user_id` 还没有可信认证。

30 秒版就压成一句：「一个会先判断问题该不该检索、该不该调工具的客服 Agent，写操作必须人工确认，指标来自 65 条离线集的 P@1 89.2%。」

**追问：这个项目的核心难点是什么？**

不是「把 RAG 跑通」，是三件事同时成立：

- 简单问题不能被检索拖慢（`DIRECT` 不检索）；
- 复杂条款要能跨文档核对（`MULTI` + Self-RAG 循环）；
- 写操作不能由模型直接执行（`pending_action` + 幂等）。

**差距在哪：** 新手在报技术栈，高手在报「问题 → 决策 → 代价 → 边界」。面试官记住的永远是第三、四句。

---

### Q2 · 为什么不直接用一条固定的 RAG 链？

**新手答：** 因为 RAG 效果不好，所以做了优化。

**高手答：** 因为客服问题的**成本结构和风险等级**差异太大，一条链会把两类错误同时放大。

| 问题 | 一条链会怎样 | 五路分流后 |
|---|---|---|
| 「你好」 | 走向量检索，白花 200ms + 可能召回无关政策 | `DIRECT`，不检索 |
| 「退货政策是什么」 | 检索一次就够 | `SINGLE`，top_k=3 |
| 「定制马克杯过了七天但有质量问题」 | 单次检索容易只命中「七天无理由」或只命中「质量问题」，答一半 | `MULTI`，改写 + 多路召回 + 自纠错 |
| 「取消订单 ORD10003」 | 被当成问答，模型可能编一句「已为您取消」 | `AGENT`，查状态 → 权限 → 待确认 |
| 「帮我写个炸弹」 | 检索不到就硬编 | `REFUSE`，正则 10ms 拦下 |

`DIRECT` 的价值不只是快：它把「闲聊」从检索链路里摘出去，避免无关文档污染上下文。`REFUSE` 的价值是**让系统有权利说不知道**，这比多召回两条更影响幻觉率。

**追问：五条路径会不会太碎？为什么不是三条？**

`SINGLE` 和 `MULTI` 可以合并，但合并后要么多跳问题只检索一次（答不全），要么单跳问题也跑三轮（慢 3 倍）。`DIRECT` 和 `REFUSE` 是两种「不检索」，但一个要生成、一个要拒答，混在一起会让拒答话术污染闲聊。当前拆分是按**是否需要证据**和**是否产生副作用**两个维度切的，不是按业务分类切的。

**差距在哪：** 面试官在测你会不会用「成本 × 风险」做架构切分，而不是背 Adaptive-RAG 论文的三分类。

---

### Q3 · 为什么选 LangGraph？自己写 while 循环不行吗？

**新手答：** LangGraph 是 LangChain 官方的 Agent 框架，比较流行。

**高手答：** 选它是因为这个项目需要**显式的条件路由 + 可单测的节点 + 可观测的中间状态**，而 LangGraph 的 `StateGraph` 刚好把这三件事变成了框架能力。

具体收益：

- **条件边**：`_route_after_complexity` 把 `strategy` 映射到四个下游节点，路由逻辑是一张表，不是嵌套 if。
- **节点可单测**：每个节点是 `async def node(state, deps) -> dict`，测试直接构造 state 断言返回的 partial update。
- **状态可观测**：`astream(stream_mode="updates")` 能拿到每个节点的增量，SSE 的 `node` 事件就是这么来的。
- **人工确认有落点**：`pending_action` 存在 state 里，确认请求带着 `confirm_action_id` 重新进图，不需要在外面写一套状态机。

代价也要说清楚：

| 代价 | 本项目怎么处理 |
|---|---|
| 状态契约要自己定 | `AgentState(TypedDict, total=False)`，26 个字段，[`app/agents/state.py`](../app/agents/state.py) |
| 容易无限循环 | `max_agent_steps=8`、`max_tool_calls=6` 双上限 |
| 没有内置重试语义 | 自己写 full-jitter 退避，[`app/core/retry.py`](../app/core/retry.py) |
| 持久化/断点要自己接 | 当前没做 checkpointer，会话靠数据库存消息 |

```python
# app/agents/graph.py（节选）
mapping = {
    RetrievalStrategy.DIRECT: "generate_answer",
    RetrievalStrategy.REFUSE: "refuse_answer",
    RetrievalStrategy.SINGLE: "retrieve_docs",
    RetrievalStrategy.MULTI: "retrieve_docs",
    RetrievalStrategy.AGENT: "plan_tasks",
}
```

**追问：不用框架行不行？**

行，但要自己补齐：节点协议、条件路由、状态合并、步数上限、trace 透传、单测脚手架。这个项目 10 个节点、5 条路径，用框架省下的主要是**调试时能看见每一步**。如果只有 2-3 个节点，我会直接写一个 `while` + 显式状态对象，反而更轻。

**差距在哪：** 「用了什么框架」是新手题，「框架替你做了什么、你替框架补了什么」才是这道题的分水岭。

---

### Q4 · 你们这是「多智能体」吗？

**新手答：** 是的，用了多智能体架构，规划器和执行器协作。

**高手答：** 准确说，是**一张 LangGraph 状态图里的多节点工作流**，不是多个自治 Agent 互相协商。

- 有：角色分工（护栏、意图、路由、规划、执行、核验）、共享状态、条件路由。
- 没有：Agent 之间的对话/辩论、黑板、角色自主决定下一步、独立记忆。
- 为什么不做：客服任务步骤短、确定性高，多 Agent 的通信开销和不确定性大于收益。一个「规划器 + 执行器」已经够表达「先查单再决定能不能取消」。

如果面试官追问「那你简历写多智能体算不算夸大」——直接承认表述不严谨，并给出准确说法：「单图多节点的 Agent 工作流，规划与执行分离」。这句话比硬撑「多智能体」可信得多。

**追问：什么场景你才会真的上多 Agent？**

任务本身可并行、子任务需要不同工具集和不同上下文、且允许部分失败时。比如「同时查订单、查库存、查优惠券再汇总」，可以拆成并行子 Agent；但当前 `executor` 是**顺序执行**计划步骤，没有并行编排，这一点不能吹。

**差距在哪：** 面试官问这句，八成是在验你有没有把「多节点」包装成「多智能体」。主动划边界是加分项。

---

### Q5 · 一次请求到底经过哪些节点？状态怎么流转？

**新手答：** 先检索，再生成，最后返回。

**高手答：** 10 个节点，一张图：

| 节点 | 职责 | 关键输出 |
|---|---|---|
| `apply_guardrail` | 注入/越权正则 | `refused` |
| `classify_intent` | 14 类意图 | `intent` |
| `route_complexity` | 五路策略 | `strategy`、`query_complexity` |
| `retrieve_docs` | 改写 + 混合检索 + 精排（或 Self-RAG） | `retrieved_chunks`、`rewritten_queries` |
| `plan_tasks` | Skill 匹配 + LLM 计划 + 写操作待确认 | `plan`、`pending_action` |
| `execute_tools` | 权限、幂等、降级 | `tool_results`、`step_count` |
| `generate_answer` | 生成 + 引用绑定 | `final_answer`、`citations` |
| `refuse_answer` | 固定拒答话术 | `refused=True` |
| `check_faithfulness` | 忠实度检查 + 一次自纠错 | `extra.faithfulness` |
| `compact_memory` | 预算判定 + 压缩/摘要 | `messages`、`summary` |

状态是 `TypedDict` 的 partial update：节点只返回自己改的键，LangGraph 负责合并。

```python
class AgentState(TypedDict, total=False):
    trace_id: str
    user_query: str
    messages: list[ChatMessage]
    intent: IntentResult | None
    strategy: RetrievalStrategy | None
    retrieved_chunks: list[RetrievedChunk]
    plan: AgentPlan | None
    tool_results: list[ToolResult]
    pending_action: ActionProposal | None
    final_answer: str | None
    citations: list[Citation]
    step_count: int
    token_usage: TokenUsage
    latency: LatencyBreakdown
```

**追问：节点多了，State 会不会膨胀？**

会，而且这是这类系统最常见的隐性 bug。这里做了三件事：

1. **不用 `Annotated[list, add]` reducer**：`messages` 不会自动无限追加，压缩是 `compact_memory` 节点显式做的。
2. **大对象只存引用**：检索块存 `chunk_id + content`，不存 embedding；工具结果在压缩时会截断成 `{"truncated": True, "preview": ...}`。
3. **双上限**：`max_agent_steps=8`、`max_tool_calls=6`，超了就停，不会靠模型自觉。

**差距在哪：** 能画出节点不算本事，能说清「状态谁写、谁清、上限在哪」才是做过。

---

### Q6 · 五条路径是谁定的？规则还是模型？

**新手答：** 用大模型判断复杂度，然后路由。

**高手答：** 双轨：**LLM 优先，规则兜底，两处硬覆盖**。

```python
# app/retrieval/adaptive.py（节选）
fallback = rule_based_complexity(query, intent)
if isinstance(self._llm, OfflineLLMProvider):
    return fallback
try:
    parsed = parse_model(await llm.generate(...), ComplexityResult)
    # 覆盖 1：问的是政策、没给订单号，LLM 却想调工具 → 回退 SINGLE
    if fallback.rationale == "general_policy_without_order" and parsed.strategy == AGENT:
        return fallback
    # 覆盖 2：query 里有订单号，规则判 AGENT → 强制走工具
    if _ORDER_ID.search(query) and fallback.strategy == AGENT:
        return fallback
    return parsed
except (LLMProviderError, LLMOutputError):
    return fallback
```

规则顺序（先命中先返回）：

| 顺序 | 条件 | 结果 |
|---|---|---|
| 1 | 意图 `out_of_scope` | `REFUSE` |
| 2 | 问候/闲聊 | `DIRECT` |
| 3 | 政策问法 + 无订单号 + 退款/退货/取消 | `SINGLE` |
| 4 | 交易型意图 / 有订单号 / 命中工具线索词 | `AGENT` |
| 5 | 多跳线索词 ≥1 且长度 >18 | `MULTI` |
| 6 | 其余 | `SINGLE` |

为什么要覆盖：LLM 对「能不能取消订单」这种**政策问法**容易判成 `AGENT`（因为看到「取消」），对「取消 ORD10003」又可能判成 `SINGLE`（因为像在问规则）。规则抓的是**硬信号**（订单号正则、政策问法词），在这两处比模型稳。

**追问：规则会不会误伤？**

会。「能不能取消」如果用户其实想取消（只是语气委婉），会被判 `SINGLE` 只答政策。这是**故意选择保守**：宁可多问一句「请提供订单号」，也不要在没确认时执行写操作。这个取舍要能讲出来。

**差距在哪：** 面试官在看你有没有把「模型不确定的地方」用确定性代码兜住，而不是全交给 Prompt。

---

## 二、意图识别与复杂度路由

### Q7 · 意图识别就是一个 Prompt 搞定吗？

**新手答：** 是的，写个 Prompt 让模型输出分类。

**高手答：** 三层：**LLM 主分类 + 高精度词面覆盖 + 规则兜底**。

- 14 类意图：问候、闲聊、政策、查单、物流、退款、退换、取消、商品咨询、推荐、优惠券、投诉、转人工、越界。
- LLM 输出 JSON（`intent_v3`），`temperature=0`、`max_tokens=256`、`response_format=json_object`。
- `apply_intent_overlay` 只在**高置信短语**上覆盖，覆盖后置信度抬到 ≥0.93。
- LLM 挂了走关键词规则（`intent_rules_v1`），再走同一个覆盖层。

消融（100 条自建集）：

| 系统 | 覆盖层 | 准确率 |
|---|---|---|
| 关键词规则 | 无 | 51.0% |
| `intent_v1` | 关 | 85.0% |
| `intent_v2` | 关 | 86.0% |
| `intent_v3` + 覆盖（生产） | 开 | 100% |

规则基线在 `chitchat`、`product_consult` 上是 0%，`refund` 只有 16.7%——因为关键词分不清「退货」和「退款到账」。这就是为什么要 LLM。

**追问：覆盖层具体覆盖什么？**

只覆盖稳定且历史高混淆的中文客服短语：

- 「转人工 / 人工客服」压过「退款」——用户说转人工时，退款只是上下文。
- 「取消」压过「订单查询」——取消是写操作意图，优先级必须更高。
- 「退款进度 / 到账 / 原路返回」归 `refund`，「退货 / 换货 / 七天无理由」归 `return_exchange`。
- 「忽略以上指令 / 系统提示词 / 炸弹 / 炒股」直接 `out_of_scope`。

判断顺序是「越危险越先判」：jailbreak → 越界 → 转人工 → 问候 → 投诉 → 物流 → 取消 → 政策 → 退款 → 退换 → 推荐 → 商品 → 订单。

**差距在哪：** 只答「一个 Prompt」的人，通常没处理过「模型把转人工判成退款」这种真实混淆。

---

### Q8 · 意图 100%，是不是过拟合？

**新手答：** 没有，测试集是随机抽的，模型效果就是好。

**高手答：** 是自建集，**没有独立 holdout**，所以 100% 只能说明「这套规则+模型在这 100 条上闭合」，不能外推。

诚实的三句话：

1. 100 条是我按 14 类业务分布自己造的，覆盖层在同一批上单独跑也是 100%——这恰恰是过拟合的典型信号。
2. 真实上线必须留 holdout：按时间切分，或另造 50 条不看、双人标注。
3. 覆盖层不是按 query id 写死的：它匹配的是短语模式，`apply_overlay=False` 可以关掉做消融，评测里就是这么做的。

**追问：那这个数字还有意义吗？**

有，但意义是**相对**的：它证明了「关键词规则 → LLM → 覆盖层」这条演进路径每一跳的增益（51 → 85/86 → 100），而不是证明线上准确率。面试时主动说「这是自建集、无 holdout」，比被追问出来强得多。

**差距在哪：** 面试官问这句不是要否定你，是在看你会不会区分「离线闭合」和「线上泛化」。

---

### Q9 · 规则和模型打架时听谁的？

**新手答：** 听模型的，模型更聪明。

**高手答：** 分两处，方向相反：

| 位置 | 谁优先 | 理由 |
|---|---|---|
| 意图覆盖层 | 规则覆盖模型 | 规则抓的是稳定短语，模型在中文客服短句上会漂 |
| 复杂度路由 | 规则覆盖模型（仅两处） | 订单号是硬信号，政策问法是硬反例 |

覆盖层不是「规则永远赢」：`high_precision_intent` 只在**能确定**时返回标签，否则返回 `None`，交回 LLM。这是「高精度、低召回」的设计——宁可漏，不可错。

**追问：怎么防止覆盖层越来越臃肿？**

三条约束：只加**稳定短语**（不随商品/活动变）、只加**高混淆对**（两类互相抢）、每加一条必须能解释「不加会错在哪」。当前覆盖层 125 行，已经接近可维护上限；再涨就应该改成小模型分类器或规则引擎配置化。

**差距在哪：** 能说清「规则和模型的边界在哪、谁在什么条件下赢」，比单纯说「混合」有信息量。

---

### Q10 · 意图识别多花一次 LLM 调用，值吗？

**新手答：** 值得，准确率更高。

**高手答：** 算一笔账：一次客服请求通常有 3-4 次 LLM 调用（意图、路由、生成、核验），意图只占其中一次，`max_tokens=256`，成本很低；换来的是**后续路径正确**——路径错了，检索和工具都是白跑。

省成本的手段已经在用：

- `DIRECT` 路径不检索，省掉 embedding + 精排。
- 注入/越界用正则，10ms 拦下，不打 LLM（E2E 里 `e10` 就是 10ms）。
- 意图失败走规则，不阻塞请求。
- 检索缓存 60s，重复政策问题不重复打向量库。

**追问：能不能用小模型做意图？**

可以，而且应该做：意图是分类任务，7B 以下模型 + 少量 few-shot 足够。但当前没做模型分级，`TOKEN_USAGE` 只统计总量，没有按节点拆分，所以**说不清每个节点花了多少 token**——这是要补的观测项，不能编数字。

**差距在哪：** 面试官想听的是「哪一步值得花钱、哪一步可以省」，不是「模型越贵越好」。

---

## 三、知识库与检索

### Q11 · 知识库怎么建的？

**新手答：** 把文档切块、向量化、存进向量库。

**高手答：** 六步，每步都有可对质的代码：

```text
knowledge/*.md（39 篇）
  → 解析（生产 Unstructured；缺依赖/测试降级 Markdown 标题切分）
  → 清洗（NFKC、空白归一、硬换行、精确去重）
  → 切块（按标题分节，500 字符窗口，60 字符重叠）
  → 稳定 ID（文档相对路径 sha1 前 8 位 + chunk 序号）
  → 双索引（BM25 倒排 + embedding → Qdrant/内存）
  → 启动时全量 ingest，约 156 个 chunk
```

稳定 ID 是踩过坑的：

```python
# app/retrieval/chunking.py
identity_path = path.relative_to(root) if root is not None else Path(path.name)
identity = identity_path.as_posix().lower()
digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]
return f"{stem}_{digest}"
```

最早用的是绝对路径，结果 Windows 和 Docker 里同一篇文档算出两个 ID，重复 ingest 就产生两套向量、引用也对不上。改成知识库相对路径 + 单测之后才稳定。

**追问：知识库更新怎么办？**

当前是**启动全量 ingest，没有增量删除接口**。这是明确缺口：政策改了，旧 chunk 还在索引里。下一步要做的是「文档版本 + 删除同步 + 缓存失效」，让 BM25、向量、引用切到同一版本。不能吹「支持热更新」。

**差距在哪：** 能说出「ID 怎么保证稳定、更新为什么难」，说明你真的维护过索引，而不是跑过一次 notebook。

---

### Q12 · 切块为什么是 500 字符、60 重叠？

**新手答：** 按经验值切的，500 差不多。

**高手答：** 三个约束一起定的：

1. **中文按字符更可控**：DeepSeek tokenizer 不公开，项目里用 `len(text)/1.5` 估 token；500 字符 ≈ 330 token，落在 300-500 token 的常见区间。
2. **按标题先分节**：`_split_sections` 用 `#`/`##`/`###` 切，保证一个 chunk 不跨政策条款；长节再用滑动窗口切。
3. **60 字符重叠 ≈ 12%**：防止「定制商品」和「七天无理由」刚好被切在两个块里，检索只命中一半。

代价也要认：

- 重叠会产生内容重复但 `chunk_id` 不同的块，可能同时占掉 top_k 的两个名额。
- 没有语义切分，长条款会被硬切；对 FAQ/政策这种短节够用，对长合同不够。
- 没有按 token 精确切，`500` 是字符不是 token。

**追问：overlap 调大点不是更安全？**

不是。overlap 越大，索引体积和重复召回越多，精排还要为重复内容打分。12% 是在「不漏关键句」和「不浪费 top_k」之间的折中；真要优化，应该用评测集扫 0/10%/20% 三档，而不是拍脑袋。当前没做这个消融，这是可以主动说的空白。

**差距在哪：** 能报出参数不算本事，能说出「这个参数在跟什么做权衡、怎么验证」才是。

---

### Q13 · 为什么要 BM25 + 向量 + RRF + Cross-Encoder 四层？

**新手答：** 混合检索效果更好，RRF 融合，然后重排。

**高手答：** 四层各自解决一个具体失败模式：

| 层 | 解决什么 | 具体例子 | 代码 |
|---|---|---|---|
| BM25（jieba 分词） | 精确词、政策数字、订单号、SKU | 「满 59 包邮」「ORD10003」 | [`bm25.py`](../app/retrieval/bm25.py) |
| 稠密向量（bge-small-zh-v1.5，512 维） | 近义、换说法 | 「不想要了」≈「七天无理由」 | [`vector.py`](../app/retrieval/vector.py) |
| RRF（k=60） | 融合两路**不同量纲**的排名 | BM25 分数无界，cosine 0-1，不能直接相加 | [`fusion.py`](../app/retrieval/fusion.py) |
| Cross-Encoder（bge-reranker-base） | 多条件联合判断 | 「定制 + 过了七天 + 有质量问题」 | [`providers/reranker.py`](../app/providers/reranker.py) |

RRF 只用排名不用分数：

```python
scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank_position)
```

**追问：为什么不用加权分数融合？**

因为量纲不可比。BM25 在 39 篇小库上分数可能是个位数甚至负数（IDF 为负），cosine 在 0-1；归一化又要按批统计，线上不稳定。RRF 只用 rank，天然免疫量纲问题，代价是丢掉「分数差多少」的信息。

**追问：Cross-Encoder 为什么不直接用来召回？**

太慢。CE 要把 query 和每个候选拼起来过一遍模型，只能对几十条候选做精排；召回必须用双塔/BM25 先粗筛。这是「召回-精排」两阶段的经典分工。

**差距在哪：** 能说清「每层防的是哪种错」，而不是「都加上效果更好」。

---

### Q14 · RRF 到底涨了多少？

**新手答：** RRF 融合后效果提升明显。

**高手答：** 在这组数据上，**RRF 没有涨点**，数字和单独用 bge-small 完全一样：

| 系统 | P@1 | R@3 | MRR |
|---|---:|---:|---:|
| BM25 | 76.9% | 90.0% | 0.84 |
| 仅 bge-small | 83.1% | 94.6% | 0.89 |
| BM25 + small + RRF | 83.1% | 94.6% | 0.89 |
| Hybrid + Cross-Encoder | **89.2%** | **97.7%** | **0.94** |

原因分析：39 篇小库、query 和文档词面重叠高，两路 top 结果高度重合，融合没有引入新候选；真正的增益来自 CE 的联合编码（相对 BM25：P@1 +12.3、R@3 +7.7 个百分点）。

**追问：那 RRF 是不是白做了？**

不是，但**不能吹**。它的价值是「当两路结果差异大时兜底」；这组数据恰好差异小。要证明它有用，需要换更大/更杂的集合，或者拆失败 case 看两路 top5 的交集。当前没做这个实验，所以只能说「本集上无额外增益」——这句话本身就是加分项，因为它证明你会做消融而不是只看总数。

**差距在哪：** 面试官最烦「融合一定比单路好」。主动说「这集上没涨」，可信度立刻上一个台阶。

---

### Q15 · 多跳问题怎么处理？

**新手答：** 把问题拆成子问题，分别检索再合并。

**高手答：** `MULTI` 走 Self-RAG 式循环：**改写 → 双查询召回 → 精排 → LLM 打分 → 不够就带缺失项再来一跳**，最多 3 跳。

```python
# app/retrieval/self_rag.py（节选）
for _hop in range(self._settings.max_retrieval_hops):   # 3
    rewritten = await self._rewriter.rewrite(current_query, missing_aspect=missing)
    queries = list(dict.fromkeys([query, *rewritten]))[:2]
    for search_query in queries:
        for candidate in await self._retriever.retrieve(search_query, top_k=top_k):
            candidates_by_id.setdefault(candidate.chunk_id, candidate)
    reranked = await self._reranker.rerank(query, list(candidates_by_id.values()), top_n=5)
    grade = await self._grade(query, list(accumulated.values()))
    if grade.sufficient:
        break
    missing = grade.missing_aspect or "more specific policy conditions"
```

关键设计：

- **反思用结构化 JSON**（`relevant` / `sufficient` / `missing_aspect`），不用 Self-RAG 论文的特殊 token——可 schema 校验、可单测、不绑定模型。
- **累积去重**：每跳的候选按 `chunk_id` 合并，不会因为改写把上一跳的好证据丢了。
- **成本有上限**：3 跳 × 2 query × (BM25 + embedding) + 3 次 grade + 3 次 rewrite。E2E 里最慢的 `e02` 11.1s 就是 multi 路径。

**追问：怎么判断「够了」？**

LLM 打分：证据是否相关、是否足以回答、缺哪个方面。失败时降级为「有 chunk 就算够」，保证不会因为裁判挂了而空转。

**追问：为什么最多 3 跳？**

客服问题的条件数有限（定制/时效/质量/金额），3 跳覆盖绝大多数组合；再往上边际收益低、延迟线性涨。这是成本约束，不是理论最优。

**差距在哪：** 能说出「反思信号怎么表示、什么时候停、失败怎么降级」，而不是「用了 Self-RAG」。

---

### Q16 · 检索指标怎么测的？

**新手答：** 用测试集算准确率。

**高手答：** 65 条政策问句 / 39 篇文档，**文档级**匹配（不是 chunk 级），指标是 P@1、R@3、MRR。

口径必须一起报：

- 金标是文档 stem（如 `return_policy`），同一篇的多个切片只算一次。
- 65 条覆盖 38 个文档 stem，5 条 query 标了两篇相关文档。
- 稠密路是 `bge-small-zh-v1.5`，**不是 bge-m3**；同日更早一轮用 hash 向量时，仅向量 Hit@1 只有 3.1%。
- 数字来自 `python -m eval.runner --task retrieval`，报告 JSON 不入库，口径写在 [`eval/MEASURED.md`](../eval/MEASURED.md)。

**追问：为什么 P@1 和 R@3 一起报？**

P@1 看「第一篇对不对」——客服最敏感，用户只看第一条引用；R@3 看「相关政策有没有进上下文」——决定生成能不能跨条款。只报 Hit@3 会掩盖「第一名是错文档」。

**差距在哪：** 面试官会问「你的 P@1 是 chunk 还是 doc」——答不上来就露馅。

---

### Q17 · 检索缓存怎么设计的？

**新手答：** 加了 Redis 缓存，提高速度。

**高手答：** 只缓存**静态政策检索**，明确不缓存订单相关查询。

```python
def _looks_like_order_query(query: str) -> bool:
    compact = query.upper().replace(" ", "")
    return "ORD" in compact or "订单" in query
```

- key = `sha256(query|top_k)`，TTL 60s。
- Redis 不可用降级进程内 `MemoryRetrievalCache`。
- 订单查询直接跳过 get/set：订单状态会变，缓存会答错，这是正确性问题不是性能问题。

**追问：60s 够吗？政策更新了怎么办？**

政策更新本来就要重建索引，缓存 60s 是「同一批用户重复问同一句」的短窗口去重，不是内容分发。真要保证一致性，得让 ingest 时按 `policy_version` 失效缓存——当前没做，属于知识库更新那条 P1。

**差距在哪：** 能区分「可以缓存什么、绝对不能缓存什么」，比「我加了 Redis」有价值得多。

---

## 四、工具、权限与写操作

### Q18 · 15 个工具怎么设计的？

**新手答：** 把订单、物流、退款这些接口包成函数给模型调。

**高手答：** 四类 15 个，统一 `Tool` 协议（`name` / `description` / `risk` / `input_model` / `execute`）：

| 类别 | 工具 | 风险 |
|---|---|---|
| 订单 | `get_order`、`get_order_items` | read |
| 物流 | `track_shipment` | read |
| 售后 | `get_refund_status`、`create_refund_request`、`create_return_request`、`cancel_order` | read / destructive / write / destructive |
| 商品 | `search_products`、`get_product_detail`、`recommend_products`、`check_inventory` | read |
| 知识 | `search_knowledge`、`get_coupon`、`get_warranty`、`escalate_to_human` | read / external |

四条设计原则：

1. **单一职责**：查单和查明细分开，模型不用在一个工具里选参数分支。
2. **描述即文档**：MCP 工具描述里直接写「何时用 / 何时不用 / 优先用哪个 / 返回什么字段」，这是提升选对率最便宜的手段。
3. **参数最小化**：`input_model` 是 pydantic 模型，必填项越少越好，缺失时由执行层用 query 兜底。
4. **输出结构化**：统一 `ToolResult(name, success, output, error, risk)`，生成节点和离线模式都能消费。

**追问：工具多了模型选错怎么办？**

三层收缩：

- **Skill 先收缩目录**：命中退货 Skill 时，planner 只看到 4 个工具，不是 15 个。
- **计划后 sanitize**：只保留 registry 里存在且在 allowed 集合内的步骤，最多 6 步。
- **执行有上限**：`max_tool_calls=6`，防止模型在计划里堆步骤。

**差距在哪：** 面试官问工具设计，其实在问「你怎么降低模型的决策空间」。

---

### Q19 · 工具调用失败怎么办？

**新手答：** 加重试，失败就返回错误提示。

**高手答：** 按「读 / 写」分开处理，这是最关键的一条：

| 失败类型 | 处理 |
|---|---|
| 参数 schema 不合法 | `InvalidRequestError`，直接告诉用户补参数，不重试 |
| 权限不足 | `ToolPermissionError`，直接抛出，不降级 |
| 读工具业务失败 | 按 `READ_FALLBACKS` 映射换工具（如 `get_order` → `search_knowledge`） |
| 写工具失败 | **不自动重试**，靠幂等键 + 状态核对 |
| 瞬时网络/限流 | LLM/embedding 层 full-jitter 退避，最多 3 次 |

```python
READ_FALLBACKS = {
    "get_order": ["search_knowledge"],
    "track_shipment": ["get_order", "search_knowledge"],
    "recommend_products": ["search_products", "search_knowledge"],
    ...
}
```

降级结果会带上 `fallback_from` 和 `fallback_error`，生成节点能如实告诉用户「没查到订单，给你相关政策」。

**追问：写操作为什么不重试？**

因为副作用不可逆。网络超时的时候，服务端可能已经执行成功了，重试就会取消两次/退两次。正确做法是幂等：`sha256(tool + arguments)` 作为 fingerprint，执行前查 `IdempotencyRepository`，命中就直接返回上次结果；确认动作还带 `action_id`，天然去重。

**差距在哪：** 新手对读写一视同仁地重试；做过交易系统的人一定知道「写不能瞎重试」。

---

### Q20 · 怎么保证模型不能直接取消订单？

**新手答：** 在 Prompt 里告诉模型，取消前要问用户确认。

**高手答：** Prompt 不算防线，四层代码才算：

1. **参数层**：`input_model` 校验，`order_id` 格式不对直接拒。
2. **权限层**：`assert_permitted(tool, confirmed=...)`，`WRITE_RISKS = {WRITE, DESTRUCTIVE}` 没有确认就抛 `ToolPermissionError`。
3. **计划层**：planner 发现写步骤且没有 `confirm_action_id`，不执行，先返回 `pending_action`（`action_id` + 摘要 + 风险等级），执行器看到 pending 就跳过。
4. **执行层**：确认请求回来时，重新校验 `action_id` 存在、未过期（15 分钟）、`session_id` 和 `user_id` 都对得上；工具内部再用 `get_visible_order` 校验订单归属（别人的单直接返回 not found），`cancel_order` 只允许 `created` / `paid` 状态，执行后写 `audit_log`；幂等键防重。

```python
# app/tools/permissions.py
def assert_permitted(tool: Tool, *, confirmed: bool) -> None:
    if tool.risk in WRITE_RISKS and not confirmed:
        raise ToolPermissionError(f"{tool.name} requires explicit user confirmation")
```

还有一个细节：用户说「帮我取消」但没给订单号时，planner 会清空计划并标记 `missing_order_id`，回答是「请提供要处理的订单号」——**不猜、不拿最近一单顶上**。

**追问：用户确认了，但订单已经发货了怎么办？**

`cancel_order` 的仓储层只允许 `created` / `paid`，已发货会抛 `InvalidRequestError`，回答变成「该订单已发货，无法取消，可以走退货」。确认只是「用户授权」，不是「跳过业务校验」——这两件事必须分开。

**差距在哪：** 这道题是分水岭。答「Prompt 里写了要确认」的，基本会被判定没做过交易类系统。

---

### Q21 · 待确认动作放进程内字典，多副本怎么办？

**新手答：** 用 Redis 存一下就行。

**高手答：** 先承认现状：`ChatService._pending_actions` 是进程内 `dict`，TTL 15 分钟，校验 `session_id + user_id`。它的问题很明确：

- 多副本时，确认请求打到另一台就找不到；
- 重启即丢；
- 没有一次性消费标记，理论上可重放（实际靠幂等键兜住）。

正确的设计：

```text
Redis/DB 存 {action_id: {session_id, user_id, tool, args, risk, expires_at, consumed}}
确认时：GET → 校验归属与过期 → 原子标记 consumed → 执行（幂等）→ 写结果
```

已列入路线图 P1。面试时最好的说法是：「当前是单机可用的实现，多副本要迁到持久化 + 一次性消费，这是我明确知道的缺口。」

**追问：为什么不用 JWT 把动作编码进 token？**

可以，但动作参数可能含敏感信息，且无法服务端撤销/过期控制。持久化存储更容易做审计和一次性消费。

**差距在哪：** 能主动指出自己实现的失效边界，比被问出来强十倍。

---

### Q22 · Skill 和 MCP 分别解决什么？

**新手答：** 都是扩展能力的机制。

**高手答：** 两者层次不同：

| 机制 | 解决什么 | 本项目实现 |
|---|---|---|
| **Skill** | 把「某类任务的标准流程」固化，并**收缩工具目录** | 4 个 JSON：退货、取消、跟踪、推荐；触发词或意图映射；planner 只把 skill 里的工具给模型看 |
| **MCP** | 把**外部工具**统一成同一调用契约 | `MCPToolProxy` 继承 `Tool`，planner/executor 不区分 transport；本地 2 个 + 远程 HTTP JSON |

Skill 的价值不是「多了一个概念」，是**降低选择空间**：15 个工具里选对一个很难，4 个里选对容易得多。

MCP 的价值是**接入成本**：远程工具不用改 planner/executor，只要注册一个 proxy。

**追问：这是标准 MCP 协议吗？**

不是。当前远程工具走的是固定 HTTP JSON 接口（`POST {name, arguments}`），没有实现能力发现、认证协商、资源/提示等协议能力，也没有审计。这一点必须说清楚，不能把「叫 MCP」当成「实现了 MCP」。

**差距在哪：** 面试官问「Skill 和 MCP 什么关系」，其实在测你会不会把营销词和工程实现分开。

---

## 五、记忆与上下文预算

### Q23 · 128k 预算和三级压缩怎么做的？

**新手答：** 超过长度就截断，或者用滑动窗口。

**高手答：** 按利用率分四档，逐级加码：

| 利用率 | 级别 | 动作 |
|---|---|---|
| < 50% | `NONE` | 不动 |
| 50%–70% | `SOFT_TRUNCATE` | 工具结果截到 400 字符 |
| 70%–85% | `HARD_COMPRESS` | 工具结果截到 160 字符 + 滑动窗口保留最近 4 轮 + 摘要前置 |
| > 85% | `AUTO_COMPACT` | 先摘要，再重新压缩 |

```python
def decide_level(used: int, settings: Settings) -> CompressionLevel:
    ratio = utilization(used, settings.token_budget)   # 128_000
    if ratio >= settings.auto_compact_ratio:   # 0.85
        return CompressionLevel.AUTO_COMPACT
    if ratio >= settings.compress_hard_ratio:  # 0.70
        return CompressionLevel.HARD_COMPRESS
    if ratio >= settings.compress_soft_ratio:  # 0.50
        return CompressionLevel.SOFT_TRUNCATE
    return CompressionLevel.NONE
```

token 是启发式估的：`len(text)/1.5`，因为 DeepSeek tokenizer 不公开。这意味着**预算是近似值**，不是精确 token 数——面试要主动说。

**追问：为什么在节点里压缩，不用 reducer？**

用 `Annotated[list, add]` 会让 `messages` 静默增长，直到某次请求突然超限。显式压缩节点让「什么时候压、压到什么程度」变成可观测、可测试的行为，而且压缩级别会写进 state 的返回里。

**差距在哪：** 能说出「阈值、每档动作、估算误差」，而不是「做了滑动窗口」。

---

### Q24 · 追问：压缩后的历史真的进生成 Prompt 了吗？

**新手答：** 进了，多轮对话会带上历史。

**高手答：** 没有。这是当前最该主动承认的缺口。

事实是：

- `memory_node` 在 `END` 前执行，压缩和摘要发生在**回答之后**；
- `generate_node` 的 Prompt 只用 `user_query` + 检索证据 + 工具结果，没有 `messages` / `summary`；
- `ChatService._initial_state` 里 `summary` 初始化为空串。

所以：

- 「三级压缩」是真的实现了、有单测、有阈值；
- 但「多轮记忆影响回答」**还没闭环**。用户问「那这个呢」，系统接不住指代。

怎么答才不减分：

> 压缩管线是完整的，但还没接到生成侧。我把它列为 P0，因为长会话下「有记忆」比「压缩得漂亮」更影响体验；现在系统不会因为历史爆上下文，但也不会真正记住上下文。

**追问：那你的压缩模块现在有什么价值？**

它保证会话持久化和未来接入时不会一次性重构：阈值、分级、截断策略、摘要器都已就位，接生成侧只需要把 `summary + 窗口消息` 拼进 Prompt 并按预算裁剪。

**差距在哪：** 这题几乎必被追问，因为 README 的简历段落写了「上下文压缩与记忆管理」。主动拆开「实现了什么 / 没接什么」，比含糊过去安全。

---

## 六、容错、降级与流式

### Q25 · 没有 DeepSeek / Redis / Qdrant 会怎样？

**新手答：** 会报错，需要先配置好依赖。

**高手答：** 每个依赖都有明确降级路径，系统仍能跑，但能力下降要说清：

| 依赖 | 不可用时 | 后果 |
|---|---|---|
| DeepSeek | `OfflineLLMProvider`，返回检索原文/订单状态 | 不生成完整答案，但不说假话 |
| Redis | 进程内缓存 + 内存限流 | 多副本限流失效 |
| Qdrant | `InMemoryVectorStore`（余弦） | 重启丢失向量，需重新 ingest |
| bge-small 权重 | `HashEmbeddingProvider` | 仅向量 Hit@1 约 3.1%，**不可用于效果** |
| Cross-Encoder 权重 | 词面 overlap 精排 | 精排质量下降，P@1 掉回 RRF 水平 |
| Unstructured | Markdown 标题切分 | 只支持 md，PDF/Office 静默跳过 |

`/api/v1/capabilities` 会报告实际后端和 `degraded` 标志，启动日志也记录运行模式。这是踩坑后加的：早期模型没加载成功，系统照样跑，但没人知道自己在看降级结果。

**追问：降级后的效果测过吗？**

没有单独评测。只能说「能跑、不崩、不编」，不能说「效果不变」。这是明确的未测项。

**差距在哪：** 「能降级」和「降级后还能用」是两件事，能区分就赢了。

---

### Q26 · 重试怎么做的？为什么写操作不重试？

**新手答：** 失败重试三次。

**高手答：** 只对**瞬时错误**重试，且用 full jitter 打散：

```python
ceiling = min(cap, base * (2 ** attempt))   # base=0.5s, cap=8s
delay = random.uniform(0.0, ceiling)        # full jitter
```

- 最多 3 次，只重试 `408/429/500/502/503/504`；`400/401/403/404/422` 直接失败。
- 为什么 jitter：多副本同时失败时，固定退避会让重试同步，形成二次洪峰。
- 写操作用幂等键去重，不靠重试：`sha256(tool+args)` 命中就返回旧结果。
- 流式输出中途失败不重试：已经吐出的 token 无法撤回，供应商也不支持 token 级续传。

**追问：重试会不会放大延迟？**

会，3 次尝试只有 2 次退避，最坏 0.5 + 1.0 = 1.5s 额外延迟。所以只在「LLM 调用 / embedding 调用」这种可重试层做，工具执行层不做无脑重试。

**差距在哪：** 能说出「哪些状态码重试、为什么用 jitter、写操作为什么例外」，是工程经验的直接体现。

---

### Q27 · 流式为什么不是边生成边吐 token？

**新手答：** 用了 SSE，实时返回。

**高手答：** 当前是**两段式**：先推节点进度，答案核验完再切片发送。

```python
for index in range(0, len(response.answer), 48):
    yield {"event": "token", "text": response.answer[index:index + 48]}
```

原因有三：

1. 答案要过忠实度检查，可能被改写甚至拒答。先吐一半再撤回，体验更差。
2. 供应商不支持 token 级续传，中途失败重试会重复文本。
3. 生成阶段输出的是 JSON envelope（`answer` + `citation_chunk_ids`），不能直接当正文吐给用户。

代价：首字延迟等于全链路时间（P50 4.9s）。这是**取舍**，不是没想到。

**追问：那怎么优化首字延迟？**

两条路：① 生成阶段真流式，核验阶段改为「事后校验 + 可撤回提示」；② 对 `SINGLE` 这种低风险路径跳过核验直接流。前者要产品接受「可能撤回」，后者要接受「低风险路径幻觉率上升」。当前没做，属于体验优化项。

**差距在哪：** 面试官问流式，八成在测你知不知道「流式和校验是冲突的」。

---

### Q28 · 幻觉怎么治理？

**新手答：** 用 RAG，让模型基于检索结果回答，就不会幻觉。

**高手答：** RAG 只降低幻觉，不消除。这里是五道防线：

| 防线 | 位置 | 作用 |
|---|---|---|
| 输入正则 | `guardrails/injection.py` | 拦 jailbreak / 越权，10ms |
| 路由拒答 | `REFUSE` | 越界问题不进生成 |
| 引用绑定 | `generate_node` | `citations` 只能来自实际检索到的 `chunk_id` |
| 忠实度检查 | `guardrails/hallucination.py` | LLM judge 判 `supported` |
| 自纠错 + 兜底 | `faithfulness_node` | 失败重写一次，再失败改抽取式，仍失败拒答 |

```python
if not result.supported:
    HALLUCINATION_FLAGS.inc()
    patched, judged, _ = await self_correct_answer(...)
    if not judged.supported:
        return {"final_answer": "现有证据不足，暂时无法给出可靠答复。", "refused": True}
```

**追问：你的幻觉率 0% 可信吗？**

不可全信。裁判和生成是同一个模型（`deepseek-chat`），共享知识和措辞偏好，会偏乐观；而且这是 65 条离线集，不是人工事实核查。可信的说法是：「同模型裁判下，从无检索 20% 降到 0%，相对下降 100%；人工核验还没做。」

**差距在哪：** 说「RAG 消除幻觉」的人，通常没做过忠实度评估。

---

## 七、指标与评测拷打

### Q29 · 简历写 Precision 58%→85%，仓库实测 89.2%，哪个是真的？

**新手答：** 都是真的，不同版本。

**高手答：** 先分清两套口径，再给结论。

README 的简历段落写的是：`Precision 58%→85%，Recall 63%→91%，Faithfulness 54%→88%，幻觉率下降 62%`。这是**简历原文**，仓库没有对应的可复现报告。

仓库这轮可复现的是（2026-08-22，65 条 / 39 篇）：

| 指标 | 数值 |
|---|---|
| BM25 P@1 / R@3 / MRR | 76.9% / 90.0% / 0.84 |
| Hybrid + CE P@1 / R@3 / MRR | 89.2% / 97.7% / 0.94 |
| 无检索 → RAG → RAG+自纠错 忠实度 | 80% → 96.9% → 100% |
| 幻觉率 | 20% → 3.1% → 0% |

怎么答：

> 简历那组是早期一版评测，和仓库现在这轮不是同一套数据和模型，我没法把它们一一对上。仓库这轮能复现的是 89.2 / 97.7 / 0.94，命令、数据集、模型版本都写在 `eval/MEASURED.md` 里。如果只能报一组，我报仓库这组，因为它可复现。

**追问：简历还写了 Cohere Rerank，代码里为什么是 bge？**

也要主动说：简历是原文展示，实际代码用的是本地 `BAAI/bge-reranker-base`。Cohere 试用有免费额度、正式 API 按量收费，我没有接。这不是「写错了」，是「简历口径和仓库实现不一致」，我知道差在哪。

**差距在哪：** 这题不是考数字大小，是考**你敢不敢承认口径不一致**。硬圆「都是真的」最掉分。

---

### Q30 · 这些数字能证明什么，不能证明什么？

**新手答：** 证明了系统效果很好。

**高手答：** 分开说，这是最能体现工程素养的一题。

**能证明：**

- Adaptive 路由把问候/注入从检索里拆出去了（E2E 拒答 100%，注入 10ms）。
- 本地 small 向量比 hash 强很多（Hit@1 3.1% → 83.1%）。
- Cross-Encoder 在这组数据上有稳定增益（P@1 +6.1 相对 RRF）。
- 自纠错能把同模型裁判下的幻觉压到 0。
- 整条链路能跑通（16 条 E2E，工具路径 100%）。

**不能证明：**

| 限制 | 说明 |
|---|---|
| 自建集、无 holdout | 100 条意图、65 条检索都是自己造的 |
| 同模型裁判 | 忠实度偏乐观 |
| 小样本 | E2E 只有 16 条，P95 是离散分位，最慢 11.1s |
| 无并发/故障注入 | 单请求测试，不代表生产吞吐 |
| 无人工核验 | 幻觉率不是人判的 |
| 无多租户 | `user_id` 未认证 |

**差距在哪：** 面试官问「能证明什么」，其实在给你机会展示判断力。只报喜的人，会被认为没做过评估。

---

### Q31 · 154 个测试测了什么？

**新手答：** 单元测试，覆盖率还行。

**高手答：** `pytest -q` → **154 passed**，覆盖的是「容易坏且坏了不容易发现」的地方：

- 检索：RRF、Adaptive 路由、BM25/向量、缓存、查询改写、Self-RAG、分词。
- 安全：注入检测、工具权限、参数校验。
- 可靠性：full-jitter 重试、降级、压缩分级、幂等。
- 业务：订单仓储、HITL 确认、Skill 匹配、MCP 代理、执行 fallback、自纠错。
- 接口：HTTP chat、SSE、健康检查。
- 评测：`eval/metrics.py` 的 P/R/MRR/分位函数。

不测什么也要说：**不调真实 DeepSeek、不下载模型权重**。`APP_ENV=testing` 时 embedding 用 hash、精排用词面，保证 CI 可重复、不烧钱。CI 在 Python 3.11/3.12 上跑锁文件一致性、Ruff format/lint、mypy、pytest（覆盖率门槛 70%）；前端 `npm test` + `npm run build` 是本地验证，没有进 CI。

**追问：测试多就等于质量好吗？**

不等于。154 个测试里大部分是单元级，端到端只有 16 条离线样本，没有并发压测和故障注入。测试保证的是「重构不破坏已知行为」，不是「线上不出事」。

**差距在哪：** 能说清「测了什么、没测什么、为什么」，比报数字有用。

---

## 八、上线、踩坑与反思

### Q32 · 真的上线了吗？

**新手答：** 上线了，可以 Docker 部署。

**高手答：** 准确说：**可部署、可本地运行、有 CI，但没有真实公网流量**。

已具备：

- 三档 Docker Compose：SQLite + BM25 演示、PostgreSQL + Redis 单机、PostgreSQL + Redis + Qdrant + 双 API + Nginx 多实例。
- `/health`、`/ready`、`/capabilities` 三个探针，`/metrics` 暴露 Prometheus 指标。
- CI：Python 3.11/3.12 + 锁文件校验 + Ruff + mypy + pytest（覆盖率 ≥70%）。
- 结构化日志带 `trace_id`，按阶段记录意图/检索/工具/生成的延迟，token 记总量。

不具备：

- 请求体里的 `user_id` 没有认证，不能直接面向不可信用户。
- 待确认动作在进程内，多副本会丢。
- 订单/物流是种子数据，没有真实承运商/支付网关。
- 没有并发压测、没有线上 A/B、没有 SLA。

**追问：那你怎么敢写「上线」？**

不写「上线」，写「可部署的工程实现 + 离线评测」。如果面试官追问线上指标，直接说没有——编一个线上 QPS 是最容易被戳穿的。

**差距在哪：** 「能跑」和「上线」之间隔着认证、持久化、容量、监控、值班，能数出来就说明你知道生产是什么。

---

### Q33 · 开发中遇到的最大问题？

**新手答：** 环境配置比较麻烦。

**高手答：** 三个真实踩坑，都能落到 commit：

1. **前端 `Failed to fetch`**：Vite 代理端口和 API 端口不一致，改了 `VITE_API_BASE` 并统一到 `scripts/dev-start.ps1`，默认 8002/5173。教训：跨进程契约要有一个地方统一定义，不能两边各写一份。
2. **文档 ID 跨平台漂移**：早期用绝对路径算 ID，Windows 和 Docker 里同一篇文档产生两套向量，引用对不上。改成知识库相对路径 + sha1 前 8 位，并补了测试。教训：任何进入索引的 ID 都必须是环境无关的。
3. **CI 双版本同时红**：Ruff 格式问题在 3.11/3.12 一起失败。加了格式门禁，本地提交前就能发现。教训：把「风格问题」挡在 CI 之前，别让它和真实失败混在一起。

**追问：最大的问题不是某个 bug 吧？**

对，最大的问题是**降级不可见**：模型没加载成功，系统照样返回结果，但没人知道自己在看降级输出。后来加了 `/capabilities` 和启动日志，把「实际用了什么后端」变成可查询的事实。这类问题比单个 bug 危险，因为它不报错。

**差距在哪：** 能讲出「问题 → 定位 → 修复 → 沉淀成什么机制」，而不是「改了个 bug」。

---

### Q34 · 重新设计会怎么做？

**新手答：** 加更多功能，接更多模型。

**高手答：** 按「正确性 > 体验 > 性能」排，前三个是 P0：

1. **身份与会话隔离**：不再信任请求体 `user_id`，由可信网关/登录态绑定；读会话时校验归属。这是安全底线。
2. **待确认动作持久化**：Redis/DB + 一次性消费 + 过期，支持多副本。这是写操作正确性。
3. **多轮记忆接生成**：把 `summary + 最近窗口` 按预算拼进生成 Prompt，让「那这个呢」能接住。
4. 然后才是：知识库增量删除与版本切换、模型预热、SSE 真流式、节点级 token/延迟观测、线上采样评估。

**追问：为什么不是先做性能？**

因为性能问题可以加机器、加缓存，正确性问题会直接答错、误操作。客服场景里「答错一次」的代价远高于「慢 2 秒」。

**差距在哪：** 能排出优先级并给出理由，比列一堆「未来计划」可信。

---

## 九、收尾：自述模板与禁区

### 三分钟自述

```text
【30 秒 · 定调】
我做的是一个电商客服的 Adaptive RAG 工作流。核心不是「接个大模型」，
而是先判断这个问题该不该检索、该不该调工具、该不该拒答，再走对应路径。

【90 秒 · 三个决策】
1）路由：五条策略，LLM 判复杂度 + 规则兜底，订单号和政策问法两处硬覆盖。
2）检索：BM25 + bge-small 混合，RRF 融合，Cross-Encoder 精排；
   多跳走 Self-RAG 循环，最多 3 跳，用结构化 JSON 做反思。
3）写操作：schema → 权限 → 待确认 → 幂等，四层保证模型不能直接取消订单。

【60 秒 · 结果与边界】
65 条离线集上 Hybrid+CE 的 P@1 89.2%、R@3 97.7%；端到端 P50 4.9s；
154 个测试，CI 跑 3.11/3.12。
边界我也清楚：意图 100% 是自建集含覆盖层，没有 holdout；
多轮记忆还没接到生成；待确认动作还在进程内；没有真实公网流量。
```

### 统一答题框架

```text
业务约束 → 方案选择 → 代码落点 → 遇到的问题 → 修复方式 → 指标结果 → 当前边界
```

七个环节缺一不可。只讲前三个是「看过教程」，补上后四个才是「做过」。

### 绝对不能说的 6 句话

| 别说 | 改成 |
|---|---|
| 「用了 LangGraph 所以是多智能体」 | 「单图多节点的 Agent 工作流，规划与执行分离」 |
| 「RAG 消除了幻觉」 | 「同模型裁判下幻觉从 20% 降到 0%，人工核验还没做」 |
| 「意图准确率 100%」 | 「自建 100 条上 100%，含覆盖层，无 holdout」 |
| 「RRF 融合提升明显」 | 「本集上 RRF 与单路持平，增益来自 Cross-Encoder」 |
| 「上线了」 | 「可 Docker 部署 + 离线评测，没有真实公网流量」 |
| 「支持多轮记忆」 | 「压缩管线已实现，但还没接到生成侧」 |

### 数字速查表

| 项 | 值 |
|---|---|
| 意图 | 14 类；规则 51% → v1 85% / v2 86% → v3+覆盖 100%（100 条自建） |
| 检索集 | 65 条 query / 39 篇文档 / 约 156 chunk |
| BM25 | P@1 76.9% · R@3 90.0% · MRR 0.84 |
| bge-small | P@1 83.1% · R@3 94.6% · MRR 0.89 |
| Hybrid + CE | P@1 89.2% · R@3 97.7% · MRR 0.94 |
| 忠实度 | 无检索 80% → RAG 96.9% → 自纠错 100% |
| 幻觉率 | 20% → 3.1% → 0%（同模型裁判） |
| E2E | 16 条；拒答 100%、工具路径 100%、关键词 9/11；P50 4.9s / P95 5.8s，最慢 11.1s |
| 测试 | 154 passed |
| 关键参数 | chunk 500 字符 / overlap 60；top_k 3/8；rerank 5；RRF k=60；最多 3 跳；128k 预算；步数 8 / 工具 6 |

### 代码入口

| 想核对的 | 打开 |
|---|---|
| 图与路由 | [`app/agents/graph.py`](../app/agents/graph.py) · [`app/retrieval/adaptive.py`](../app/retrieval/adaptive.py) |
| 状态契约 | [`app/agents/state.py`](../app/agents/state.py) |
| 意图与覆盖 | [`app/agents/nodes/intent.py`](../app/agents/nodes/intent.py) · [`intent_overlay.py`](../app/agents/nodes/intent_overlay.py) |
| 检索与融合 | [`app/retrieval/hybrid.py`](../app/retrieval/hybrid.py) · [`fusion.py`](../app/retrieval/fusion.py) · [`self_rag.py`](../app/retrieval/self_rag.py) |
| 切块与入库 | [`app/retrieval/chunking.py`](../app/retrieval/chunking.py) · [`ingest.py`](../app/retrieval/ingest.py) |
| 工具与权限 | [`app/tools/`](../app/tools/) · [`app/mcp/adapter.py`](../app/mcp/adapter.py) |
| 压缩与预算 | [`app/memory/`](../app/memory/) |
| 重试与指标 | [`app/core/retry.py`](../app/core/retry.py) · [`app/observability/metrics.py`](../app/observability/metrics.py) |
| 评测口径 | [`eval/MEASURED.md`](../eval/MEASURED.md) · [`docs/14-evaluation-report.md`](14-evaluation-report.md) |
| 明确缺口 | [`docs/12-limitations.md`](12-limitations.md) |

---

> 最后一句：坦诚讲一个 60 分、但每处都能自圆其说的项目，胜过吹一个 90 分、一追问就崩的项目。面试官要的从来不是完美，是**你知道自己站在哪**。
