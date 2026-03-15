"""
Decision Analysis Module - 交易决策分析模块

在交易执行前自动进行全面的分析和决策支持
"""

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime

from agent.config import config
from agent.state import get_state


@dataclass
class AnalysisResult:
    """分析结果"""

    token_contract: str
    token_symbol: str

    # 安全分析
    security_score: int
    security_risks: List[str]
    is_honeypot: bool
    buy_tax: float
    sell_tax: float

    # 流动性分析
    liquidity_usd: float
    liquidity_score: int

    # 交易活动
    volume_24h: float
    buyers_24h: int
    sellers_24h: int
    buy_ratio: float

    # 价格分析
    current_price: float
    price_change_24h: float

    # 综合评分
    total_score: int
    risk_level: str  # LOW, MEDIUM, HIGH, VERY_HIGH

    # 决策建议
    recommendation: str  # BUY, AVOID, WATCH
    confidence: float
    reasons: List[str]


class DecisionAnalyzer:
    """决策分析器"""

    def __init__(self):
        self.script_path = self._get_bitget_script_path()
        self.min_score = config.trading.min_risk_score
        self.min_liquidity = config.trading.min_liquidity_usd

    def _get_bitget_script_path(self) -> str:
        """获取 Bitget API 脚本路径"""
        return str(
            Path(__file__).parent.parent
            / "skills"
            / "bitget-wallet-skill"
            / "scripts"
            / "bitget_agent_api.py"
        )

    def analyze_token(self, token_contract: str, chain: str = "sol") -> Optional[AnalysisResult]:
        """
        分析代币，返回综合评估结果

        Args:
            token_contract: 代币合约地址
            chain: 链代码

        Returns:
            AnalysisResult 或 None（如果分析失败）
        """
        print(f"[SEARCH] Analyzing token: {token_contract}")

        # 1. 安全分析
        security_data = self._get_security_data(token_contract, chain)
        if not security_data:
            print("[ERROR] Unable to get security data")
            return None

        # 2. 流动性分析
        liquidity_data = self._get_liquidity_data(token_contract, chain)

        # 3. 交易数据分析
        tx_data = self._get_tx_data(token_contract, chain)

        # 4. 价格数据
        price_data = self._get_price_data(token_contract, chain)

        # 5. 计算综合评分
        result = self._calculate_analysis(
            token_contract, security_data, liquidity_data, tx_data, price_data
        )

        return result

    def _get_security_data(self, contract: str, chain: str) -> Optional[Dict]:
        """获取安全数据"""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "security",
                "--chain",
                chain,
                "--contract",
                contract,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("status") == 0 and data.get("data"):
                    items = data["data"]
                    if isinstance(items, list) and len(items) > 0:
                        return items[0]
                    elif isinstance(items, dict):
                        return items

            return None
        except Exception as e:
            print(f"Error getting security data: {e}")
            return None

    def _get_liquidity_data(self, contract: str, chain: str) -> Optional[Dict]:
        """获取流动性数据"""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "liquidity",
                "--chain",
                chain,
                "--contract",
                contract,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("status") == 0 and data.get("data"):
                    return data["data"]

            return None
        except Exception as e:
            print(f"Error getting liquidity data: {e}")
            return None

    def _get_tx_data(self, contract: str, chain: str) -> Optional[Dict]:
        """获取交易数据"""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "tx-info",
                "--chain",
                chain,
                "--contract",
                contract,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("status") == 0 and data.get("data"):
                    return data["data"]

            return None
        except Exception as e:
            print(f"Error getting transaction data: {e}")
            return None

    def _get_price_data(self, contract: str, chain: str) -> Optional[Dict]:
        """获取价格数据"""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "token-price",
                "--chain",
                chain,
                "--contract",
                contract,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                # token-price 直接返回价格数据，没有 status 字段
                if data.get("price") is not None:
                    return data

            return None
        except Exception as e:
            print(f"Error getting price data: {e}")
            return None

    def _calculate_analysis(
        self,
        token_contract: str,
        security_data: Dict,
        liquidity_data: Optional[Dict],
        tx_data: Optional[Dict],
        price_data: Optional[Dict],
    ) -> AnalysisResult:
        """计算综合分析结果"""

        # 提取安全数据
        is_honeypot = security_data.get("isHoneypot", False)
        buy_tax = float(security_data.get("buyTax", 0) or 0)
        sell_tax = float(security_data.get("sellTax", 0) or 0)
        is_open_source = security_data.get("isOpenSource", False)
        freeze_auth = security_data.get("freezeAuth", False)
        mint_auth = security_data.get("mintAuth", False)
        high_risk = security_data.get("highRisk", False)

        # 计算安全评分 (0-100)
        security_score = self._calculate_security_score(
            is_honeypot, buy_tax, sell_tax, is_open_source, freeze_auth, mint_auth, high_risk
        )

        # 提取流动性数据
        liquidity_usd = 0
        liquidity_score = 0
        if liquidity_data:
            liquidity_usd = float(liquidity_data.get("totalLpValue", 0))
            liquidity_score = self._calculate_liquidity_score(liquidity_usd)

        # 提取交易数据
        volume_24h = 0
        buyers_24h = 0
        sellers_24h = 0
        buy_ratio = 0.5
        if tx_data:
            txn_info = tx_data.get("txn_info", {}).get("24h", {})
            volume_24h = float(txn_info.get("volume", 0))
            buyers_24h = int(txn_info.get("buyers", 0))
            sellers_24h = int(txn_info.get("sellers", 0))
            total = buyers_24h + sellers_24h
            if total > 0:
                buy_ratio = buyers_24h / total

        # 提取价格数据
        current_price = 0
        price_change_24h = 0
        token_symbol = "UNKNOWN"
        if price_data:
            current_price = float(price_data.get("price", 0))
            price_change_24h = float(price_data.get("change24h", 0) or 0)
            token_symbol = price_data.get("symbol", "UNKNOWN")
            print(f"[OK] Price data retrieved: {token_symbol} = ${current_price:.8f}")
        else:
            print("[WARN] Price data empty, using default values")

        # 计算活动评分
        activity_score = self._calculate_activity_score(
            volume_24h, buyers_24h, sellers_24h, buy_ratio
        )

        # 综合评分 (加权)
        total_score = int(
            security_score * 0.4  # 安全 40%
            + liquidity_score * 0.3  # 流动性 30%
            + activity_score * 0.3  # 活动 30%
        )

        # 确定风险等级
        risk_level = self._get_risk_level(total_score)

        # 生成风险列表
        security_risks = self._identify_security_risks(
            is_honeypot, buy_tax, sell_tax, high_risk, freeze_auth, mint_auth
        )

        # 生成决策建议
        recommendation, confidence, reasons = self._generate_recommendation(
            total_score, risk_level, security_risks, liquidity_usd, price_change_24h, buy_ratio
        )

        return AnalysisResult(
            token_contract=token_contract,
            token_symbol=token_symbol,
            security_score=security_score,
            security_risks=security_risks,
            is_honeypot=is_honeypot,
            buy_tax=buy_tax,
            sell_tax=sell_tax,
            liquidity_usd=liquidity_usd,
            liquidity_score=liquidity_score,
            volume_24h=volume_24h,
            buyers_24h=buyers_24h,
            sellers_24h=sellers_24h,
            buy_ratio=buy_ratio,
            current_price=current_price,
            price_change_24h=price_change_24h,
            total_score=total_score,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence=confidence,
            reasons=reasons,
        )

    def _calculate_security_score(
        self,
        is_honeypot: bool,
        buy_tax: float,
        sell_tax: float,
        is_open_source: bool,
        freeze_auth: bool,
        mint_auth: bool,
        high_risk: bool,
    ) -> int:
        """计算安全评分"""
        if is_honeypot or high_risk:
            return 0

        score = 0

        # 无蜜罐 (30分)
        score += 30

        # 税率 (30分)
        if buy_tax == 0 and sell_tax == 0:
            score += 30
        elif buy_tax <= 5 and sell_tax <= 5:
            score += 25
        elif buy_tax <= 10 and sell_tax <= 10:
            score += 15
        else:
            score += 5

        # 开源 (20分)
        if is_open_source:
            score += 20

        # 权限 (20分)
        if not freeze_auth and not mint_auth:
            score += 20
        elif not freeze_auth or not mint_auth:
            score += 10

        return score

    def _calculate_liquidity_score(self, liquidity_usd: float) -> int:
        """计算流动性评分"""
        if liquidity_usd >= 1000000:  # $1M+
            return 100
        elif liquidity_usd >= 500000:  # $500K+
            return 80
        elif liquidity_usd >= 100000:  # $100K+
            return 60
        elif liquidity_usd >= 50000:  # $50K+
            return 40
        elif liquidity_usd >= 10000:  # $10K+
            return 20
        else:
            return 0

    def _calculate_activity_score(
        self, volume_24h: float, buyers: int, sellers: int, buy_ratio: float
    ) -> int:
        """计算活动评分"""
        score = 0

        # 交易量 (50分)
        if volume_24h >= 10000000:  # $10M+
            score += 50
        elif volume_24h >= 1000000:  # $1M+
            score += 40
        elif volume_24h >= 100000:  # $100K+
            score += 25
        elif volume_24h >= 10000:  # $10K+
            score += 10

        # 买卖比例 (30分)
        if buy_ratio >= 0.6:
            score += 30
        elif buy_ratio >= 0.5:
            score += 20
        elif buy_ratio >= 0.4:
            score += 10

        # 交易者数量 (20分)
        total = buyers + sellers
        if total >= 5000:
            score += 20
        elif total >= 1000:
            score += 15
        elif total >= 500:
            score += 10
        elif total >= 100:
            score += 5

        return score

    def _get_risk_level(self, score: int) -> str:
        """获取风险等级"""
        if score >= 80:
            return "LOW"
        elif score >= 60:
            return "MEDIUM"
        elif score >= 40:
            return "HIGH"
        else:
            return "VERY_HIGH"

    def _identify_security_risks(
        self,
        is_honeypot: bool,
        buy_tax: float,
        sell_tax: float,
        high_risk: bool,
        freeze_auth: bool,
        mint_auth: bool,
    ) -> List[str]:
        """识别安全风险"""
        risks = []

        if is_honeypot:
            risks.append("Honeypot contract - cannot sell")
        if high_risk:
            risks.append("High-risk flag detected")
        if buy_tax > 10 or sell_tax > 10:
            risks.append(f"High tax: buy {buy_tax}% / sell {sell_tax}%")
        elif buy_tax > 5 or sell_tax > 5:
            risks.append(f"Medium tax: buy {buy_tax}% / sell {sell_tax}%")
        if freeze_auth:
            risks.append("Freeze authority present - trading may be blocked")
        if mint_auth:
            risks.append("Mint authority present - supply may be inflated")

        return risks

    def _generate_recommendation(
        self,
        score: int,
        risk_level: str,
        security_risks: List[str],
        liquidity_usd: float,
        price_change: float,
        buy_ratio: float,
    ) -> tuple:
        """生成交易建议"""
        reasons = []

        # 基础判断
        if score >= 80 and not security_risks:
            recommendation = "BUY"
            confidence = 0.85
            reasons.append("Composite score is excellent")
        elif score >= 60:
            recommendation = "BUY"
            confidence = 0.65
            reasons.append("Composite score is good, but risk still exists")
        elif score >= 40:
            recommendation = "WATCH"
            confidence = 0.45
            reasons.append("Score is average; watch before acting")
        else:
            recommendation = "AVOID"
            confidence = 0.9
            reasons.append("Score is too low; risk is elevated")

        # 添加具体原因
        if liquidity_usd < config.trading.min_liquidity_usd:
            reasons.append(
                f"Liquidity too low: ${liquidity_usd:,.0f} < ${config.trading.min_liquidity_usd:,.0f}"
            )
            if recommendation == "BUY":
                recommendation = "WATCH"
                confidence = 0.4
        else:
            reasons.append(f"Liquidity is sufficient: ${liquidity_usd:,.0f}")

        if price_change > 0.5:  # +50%
            reasons.append(f"Large 24h price increase: +{price_change:.1%}")
        elif price_change < -0.3:  # -30%
            reasons.append(f"Large 24h price decrease: {price_change:.1%}")

        if buy_ratio >= 0.6:
            reasons.append(f"Buy pressure is strong: {buy_ratio:.0%} buyers")
        elif buy_ratio <= 0.4:
            reasons.append(f"Sell pressure is higher: {buy_ratio:.0%} buyers")

        if security_risks:
            reasons.extend(security_risks[:3])  # 最多显示3个风险
            recommendation = "AVOID"
            confidence = 0.95

        return recommendation, confidence, reasons

    def format_report(self, result: AnalysisResult) -> str:
        """格式化分析报告"""
        lines = [
            f"\n{'=' * 60}",
            f"[REPORT] Token Analysis: {result.token_symbol}",
            f"{'=' * 60}",
            f"",
            f"[CONTRACT] Address: {result.token_contract}",
            f"[PRICE] Current: ${result.current_price:.8f}",
            f"[CHANGE] 24h: {result.price_change_24h:+.2%}",
            f"",
            f"{'-' * 60}",
            f"[SECURITY] Score: {result.security_score}/100",
            f"   - Honeypot: {'[WARN] YES' if result.is_honeypot else '[OK] NO'}",
            f"   - Buy Tax: {result.buy_tax}%",
            f"   - Sell Tax: {result.sell_tax}%",
            f"",
            f"[LIQUIDITY] Score: {result.liquidity_score}/100",
            f"   - Liquidity: ${result.liquidity_usd:,.2f}",
            f"",
            f"[ACTIVITY] Score",
            f"   - 24h Volume: ${result.volume_24h:,.2f}",
            f"   - Buyers: {result.buyers_24h} | Sellers: {result.sellers_24h}",
            f"   - Buy Ratio: {result.buy_ratio:.1%}",
            f"",
            f"{'-' * 60}",
            f"[TOTAL] Score: {result.total_score}/100",
            f"[RISK] Level: {result.risk_level}",
            f"",
            f"[ADVICE] {'BUY' if result.recommendation == 'BUY' else 'AVOID' if result.recommendation == 'AVOID' else 'WATCH'}",
            f"[CONFIDENCE] {result.confidence:.0%}",
            f"",
            f"[REASONS]:",
        ]

        for reason in result.reasons:
            lines.append(f"   - {reason}")

        lines.extend([f"{'=' * 60}", ""])

        return "\n".join(lines)


def should_execute_buy(analysis: AnalysisResult) -> tuple[bool, str]:
    """
    判断是否应执行买入

    Returns:
        (should_buy, reason)
    """
    # 检查风险等级
    if analysis.risk_level == "VERY_HIGH":
        return False, "Risk level is too high"

    # 检查蜜罐
    if analysis.is_honeypot:
        return False, "Honeypot detected; selling may fail"

    # 检查综合评分
    if analysis.total_score < config.trading.min_risk_score:
        return (
            False,
            f"Composite score {analysis.total_score} is below minimum {config.trading.min_risk_score}",
        )

    # 检查流动性
    if analysis.liquidity_usd < config.trading.min_liquidity_usd:
        return (
            False,
            f"Liquidity ${analysis.liquidity_usd:,.0f} is below minimum ${config.trading.min_liquidity_usd:,.0f}",
        )

    # 检查建议
    if analysis.recommendation == "AVOID":
        return False, "Analysis recommends avoiding this buy"

    if analysis.recommendation == "WATCH":
        return False, "Analysis recommends watching only; risk is elevated"

    return True, "Analysis passed; buy is allowed"
