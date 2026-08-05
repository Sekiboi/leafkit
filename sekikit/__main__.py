"""Allow `python -m sekikit` (GUI) or `python -m sekikit.cli`."""

import sys

if __name__ == "__main__":
    # Default GUI; CLI when argv is a known subcommand.
    if len(sys.argv) > 1 and sys.argv[1] in (
        "info",
        "merge",
        "extract",
        "split",
        "compress",
        "rotate",
        "delete",
        "mix",
        "insert",
        "images",
        "assemble",
        "crop",
        "crop-box",
        "clean",
        "encrypt",
        "decrypt",
        "resize",
        "reverse",
        "blank",
        "stamp-image",
        "text",
        "nup",
        "grayscale",
        "page-numbers",
        "renumber",
        "flatten",
        "watch",
        "gui",
        "-h",
        "--help",
        "--version",
    ):
        from sekikit.cli import main as cli_main

        raise SystemExit(cli_main())
    from sekikit.app import main as gui_main

    gui_main()
