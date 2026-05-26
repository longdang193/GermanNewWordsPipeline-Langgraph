from __future__ import annotations
import argparse
import sys
import pathlib
from .core import process_markdown, extract_words, preprocess_file1, merge_see_also


def main() -> int:
    parser = argparse.ArgumentParser(prog="mdproc")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("process")
    p1.add_argument("input")
    p1.add_argument("--output")

    p2 = sub.add_parser("words")
    p2.add_argument("input")
    p2.add_argument("--output")

    p3 = sub.add_parser("preprocess")
    p3.add_argument("file1")
    p3.add_argument("--output")

    p4 = sub.add_parser("merge-see-also")
    p4.add_argument("file1")
    p4.add_argument("file2")
    p4.add_argument("--output")

    args = parser.parse_args()

    if args.cmd == "process":
        inp = pathlib.Path(args.input).read_text(encoding="utf-8")
        out = process_markdown(inp)
    elif args.cmd == "words":
        inp = pathlib.Path(args.input).read_text(encoding="utf-8")
        words = extract_words(inp)
        out = "".join(f"- {w}\n" for w in words)
    elif args.cmd == "preprocess":
        text1 = pathlib.Path(args.file1).read_text(encoding="utf-8")
        out = preprocess_file1(text1)
    elif args.cmd == "merge-see-also":
        text1 = pathlib.Path(args.file1).read_text(encoding="utf-8")
        text2 = pathlib.Path(args.file2).read_text(encoding="utf-8")
        out = merge_see_also(text1, text2)

    if args.output:
        pathlib.Path(args.output).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
