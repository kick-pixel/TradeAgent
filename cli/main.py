"""
Solana Meme Trading Agent CLI

Main entry point for the trading agent.
"""

from agent.decision import DecisionAnalyzer, should_execute_buy
from agent.intent import Intent, IntentRecognizer, IntentType, get_intent_description
from agent.wallet import get_wallet_manager, get_solana_address
from agent.core import MemeTradingAgent, create_agent
from agent.capabilities import build_capability_help, get_capability_examples
from agent.allocation import allocate_auto_invest_budget
from agent.position_display import describe_exit_reason, describe_position_exit_strategy
from agent.state import AgentState, get_state, save_state
from agent.config import config
import asyncio
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, cast

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.live import Live
from rich.markdown import Markdown

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

stdout_stream = cast(Any, sys.stdout)
if hasattr(stdout_stream, "reconfigure"):
    stdout_stream.reconfigure(encoding="utf-8", errors="replace")
stderr_stream = cast(Any, sys.stderr)
if hasattr(stderr_stream, "reconfigure"):
    stderr_stream.reconfigure(encoding="utf-8", errors="replace")


app = typer.Typer(
    name="meme-agent",
    help="Solana Meme Coin AI Trading Agent",
    add_completion=False,
)
console = Console()

# 初始化意图识别器
intent_recognizer = IntentRecognizer()


def _normalize_chat_input(user_input: str) -> str:
    """Normalize chat input for command recognition."""
    normalized = user_input.strip()
    while normalized.endswith("/"):
        normalized = normalized[:-1].rstrip()

    lowered = normalized.lower()
    typo_map = {
        "positons": "positions",
        "postions": "positions",
        "stats": "status",
    }
    if lowered in typo_map:
        return typo_map[lowered]
    return normalized


def _handle_unknown_intent(user_input: str) -> str:
    """Return a stable help-style reply for unsupported free-form chat."""
    lowered = user_input.lower()
    if any(phrase in lowered for phrase in ["what can you do", "help", "how to use"]):
        return build_capability_help()

    return f"I couldn't map that request to a supported action yet.\n\n{build_capability_help()}"


def _remember_message(role: str, content: str) -> None:
    """Persist a chat turn into agent state."""
    state = get_state()
    state.add_conversation_message(role, content)
    save_state(state)


def _build_action_acknowledgement(intent: Intent) -> str:
    """Build a short assistant memory note for an action-oriented turn."""
    if intent.type == IntentType.HELP:
        return build_capability_help()
    return f"Understood. {get_intent_description(intent)}."


def _dispatch_chat_intent(intent: Intent, agent: MemeTradingAgent) -> Optional[str]:
    """Dispatch a recognized intent and return a memory-safe assistant reply when available."""
    handlers = {
        IntentType.BUY: _handle_buy_intent,
        IntentType.SELL: _handle_sell_intent,
        IntentType.SCAN: _handle_scan_intent,
        IntentType.ANALYZE: _handle_analyze_intent,
        IntentType.AUTO_INVEST: _handle_auto_invest_intent,
        IntentType.STATUS: lambda _intent, _agent: _show_status(),
        IntentType.POSITIONS: lambda _intent, _agent: _show_positions(),
        IntentType.HISTORY: lambda _intent, _agent: _show_history(),
        IntentType.HELP: lambda _intent, _agent: console.print(
            f"\n[bold green]Agent[/bold green]: {build_capability_help()}"
        ),
    }
    handler = handlers.get(intent.type)
    if not handler:
        return None

    handler(intent, agent)
    return _build_action_acknowledgement(intent)


