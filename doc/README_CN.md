# Solana Meme Trading Agent

<div align="center">

一个面向 Solana Meme 币的自然语言交易助手，底层使用 Bitget Wallet 的市场数据与执行能力。

[![黑客松](https://img.shields.io/badge/黑客松-Agent%20Talent%20Show-blue)](https://x.com/i/communities/2031959181063049384)
[![赛道](https://img.shields.io/badge/赛道-Bitget%20Wallet-orange)](https://github.com/bitget-wallet-ai-lab/bitget-wallet-skill)
[![许可](https://img.shields.io/badge/许可-MIT-yellow)](../LICENSE)

[快速开始](#快速开始) • [当前能力](#当前能力) • [真实示例](#真实示例) • [CLI 命令](#cli-命令) • [风控与退出策略](#风控与退出策略) • [系统结构](#系统结构)

</div>

---

## 当前能力

你可以直接用自然语言和这个 Agent 交流。

当前支持：

- 扫描热门 Solana Meme 币
- 在交易前分析代币风险
- 通过 mint 地址或常见 symbol（如 `BONK`）发起买入
- 卖出已有持仓
- 查看钱包状态、余额、持仓和最近交易历史
- 自动生成一个小额 auto-invest 投资计划
- 持续监控仓位，并按动态策略自动退出

Agent 会把最近几轮对话保存在 `.agent/state.json` 里，因此重开后仍能保留短期上下文，比纯无状态 CLI 更适合连续交互。

## 关键实现特性

| 能力 | 当前行为 |
|---|---|
| 自然语言聊天 | `python -m cli.main chat` 接受自由输入；正则意图未命中时会回退到 LLM 意图识别 |
| 专用系统提示词 | 使用面向 Solana meme trading 的专用 prompt |
| 多轮记忆 | 最近聊天消息会持久化保存并在后续轮次复用 |
| Symbol 解析 | 买入/分析流程可以把 `BONK` 这类 symbol 解析成 Solana mint |
| 交易前分析 | 每次买入前都会做安全性、流动性、活动度分析 |
| Auto-invest 加权分配 | auto-invest 按分数和流动性加权，不再等权分配 |
| 动态退出策略 | monitor 支持部分止盈、保本提升、trailing stop、time stop 和退出归因 |
| 人工确认 | 实盘买入、卖出、auto-invest 执行仍然需要确认 |

---

## 快速开始

### 环境要求

- Python 3.9+
- 一个兼容 OpenAI 风格接口的 LLM API Key
- 一个用于实盘或监控的 Solana 钱包助记词

### 安装

```bash
git clone <仓库地址>
cd BestTradeAgent
pip install -r requirements.txt
```

### 配置 `.env`

```bash
cp .env.example .env
```

常见配置示例：

```bash
# LLM
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=qwen-plus

# 钱包
MNEMONIC_PHRASE=你的十二个单词助记词

# 风控参数
MIN_RISK_SCORE=50
MIN_LIQUIDITY_USD=10000
STOP_LOSS_PCT=15
TAKE_PROFIT_PCT=30
MAX_DAILY_TRADES=5
MAX_HOLDINGS=3
```

### 初始化

```bash
python -m cli.main init
```

### 从聊天开始

```bash
python -m cli.main chat
```

---

## 真实示例

以下示例已从 `doc/result.txt` 精简整理，反映的是当前项目真实输出。

### 1. CLI 帮助

```text
$ python -m cli.main --help

Commands:
  chat
  scan
  analyze
  status
  positions
  auto-invest
  balance
  set-wallet
  trade
  close
  monitor
  init
```

### 2. Chat 入口

```text
$ python -m cli.main chat

Solana Meme Trading Agent
Talk naturally. Try things like:
  - scan hot Solana memes
  - analyze this token 7xKX...
  - buy BONK with 0.05 SOL
  - sell position abc123
  - show my portfolio status
  - auto invest 0.01 SOL
```

### 3. Auto-invest 示例

```text
You: auto invest 0.01 SOL
Intent: Auto-invest with budget 0.01 SOL (~1.50 USDT)

Found 4 qualified tokens

Investment Plan
1. Rosie  Allocation: $0.06 USDT ~= 0.0004 SOL
2. Punch  Allocation: $0.17 USDT ~= 0.0011 SOL
3. TRUMP  Allocation: $1.27 USDT ~= 0.0085 SOL
Total: $1.50 USDT
```

这个例子很重要，因为它说明当前实现已经不是平均分配，而是会把更多预算分给高分、流动性更好的代币。

### 4. Monitor 策略摘要

```text
$ python -m cli.main monitor

Initial stop loss: -15.0%
Partial take profit: +15.0% (sell 50%)
Breakeven promotion: enabled after partial TP
Trailing stop: 10.0% on remainder
Max hold: 24h
```

---

## 聊天体验

推荐优先使用 `chat` 模式。

你可以直接说：

```text
scan hot Solana memes
analyze this token 7xKX...
buy BONK with 0.05 SOL
show my portfolio status
sell position abc123
auto invest 0.01 SOL
```

一次买入请求的真实流程：

1. 将输入识别为交易意图
2. 如果输入的是 symbol，会先尝试解析成 Solana mint
3. 执行决策分析
4. 展示评分、流动性和建议
5. 只有确认后才继续执行交易

如果 symbol 不明确、冲突或无法安全解析，系统会直接中止，而不是继续拿错误代币地址做分析。

---

## CLI 命令

| 命令 | 作用 | 示例 |
|---|---|---|
| `chat` | 启动自然语言交易聊天 | `python -m cli.main chat` |
| `init` | 检查配置、skills、钱包和本地状态 | `python -m cli.main init` |
| `scan` | 扫描并总结热门代币 | `python -m cli.main scan --limit 5` |
| `analyze` | 从命令行分析指定合约 | `python -m cli.main analyze <contract>` |
| `status` | 查看钱包状态、PnL、余额和 monitor 策略摘要 | `python -m cli.main status` |
| `positions` | 查看当前持仓和策略化退出信息 | `python -m cli.main positions` |
| `auto-invest` | 基于热门代币生成加权投资计划 | `python -m cli.main auto-invest --budget 10 --dry-run` |
| `balance` | 查询钱包余额 | `python -m cli.main balance` |
| `set-wallet` | 将钱包地址写入本地状态 | `python -m cli.main set-wallet <address>` |
| `trade` | 手动准备一笔 swap | `python -m cli.main trade --from SOL --to <token> --amount 0.1` |
| `close` | 按持仓 ID 平仓 | `python -m cli.main close <position_id>` |
| `monitor` | 监控持仓并在动态条件触发时自动卖出 | `python -m cli.main monitor --interval 60` |

### 需要注意

- `chat` 支持 `buy BONK with 0.05 SOL` 这类 symbol 买入。
- `analyze` 和 `trade` 这类显式 CLI 命令仍然更适合直接传合约地址。
- `auto-invest` 的 CLI 模式接收 `USDT` 预算；聊天模式可以理解 `SOL` 或 `USDT` 表达。
- `positions` 和卖出预览会显示策略化退出文本，如 `initial SL`、`partial TP`、`breakeven armed`、`trailing`。
- `history` 会显示退出原因，如 `partial take profit`、`trailing stop`、`stop loss`、`time stop`。

---

## 风控与退出策略

项目最初只有固定止盈止损，但当前 monitor 已经升级为动态退出机制。

### 组合级规则

| 规则 | 默认值 |
|---|---|
| 单笔最大仓位 | 组合价值的 5% |
| 每日最大交易数 | 5 |
| 最大同时持仓数 | 3 |
| 最低流动性 | $10,000 |
| 最低风险分 | 50 / 100 |

### 仓位级退出策略

| 阶段 | 默认行为 |
|---|---|
| 初始止损 | -15% |
| 首次止盈事件 | +15% 部分止盈，卖出 50% |
| 部分止盈后 | 止损抬到保本 |
| 剩余仓位 | 10% trailing stop |
| 时间止损 | 最长持有 24h |

说明：买入执行回执里仍然可能显示初始写入的固定 `Stop Loss / Take Profit` 价格，但仓位进入 monitor 后，实际退出逻辑会按上面的动态策略执行。

`agent/decision.py` 里的分析器重点评估：

- 安全性：蜜罐、税率、权限风险
- 流动性：LP 深度和最低阈值
- 活动度：近期买卖人数和成交量

`agent/monitor.py` 目前还支持：

- `exit_pending` 防重复触发
- 基于真实订单详情的卖后对账
- 程序重启后的 pending exit 恢复
- 退出原因持久化到 state 和 trade history

---

## 系统结构

```text
自然语言聊天 / CLI
        ↓
意图识别 + LLM 回退分类
        ↓
Solana meme 专用系统提示词 + 对话记忆
        ↓
决策分析器（安全 + 流动性 + 活动度）
        ↓
基于 Bitget 的市场数据与执行工具
        ↓
状态持久化 + monitor + 交易历史归因
```

关键文件：

- `cli/main.py` - 聊天循环、CLI 命令、用户交互流程
- `agent/core.py` - LangGraph / LangChain Agent 与交易工具编排
- `agent/prompts.py` - Solana meme 专用系统提示词
- `agent/capabilities.py` - 支持的能力目录与聊天示例
- `agent/decision.py` - 交易前分析与 symbol 解析
- `agent/allocation.py` - auto-invest 加权分配
- `agent/state.py` - 持仓、交易历史、记忆、对话历史
- `agent/monitor.py` - 动态退出监控、对账、恢复
- `agent/position_display.py` - 策略化显示文本与退出原因标签

---

## 项目结构

```text
BestTradeAgent/
├── agent/
│   ├── allocation.py
│   ├── capabilities.py
│   ├── config.py
│   ├── core.py
│   ├── decision.py
│   ├── monitor.py
│   ├── position_display.py
│   ├── prompts.py
│   └── state.py
├── cli/
│   └── main.py
├── skills/
│   ├── bitget-wallet-skill/
│   ├── meme-scanner-skill/
│   ├── risk-scorer-skill/
│   └── trading-strategy-skill/
├── tests/
│   ├── test_auto_invest_allocation.py
│   ├── test_chat_features.py
│   ├── test_config.py
│   ├── test_monitor_strategy.py
│   └── test_token_resolution.py
├── doc/
│   ├── DEMAND.md
│   ├── README_CN.md
└── README.md
```

---

## 安全说明

- 这个项目在你确认后可以执行真实交易。
- symbol 解析是尽力而为，最稳妥的输入仍然是明确的 mint 地址。
- 请妥善保管助记词；钱包操作会依赖它。
- 对于 meme 币，尤其要警惕同名代币和伪装项目。

---

## 黑客松说明

本仓库最初面向 Solana Agent Economy Hackathon 的 Bitget Wallet 赛道构建。

---

## 许可

MIT，详见 `../LICENSE`。
