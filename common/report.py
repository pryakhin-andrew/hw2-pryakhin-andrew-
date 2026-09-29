def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def section(title: str) -> None:
    print(f"\n## {title}\n")