@app.command()
def chat():
    """
    Start interactive chat with the trading agent.

    Natural language commands supported:
    - "buy <token> with <amount> SOL" - buy token with auto-analysis
    - "sell <position_id>" - sell an open position
    - "scan" or "扫描" - scan trending tokens
    - "analyze <token>" - analyze a token
    - "status" or "状态" - show portfolio status
    - "positions" or "持仓" - show open positions
    - "auto invest <budget>" - auto-invest

    All buy operations automatically perform risk analysis before execution.
    """
    console.print(
        Panel.fit(
            "[bold green]Solana Meme Trading Agent[/bold green]\n"
            "[dim]Talk naturally. Try things like:[/dim]\n"
            + "\n".join(f"  - {example}" for example in get_capability_examples(limit=6))
            + "\n"
            "[dim]Type 'help' for more commands, 'quit' to exit[/dim]",
            border_style="green",
        )
    )

    # Initialize agent
    try:
        agent = create_agent()
        console.print("[dim]Agent initialized successfully[/dim]")
    except Exception as e:
        console.print(f"[red]Failed to initialize agent: {e}[/red]")
        console.print("\n[yellow]Please ensure you have configured .env with:[/yellow]")
        console.print("  OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1")
        console.print("  OPENAI_API_KEY=sk-your-key")
        console.print("  OPENAI_MODEL=qwen-plus")
        raise typer.Exit(1)

    chat_history = get_state().get_recent_conversation(limit=20)

    while True:
        try:
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
            normalized_input = _normalize_chat_input(user_input)

            if normalized_input.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            # 使用意图识别处理自然语言
            intent = intent_recognizer.recognize(normalized_input)

            if intent.type == IntentType.UNKNOWN:
                intent = agent.classify_intent_with_llm(normalized_input, chat_history)

            console.print(f"[dim]Intent: {get_intent_description(intent)}[/dim]")

            _remember_message("human", normalized_input)

            assistant_note = _dispatch_chat_intent(intent, agent)

            if assistant_note is None:
                response = _handle_unknown_intent(normalized_input)
                console.print(f"\n[bold green]Agent[/bold green]: {response}")
                assistant_note = response

            _remember_message("ai", assistant_note)
            chat_history = get_state().get_recent_conversation(limit=20)

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def _handle_buy_intent(intent, agent):
    """Handle buy intent."""
    token = intent.params.get("token")
    amount_sol = intent.params.get("amount_sol")

    if not token:
        console.print("[yellow]Please provide a token contract address[/yellow]")
        token = Prompt.ask("Enter token contract address")

    if not amount_sol:
        amount_sol = Prompt.ask("Enter amount in SOL", default="0.01")
        try:
            amount_sol = float(amount_sol)
        except:
            console.print("[red]Invalid amount[/red]")
            return

    console.print(f"\n[bold cyan]Preparing buy for {token} with {amount_sol} SOL[/bold cyan]")
    console.print("[dim]Running automatic decision analysis...[/dim]\n")

    # 1. 自动决策分析
    analyzer = DecisionAnalyzer()
    analysis = analyzer.analyze_token(token)

    if not analysis:
        console.print(
            "[red]Unable to resolve or analyze that token. Use a Solana mint address or a unique supported symbol.[/red]"
        )
        return

    # 显示分析报告
    console.print(analyzer.format_report(analysis))

    # 2. 判断是否应执行买入
    should_buy, reason = should_execute_buy(analysis)

    if not should_buy:
        console.print(f"\n[red][FAIL] Buy rejected: {reason}[/red]")
        console.print(
            "[yellow]Recommendation: current analysis does not support this buy.[/yellow]"
        )
        return

    console.print(f"\n[green][OK] Analysis passed: {reason}[/green]")

    # 3. 用户确认
    if not Confirm.ask("\n[bold red]Confirm buy execution?[/bold red]"):
        console.print("[yellow]Buy cancelled[/yellow]")
        return

    # 4. 直接执行买入（不通过 AI Agent）
    console.print("\n[bold green]Executing buy...[/bold green]")

    # 记录执行前状态，后续做硬校验，避免“假成功”
    state_before = get_state()
    open_positions_before = len(state_before.open_positions)
    total_trades_before = state_before.total_trades

    try:
        console.print("\n[cyan]Step 1: Get trade quote...[/cyan]")
        prepare_result = agent.prepare_buy_transaction(
            token_contract=analysis.token_contract,
            token_symbol=analysis.token_symbol,
            amount_sol=amount_sol,
            slippage=config.trading.default_slippage,
        )
        console.print(prepare_result["message"])

        if not prepare_result.get("ok"):
            console.print("\n[red][FAIL] Buy preparation failed[/red]")
            return

        console.print("\n[cyan]Step 2: Confirm and execute trade...[/cyan]")
        console.print(f"Market: {prepare_result['market']}")
        console.print(f"Protocol: {prepare_result['protocol']}")

        execute_result = agent.execute_buy_transaction(
            token_contract=analysis.token_contract,
            token_symbol=prepare_result["token_symbol"],
            amount_sol=amount_sol,
            market=prepare_result["market"],
            protocol=prepare_result["protocol"],
            slippage=config.trading.default_slippage,
        )
        console.print(execute_result["message"])

        state_after = get_state()
        open_positions_after = len(state_after.open_positions)
        total_trades_after = state_after.total_trades

        position_added = open_positions_after > open_positions_before
        trade_recorded = total_trades_after > total_trades_before
        has_tx_hint = bool(execute_result.get("tx_id"))

        if execute_result.get("ok") and (position_added or trade_recorded):
            console.print("\n[green][OK] Buy succeeded with confirmed state update[/green]")
            console.print(
                f"[dim]Open Positions: {open_positions_before} -> {open_positions_after}, "
                f"Total Trades: {total_trades_before} -> {total_trades_after}[/dim]"
            )
            _show_status()
        elif has_tx_hint:
            console.print(
                "\n[yellow][WARN] Trade receipt found but local state did not update. Refresh or retry.[/yellow]"
            )
        else:
            console.print(
                "\n[red][FAIL] Buy did not complete: no valid state change detected.[/red]"
            )

    except Exception as e:
        console.print(f"\n[red]Execution error: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")


