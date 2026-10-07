from .models import Link

TILE_SIZE = 80
TILE_GAP = 12
TILE_MARGIN = 8
TILE_COLUMNS = 3


def next_tile_position(links: list[Link]) -> tuple[int, int]:
    """Find an empty initial slot without covering freely positioned tiles."""
    index = 0
    while True:
        x = TILE_MARGIN + (index % TILE_COLUMNS) * (TILE_SIZE + TILE_GAP)
        y = TILE_MARGIN + (index // TILE_COLUMNS) * (TILE_SIZE + TILE_GAP)
        if not any(
            link.x is not None and link.y is not None
            and x < link.x + TILE_SIZE and x + TILE_SIZE > link.x
            and y < link.y + TILE_SIZE and y + TILE_SIZE > link.y
            for link in links
        ):
            return x, y
        index += 1
