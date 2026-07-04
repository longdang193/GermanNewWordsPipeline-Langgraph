from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS_SRC = ROOT / "Tools" / "src"
if str(TOOLS_SRC) not in sys.path:
    sys.path.insert(0, str(TOOLS_SRC))

from gnw_pipeline.langgraph_app import build_steps
from gnw_pipeline.nw1_steps import build_nw1_steps


def test_langgraph_and_shared_nw1_steps_stay_in_parity() -> None:
    shared_generate, shared_validate, shared_qa = build_nw1_steps(root=ROOT)
    graph_steps = build_steps(ROOT)

    assert graph_steps[0].name == shared_generate.name
    assert graph_steps[0].cmd == shared_generate.cmd
    assert graph_steps[0].continue_on_parseable_blocks is True

    assert graph_steps[1].name == shared_validate.name
    assert graph_steps[1].cmd == shared_validate.cmd
    assert graph_steps[1].continue_on_parseable_blocks is True

    assert graph_steps[2].name == shared_qa.name
    assert graph_steps[2].cmd == shared_qa.cmd
    assert graph_steps[2].allow_nonzero is True
