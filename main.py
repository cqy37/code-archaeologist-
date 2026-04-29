#!/usr/bin/env python3
"""
Code Archaeologist - Main CLI Entry Point
"""

import argparse
import json
import os
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from core.dependency_graph import DependencyGraph
from core.knowledge_base import KnowledgeBase
from utils.llm_client import LLMClient
from agents.explorer import ExplorerAgent
from agents.reasoner import ReasonerAgent
from agents.refactor import RefactorAgent
from agents.validator import ValidatorAgent

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def cmd_analyze(args):
    config = load_config(args.config)
    kb = KnowledgeBase(db_path=args.db)
    graph = DependencyGraph()
    explorer = ExplorerAgent(config.get("explorer", {}))

    console.print(Panel(f"[bold cyan]Exploring[/] {args.directory}", box=box.ROUNDED))
    result = explorer.explore(args.directory, kb, graph)

    # Display results
    table = Table(title="Exploration Results", box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Files Scanned", str(result["total_files"]))
    table.add_row("Successfully Parsed", str(result["parsed_files"]))
    table.add_row("Hotspots Found", str(len(result["hotspots"])))
    table.add_row("Orphans (Dead Code?)", str(len(result["orphans"])))
    table.add_row("Circular Dependencies", str(len(result["cycles"])))
    console.print(table)

    if result["hotspots"]:
        ht = Table(title="Top Hotspots", box=box.SIMPLE_HEAD)
        ht.add_column("File", style="yellow")
        ht.add_column("Centrality", justify="right")
        ht.add_column("In", justify="right")
        ht.add_column("Out", justify="right")
        for h in result["hotspots"][:5]:
            ht.add_row(Path(h["file"]).name, str(h["centrality"]), str(h["in_degree"]), str(h["out_degree"]))
        console.print(ht)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Report saved to {args.output}[/]")


def cmd_reason(args):
    config = load_config(args.config)
    kb = KnowledgeBase(db_path=args.db)
    llm = LLMClient(**config.get("llm", {}))
    reasoner = ReasonerAgent(llm, config.get("reasoner", {}))

    if not llm.is_available():
        console.print("[yellow]Warning: No LLM API key found. Running in mock mode.[/]")

    if args.file:
        console.print(Panel(f"[bold cyan]Reasoning about[/] {args.file}", box=box.ROUNDED))
        result = reasoner.analyze(args.file, kb)
    else:
        console.print(Panel(f"[bold cyan]Reasoning about module[/] {args.target}", box=box.ROUNDED))
        result = reasoner.analyze_module(args.target, kb)

    console.print_json(json.dumps(result, ensure_ascii=False, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Report saved to {args.output}[/]")


def cmd_plan(args):
    config = load_config(args.config)
    kb = KnowledgeBase(db_path=args.db)
    llm = LLMClient(**config.get("llm", {}))
    refactor = RefactorAgent(llm, config.get("refactor", {}))

    if not llm.is_available():
        console.print("[yellow]Warning: No LLM API key found. Running in mock mode.[/]")

    console.print(Panel(f"[bold cyan]Generating modernization plan for[/] {args.target}", box=box.ROUNDED))
    plan = refactor.plan(args.target, kb)

    if plan.get("parse_error"):
        console.print("[red]Could not parse structured plan. Raw output:[/]")
        console.print(plan.get("raw_plan", "N/A"))
    else:
        console.print_json(json.dumps(plan, ensure_ascii=False, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Plan saved to {args.output}[/]")


def cmd_pipeline(args):
    config = load_config(args.config)
    kb = KnowledgeBase(db_path=args.db)
    kb.clear()

    graph = DependencyGraph()
    llm = LLMClient(**config.get("llm", {}))

    explorer = ExplorerAgent(config.get("explorer", {}))
    reasoner = ReasonerAgent(llm, config.get("reasoner", {}))
    refactor = RefactorAgent(llm, config.get("refactor", {}))
    validator = ValidatorAgent(llm, config.get("validator", {}))

    if not llm.is_available():
        console.print("[yellow]Warning: No LLM API key found. Running in mock/demo mode.[/]")

    # Step 1: Explore
    console.print(Panel("[bold]Step 1: Exploration[/]", box=box.HEAVY, style="blue"))
    explore_result = explorer.explore(args.directory, kb, graph)
    console.print(f"Scanned {explore_result['total_files']} files, {explore_result['parsed_files']} parsed.")

    # Step 2: Reason
    console.print(Panel("[bold]Step 2: Business Intent Reconstruction[/]", box=box.HEAVY, style="magenta"))
    reason_result = reasoner.analyze_module(args.target, kb)
    summary = reason_result.get("summary", {})
    console.print(f"Primary Domain: [cyan]{summary.get('primary_domain', 'unknown')}[/]")
    console.print(f"Files Analyzed: {summary.get('files_count', 0)}")
    console.print(f"Key Entities: {', '.join(summary.get('key_entities', [])[:5])}")

    # Step 3: Refactor
    console.print(Panel("[bold]Step 3: Modernization Planning[/]", box=box.HEAVY, style="yellow"))
    plan = refactor.plan(args.target, kb)
    console.print(f"Strategy: [cyan]{plan.get('strategy', 'N/A')}[/]")
    console.print(f"Estimated Risk: [bold {'green' if plan.get('estimated_risk')=='low' else 'red'}]{plan.get('estimated_risk', 'unknown').upper()}[/]")
    if plan.get("steps"):
        for i, step in enumerate(plan["steps"][:5], 1):
            console.print(f"  {i}. {step}")

    # Step 4: Validate
    console.print(Panel("[bold]Step 4: Validation[/]", box=box.HEAVY, style="green"))
    validation = validator.validate(plan, kb)
    approval = validation.get("approval", False)
    console.print(f"Behavioral Consistency: [cyan]{validation.get('behavioral_consistency', 'unknown')}[/]")
    console.print(f"Approval: [bold {'green' if approval else 'red'}]{'APPROVED' if approval else 'REJECTED'}[/]")
    if validation.get("warnings"):
        for w in validation["warnings"]:
            console.print(f"  [yellow]⚠ {w}[/]")

    # Final report
    report = {
        "directory": args.directory,
        "target": args.target,
        "exploration": explore_result,
        "reasoning": reason_result,
        "plan": plan,
        "validation": validation,
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        console.print(f"\n[green]Full pipeline report saved to {args.output}[/]")

    return report


def main():
    parser = argparse.ArgumentParser(
        prog="code-archaeologist",
        description="AI-powered legacy codebase analysis and modernization",
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--db", default=".code_archaeologist.db", help="Knowledge base SQLite path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Analyze
    analyze_parser = subparsers.add_parser("analyze", help="Explore and map a codebase")
    analyze_parser.add_argument("directory", help="Target directory to analyze")
    analyze_parser.add_argument("--output", "-o", help="Output JSON file")
    analyze_parser.set_defaults(func=cmd_analyze)

    # Reason
    reason_parser = subparsers.add_parser("reason", help="Infer business intent from code")
    reason_parser.add_argument("--file", help="Specific file to analyze")
    reason_parser.add_argument("--target", default="", help="Module/target name")
    reason_parser.add_argument("--output", "-o", help="Output JSON file")
    reason_parser.set_defaults(func=cmd_reason)

    # Plan
    plan_parser = subparsers.add_parser("plan", help="Generate modernization plan")
    plan_parser.add_argument("target", help="Target module name")
    plan_parser.add_argument("--output", "-o", help="Output JSON file")
    plan_parser.set_defaults(func=cmd_plan)

    # Pipeline
    pipeline_parser = subparsers.add_parser("pipeline", help="Run full pipeline")
    pipeline_parser.add_argument("directory", help="Target directory")
    pipeline_parser.add_argument("--target", required=True, help="Target module name")
    pipeline_parser.add_argument("--output", "-o", default="pipeline_report.json", help="Output JSON file")
    pipeline_parser.set_defaults(func=cmd_pipeline)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
