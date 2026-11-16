import argparse

COMMANDES = ("run", "init-db", "stats")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="denicheur")
    sub = parser.add_subparsers(dest="commande", required=True)
    for nom in COMMANDES:
        sub.add_parser(nom)
    args = parser.parse_args(argv)
    print(f"{args.commande} : non implémenté")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
