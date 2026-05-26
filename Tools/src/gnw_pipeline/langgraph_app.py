from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    root: str
    clear_proxy: bool
    last_step: str
    enable_nw1_qa: bool


@dataclass(frozen=True)
class CommandStep:
    name: str
    cmd: list[str]


def _run_step(state: PipelineState, step: CommandStep) -> PipelineState:
    root = Path(state["root"])
    env = None
    if state.get("clear_proxy"):
        import os

        env = os.environ.copy()
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env[k] = ""

    proc = subprocess.run(step.cmd, cwd=str(root), env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"step failed: {step.name} exit={proc.returncode}")

    state["last_step"] = step.name
    return state


def build_graph() -> Any:
    # Lazy import so Tools can be installed without langgraph extra.
    from langgraph.graph import StateGraph, END  # type: ignore[import-not-found]

    graph = StateGraph(PipelineState)

    root = Path(__file__).resolve().parents[3]
    scripts = root / "Tools" / "scripts"

    steps: list[CommandStep] = [
        CommandStep("nw1_generate", [sys.executable, str(scripts / "process_requirement1.py")]),
        CommandStep("nw1_validate", [sys.executable, str(scripts / "validate_word_list.py")]),
        CommandStep("nw1_qa_review", [sys.executable, str(scripts / "nw1_qa_review.py"), "--root", "."]),
        CommandStep("nw2_process", ["py", "-m", "mdproc", "process", "Outputs/01_words.md", "--output", "Outputs/02_words_fixed.md"]),
        CommandStep("nw2_words", ["py", "-m", "mdproc", "words", "Outputs/02_words_fixed.md", "--output", "Outputs/03_word_list.md"]),
        CommandStep("nw3_query", [sys.executable, str(scripts / "query_see_also_notebooklm.py"), "--root", ".", "--mcp-url", "http://127.0.0.1:8010/mcp"]),
        CommandStep("nw3_preprocess", ["py", "-m", "mdproc", "preprocess", "Outputs/04_see_also.md", "--output", "Outputs/05_see_also_fixed.md"]),
        CommandStep("nw3_merge", ["py", "-m", "mdproc", "merge-see-also", "Outputs/05_see_also_fixed.md", "Outputs/02_words_fixed.md", "--output", "Outputs/06_words_final.md"]),
        CommandStep("nw4_process", [sys.executable, str(scripts / "process_requirement4.py")]),
        CommandStep("nw4_validate", [sys.executable, str(scripts / "validate_requirement4.py")]),
    ]

    for i, step in enumerate(steps):
        node_name = step.name

        def make_fn(s: CommandStep):
            def fn(st: PipelineState):
                if s.name == "nw1_qa_review" and not st.get("enable_nw1_qa", False):
                    st["last_step"] = "nw1_qa_review(skipped)"
                    return st
                return _run_step(st, s)

            return fn

        graph.add_node(node_name, make_fn(step))
        if i == 0:
            graph.set_entry_point(node_name)
        else:
            graph.add_edge(steps[i - 1].name, node_name)

    graph.add_edge(steps[-1].name, END)
    return graph.compile()


def run(*, root: Path, clear_proxy: bool) -> None:
    app = build_graph()
    init: PipelineState = {
        "root": str(root),
        "clear_proxy": clear_proxy,
        "enable_nw1_qa": bool(int(__import__("os").environ.get("GNW_ENABLE_NW1_QA", "0"))),
    }
    app.invoke(init)
