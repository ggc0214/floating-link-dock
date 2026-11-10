TILE_SIZE = 80
TILE_GAP = 12
TILE_MARGIN = 8
TILE_COLUMNS = 3


def next_tile_position(tiles) -> tuple[int, int]:
    """Find an empty initial slot without covering freely positioned tiles."""
    index = 0
    while True:
        x = TILE_MARGIN + (index % TILE_COLUMNS) * (TILE_SIZE + TILE_GAP)
        y = TILE_MARGIN + (index // TILE_COLUMNS) * (TILE_SIZE + TILE_GAP)
        if not any(
            tile.x is not None and tile.y is not None
            and x < tile.x + TILE_SIZE and x + TILE_SIZE > tile.x
            and y < tile.y + TILE_SIZE and y + TILE_SIZE > tile.y
            for tile in tiles
        ):
            return x, y
        index += 1
