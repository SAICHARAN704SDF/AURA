"""Print AURA's compiled LangGraph topology without executing any nodes.

Uses the adjacent backend/src checkout; install its dependencies first.
The text view lists real
edges; --format mermaid exports LangGraph's diagram source for a renderer.
This is the orchestration topology, not a live run or its research task plan.
"""
import argparse
from pathlib import Path
import sys

# Direct script execution normally adds scripts/, not backend/src, to sys.path.
# Resolve from this file so the command also works outside the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / 'backend' / 'src'))


def main():
    """Compile only the graph structure and print the requested diagram format."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', choices=('text', 'mermaid'), default='text')
    args = parser.parse_args()
    try:
        from aura.orchestration.graph.workflow import build_graph
    except ModuleNotFoundError as exc:
        parser.exit(1, f"Missing dependency: {exc.name}. Install AURA into this Python environment:\n"
                    f'  "{sys.executable}" -m pip install -e "{PROJECT_ROOT}"\n')
    # These dependencies are captured by node closures, but never used here:
    # get_graph inspects topology; no invoke/ainvoke call is made.
    graph = build_graph(None, None, None).get_graph()
    if args.format == 'mermaid':
        print(graph.draw_mermaid())
        return
    print('AURA — actual LangGraph topology (not a live execution)\n')
    for edge in graph.edges:
        arrow = '- - >' if edge.conditional else '---->'
        print(f'[{edge.source}] {arrow} [{edge.target}]')
    print('\nDashed arrows are conditional. task_wave repeats until tasks finish.')
    print('Research/analysis tasks run inside task_wave; they are not separate graph nodes.')


if __name__ == '__main__':
    main()
