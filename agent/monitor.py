"""Simple position monitor with auto-sell rules."""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from agent.config import config
from agent.state import Position, PositionStatus, get_state, save_state
from agent.wallet import get_wallet_manager


@dataclass
class ExitAction:
    action: str
    reason: str
    sell_amount: Decimal


def build_monitor_strategy_summary() -> str:
    """Return a user-facing summary of the current monitor strategy."""
    partial_fraction_pct = config.trading.partial_take_profit_fraction * 100
    return (
        f"Initial stop loss: -{config.trading.stop_loss_pct}%\n"
        f"Partial take profit: +{config.trading.partial_take_profit_pct}% (sell {partial_fraction_pct:.0f}%)\n"
        "Breakeven promotion: enabled after partial TP\n"
        f"Trailing stop: {config.trading.trailing_stop_pct}% on remainder\n"
        f"Max hold: {config.trading.max_hold_hours}h"
    )


class SimplePositionMonitor:
    """Simple position monitor."""

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
        print("[MONITOR] Started")
        print(f"[MONITOR] Check interval: {self.check_interval}s")
        for line in build_monitor_strategy_summary().splitlines():
            print(f"[MONITOR] {line}")
        print()

        while self.running:
            try:
                await self.check_all_positions()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"[ERROR] Monitor error: {e}")
                await asyncio.sleep(10)

    async def check_all_positions(self):
        """检查所有持仓"""
        state = get_state()

        if not state.open_positions:
            return

        await self._recover_pending_positions(state)

        print(
            f"\n[CHECK {datetime.now().strftime('%H:%M:%S')}] Reviewing {len(state.open_positions)} open positions..."
        )

        for position in state.open_positions:
            exit_action = await self.evaluate_position(position)

            if exit_action:
                print(f"[TRIGGER] Sell {position.token_symbol} - {exit_action.reason}")
                success = await self.execute_sell(position, exit_action)

                if success:
                    print(f"[OK] Sell succeeded: {position.token_symbol}")
                else:
                    print(f"[FAIL] Sell failed: {position.token_symbol}")
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
                        f"[TRACK] {position.token_symbol}: ${current_price:.8f} ({pnl_pct:+.1f}%) | Hold: {hold_hours:.1f}h"
                    )

        save_state(state)

    async def evaluate_position(self, position: Position) -> Optional[ExitAction]:
        """Evaluate whether a position should be sold."""
        current_price = await self.get_token_price(position.token_contract)
        if current_price is None:
            return None

        self._update_dynamic_stops(position, current_price)
        action = self._determine_exit_action(position, current_price)
        if action:
            return action

        hold_hours = position.hold_duration_hours
        if hold_hours >= config.trading.max_hold_hours:
            return ExitAction(
                action="time_stop",
                reason=f"Time stop triggered (held {hold_hours:.1f}h)",
                sell_amount=position.active_amount,
            )

        return None

    def _determine_exit_action(
        self, position: Position, current_price: float
    ) -> Optional[ExitAction]:
        """Determine whether to do a partial or full exit."""
        if position.exit_pending:
            return None

        if (
            not position.partial_take_profit_taken
            and position.take_profit_price
            and current_price >= float(position.take_profit_price)
        ):
            sell_amount = position.active_amount * Decimal(
                str(config.trading.partial_take_profit_fraction)
            )
            return ExitAction(
                action="partial_take_profit",
                reason=f"Partial take-profit triggered (target: ${float(position.take_profit_price):.8f})",
                sell_amount=sell_amount,
            )

        if position.trailing_stop_price and current_price <= float(position.trailing_stop_price):
            return ExitAction(
                action="trailing_stop",
                reason=f"Trailing stop triggered (target: ${float(position.trailing_stop_price):.8f})",
                sell_amount=position.active_amount,
            )

        if position.stop_loss_price and current_price <= float(position.stop_loss_price):
            return ExitAction(
                action="stop_loss",
                reason=f"Stop-loss triggered (target: ${float(position.stop_loss_price):.8f})",
                sell_amount=position.active_amount,
            )

        return None

    def _apply_partial_take_profit(self, position: Position, current_price: float) -> None:
        """Apply post-partial-exit state updates."""
        sell_fraction = Decimal(str(config.trading.partial_take_profit_fraction))
        remaining_amount = position.active_amount * (Decimal("1") - sell_fraction)
        position.remaining_amount = remaining_amount
        position.partial_take_profit_taken = True
        position.stop_loss_price = position.entry_price
        highest_price = Decimal(str(current_price))
        position.highest_price = highest_price
        trailing_multiplier = Decimal(str(1 - config.trading.trailing_stop_pct / 100))
        position.trailing_stop_price = highest_price * trailing_multiplier

    def _update_dynamic_stops(self, position: Position, current_price: float) -> None:
        """Update peak and trailing stop after first profit lock-in."""
        current_price_decimal = Decimal(str(current_price))
        if position.highest_price is None or current_price_decimal > position.highest_price:
            position.highest_price = current_price_decimal

        if position.partial_take_profit_taken and position.highest_price is not None:
            trailing_multiplier = Decimal(str(1 - config.trading.trailing_stop_pct / 100))
            position.trailing_stop_price = position.highest_price * trailing_multiplier

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
            print(f"[ERROR] Failed to get price: {e}")
            return None

    async def execute_sell(self, position: Position, exit_action: ExitAction) -> bool:
        """执行卖出"""
        try:
            if position.exit_pending:
                print(f"[SKIP] Exit already pending for {position.token_symbol}")
                return False

            self._mark_exit_pending(position, True)
            wm = get_wallet_manager()
            if not wm.has_mnemonic:
                self._mark_exit_pending(position, False)
                print("[ERROR] Wallet mnemonic is not configured")
                return False

            address = wm.get_solana_address()

            # 1. 获取卖出报价 (卖回 SOL)
            quote_result = await self._get_sell_quote(position, address, exit_action.sell_amount)
            if not quote_result:
                self._mark_exit_pending(position, False)
                return False

            market = quote_result["market"]
            protocol = quote_result["protocol"]
            out_amount = quote_result["out_amount"]

            print(f"[QUOTE] Expected receive: {out_amount} SOL")

            # 2. 确认订单
            order_id = await self._confirm_sell_order(
                position, address, market, protocol, exit_action.sell_amount
            )
            if not order_id:
                self._mark_exit_pending(position, False)
                return False

            self._store_pending_execution(position, order_id, exit_action)

            # 3. 执行签名和发送
            send_result = await self._sign_and_send_sell(
                position, address, order_id, market, protocol, exit_action.sell_amount
            )

            if send_result.get("ok"):
                order_details = await self._get_order_details(order_id)
                reconciled = self._reconcile_execution_result(
                    fallback_out_amount=out_amount,
                    fallback_tx_id=send_result.get("tx_id", ""),
                    order_details=order_details,
                )
                await self._update_position_after_sell(
                    position,
                    str(reconciled["out_amount"]),
                    exit_action,
                    str(reconciled["tx_id"]),
                )
                return True

            self._mark_exit_pending(position, False)
            return False

        except Exception as e:
            self._mark_exit_pending(position, False)
            print(f"[ERROR] Sell execution error: {e}")
            return False

    def _mark_exit_pending(self, position: Position, pending: bool) -> None:
        """Persist exit pending state on the tracked position."""
        state = get_state()
        for stored_position in state.positions:
            if stored_position.id == position.id:
                stored_position.exit_pending = pending
                stored_position.monitor_state = (
                    "exit_pending"
                    if pending
                    else (
                        "trailing_active" if stored_position.partial_take_profit_taken else "open"
                    )
                )
                position.exit_pending = pending
                position.monitor_state = stored_position.monitor_state
                if not pending:
                    stored_position.pending_order_id = None
                    stored_position.pending_exit_action = None
                    stored_position.pending_sell_amount = None
                    position.pending_order_id = None
                    position.pending_exit_action = None
                    position.pending_sell_amount = None
                break
        save_state(state)

    def _store_pending_execution(
        self, position: Position, order_id: str, exit_action: ExitAction
    ) -> None:
        """Persist order details needed for restart recovery."""
        state = get_state()
        for stored_position in state.positions:
            if stored_position.id == position.id:
                stored_position.pending_order_id = order_id
                stored_position.pending_exit_action = exit_action.action
                stored_position.pending_sell_amount = exit_action.sell_amount
                position.pending_order_id = order_id
                position.pending_exit_action = exit_action.action
                position.pending_sell_amount = exit_action.sell_amount
                break
        save_state(state)

    async def _get_sell_quote(
        self, position: Position, address: str, sell_amount: Decimal
    ) -> Optional[dict]:
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
                str(float(sell_amount)),
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
                print(f"[ERROR] Quote request failed: {result.stderr}")
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
            print(f"[ERROR] Quote parsing error: {e}")
            return None

    async def _confirm_sell_order(
        self, position: Position, address: str, market: str, protocol: str, sell_amount: Decimal
    ) -> Optional[str]:
        """Confirm sell order."""
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
                str(float(sell_amount)),
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
                print(f"[ERROR] Confirm order failed: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            if data.get("error_code", 0) != 0:
                print(f"[ERROR] Confirm error: {data.get('msg')}")
                return None

            return data["data"]["orderId"]

        except Exception as e:
            print(f"[ERROR] Confirm order exception: {e}")
            return None

    async def _sign_and_send_sell(
        self,
        position: Position,
        address: str,
        order_id: str,
        market: str,
        protocol: str,
        sell_amount: Decimal,
    ) -> dict:
        """Sign and send sell transaction."""
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
                str(float(sell_amount)),
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
                print(f"[ERROR] Trade failed: {result.stderr}")
                return {"ok": False, "tx_id": "", "raw": result.stderr}

            # 解析结果
            data = json.loads(result.stdout)
            details = data.get("data", {}).get("details", {})
            return {
                "ok": data.get("status") == 0,
                "tx_id": details.get("fromTxId", "") or details.get("toTxId", ""),
                "raw": data,
            }

        except Exception as e:
            print(f"[ERROR] Sign/send exception: {e}")
            return {"ok": False, "tx_id": "", "raw": str(e)}

    async def _get_order_details(self, order_id: str) -> Optional[dict]:
        """Fetch actual order details after send."""
        try:
            cmd = [
                sys.executable,
                self.script_path,
                "get-order-details",
                "--order-id",
                order_id,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return None
            return json.loads(result.stdout)
        except Exception:
            return None

    def _reconcile_execution_result(
        self, fallback_out_amount: str, fallback_tx_id: str, order_details: Optional[dict]
    ) -> dict[str, Decimal | str]:
        """Prefer actual execution values over quote assumptions when available."""
        out_amount = Decimal(str(fallback_out_amount))
        tx_id = fallback_tx_id

        if order_details:
            data = order_details.get("data", {}) if isinstance(order_details, dict) else {}
            details = data.get("details", {}) if isinstance(data, dict) else {}
            actual_amount = data.get("toAmount") or details.get("toAmount")
            actual_tx_id = details.get("fromTxId") or details.get("toTxId") or tx_id

            if actual_amount is not None:
                out_amount = Decimal(str(actual_amount))
            tx_id = actual_tx_id

        return {"out_amount": out_amount, "tx_id": tx_id}

    def _recover_position_from_order_details(self, position: Position, order_details: dict) -> bool:
        """Recover a pending position from a successful stored order result."""
        data = order_details.get("data", {}) if isinstance(order_details, dict) else {}
        details = data.get("details", {}) if isinstance(data, dict) else {}
        if details.get("status") != "success":
            return False

        position.exit_pending = False
        position.pending_order_id = None
        position.pending_exit_action = None
        position.pending_sell_amount = None
        position.monitor_state = "closed"
        return True

    async def _recover_pending_positions(self, state) -> None:
        """Recover exit-pending positions before normal monitoring continues."""
        for position in state.open_positions:
            if not position.exit_pending or not position.pending_order_id:
                continue

            original_action = position.pending_exit_action or "stop_loss"
            original_sell_amount = position.pending_sell_amount or position.active_amount

            order_details = await self._get_order_details(position.pending_order_id)
            if not order_details or not self._recover_position_from_order_details(
                position, order_details
            ):
                continue

            reconciled = self._reconcile_execution_result(
                fallback_out_amount="0",
                fallback_tx_id="",
                order_details=order_details,
            )
            await self._update_position_after_sell(
                position,
                str(reconciled["out_amount"]),
                ExitAction(
                    action=original_action,
                    reason="Recovered pending exit",
                    sell_amount=original_sell_amount,
                ),
                str(reconciled["tx_id"]),
            )

    async def _update_position_after_sell(
        self, position: Position, out_amount: str, exit_action: ExitAction, exit_tx_id: str
    ):
        """Update position state after sell."""
        try:
            state = get_state()

            # 找到并更新仓位
            for p in state.positions:
                if p.id == position.id:
                    sold_amount = exit_action.sell_amount
                    sol_received = Decimal(str(out_amount))
                    exit_price = sol_received / sold_amount if sold_amount else Decimal("0")
                    exit_value_usd = sol_received * await self._get_sol_price()

                    # 记录交易
                    from agent.state import Trade, TradeAction

                    trade = Trade(
                        action=TradeAction.SELL,
                        token_symbol=p.token_symbol,
                        token_contract=p.token_contract,
                        amount=sold_amount,
                        price=exit_price,
                        value_usd=exit_value_usd,
                        position_id=p.id,
                        exit_reason=exit_action.action,
                    )
                    state.record_trade(trade)

                    if exit_action.action == "partial_take_profit":
                        self._apply_partial_take_profit(p, float(p.highest_price or p.entry_price))
                        p.exit_tx_id = exit_tx_id or p.exit_tx_id
                        p.exit_reason = exit_action.action
                        p.exit_pending = False
                        p.monitor_state = "trailing_active"
                    else:
                        p.status = PositionStatus.CLOSED
                        p.remaining_amount = Decimal("0")
                        p.exit_price = exit_price
                        p.exit_amount = p.entry_amount
                        p.exit_value_usd = exit_value_usd
                        p.exit_tx_id = exit_tx_id
                        p.exit_time = datetime.utcnow()
                        p.exit_reason = exit_action.action
                        p.exit_pending = False
                        p.monitor_state = "closed"

                    # 显示盈亏
                    if exit_action.action != "partial_take_profit":
                        pnl = p.pnl_usd
                        pnl_pct = p.pnl_pct
                        if pnl and pnl_pct:
                            tag = "[PROFIT]" if pnl > 0 else "[LOSS]"
                            print(f"{tag} PnL: ${float(pnl):.2f} ({float(pnl_pct):.1f}%)")

                    break

            save_state(state)

        except Exception as e:
            print(f"[ERROR] Failed to update position: {e}")

    async def _get_sol_price(self) -> Decimal:
        """Get current SOL price."""
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

            return Decimal("150")

        except Exception:
            return Decimal("150")

    def stop(self):
        """Stop monitoring."""
        self.running = False
        print("\n[MONITOR] Stopped")


async def run_monitor_once():
    """Run one monitoring pass."""
    monitor = SimplePositionMonitor()
    await monitor.check_all_positions()


def run_monitor_continuous():
    """Run monitoring continuously."""
    monitor = SimplePositionMonitor()

    try:
        asyncio.run(monitor.start())
    except KeyboardInterrupt:
        monitor.stop()
