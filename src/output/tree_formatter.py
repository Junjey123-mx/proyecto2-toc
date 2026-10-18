UNAVAILABLE = "Parse tree: no disponible."
BRANCH = "├── "
LAST_BRANCH = "└── "
PIPE_INDENT = "│   "
SPACE_INDENT = "    "


def visible_children(node, hidden_symbols):
    if node.token is not None:
        return [node.token]
    items = []
    for child in node.children:
        if child.symbol in hidden_symbols:
            items.extend(visible_children(child, hidden_symbols))
        else:
            items.append(child)
    return items


def append_children(lines, items, prefix, hidden_symbols):
    for index, item in enumerate(items):
        last = index == len(items) - 1
        connector = LAST_BRANCH if last else BRANCH
        if isinstance(item, str):
            lines.append(f"{prefix}{connector}{item}")
            continue
        lines.append(f"{prefix}{connector}{item.symbol}")
        child_prefix = prefix + (SPACE_INDENT if last else PIPE_INDENT)
        append_children(lines, visible_children(item, hidden_symbols), child_prefix, hidden_symbols)


def format_parse_tree(tree, hidden_symbols=()):
    if tree is None:
        return UNAVAILABLE
    hidden = frozenset(hidden_symbols)
    lines = [tree.symbol]
    append_children(lines, visible_children(tree, hidden), "", hidden)
    return "\n".join(lines)
