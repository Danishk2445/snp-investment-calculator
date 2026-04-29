#!/usr/bin/env python3
"""
S&P 500 Investment Calculator
────────────────────────────
A CLI tool that simulates historical S&P 500 investment growth
using real market data from Yahoo Finance.
"""

import sys
from datetime import datetime, date
from typing import Optional

import yfinance as yf
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.text import Text
from rich.rule import Rule
from rich.columns import Columns
from rich import box

console = Console()


# ──────────────────────────────────────────────
# Data fetching
# ──────────────────────────────────────────────

def fetch_snp_data(start_year: int, end_year: int) -> dict[int, dict]:
    """
    Fetch S&P 500 (^GSPC) yearly open/close prices.
    Returns a dict keyed by year with open_price, close_price, and annual_return.
    """
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year + 1}-01-31"  # buffer to capture end-of-year data

    console.print()
    with console.status("[bold cyan]Fetching S&P 500 data from Yahoo Finance…[/]", spinner="dots"):
        ticker = yf.Ticker("^GSPC")
        hist = ticker.history(start=start_date, end=end_date, auto_adjust=True)

    if hist.empty:
        console.print("[bold red]Error:[/] No data returned from Yahoo Finance. Check your date range.")
        sys.exit(1)

    yearly_data: dict[int, dict] = {}

    for year in range(start_year, end_year + 1):
        year_df = hist[hist.index.year == year]
        if year_df.empty:
            continue

        open_price = year_df.iloc[0]["Open"]
        close_price = year_df.iloc[-1]["Close"]
        annual_return = (close_price - open_price) / open_price

        yearly_data[year] = {
            "open": open_price,
            "close": close_price,
            "return": annual_return,
        }

    return yearly_data


# ──────────────────────────────────────────────
# Simulation
# ──────────────────────────────────────────────

def simulate_investment(
    yearly_data: dict[int, dict],
    initial_investment: float,
    contribution_amount: float,
    contribution_frequency: str,   # "monthly" | "yearly"
    contribution_timing: str,      # "beginning" | "end"
    start_year: int,
    num_years: int,
) -> list[dict]:
    """
    Simulate year-by-year investment growth using actual S&P 500 returns.
    Returns a list of dicts, one per year, with all relevant figures.
    """
    results: list[dict] = []
    balance = 0.0
    total_contributions = 0.0

    for i, year in enumerate(range(start_year, start_year + num_years)):
        data = yearly_data.get(year)
        if data is None:
            console.print(f"[yellow]Warning:[/] No S&P data for {year}, skipping.")
            continue

        annual_return = data["return"]
        start_balance = balance

        # ── Initial investment (first year only) ──
        year_contributions = 0.0
        if i == 0:
            balance += initial_investment
            year_contributions += initial_investment

        # ── Contributions logic ──
        if contribution_frequency == "yearly":
            if i == 0:
                # Initial investment already counted; skip additional contribution first year
                yearly_contribution = 0.0
            else:
                yearly_contribution = contribution_amount

            if contribution_timing == "beginning":
                # Add contribution at the beginning, then apply full-year growth
                balance += yearly_contribution
                year_contributions += yearly_contribution
                total_contributions += yearly_contribution
                growth = balance * annual_return
                balance += growth
            else:
                # Apply full-year growth first, then add contribution at end
                growth = balance * annual_return
                balance += growth
                balance += yearly_contribution
                year_contributions += yearly_contribution
                total_contributions += yearly_contribution

        elif contribution_frequency == "monthly":
            if i == 0:
                monthly_contribution = 0.0
            else:
                monthly_contribution = contribution_amount

            # Approximate monthly growth from annual return
            monthly_return = (1 + annual_return) ** (1 / 12) - 1
            growth = 0.0

            for month in range(12):
                if contribution_timing == "beginning":
                    balance += monthly_contribution
                    year_contributions += monthly_contribution
                    total_contributions += monthly_contribution
                    month_growth = balance * monthly_return
                    growth += month_growth
                    balance += month_growth
                else:
                    month_growth = balance * monthly_return
                    growth += month_growth
                    balance += month_growth
                    balance += monthly_contribution
                    year_contributions += monthly_contribution
                    total_contributions += monthly_contribution

        if i == 0:
            total_contributions += initial_investment

        end_balance = balance
        interest_earned = end_balance - start_balance - year_contributions

        results.append({
            "year": year,
            "snp_return": annual_return,
            "start_balance": start_balance,
            "contributions": year_contributions,
            "interest": interest_earned,
            "end_balance": end_balance,
        })

    return results


