"""
Intent Recognition Module - 自然语言意图识别

识别用户的交易意图并转换为结构化命令
"""

import re
from enum import Enum
from typing import Dict, Optional, Any
from dataclasses import dataclass


class IntentType(Enum):
    """意图类型"""

    BUY = "buy"  # 买入
    SELL = "sell"  # 卖出
    SCAN = "scan"  # 扫描
    ANALYZE = "analyze"  # 分析
    STATUS = "status"  # 查看状态
    POSITIONS = "positions"  # 查看持仓
    HISTORY = "history"  # 查看历史
    AUTO_INVEST = "auto_invest"  # 自动投资
    HELP = "help"  # 帮助
    UNKNOWN = "unknown"  # 未知


@dataclass
class Intent:
    """识别到的意图"""

    type: IntentType
    params: Dict[str, Any]
    confidence: float
    raw_input: str


class IntentRecognizer:
    """意图识别器"""

    # 买入关键词模式（排除 auto invest）
    BUY_PATTERNS = [
        r"(?<!auto\s)(?:买|buy|purchase|get).*?(?:代币|token|币)",
        r"(?<!auto\s)(?:买入|buy).*?(\w+).*?(?:用|with|for).*?(\d+(?:\.\d+)?)",
        r"(?<!auto\s)(?:我想买|i want to buy)\s+(\w+)",
        r"(?<!auto\s)(?:投资|invest).*?(?:in|到)?\s*(\w+)",
    ]

    # 卖出关键词模式
    SELL_PATTERNS = [
        r"(?:卖|sell).*?(?:代币|token|币|position)",
        r"(?:卖出|sell).*?(position\s+)?(\w+)",
        r"(?:平仓|close).*?(?:position|仓位)?",
        r"(?:我想卖|i want to sell)\s+(\w+)",
    ]

    # 扫描关键词
    SCAN_PATTERNS = [
        r"^(?:scan|扫描)$",
        r"(?:扫描|scan|找|find|发现|discover).*?(?:趋势|trending|热门|hot|新币|new)",
        r"(?:有什么|what are).*?(?:新币|new tokens|机会|opportunities)",
        r"(?:看看|show me).*?(?:市场|market|行情)",
    ]

    # 分析关键词
    ANALYZE_PATTERNS = [
        r"(?:分析|analyze|评估|evaluate).*?(?:代币|token|币)?\s*(\w+)",
        r"(?:看看|check|how is).*?(?:这个|this)?\s*(\w+)",
        r"(?:\w+)\s+(?:怎么样|how is|analysis)",
    ]

    # 状态关键词
    STATUS_PATTERNS = [
        r"^(?:状态|status)$",
        r"(?:状态|status|情况|portfolio|余额|balance)",
        r"(?:我的|my).*?(?:账户|account|钱|money)",
        r"(?:查看|show).*?(?:状态|status)",
    ]

    # 持仓关键词
    POSITION_PATTERNS = [
        r"^(?:持仓|positions|position|positons)$",
        r"(?:持仓|positions|holding|仓位)",
        r"(?:我买了|i bought|我持有|i hold).+?",
        r"(?:查看|show).*?(?:持仓|positions)",
    ]

    # 历史关键词
    HISTORY_PATTERNS = [
        r"^(?:历史|history|trades)$",
        r"(?:历史|history|记录|records|交易记录|trades)",
        r"(?:我交易|i traded|我之前|my past).+?",
    ]

    # 自动投资关键词（优先级最高，需要放在最前面检查）
    AUTO_PATTERNS = [
        r"(?:auto\s+invest|自动投资|自动买入).*?(?:with|用|预算|budget)?\s*(\d+(?:\.\d+)?)?\s*(?:usdt|sol|usd|u)?",
        r"(?:auto|自动).*?(?:invest|投资).*?(?:with|用|预算)?\s*(\d+(?:\.\d+)?)?",
        r"(?:帮我|help me).*?(?:自动投资|auto\s+invest)",
        r"(?:智能|smart).*?(?:投资|invest)",
    ]

    # 帮助关键词
    HELP_PATTERNS = [
        r"(?:帮助|help|怎么用|how to use|指南|guide)",
        r"(?:什么|what).*?(?:能做|can do|功能|features)",
    ]

    def __init__(self):
        self.patterns = {
            IntentType.BUY: self.BUY_PATTERNS,
            IntentType.SELL: self.SELL_PATTERNS,
            IntentType.SCAN: self.SCAN_PATTERNS,
            IntentType.ANALYZE: self.ANALYZE_PATTERNS,
            IntentType.STATUS: self.STATUS_PATTERNS,
            IntentType.POSITIONS: self.POSITION_PATTERNS,
            IntentType.HISTORY: self.HISTORY_PATTERNS,
            IntentType.AUTO_INVEST: self.AUTO_PATTERNS,
            IntentType.HELP: self.HELP_PATTERNS,
        }

    def recognize(self, user_input: str) -> Intent:
        """
        识别用户意图

        Args:
            user_input: 用户输入的文本

        Returns:
            Intent 对象
        """
        text = user_input.strip()
        while text.endswith("/"):
            text = text[:-1].rstrip()

        typo_map = {
            "positons": "positions",
            "postions": "positions",
            "stats": "status",
        }
        lowered = text.lower()
        if lowered in typo_map:
            text = typo_map[lowered]

        # 🔴 优先级 1: 先检查 AUTO_INVEST（避免被 BUY 匹配）
        for pattern in self.AUTO_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                params = self._extract_auto_params(text, match)
                return Intent(
                    type=IntentType.AUTO_INVEST, params=params, confidence=0.9, raw_input=user_input
                )

        # 🟡 优先级 2: 检查其他意图
        priority_order = [
            IntentType.HELP,
            IntentType.STATUS,
            IntentType.POSITIONS,
            IntentType.HISTORY,
            IntentType.SCAN,
            IntentType.ANALYZE,
            IntentType.SELL,
            IntentType.BUY,
        ]

        for intent_type in priority_order:
            patterns = self.patterns.get(intent_type, [])
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    params = self._extract_params(intent_type, text, match)
                    return Intent(
                        type=intent_type, params=params, confidence=0.8, raw_input=user_input
                    )

        # 如果没有匹配到任何模式，返回 UNKNOWN
        return Intent(type=IntentType.UNKNOWN, params={}, confidence=0.0, raw_input=user_input)

    def _extract_auto_params(self, text: str, match) -> Dict[str, Any]:
        """提取自动投资参数"""
        params = {}

        # 尝试提取预算金额
        amount_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:usdt|sol|usd|刀 |u|u 刀)?", text, re.IGNORECASE
        )
        if amount_match:
            amount = float(amount_match.group(1))
            # 判断是 SOL 还是 USDT
            if "sol" in text.lower():
                params["budget_sol"] = amount
                params["budget_usd"] = amount * 150  # 估算
            else:
                params["budget_usd"] = amount
                params["budget_sol"] = amount / 150  # 估算
        else:
            # 默认预算
            params["budget_usd"] = 10
            params["budget_sol"] = 10 / 150

        return params

    def _extract_params(self, intent_type: IntentType, text: str, match) -> Dict[str, Any]:
        """提取参数"""
        params = {}

        if intent_type == IntentType.BUY:
            # 尝试提取代币合约和金额
            params.update(self._extract_buy_params(text))

        elif intent_type == IntentType.SELL:
            # 尝试提取仓位ID或代币
            params.update(self._extract_sell_params(text))

        elif intent_type == IntentType.ANALYZE:
            # 提取代币合约
            token = self._extract_token_contract(text)
            if token:
                params["token"] = token

        elif intent_type == IntentType.SCAN:
            # 提取数量限制
            limit = self._extract_number(text, default=5)
            params["limit"] = limit

        elif intent_type == IntentType.AUTO_INVEST:
            # 提取预算
            budget = self._extract_budget(text)
            params["budget"] = budget

        return params

    def _extract_buy_params(self, text: str) -> Dict[str, Any]:
        """提取买入参数"""
        params = {}

        # 尝试匹配 "buy <token> with <amount> SOL"
        buy_match = re.search(
            r"(?:buy|买|买入)\s+(\w+)\s+(?:with|用|for)\s+(\d+(?:\.\d+)?)\s*(?:sol|SOL)?",
            text,
            re.IGNORECASE,
        )
        if buy_match:
            params["token"] = buy_match.group(1)
            params["amount_sol"] = float(buy_match.group(2))
            return params

        # 尝试匹配 "invest <amount> in <token>"
        invest_match = re.search(
            r"(?:invest|投资)\s+(\d+(?:\.\d+)?)\s*(?:sol|SOL)?\s+(?:in|到|买)\s+(\w+)",
            text,
            re.IGNORECASE,
        )
        if invest_match:
            params["amount_sol"] = float(invest_match.group(1))
            params["token"] = invest_match.group(2)
            return params

        # 尝试匹配 "buy <token>"
        simple_match = re.search(r"(?:buy|买|买入)\s+(\w+)", text, re.IGNORECASE)
        if simple_match:
            params["token"] = simple_match.group(1)
            # 尝试在后面找金额
            amount_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sol|SOL)", text, re.IGNORECASE)
            if amount_match:
                params["amount_sol"] = float(amount_match.group(1))

        return params

    def _extract_sell_params(self, text: str) -> Dict[str, Any]:
        """提取卖出参数"""
        params = {}

        # 匹配 "sell position <id>"
        position_match = re.search(
            r"(?:sell|卖|卖出)\s+(?:position|仓位|持仓)?\s*(\w+)", text, re.IGNORECASE
        )
        if position_match:
            params["position_id"] = position_match.group(1)
            return params

        # 匹配 "close position"
        close_match = re.search(
            r"(?:close|平仓).*?(?:position|仓位|持仓)?\s*(\w+)?", text, re.IGNORECASE
        )
        if close_match and close_match.group(1):
            params["position_id"] = close_match.group(1)

        return params

    def _extract_token_contract(self, text: str) -> Optional[str]:
        """提取代币合约地址"""
        # Solana 合约地址通常是 base58 编码，44字符
        patterns = [
            r"[A-HJ-NP-Za-km-z1-9]{32,44}",  # Base58 地址
            r"0x[a-fA-F0-9]{40}",  # EVM 地址
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        # 如果没有找到地址，尝试提取最后一个单词作为代币符号
        words = text.split()
        if len(words) > 0:
            return words[-1].strip()

        return None

    def _extract_number(self, text: str, default: int = 5) -> int:
        """提取数字"""
        match = re.search(r"(\d+)\s*(?:个|tokens?)?", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return default

    def _extract_budget(self, text: str) -> float:
        """提取预算"""
        # 匹配 "<number> USDT/SOL/USD"
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:usdt|USDT|sol|SOL|usd|USD)?", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 10.0  # 默认预算


def get_intent_description(intent: Intent) -> str:
    """Get human-readable intent description."""
    if intent.type == IntentType.AUTO_INVEST:
        budget_sol = intent.params.get("budget_sol")
        budget_usd = intent.params.get("budget_usd")
        budget = intent.params.get("budget")

        if budget_sol is not None:
            sol_text = f"{float(budget_sol):g} SOL"
            if budget_usd is not None:
                return f"Auto-invest with budget {sol_text} (~{float(budget_usd):.2f} USDT)"
            return f"Auto-invest with budget {sol_text}"

        if budget_usd is not None:
            return f"Auto-invest with budget {float(budget_usd):.2f} USDT"

        if budget is not None:
            return f"Auto-invest with budget {float(budget):g} USDT"

    descriptions = {
        IntentType.BUY: f"Buy {intent.params.get('token', 'token')} with {intent.params.get('amount_sol', '?')} SOL",
        IntentType.SELL: f"Sell position {intent.params.get('position_id', '?')}",
        IntentType.SCAN: f"Scan top {intent.params.get('limit', 5)} tokens",
        IntentType.ANALYZE: f"Analyze token {intent.params.get('token', '?')}",
        IntentType.STATUS: "Show portfolio status",
        IntentType.POSITIONS: "Show open positions",
        IntentType.HISTORY: "Show trade history",
        IntentType.AUTO_INVEST: "Auto-invest",
        IntentType.HELP: "Show help",
        IntentType.UNKNOWN: "Unknown intent, falling back to chat",
    }
    return descriptions.get(intent.type, "Unknown action")