def _handle_sell_intent(intent, agent):
    """Handle sell intent."""
    position_id = intent.params.get("position_id")

    if not position_id:
        # 显示持仓列表供选择
        _show_positions()
        position_id = Prompt.ask("Enter position ID to sell")

    state = get_state()
    position = None
    for p in state.open_positions:
        if p.id == position_id:
            position = p
            break

    if not position:
        console.print(f"[red]Position {position_id} not found or already closed[/red]")
        return

    console.print(f"\n[bold cyan]Preparing sell for position: {position.token_symbol}[/bold cyan]")
    console.print(f"Entry Price: ${float(position.entry_price):.6f}")
    console.print(f"Entry Amount: {float(position.entry_amount):.4f}")
    console.print(f"Exit Strategy: {describe_position_exit_strategy(position)}")

    if not Confirm.ask("\n[bold red]Confirm sell execution?[/bold red]"):
        console.print("[yellow]Sell cancelled[/yellow]")
        return

    state_before = get_state()
    open_positions_before = len(state_before.open_positions)
    total_trades_before = state_before.total_trades

    try:
        console.print("\n[cyan]Step 1: Get sell quote...[/cyan]")
        prepare_result = agent.prepare_sell_transaction(
            position_id=position_id,
            slippage=config.trading.default_slippage,
        )
        console.print(prepare_result["message"])

        if not prepare_result.get("ok"):
            console.print("\n[red][FAIL] Sell preparation failed[/red]")
            return

        console.print("\n[cyan]Step 2: Confirm and execute sell...[/cyan]")
        console.print(f"Market: {prepare_result['market']}")
        console.print(f"Protocol: {prepare_result['protocol']}")

        execute_result = agent.execute_sell_transaction(
            position_id=position_id,
            market=prepare_result["market"],
            protocol=prepare_result["protocol"],
            slippage=config.trading.default_slippage,
        )
        console.print(execute_result["message"])

        state_after = get_state()
        open_positions_after = len(state_after.open_positions)
        total_trades_after = state_after.total_trades

        position_reduced = open_positions_after < open_positions_before
        trade_recorded = total_trades_after > total_trades_before
        has_tx_hint = bool(execute_result.get("tx_id"))

        if execute_result.get("ok") and (position_reduced or trade_recorded):
            console.print("\n[green][OK] Sell succeeded with confirmed state update[/green]")
            console.print(
                f"[dim]Open Positions: {open_positions_before} -> {open_positions_after}, "
                f"Total Trades: {total_trades_before} -> {total_trades_after}[/dim]"
            )
            _show_status()
        elif has_tx_hint:
            console.print(
                "\n[yellow][WARN] Trade receipt found but local state did not update. Refresh or retry.[/yellow]"
            )
        else:
            console.print(
                "\n[red][FAIL] Sell did not complete: no valid state change detected.[/red]"
            )
    except Exception as e:
        console.print(f"\n[red]Execution error: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")


def _handle_scan_intent(intent, agent):
    """Handle scan intent."""
    limit = intent.params.get("limit", 5)

    console.print(f"[bold cyan]Scanning top {limit} trending tokens...[/bold cyan]")
    try:
        result = agent._run_bitget_api("rankings", "name=Hotpicks")
        data = json.loads(result)
        status = data.get("status", 0)
        error_code = data.get("error_code", 0)
        if status != 0 or error_code != 0:
            console.print(
                f"[red]Scan failed: {data.get('msg') or data.get('title') or 'Unknown error'}[/red]"
            )
            return

        tokens = data.get("data", {}).get("list", [])
        sol_tokens = [t for t in tokens if t.get("chain") == "sol"][:limit]
        if not sol_tokens:
            console.print("[yellow]No trending Solana tokens found[/yellow]")
            return

        analyzer = DecisionAnalyzer()
        console.print("\n[bold green]Scan Results[/bold green]:")
        for index, token in enumerate(sol_tokens, 1):
            contract = token.get("contract", "")
            symbol = token.get("symbol", "UNKNOWN")
            if not contract:
                continue
            analysis = analyzer.analyze_token(contract)
            if not analysis:
                console.print(f"{index}. {symbol} - [red]Analysis failed[/red]")
                continue
            console.print(
                f"{index}. {analysis.token_symbol} | Score: {analysis.total_score}/100 | "
                f"Risk: {analysis.risk_level} | Advice: {analysis.recommendation}"
            )
            console.print(f"   Contract: {contract}")
            console.print(
                f"   Price: ${analysis.current_price:.8f} | Liquidity: ${analysis.liquidity_usd:,.2f}"
            )
    except Exception as e:
        console.print(f"[red]Scan failed: {e}[/red]")


def _handle_analyze_intent(intent, agent):
    """Handle analyze intent."""
    token = intent.params.get("token")

    if not token:
        token = Prompt.ask("Enter token contract address to analyze")

    console.print(f"[bold cyan]Analyzing token: {token}[/bold cyan]\n")

    # 使用决策分析器进行全面分析
    analyzer = DecisionAnalyzer()
    analysis = analyzer.analyze_token(token)

    if analysis:
        console.print(analyzer.format_report(analysis))
    else:
        # 回退到AI分析
        prompt = f"""Analyze token {token} on Solana.
Check security, liquidity, and trading activity.
Give me a detailed analysis with buy/avoid recommendation."""

        with console.status("[bold green]Analyzing...[/bold green]"):
            response = agent.run(prompt)

        console.print(Markdown(response))