# ──────────────────────────────────────────────
# Display
# ──────────────────────────────────────────────

def color_pct(value: float) -> str:
    """Format a percentage with green/red color."""
    color = "green" if value >= 0 else "red"
    sign = "+" if value >= 0 else ""
    return f"[{color}]{sign}{value:.2%}[/{color}]"


def color_money(value: float) -> str:
    """Format money with green/red color."""
    color = "green" if value >= 0 else "red"
    sign = "+" if value >= 0 else "-"
    return f"[{color}]{sign}${abs(value):,.2f}[/{color}]"


def display_results(
    results: list[dict],
    initial_investment: float,
    contribution_amount: float,
    contribution_frequency: str,
    contribution_timing: str,
    start_year: int,
    num_years: int,
):
    if not results:
        console.print("[bold red]No results to display.[/]")
        return

    console.print()

    # ── Parameters panel ──
    params_text = Text()
    params_text.append("Start Year:  ", style="dim")
    params_text.append(f"{start_year}\n", style="bold white")
    params_text.append("End Year:    ", style="dim")
    params_text.append(f"{start_year + num_years - 1}\n", style="bold white")
    params_text.append("Duration:    ", style="dim")
    params_text.append(f"{num_years} years\n", style="bold white")
    params_text.append("Initial:     ", style="dim")
    params_text.append(f"${initial_investment:,.2f}\n", style="bold cyan")
    if contribution_amount > 0:
        params_text.append("Contribution:", style="dim")
        params_text.append(
            f" ${contribution_amount:,.2f} / {contribution_frequency}",
            style="bold cyan",
        )
        params_text.append(f" ({contribution_timing} of {contribution_frequency.rstrip('ly')})\n", style="dim italic")

    console.print(
        Panel(
            params_text,
            title="[bold magenta]📊 Investment Parameters[/]",
            border_style="magenta",
            padding=(1, 2),
        )
    )

    # ── Year-by-year table ──
    table = Table(
        title="[bold]📈 Year-by-Year S&P 500 Growth[/]",
        box=box.ROUNDED,
        border_style="bright_blue",
        header_style="bold bright_white on dark_blue",
        show_lines=True,
        padding=(0, 1),
    )

    table.add_column("Year", justify="center", style="bold", width=6)
    table.add_column("S&P Return", justify="right", width=12)
    table.add_column("Start Balance", justify="right", width=16)
    table.add_column("Contributions", justify="right", width=16)
    table.add_column("Interest", justify="right", width=16)
    table.add_column("End Balance", justify="right", width=16)

    for row in results:
        table.add_row(
            str(row["year"]),
            color_pct(row["snp_return"]),
            f"[white]${row['start_balance']:,.2f}[/]",
            f"[cyan]${row['contributions']:,.2f}[/]",
            color_money(row["interest"]),
            f"[bold white]${row['end_balance']:,.2f}[/]",
        )

    console.print(table)
    console.print()

    # ── Summary ──
    final = results[-1]
    total_contributions = sum(r["contributions"] for r in results)
    total_interest = sum(r["interest"] for r in results)
    end_balance = final["end_balance"]
    total_return_pct = (end_balance - total_contributions) / total_contributions if total_contributions else 0

    summary_table = Table(
        box=box.HEAVY,
        border_style="bright_green",
        show_header=False,
        padding=(0, 2),
        width=50,
    )
    summary_table.add_column("Label", style="bold", width=24)
    summary_table.add_column("Value", justify="right", width=22)

    summary_table.add_row("💰 Starting Amount", f"[cyan]${initial_investment:,.2f}[/]")
    summary_table.add_row("📥 Total Contributions", f"[cyan]${total_contributions:,.2f}[/]")
    summary_table.add_row("📈 Total Interest Earned", color_money(total_interest))
    summary_table.add_row(
        "🏦 [bold]Final Balance[/]",
        f"[bold bright_green]${end_balance:,.2f}[/]",
    )
    summary_table.add_row("📊 Total Return", color_pct(total_return_pct))

    console.print(
        Panel(
            summary_table,
            title="[bold green]✨ Investment Summary[/]",
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()


# ──────────────────────────────────────────────
# User input
# ──────────────────────────────────────────────

def get_user_inputs() -> dict:
    """Interactively gather all investment parameters from the user."""

    console.print()
    console.print(
        Panel(
            "[bold bright_white]S&P 500 Historical Investment Calculator[/]\n"
            "[dim]Simulate how your money would have grown in the S&P 500[/]",
            border_style="bright_magenta",
            padding=(1, 4),
        )
    )
    console.print()

    current_year = datetime.now().year

    # Start year
    while True:
        start_year = IntPrompt.ask(
            "[bold cyan]📅 Enter the start year[/]",
            default=2010,
        )
        if 1928 <= start_year <= current_year:
            break
        console.print(f"[red]Please enter a year between 1928 and {current_year}.[/]")

    # Number of years
    while True:
        num_years = IntPrompt.ask(
            "[bold cyan]⏳ How many years to invest?[/]",
            default=10,
        )
        if 1 <= num_years <= (current_year - start_year + 1):
            break
        console.print(
            f"[red]Please enter between 1 and {current_year - start_year + 1} years "
            f"(data goes up to {current_year}).[/]"
        )

    # Initial investment
    while True:
        initial_investment = FloatPrompt.ask(
            "[bold cyan]💵 Initial investment amount ($)[/]",
            default=10000.0,
        )
        if initial_investment >= 0:
            break
        console.print("[red]Amount must be non-negative.[/]")

    # Recurring contributions
    has_contributions = Confirm.ask(
        "[bold cyan]📥 Add recurring contributions?[/]",
        default=True,
    )

    contribution_amount = 0.0
    contribution_frequency = "monthly"
    contribution_timing = "end"

    if has_contributions:
        while True:
            contribution_amount = FloatPrompt.ask(
                "[bold cyan]   💲 Contribution amount ($)[/]",
                default=500.0,
            )
            if contribution_amount >= 0:
                break
            console.print("[red]Amount must be non-negative.[/]")

        contribution_frequency = Prompt.ask(
            "[bold cyan]   🔁 Contribution frequency[/]",
            choices=["monthly", "yearly"],
            default="monthly",
        )

        contribution_timing = Prompt.ask(
            "[bold cyan]   ⏱️  Contribute at beginning or end of period?[/]",
            choices=["beginning", "end"],
            default="end",
        )

    return {
        "start_year": start_year,
        "num_years": num_years,
        "initial_investment": initial_investment,
        "contribution_amount": contribution_amount,
        "contribution_frequency": contribution_frequency,
        "contribution_timing": contribution_timing,
    }


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    try:
        inputs = get_user_inputs()

        start_year = inputs["start_year"]
        num_years = inputs["num_years"]
        end_year = start_year + num_years - 1

        yearly_data = fetch_snp_data(start_year, end_year)

        if not yearly_data:
            console.print("[bold red]Could not retrieve any S&P 500 data for that range.[/]")
            sys.exit(1)

        results = simulate_investment(
            yearly_data=yearly_data,
            initial_investment=inputs["initial_investment"],
            contribution_amount=inputs["contribution_amount"],
            contribution_frequency=inputs["contribution_frequency"],
            contribution_timing=inputs["contribution_timing"],
            start_year=start_year,
            num_years=num_years,
        )

        display_results(
            results=results,
            initial_investment=inputs["initial_investment"],
            contribution_amount=inputs["contribution_amount"],
            contribution_frequency=inputs["contribution_frequency"],
            contribution_timing=inputs["contribution_timing"],
            start_year=start_year,
            num_years=num_years,
        )

    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/]")
        sys.exit(0)


if __name__ == "__main__":
    main()
