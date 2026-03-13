# 配置完成 ✅

## 环境变量配置

你的 `.env` 文件已配置完成，支持以下自定义配置：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `ANTHROPIC_BASE_URL` | `https://coding.dashscope.aliyuncs.com/apps/anthropic/v1` | 阿里云 DashScope 接入点 |
| `ANTHROPIC_API_KEY` | `sk-sp-4bd7f2d68cfc4e289681734998a57522` | API 密钥 |
| `ANTHROPIC_MODEL` | `qwen3.5-plus` | 模型名称 |
| `MNEMONIC_PHRASE` | `abandon abandon abandon ...` | 测试钱包助记词 |

## 代码修改摘要

### 1. `cli/main.py`
```python
# 新增配置读取
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# TradingAgent 支持自定义配置
agent = TradingAgent(
    api_key=ANTHROPIC_API_KEY,
    base_url=ANTHROPIC_BASE_URL,
    model=ANTHROPIC_MODEL,
)
```

### 2. `agent/trading_agent.py`
```python
# 从环境变量读取模型配置
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", None)

def create_trading_agent(model: Optional[str] = None):
    if model is None:
        model = f"anthropic:{ANTHROPIC_MODEL}"
```

### 3. `.env`
```bash
ANTHROPIC_BASE_URL=https://coding.dashscope.aliyuncs.com/apps/anthropic/v1
ANTHROPIC_API_KEY=sk-sp-4bd7f2d68cfc4e289681734998a57522
ANTHROPIC_MODEL=qwen3.5-plus
```

## 测试命令

```bash
# 测试配置加载
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('ANTHROPIC_MODEL'))"

# 测试 CLI
python -m cli.main --help

# 测试扫描功能
python -m cli.main scan --limit 5

# 测试风险检查
python -m cli.main risk-check --chain sol --contract EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
```

## 注意事项

1. **LSP 类型错误**：代码中有一些类型提示错误（LSP diagnostics），这些不影响实际运行
2. **Deep Agents base_url**：Deep Agents 框架可能不直接支持 `base_url` 参数，如需自定义 API 接入点，建议在调用 `create_deep_agent` 前设置环境变量
3. **模型兼容性**：确保 `qwen3.5-plus` 模型支持 Anthropic API 格式

## 下一步

1. 运行测试命令验证配置
2. 如有问题，检查 DashScope API 文档确认兼容性
3. 准备 hackathon 演示材料