def _handle_auto_invest_intent(intent, agent):
    """Handle auto-invest intent."""
    # 优先从参数中获取预算
    budget_usd = intent.params.get("budget_usd")
    budget_sol = intent.params.get("budget_sol")

    # 如果没有参数，尝试从原始输入提取
    if not budget_usd and not budget_sol:
        budget_usd = intent.params.get("budget", 10)

    # 显示预算
    if budget_sol:
        budget_usd = budget_sol * 150
        console.print(
            f"[bold cyan]Auto-invest mode - Budget: {budget_sol} SOL (~${budget_usd:.0f} USDT)[/bold cyan]"
        )
    else:
        console.print(f"[bold cyan]Auto-invest mode - Budget: ${budget_usd:.0f} USDT[/bold cyan]")

    console.print("[dim]Scanning opportunities and running risk analysis...[/dim]\n")

    # Step 1: 扫描热门代币
    console.print("[bold yellow]Step 1: Scan trending tokens...[/bold yellow]")

    try:
        # 使用 agent 的 Bitget API 获取热门代币
        result = agent._run_bitget_api("rankings", "name=Hotpicks")
        data = json.loads(result)

        status = data.get("status", 0)
        error_code = data.get("error_code", 0)
        if status != 0 or error_code != 0:
            console.print(
                f"[red]Scan failed: {data.get('msg') or data.get('title') or 'Unknown error'}[/red]"
            )
            return

        tokens = data.get("data", {}).get("list", [])
        # 只取 Solana 链上的代币
        sol_tokens = [t for t in tokens if t.get("chain") == "sol"][:10]

        if not sol_tokens:
            console.print("[red]No trending Solana tokens found[/red]")
            return

        console.print(f"[green]Found {len(sol_tokens)} trending Solana tokens[/green]\n")
    except Exception as e:
        console.print(f"[red]Scan failed: {e}[/red]")
        return

    # Step 2: 分析每个代币
    console.print("[bold yellow]Step 2: Run risk analysis...[/bold yellow]")
    analyzer = DecisionAnalyzer()
    qualified_tokens = []

    for i, token in enumerate(sol_tokens[:5], 1):  # 分析前5个
        contract = token.get("contract", "")
        symbol = token.get("symbol", "UNKNOWN")

        if not contract:
            continue

        console.print(f"\n[cyan]Analyzing {i}/5: {symbol}[/cyan]")

        try:
            analysis = analyzer.analyze_token(contract)
            if analysis and analysis.total_score >= config.trading.min_risk_score:
                qualified_tokens.append(
                    {
                        "symbol": analysis.token_symbol,
                        "contract": contract,
                        "score": analysis.total_score,
                        "price": analysis.current_price,
                        "recommendation": analysis.recommendation,
                        "analysis": analysis,
                    }
                )
                console.print(f"[green]  [OK] Passed - Score: {analysis.total_score}/100[/green]")
            elif analysis:
                console.print(
                    f"[yellow]  [SKIP] Rejected - Score: {analysis.total_score}/100 (need > {config.trading.min_risk_score})[/yellow]"
                )
        except Exception as e:
            console.print(f"[red]  [ERROR] Analysis failed: {e}[/red]")
            continue

    if not qualified_tokens:
        console.print("\n[red]No tokens met the selection criteria[/red]")
        return

    # Step 3: 显示投资计划
    console.print(f"\n[bold green]Found {len(qualified_tokens)} qualified tokens[/bold green]")

    # 选择前2-3个
    selected = qualified_tokens[: min(3, len(qualified_tokens))]
    allocations = allocate_auto_invest_budget(selected, budget_usd)

    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Investment Plan[/bold cyan]")
    console.print("=" * 60)

    for i, token in enumerate(selected, 1):
        allocation_usd = allocations[token["symbol"]]
        sol_amount = allocation_usd / 150  # 假设 SOL=$150
        console.print(f"\n{i}. {token['symbol']}")
        console.print(f"   Contract: {token['contract'][:20]}...")
        console.print(f"   Score: {token['score']}/100")
        console.print(f"   Price: ${token['price']:.8f}")
        console.print(f"   Allocation: ${allocation_usd:.2f} USDT ~= {sol_amount:.4f} SOL")

    console.print(f"\nTotal: ${budget_usd:.2f} USDT")
    console.print("=" * 60)

    # 用户确认
    if not Confirm.ask("\n[bold red]Confirm this investment plan?[/bold red]"):
        console.print("[yellow]Investment cancelled.[/yellow]")
        return

    # Step 4: 执行交易
    console.print("\n[bold]Executing trades...[/bold]")

    for token in selected:
        allocation_usd = allocations[token["symbol"]]
        sol_amount = allocation_usd / 150
        console.print(f"\n[cyan]Buying {token['symbol']}...[/cyan]")

        try:
            prepare_result = agent.prepare_buy_transaction(
                token_contract=token["contract"],
                token_symbol=token["symbol"],
                amount_sol=sol_amount,
                slippage=config.trading.default_slippage,
            )
            console.print(prepare_result["message"])

            if not prepare_result.get("ok"):
                console.print(f"[red]Buy preparation failed for {token['symbol']}[/red]")
                continue

            execute_result = agent.execute_buy_transaction(
                token_contract=token["contract"],
                token_symbol=prepare_result["token_symbol"],
                amount_sol=sol_amount,
                market=prepare_result["market"],
                protocol=prepare_result["protocol"],
                slippage=config.trading.default_slippage,
            )
            console.print(execute_result["message"])

            if not execute_result.get("ok"):
                console.print(f"[red]Buy execution failed for {token['symbol']}[/red]")

        except Exception as e:
            console.print(f"[red]Buy failed for {token['symbol']}: {e}[/red]")
            continue

    console.print("\n[bold green]Auto-invest execution complete[/bold green]")


