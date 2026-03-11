from __future__ import annotations

from configuration.parser import setup_parser


def test_setup_parser_should_generate_a_valid_parser() -> None:
    parser = setup_parser()
    parser.print_help()
