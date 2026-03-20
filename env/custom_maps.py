import re
from pathlib import Path
from random import Random

import yaml

with open(Path(__file__).parent / "maps.yaml", "r") as f:
    maps = yaml.safe_load(f)

with open(Path(__file__).parent / "random-pico.yaml", "r") as f:
    random_pico = yaml.safe_load(f)

with open(Path(__file__).parent / "random.yaml", "r") as f:
    random_map = yaml.safe_load(f)

with open(Path(__file__).parent / "street_map.yaml", "r") as f:
    street = yaml.safe_load(f)

with open(Path(__file__).parent / "maps_3d.yaml", "r") as f:
    maps_3d = yaml.safe_load(f)


def _grid_to_text(grid):
    return "\n".join("".join(row) for row in grid)


def _generate_layered_corridor_map(spec):
    size = int(spec["size"])
    height_levels = int(spec.get("height_levels", 4))
    seed = int(spec.get("seed", 0))
    layers = []

    for z in range(height_levels):
        rng = Random(seed + z * 9973)
        grid = [["." for _ in range(size)] for _ in range(size)]
        stride = max(5, size // 6)
        gap_half = max(1, size // 12)
        edge_margin = max(1, size // 10)

        for idx, row in enumerate(range(stride, size - stride, stride)):
            if (idx + z) % 2 == 1:
                continue
            start = rng.randint(1, max(1, size // 5))
            end = size - rng.randint(2, max(2, size // 5))
            gap_center = rng.randint(size // 6, size - size // 6 - 1)
            for y in range(start, end):
                if gap_center - gap_half <= y <= gap_center + gap_half:
                    continue
                grid[row][y] = "#"

        for idx, col in enumerate(range(stride // 2 + 1, size - stride // 2, stride)):
            if (idx + z) % 2 == 0:
                continue
            start = rng.randint(1, max(1, size // 5))
            end = size - rng.randint(2, max(2, size // 5))
            gap_center = rng.randint(size // 6, size - size // 6 - 1)
            for x in range(start, end):
                if gap_center - gap_half <= x <= gap_center + gap_half:
                    continue
                grid[x][col] = "#"

        for _ in range(max(3, size // 16)):
            block_h = rng.randint(2, max(2, size // 8))
            block_w = rng.randint(2, max(2, size // 8))
            block_x = rng.randint(1, size - block_h - 1)
            block_y = rng.randint(1, size - block_w - 1)
            for x in range(block_x, block_x + block_h):
                for y in range(block_y, block_y + block_w):
                    grid[x][y] = "#"

        for idx in range(size):
            grid[0][idx] = "."
            grid[size - 1][idx] = "."
            grid[idx][0] = "."
            grid[idx][size - 1] = "."

        for row in range(edge_margin, size - edge_margin, stride * 2):
            for y in range(edge_margin, size - edge_margin):
                grid[row][y] = "."
        for col in range(edge_margin, size - edge_margin, stride * 2):
            for x in range(edge_margin, size - edge_margin):
                grid[x][col] = "."

        layers.append(_grid_to_text(grid))

    return {
        "layers": layers,
        "height_levels": height_levels,
        "generated": dict(spec),
    }


def _expand_generated_maps(map_registry):
    expanded = {}
    for map_name, definition in map_registry.items():
        if isinstance(definition, dict) and definition.get("generated"):
            expanded[map_name] = _generate_layered_corridor_map(definition["generated"])
        else:
            expanded[map_name] = definition
    return expanded


maps_3d = _expand_generated_maps(maps_3d)
maps = {**maps, **random_pico, **random_map, **street, **maps_3d}

MAPS_REGISTRY = maps
_test_regexp = '(wc3-[A-P]|sc1-[A-S]|sc1-TaleofTwoCities|street-[A-P]|mazes-s[0-9]_|mazes-s[1-3][0-9]_|random-s[0-9]_|random-s[1-3][0-9]_)'


def split_train_test():
    with open(Path(__file__).parent / "maps.yaml", "r") as f:
        maps = yaml.safe_load(f)
    collections = dict()
    for m in maps:
        if m.split('-')[0] not in collections:
            collections[m.split('-')[0]] = [m]
        else:
            collections[m.split('-')[0]].append(m)
    train = []
    test = []
    for c in collections:
        i = 0
        while (i < len(collections[c]) * 0.8):
            train.append(collections[c][i])
            i += 1
        while i < len(collections[c]):
            test.append(collections[c][i])
            i += 1

    for name in train:
        assert re.match(_test_regexp, name), f'{name} must be in train'

    for name in test:
        assert not re.match(_test_regexp, name), f'{name} must not be in train'


def main():
    with open(Path(__file__).parent / "maps.yaml", "r") as f:
        maps = yaml.safe_load(f)

    train = []
    test = []
    for name in maps:
        if re.match(_test_regexp, name):
            train.append(name)
        else:
            test.append(name)
    print(train)
    print(test)


if __name__ == '__main__':
    main()