@app.command()
def scan(
    chain: str = typer.Option("sol", help="Chain to scan"),
    limit: int = typer.Option(5, help="Number of tokens to analyze"),
):
    """Scan for trending tokens and analyze them"""
    agent = create_agent()

    prompt = f"Scan for trending tokens on {chain} chain. Analyze the top {limit} tokens for trading potential. For each token: check security, liquidity, and recent activity. Provide a summary with buy/avoid recommendations."

    with console.status("[bold green]Scanning and analyzing...[/bold green]"):
        response = agent.run(prompt)

    # Remove emojis for Windows compatibility
    response_clean = response.encode("ascii", "ignore").decode("ascii")
    console.print(response_clean)


@app.command()
def analyze(
    contract: str = typer.Argument(..., help="Token contract address"),
    chain: str = typer.Option("sol", help="Chain code"),
):
    """Analyze a specific token"""
    agent = create_agent()

    prompt = f"""Analyze token on {chain} chain with contract: {contract}

Please:
1. Get token info and current price
2. Run security audit (check for honeypot, taxes, risks)
3. Check liquidity pools
4. Check recent trading activity
5. Provide a trading recommendation (buy/avoid/hold) with reasons
"""

    with console.status("[bold green]Analyzing token...[/bold green]"):
        response = agent.run(prompt)

    # Remove emojis for Windows compatibility
    response_clean = response.encode("ascii", "ignore").decode("ascii")
    console.print(response_clean)


@app.command()
def status():
    """Show current portfolio status"""
    _show_status()


@app.command()
def positions():
    """Show open positions"""
    _show_positions()


@app.command()
def auto_invest(
    budget: float = typer.Option(..., help="Total budget in USDT to invest"),
    max_positions: int = typer.Option(3, help="Maximum number of positions to open"),
    min_score: int = typer.Option(70, help="Minimum risk score threshold (0-100)"),
    dry_run: bool = typer.Option(True, help="Analyze only, don't execute trades"),
):
    """
    Automatically analyze trending tokens and invest within budget.

    Performs comprehensive decision analysis for each token before investing:
    - Security audit (honeypot, taxes, contract)
    - Liquidity assessment
    - Trading activity analysis
    - Risk scoring

    Only invests in tokens passing all safety checks.

    Example:
        meme-agent auto-invest --budget 10 --max-positions 2 --dry-run
        meme-agent auto-invest --budget 10 --max-positions 2 --no-dry-run
    """
    from agent.wallet import get_wallet_manager
    from agent.decision import DecisionAnalyzer, should_execute_buy

    wm = get_wallet_manager()
    if not wm.has_mnemonic:
        console.print(
            "[red]Error: No wallet mnemonic configured. Set MNEMONIC_PHRASE in .env[/red]"
        )
        raise typer.Exit(1)

    wallet_address = wm.get_solana_address()

    console.print(
        Panel.fit(
            f"[bold green]Auto Investment Mode with Decision Analysis[/bold green]\n"
            f"Budget: [cyan]{budget} USDT[/cyan]\n"
            f"Max Positions: [cyan]{max_positions}[/cyan]\n"
            f"Min Risk Score: [cyan]{min_score}[/cyan]\n"
            f"Mode: [yellow]{'DRY RUN (Analysis Only)' if dry_run else 'LIVE TRADING'}[/yellow]\n"
            f"[dim]Each token will undergo comprehensive analysis before investment[/dim]",
            border_style="green",
        )
    )

    agent = create_agent()

    # Step 1: Use the dedicated analysis tool
    console.print("\n[bold]Step 1: Scanning and pre-filtering opportunities...[/bold]")

    # Directly call the analysis tool for more reliable results
    analysis_result = agent.tools[-1].func(budget, max_positions, min_score)

    console.print("\n[bold]Pre-filtering Results:[/bold]")
    analysis_clean = analysis_result.encode("ascii", "ignore").decode("ascii")
    console.print(analysis_clean)

    # Check if there are opportunities
    if "No tokens met" in analysis_result or "Qualified Opportunities: 0" in analysis_result:
        console.print("\n[yellow]No suitable investment opportunities found. Exiting.[/yellow]")
        return

    # Step 2: Decision Analysis for each candidate
    console.print("\n[bold]Step 2: Comprehensive Decision Analysis...[/bold]")
    console.print("[dim]Performing deep analysis on candidate tokens...[/dim]\n")

    analyzer = DecisionAnalyzer()
    approved_tokens = []

    # Extract token contracts from analysis result
    # This is a simplified approach - in production, parse the JSON
    console.print(
        "[yellow]Note: Deep analysis will be performed during execution for each token.[/yellow]"
    )

    # Step 3: Get investment plan from agent
    console.print("\n[bold]Step 3: Generating investment plan...[/bold]")

    plan_prompt = f"""Based on the analysis above, create an investment plan.

Budget: {budget} USDT
Max Positions: {max_positions}
Wallet: {wallet_address}
Min Score: {min_score}

IMPORTANT: For each token in the plan:
1. Use DecisionAnalyzer to perform comprehensive analysis (security, liquidity, activity)
2. Only proceed if the token passes should_execute_buy() check
3. Calculate position size (respect 5% max per trade rule, so max {min(budget / max_positions, budget * 0.05):.2f} USDT per position)
4. Set stop loss (-{config.trading.stop_loss_pct}%) and take profit (+{config.trading.take_profit_pct}%)

Return a clear investment plan with:
- Which tokens to buy (only those passing all checks)
- How much to invest in each (in USDT and SOL)
- Expected token amounts
- Risk/Reward assessment
- Analysis scores for each token

If no tokens pass the safety checks, say "NO SUITABLE OPPORTUNITIES FOUND".
"""

    with console.status("[bold green]Creating investment plan...[/bold green]"):
        plan_result = agent.run(plan_prompt)

    console.print("\n[bold]Investment Plan:[/bold]")
    plan_clean = plan_result.encode("ascii", "ignore").decode("ascii")
    console.print(plan_clean)

    # Check if there are opportunities
    if "NO SUITABLE" in plan_result.upper() or "no suitable" in plan_result.lower():
        console.print("\n[yellow]No suitable investment opportunities found. Exiting.[/yellow]")
        return

    # Step 4: Execute or simulate
    if dry_run:
        console.print("\n[bold yellow]DRY RUN COMPLETE[/bold yellow]")
        console.print("No trades were executed. Use --no-dry-run to execute.")
        return

    # Confirm before executing
    if not Confirm.ask(
        "\n[bold red]Execute the investment plan? This will perform actual trades.[/bold red]"
    ):
        console.print("[yellow]Investment cancelled.[/yellow]")
        return

    # Step 5: Execute trades with per-token analysis
    console.print("\n[bold]Step 4: Executing trades with per-token decision analysis...[/bold]")

    # The execute_buy tool will now automatically perform decision analysis
    execute_prompt = f"""Execute the investment plan above with budget {budget} USDT.

For each token in the plan:
1. Use DecisionAnalyzer.analyze_token() for comprehensive analysis
2. Check should_execute_buy() - only proceed if it returns True
3. If rejected, skip and try next token
4. Use execute_buy tool to prepare and execute the trade
5. Record the position with stop-loss and take-profit prices

Execute trades one by one and report:
- Analysis result for each token (score, recommendation)
- Whether it passed safety checks
- Success/failure of each trade
- Transaction IDs
- Actual amounts received
- Any errors encountered

Wallet address: {wallet_address}
Min Score Required: {min_score}
Min Liquidity Required: ${config.trading.min_liquidity_usd:,.0f}
"""

    with console.status("[bold green]Executing trades...[/bold green]"):
        execute_result = agent.run(execute_prompt)

    console.print("\n[bold]Execution Results:[/bold]")
    execute_clean = execute_result.encode("ascii", "ignore").decode("ascii")
    console.print(execute_clean)

    # Show final status
    console.print("\n[bold]Final Portfolio Status:[/bold]")
    _show_status()


