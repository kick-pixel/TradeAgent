"""
Simple Position Monitor - 极简持仓监控

自动监控持仓，触发止盈/止损/时间止损时自动卖出
"""

import asyncio
import json
import subprocess
import sys
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from agent.state import Position, PositionStatus, get_state, save_state
from agent.config import config
from agent.wallet import get_wallet_manager


class SimplePositionMonitor:
    """极简持仓监控器"""

    def __init__(self):
        self.check_interval = 60  # 每60秒检查一次
        self.running = False
        self.script_path = self._get_bitget_script_path()

    def _get_bitget_script_path(self) -> str:
        """获取 Bitget API 脚本路径"""
        return str(
            Path(__file__).parent.parent
            / "skills"
            / "bitget-wallet-skill"
            / "scripts"
            / "bitget_agent_api.py"
        )

    async def start(self):
        """启动监控循环"""
        self.running = True
        print("🚀 持仓监控已启动...")
        print(f"⏱️  检查间隔: {self.check_interval}秒")
        print(
            f"🎯 止盈: +{config.trading.take_profit_pct}% | 止损: -{config.trading.stop_loss_pct}%"
        )
        print(f"⏰ 最大持仓时间: {config.trading.max_hold_hours}小时\n")

        while self.running:
            try:
                await self.check_all_positions()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ 监控错误: {e}")
                await asyncio.sleep(10)

    async def check_all_positions(self):
        """检查所有持仓"""
        state = get_state()

        if not state.open_positions:
            return

        print(
            f"\n📊 [{datetime.now().strftime('%H:%M:%S')}] 检查 {len(state.open_positions)} 个持仓..."
        )

        for position in state.open_positions:
            should_sell, reason = await self.evaluate_position(position)

            if should_sell:
                print(f"⚡ 触发卖出: {position.token_symbol} - {reason}")
                success = await self.execute_sell(position)

                if success:
                    print(f"✅ 卖出成功: {position.token_symbol}")
                else:
                    print(f"❌ 卖出失败: {position.token_symbol}")
            else:
                # 显示监控信息
                current_price = await self.get_token_price(position.token_contract)
                if current_price:
                    pnl_pct = (
                        (current_price - float(position.entry_price))
                        / float(position.entry_price)
                        * 100
                    )
                    hold_hours = position.hold_duration_hours
                    print(
                        f"📈 {position.token_symbol}: ${current_price:.8f} ({pnl_pct:+.1f}%) | 持仓: {hold_hours:.1f}h"
                    )

        save_state(state)

    async def evaluate_position(self, position: Position) -> Tuple[bool, str]:
        """
        评估是否该卖出

        返回: (should_sell, reason)
        """
        # 1. 获取当前价格
        current_price = await self.get_token_price(position.token_contract)
        if current_price is None:
            return False, "无法获取价格"

        entry_price = float(position.entry_price)

        # 2. 检查止盈
        if position.take_profit_price and current_price >= float(position.take_profit_price):
            return True, f"止盈触发 (目标: ${float(position.take_profit_price):.8f})"

        # 3. 检查止损
        if position.stop_loss_price and current_price <= float(position.stop_loss_price):
            return True, f"止损触发 (目标: ${float(position.stop_loss_price):.8f})"

        # 4. 检查持仓时间
        hold_hours = position.hold_duration_hours
        if hold_hours >= config.trading.max_hold_hours:
            return True, f"时间止损 (持有{hold_hours:.1f}小时)"

        # 5. 未触发任何条件
        return False, "监控中"

    async def get_token_price(self, contract: str) -> Optional[float]:
        """获取代币当前价格"""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "token-price",
                "--chain",
                "sol",
                "--contract",
                contract,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("status") == 0 and data.get("data"):
                    return float(data["data"].get("price", 0))

            return None

        except Exception as e:
            print(f"获取价格失败: {e}")
            return None

    async def execute_sell(self, position: Position) -> bool:
        """执行卖出"""
        try:
            wm = get_wallet_manager()
            if not wm.has_mnemonic:
                print("错误: 未配置钱包")
                return False

            address = wm.get_solana_address()

            # 1. 获取卖出报价 (卖回 SOL)
            quote_result = await self._get_sell_quote(position, address)
            if not quote_result:
                return False

            market = quote_result["market"]
            protocol = quote_result["protocol"]
            out_amount = quote_result["out_amount"]

            print(f"💰 预计获得: {out_amount} SOL")

            # 2. 确认订单
            order_id = await self._confirm_sell_order(position, address, market, protocol)
            if not order_id:
                return False

            # 3. 执行签名和发送
            success = await self._sign_and_send_sell(position, address, order_id, market, protocol)

            if success:
                # 更新仓位状态
                await self._update_position_after_sell(position, out_amount)
                return True

            return False

        except Exception as e:
            print(f"执行卖出错误: {e}")
            return False

    async def _get_sell_quote(self, position: Position, address: str) -> Optional[dict]:
        """获取卖出报价"""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "quote",
                "--from-chain",
                "sol",
                "--from-contract",
                position.token_contract,
                "--from-symbol",
                position.token_symbol,
                "--from-amount",
                str(float(position.entry_amount)),
                "--to-chain",
                "sol",
                "--to-contract",
                "",
                "--to-symbol",
                "SOL",
                "--from-address",
                address,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                print(f"获取报价失败: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            if data.get("error_code", 0) != 0:
                print(f"报价错误: {data.get('msg')}")
                return None

            # 获取第一个市场结果
            quote_result = data["data"]["quoteResults"][0]
            return {
                "market": quote_result["market"]["id"],
                "protocol": quote_result["market"]["protocol"],
                "out_amount": quote_result["outAmount"],
            }

        except Exception as e:
            print(f"获取报价错误: {e}")
            return None

    async def _confirm_sell_order(
        self, position: Position, address: str, market: str, protocol: str
    ) -> Optional[str]:
        """确认卖出订单"""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "confirm",
                "--from-chain",
                "sol",
                "--from-contract",
                position.token_contract,
                "--from-symbol",
                position.token_symbol,
                "--from-amount",
                str(float(position.entry_amount)),
                "--to-chain",
                "sol",
                "--to-contract",
                "",
                "--to-symbol",
                "SOL",
                "--from-address",
                address,
                "--to-address",
                address,
                "--market",
                market,
                "--protocol",
                protocol,
                "--slippage",
                str(config.trading.default_slippage),
                "--feature",
                "user_gas",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                print(f"确认订单失败: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            if data.get("error_code", 0) != 0:
                print(f"确认错误: {data.get('msg')}")
                return None

            return data["data"]["orderId"]

        except Exception as e:
            print(f"确认订单错误: {e}")
            return None

    async def _sign_and_send_sell(
        self,
        position: Position,
        address: str,
        order_id: str,
        market: str,
        protocol: str,
    ) -> bool:
        """签名并发送卖出交易"""
        try:
            # 派生私钥
            wm = get_wallet_manager()
            _, private_key_sol = wm.derive_solana_keypair()

            # 调用 order_make_sign_send.py
            script_path = (
                Path(__file__).parent.parent
                / "skills"
                / "bitget-wallet-skill"
                / "scripts"
                / "order_make_sign_send.py"
            )

            cmd = [
                sys.executable,
                str(script_path),
                "--private-key-sol",
                private_key_sol,
                "--from-address",
                address,
                "--to-address",
                address,
                "--order-id",
                order_id,
                "--from-chain",
                "sol",
                "--from-contract",
                position.token_contract,
                "--from-symbol",
                position.token_symbol,
                "--to-chain",
                "sol",
                "--to-contract",
                "",
                "--to-symbol",
                "SOL",
                "--from-amount",
                str(float(position.entry_amount)),
                "--slippage",
                str(config.trading.default_slippage),
                "--market",
                market,
                "--protocol",
                protocol,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # 清除私钥
            private_key_sol = None

            if result.returncode != 0:
                print(f"交易失败: {result.stderr}")
                return False

            # 解析结果
            data = json.loads(result.stdout)
            return data.get("status") == 0

        except Exception as e:
            print(f"签名发送错误: {e}")
            return False

    async def _update_position_after_sell(self, position: Position, out_amount: str):
        """卖出后更新仓位状态"""
        try:
            state = get_state()

            # 找到并更新仓位
            for p in state.positions:
                if p.id == position.id:
                    p.status = PositionStatus.CLOSED
                    p.exit_price = Decimal(str(out_amount)) / p.entry_amount
                    p.exit_amount = p.entry_amount
                    p.exit_value_usd = Decimal(str(out_amount)) * await self._get_sol_price()
                    p.exit_time = datetime.utcnow()

                    # 记录交易
                    from agent.state import Trade, TradeAction

                    trade = Trade(
                        action=TradeAction.SELL,
                        token_symbol=p.token_symbol,
                        token_contract=p.token_contract,
                        amount=p.entry_amount,
                        price=p.exit_price,
                        value_usd=p.exit_value_usd,
                        position_id=p.id,
                    )
                    state.record_trade(trade)

                    # 显示盈亏
                    pnl = p.pnl_usd
                    pnl_pct = p.pnl_pct
                    if pnl and pnl_pct:
                        emoji = "🟢" if pnl > 0 else "🔴"
                        print(f"{emoji} 盈亏: ${float(pnl):.2f} ({float(pnl_pct):.1f}%)")

                    break

            save_state(state)

        except Exception as e:
            print(f"更新仓位错误: {e}")

    async def _get_sol_price(self) -> Decimal:
        """获取 SOL 当前价格"""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "token-price",
                "--chain",
                "sol",
                "--contract",
                "",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data.get("status") == 0 and data.get("data"):
                    return Decimal(str(data["data"].get("price", "150")))

            return Decimal("150")  # 默认值

        except:
            return Decimal("150")

    def stop(self):
        """停止监控"""
        self.running = False
        print("\n🛑 监控已停止")


# 便捷函数
async def run_monitor_once():
    """运行一次监控"""
    monitor = SimplePositionMonitor()
    await monitor.check_all_positions()


def run_monitor_continuous():
    """持续运行监控"""
    monitor = SimplePositionMonitor()

    try:
        asyncio.run(monitor.start())
    except KeyboardInterrupt:
        monitor.stop()