@app.command()
def balance(
    address: Optional[str] = typer.Option(None, help="Wallet address"),
):
    """Check wallet balance"""
    state = get_state()

    if not address and state.wallet_address:
        address = state.wallet_address

    if not address:
        console.print(
            "[red]No wallet address configured. Set one with: meme-agent set-wallet[/red]"
        )
        raise typer.Exit(1)

    agent = create_agent()

    prompt = f"Check balance for wallet {address} on Solana chain. Show all token balances with USD values."

    with console.status("[bold green]Checking balance...[/bold green]"):
        response = agent.run(prompt)

    console.print(Markdown(response))


@app.command()
def set_wallet(address: str = typer.Argument(..., help="Wallet address")):
    """Set the wallet address for trading"""
    state = get_state()
    state.wallet_address = address
    save_state(state)
    console.print(f"[green]Wallet address set to: {address}[/green]")


@app.command()
def trade(
    from_token: str = typer.Option(..., help="Token to sell (contract or SOL)"),
    to_token: str = typer.Option(..., help="Token to buy (contract or SOL)"),
    amount: float = typer.Option(..., help="Amount to trade"),
    slippage: float = typer.Option(1.0, help="Slippage tolerance %"),
    dry_run: bool = typer.Option(True, help="Simulate without executing"),
):
    """
    Execute a trade (requires confirmation).

    By default runs in dry-run mode. Use --no-dry-run to execute.
    """
    agent = create_agent()
    state = get_state()

    if not state.wallet_address:
        console.print(
            "[red]No wallet address configured. Set one with: meme-agent set-wallet[/red]"
        )
        raise typer.Exit(1)

    # Determine contracts
    from_contract = "" if from_token.upper() == "SOL" else from_token
    to_contract = "" if to_token.upper() == "SOL" else to_token

    prompt = f"""Prepare a swap on Solana:
- From: {from_token} ({from_contract or "native SOL"})
- To: {to_token} ({to_contract or "native SOL"})
- Amount: {amount}
- Slippage: {slippage}%
- Wallet: {state.wallet_address}

Please:
1. Check my wallet balance first
2. Run security check on both tokens
3. Get a swap quote
4. Show me the details for confirmation

{"DRY RUN - Do not execute, just show what would happen" if dry_run else "After I confirm, execute the swap"}
"""

    with console.status("[bold green]Preparing trade...[/bold green]"):
        response = agent.run(prompt)

    console.print(Markdown(response))

    if not dry_run:
        if Confirm.ask("\n[bold red]Execute this trade?[/bold red]"):
            execute_prompt = (
                f"Execute the swap with the quote from above for wallet {state.wallet_address}"
            )
            with console.status("[bold green]Executing trade...[/bold green]"):
                result = agent.run(execute_prompt)
            console.print(Markdown(result))


@app.command()
def close(
    position_id: str = typer.Argument(..., help="Position ID to close"),
):
    """Close an open position"""
    state = get_state()

    position = None
    for p in state.positions:
        if p.id == position_id and p.is_open:
            position = p
            break

    if not position:
        console.print(f"[red]Position {position_id} not found or already closed[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Position to close:[/bold]")
    console.print(f"  Token: {position.token_symbol}")
    console.print(f"  Entry: ${position.entry_value_usd}")
    console.print(f"  Amount: {position.entry_amount}")

    if not Confirm.ask("\n[bold red]Close this position?[/bold red]"):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit(0)

    agent = create_agent()

    prompt = f"""Close position {position_id}:
- Token: {position.token_symbol} ({position.token_contract})
- Sell {position.entry_amount} tokens for SOL
- Wallet: {state.wallet_address}

Please:
1. Get current token price
2. Get swap quote to sell all tokens for SOL
3. Execute the swap
4. Record the position closure
"""

    with console.status("[bold green]Closing position...[/bold green]"):
        response = agent.run(prompt)

    console.print(Markdown(response))


def _show_help():
    """Show help message"""
    console.print(
        Panel(
            f"""[bold]Natural Language Chat:[/bold]
{build_capability_help()}

[bold]CLI Commands:[/bold]
  [cyan]scan[/cyan]              - Scan and analyze tokens
  [cyan]analyze <contract>[/cyan] - Analyze specific token
  [cyan]auto-invest[/cyan]       - Auto analyze and invest
  [cyan]status[/cyan]            - Show portfolio status
  [cyan]positions[/cyan]         - Show open positions
  [cyan]chat[/cyan]              - Start interactive chat

[bold]Examples:[/bold]
  "Scan for new Solana meme coins launched today"
  "What's the price of [contract address]?"
  "Should I buy [token]? Run a full analysis"
  "Check my portfolio status"
  "Sell my position in [token]"
  "Auto-invest 10 USDT in top 2 opportunities"
""",
            title="Help",
            border_style="blue",
        )
    )


def _refresh_wallet_balance(state: AgentState) -> bool:
    """
    Refresh wallet balance from on-chain data using Bitget API.
    Updates state.native_balance in place and saves state.

    Returns:
        True if refresh succeeded, False otherwise
    """
    if not state.wallet_address:
        return False

    # Path to Bitget API script
    script_path = (
        Path(__file__).parent.parent
        / "skills"
        / "bitget-wallet-skill"
        / "scripts"
        / "bitget_agent_api.py"
    )

    try:
        # Query SOL balance (native token)
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "get-processed-balance",
                "--chain",
                "sol",
                "--address",
                state.wallet_address,
                "--contract",
                "",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("status") == 0 and data.get("data"):
                balance_data = data["data"][0]
                token_list = balance_data.get("list", {})

                # Update native SOL balance
                if "" in token_list:
                    sol_balance = Decimal(token_list[""].get("balance", "0"))
                    state.native_balance = sol_balance
                    save_state(state)
                    return True

        return False

    except Exception:
        # Silently fail - we'll show cached values
        return False


def _show_status():
    """Show portfolio status with refreshed balances"""
    state = get_state()

    # Refresh wallet balance before displaying
    with console.status("[dim]Refreshing balances..."):
        _refresh_wallet_balance(state)

    console.print(
        Panel(
            f"""[bold]Wallet:[/bold] {state.wallet_address or "Not set"}
[bold]SOL Balance:[/bold] {state.native_balance:.6f}
[bold]Total Value:[/bold] ${state.total_value_usd:.2f}

[bold]Trading Stats:[/bold]
  Total PnL: ${state.total_pnl_usd:.2f}
  Total Trades: {state.total_trades}
  Win Rate: {state.win_rate * 100:.1f}%
  Daily Trades: {state.daily_trade_count}/{config.trading.max_daily_trades}

[bold]Monitor Exit Strategy:[/bold]
  Initial SL: -{config.trading.stop_loss_pct}%
  Partial TP: +{config.trading.partial_take_profit_pct}% (sell {config.trading.partial_take_profit_fraction * 100:.0f}%)
  Breakeven: enabled after partial TP
  Trailing: {config.trading.trailing_stop_pct}% on remainder
""",
            title="Portfolio Status",
            border_style="green",
        )
    )

    if state.token_balances:
        table = Table(title="Token Balances")
        table.add_column("Symbol")
        table.add_column("Balance")
        table.add_column("Value (USD)")

        for b in state.token_balances:
            table.add_row(
                b.symbol, f"{b.balance:.4f}", f"${b.balance_usd:.2f}" if b.balance_usd else "-"
            )

        console.print(table)


def _show_positions():
    """Show open positions"""
    state = get_state()

    if not state.open_positions:
        console.print("[yellow]No open positions[/yellow]")
        return

    table = Table(title="Open Positions")
    table.add_column("ID")
    table.add_column("Token")
    table.add_column("Entry Price")
    table.add_column("Amount")
    table.add_column("Entry Value")
    table.add_column("Hold Time")
    table.add_column("Exit Strategy")

    for p in state.open_positions:
        table.add_row(
            p.id,
            p.token_symbol,
            f"${p.entry_price:.6f}",
            f"{p.entry_amount:.4f}",
            f"${p.entry_value_usd:.2f}",
            f"{p.hold_duration_hours:.1f}h",
            describe_position_exit_strategy(p),
        )

    console.print(table)


def _show_history():
    """Show trade history"""
    state = get_state()

    if not state.trades:
        console.print("[yellow]No trade history[/yellow]")
        return

    table = Table(title="Trade History")
    table.add_column("Time")
    table.add_column("Action")
    table.add_column("Token")
    table.add_column("Amount")
    table.add_column("Value")
    table.add_column("Exit Reason")

    for t in state.trades[-20:]:  # Last 20 trades
        table.add_row(
            t.timestamp.strftime("%m-%d %H:%M"),
            t.action.value.upper(),
            t.token_symbol,
            f"{t.amount:.4f}",
            f"${t.value_usd:.2f}",
            describe_exit_reason(t.exit_reason),
        )

    console.print(table)


@app.command()
def monitor(
    interval: int = typer.Option(60, help="Check interval in seconds"),
    once: bool = typer.Option(False, help="Run once and exit"),
):
    """
    Monitor open positions and auto-sell on stop-loss/take-profit triggers.

    Automatically checks all open positions every interval seconds.
    Sells positions when:
    - Price reaches take-profit target (+30% by default)
    - Price hits stop-loss (-15% by default)
    - Maximum hold time exceeded (24h by default)

    Examples:
        python -m cli.main monitor                    # Continuous monitoring
        python -m cli.main monitor --interval 30      # Check every 30 seconds
        python -m cli.main monitor --once             # Check once and exit
    """
    from agent.monitor import (
        SimplePositionMonitor,
        build_monitor_strategy_summary,
        run_monitor_once,
    )
    from agent.wallet import get_wallet_manager

    wm = get_wallet_manager()
    if not wm.has_mnemonic:
        console.print(
            "[red]Error: No wallet mnemonic configured. Set MNEMONIC_PHRASE in .env[/red]"
        )
        raise typer.Exit(1)

    if once:
        console.print("[bold]Running position check once...[/bold]")
        import asyncio

        asyncio.run(run_monitor_once())
    else:
        console.print(
            Panel.fit(
                "[bold green]🚀 Position Monitor Starting[/bold green]\n"
                f"Check Interval: [cyan]{interval}s[/cyan]\n"
                + build_monitor_strategy_summary()
                .replace("Initial stop loss: ", "Initial stop loss: [red]")
                .replace("\nPartial take profit: ", "[/red]\nPartial take profit: [green]")
                .replace("\nBreakeven promotion: ", "[/green]\nBreakeven promotion: [cyan]")
                .replace("\nTrailing stop: ", "[/cyan]\nTrailing stop: [yellow]")
                .replace("\nMax hold: ", "[/yellow]\nMax hold: [yellow]")
                + "[/yellow]\n\n"
                "[dim]Press Ctrl+C to stop[/dim]",
                border_style="green",
            )
        )

        monitor = SimplePositionMonitor()
        monitor.check_interval = interval

        try:
            import asyncio

            asyncio.run(monitor.start())
        except KeyboardInterrupt:
            monitor.stop()


@app.command()
def init():
    """Initialize the agent with configuration check"""
    console.print("[bold]Solana Meme Trading Agent - Initialization[/bold]\n")

    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        console.print("[yellow]No .env file found. Creating from template...[/yellow]")
        import shutil

        shutil.copy(".env.example", ".env")
        console.print("[green]Created .env file. Please edit with your API keys.[/green]")
    else:
        console.print("[green][OK] .env file exists[/green]")

    # Check configuration
    try:
        from agent.config import config

        if config.llm.api_key:
            console.print("[green][OK] LLM API key configured[/green]")
        else:
            console.print("[red][X] LLM API key not set[/red]")
            console.print("  Set OPENAI_API_KEY in .env file")
    except Exception as e:
        console.print(f"[red][X] Configuration error: {e}[/red]")

    # Check skills
    skills_path = Path("skills")
    if skills_path.exists():
        skills = list(skills_path.glob("*/SKILL.md"))
        console.print(f"[green][OK] Found {len(skills)} skill(s)[/green]")
        for s in skills:
            console.print(f"    - {s.parent.name}")
    else:
        console.print("[red][X] Skills directory not found[/red]")

    # Initialize state
    state = get_state()
    console.print(f"[green][OK] State initialized (Agent ID: {state.agent_id})[/green]")

    # Check wallet
    wm = get_wallet_manager()
    if wm.has_mnemonic:
        try:
            sol_address = wm.get_solana_address()
            console.print(
                f"[green][OK] Solana wallet configured: {sol_address[:20]}...{sol_address[-8:]}[/green]"
            )
            # Auto-set wallet address if not set
            if not state.wallet_address:
                state.wallet_address = sol_address
                save_state(state)
        except Exception as e:
            console.print(f"[yellow][!] Wallet configured but error deriving address: {e}[/yellow]")
    else:
        console.print("[yellow][!] No wallet mnemonic configured[/yellow]")

    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Start chatting: python -m cli.main chat")
    console.print("2. Scan for tokens: python -m cli.main scan")
    console.print("3. Check status: python -m cli.main status")


if __name__ == "__main__":
    app()
