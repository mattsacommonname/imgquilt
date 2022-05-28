import enum
from argparse import ArgumentParser, FileType
from enum import Enum
from logging import DEBUG, debug, getLogger, INFO, Logger, WARNING
from math import ceil, sqrt
from os.path import exists
from PIL import Image
from typing import List, Tuple


@enum.unique
class Direction(str, Enum):
    """Enumeration of tiling directions."""

    HORIZONTAL = "h"
    VERTICAL = "v"


class CoordinateBuilder:
    """Generates column, row coordinates for a tableau.

    Attributes:
        column_count: The number of columns.
        current_column: The current column (will be returned by the next call to next).
        current_row: The current row (will be returned by the next call to next).
        direction: The direction.
        row_count: The number of rows.
    """

    def __init__(
        self, direction: Direction, column_count: int, row_count: int, starting_column: int = 0, starting_row: int = 0
    ):
        """Initializes builder.

        Note that the specified starting column and row will be returned from the first call to `next`.

        :param direction: Direction of the tiling.
        :param column_count: Number of columns.
        :param row_count: Number of rows.
        :param starting_column: Starting column.
        :param starting_row: Starting row.
        """

        self.column_count = column_count
        self.current_column = starting_column
        self.current_row = starting_row
        self.direction = direction
        self.row_count = row_count

    def increment(self, step: int = 1):
        """Increments to the next tile with respect to the directionality.

        :param step: Step size.
        """

        if self.direction == Direction.HORIZONTAL:
            self.increment_horizontal(step)
        elif self.direction == Direction.VERTICAL:
            self.increment_vertical(step)

    def increment_horizontal(self, step: int = 1):
        """Horizontally increments to the next tile.

        :param step: Step size.
        """

        self.current_column += step
        if self.current_column < self.column_count:
            return
        self.current_column = 0
        self.current_row += 1

    def increment_vertical(self, step: int = 1):
        """Vertically increments to the next tile.

        :param step: Step size.
        """

        self.current_row += step
        if self.current_row < self.row_count:
            return
        self.current_row = 0
        self.current_column += 1

    def next(self) -> Tuple[int, int]:
        """Returns the next tile's coordinates."""

        coordinate = self.current_column, self.current_row
        self.increment(1)
        return coordinate

    def set(self, column: int, row: int):
        """Sets the current tile coordinates.

        Note: this will be the next coordinate returned.

        :param column: The column.
        :param row: The row.
        """

        self.current_column = column
        self.current_row = row


class Tile:
    """Holds an image, and it's location in the tableau.

    Attributes:
        image: The image.
        location: The pixel x,y location to paste the image.
    """

    def __init__(self, image: Image.Image, location: Tuple[int, int]):
        """Creates a tile.

        :param image: The image for that tile.
        :param location: The tile's location in pixels.
        """

        self.image = image
        self.location = location


class Tableau:
    """Builds and holds a collection of (potentially irregularly) tiled images.

    Tableau is probably a bad word for this, but I'm not changing it now.

    Attributes:
        output_size: Required dimensions of the output image to fit all tiles.
        tiles: The tiles that the final image will be built using.
    """

    def __init__(
        self,
        images: List[Image.Image],
        direction: Direction,
        max_columns: int = 0,
        max_rows: int = 0,
        logger: Logger = getLogger(),
    ):
        """Creates an image tile tableau.

        Calculates the positions and sizing based on the inputted images and defined parameters (direction, max sizes,
        etc).

        :param images: The inputted images.
        :param direction: The direction to tile in.
        :param max_columns: Maximum number of columns.
        :param max_rows: Maximum number of rows.
        :param logger: A logger, if you feel like it.
        """

        self._logger = logger

        self._logger.debug(f"direction {direction}")

        # calculate the number of rows, columns and images to output (if a max row & column combination would result in
        # less images than passed in being displayed). If no max for row or column is defined, the calculation attempts
        # to make the tableau as square as possible

        max_columns = max(max_columns, 0)
        self._logger.debug(f"max_columns {max_columns}")
        max_rows = max(max_rows, 0)
        self._logger.debug(f"max_rows {max_rows}")
        max_image_count = max_columns * max_rows

        self._count = len(images)
        if max_image_count > 0:
            self._count = min(self._count, max_image_count)
        self._logger.debug(f"image count {self._count}")

        if direction == Direction.HORIZONTAL:
            column_count, row_count = self._calculate_counts(max_columns, max_rows)
        else:
            row_count, column_count = self._calculate_counts(max_rows, max_columns)

        self._logger.debug(f"column_count {column_count}")
        self._logger.debug(f"row_count {row_count}")

        # restrict the image's we're working with

        self._images = images[: self._count]

        # calculate each column's width and row's height

        column_widths = (
            self._direction_vector_dimensions(column_count, 0)
            if direction == Direction.HORIZONTAL
            else self._perpendicular_vector_dimensions(column_count, row_count, 0)
        )
        self._logger.debug(f"column_widths {column_widths}")
        self.row_heights = (
            self._perpendicular_vector_dimensions(row_count, column_count, 1)
            if direction == Direction.HORIZONTAL
            else self._direction_vector_dimensions(row_count, 1)
        )
        self._logger.debug(f"row_heights {self.row_heights}")

        # calculate the output image's size

        self.output_size = sum(column_widths), sum(self.row_heights)
        self._logger.debug(f"output_size {self.output_size}")

        # calculate the starting locations by row & column

        self._column_starts = [sum(column_widths[0:i]) for i in range(column_count)]
        self._logger.debug(f"column_starts {self._column_starts}")
        self._row_starts = [sum(self.row_heights[0:i]) for i in range(row_count)]
        self._logger.debug(f"row_starts {self._row_starts}")

        # build the tiles, specifying their locations

        coordinate_builder = CoordinateBuilder(direction, column_count, row_count)
        self.tiles = [Tile(image, self._location_builder(coordinate_builder.next())) for image in images[: self._count]]

    def _calculate_counts(self, max_directional: int, max_perpendicular: int) -> Tuple[int, int]:
        """Calculates the row and column counts given the tiling direction within the given maximums.

        :param max_directional: Maximum count for the vector in the tiling direction.
        :param max_perpendicular: Maximum count for the vector perpendicular to the tiling direction.
        :return: The row, column count in directional, perpendicular order.
        """

        directional_count = ceil(sqrt(self._count))
        perpendicular_count = ceil(self._count / directional_count)

        if max_directional < 1 and max_perpendicular > 0:
            perpendicular_count = min(perpendicular_count, max_perpendicular)
            directional_count = ceil(self._count / perpendicular_count)
        elif max_directional > 0 and max_perpendicular < 1:
            directional_count = min(directional_count, max_directional)
            perpendicular_count = ceil(self._count / directional_count)
        elif max_directional > 0 and max_perpendicular > 0:
            directional_count = min(directional_count, max_directional)
            perpendicular_count = min(ceil(self._count / directional_count), max_perpendicular)

        return directional_count, perpendicular_count

    def _direction_vector_dimensions(self, direction_vector_count: int, dimension: int) -> List[int]:
        """Calculates the dimensions for a given vector.

        E.g. the widths of the columns.

        :param direction_vector_count: Number of tiles in the vector.
        :param dimension: The dimension to calculate with, 0 for width (x-dimension), 1 for height (y-dimension).
        :return: A list of dimensions for a vector.
        """

        return [
            max(image.size[dimension] for image in self._images[vector::direction_vector_count])
            for vector in range(direction_vector_count)
        ]

    def _location_builder(self, coordinates: Tuple[int, int]) -> Tuple[int, int]:
        """Calculates a tile's pixel location based on its column, row coordinates.

        :param coordinates: The column, row coordinates to calculate the location for.
        :return: The x,y pixel location for the given coordinates.
        """

        location = self._column_starts[coordinates[0]], self._row_starts[coordinates[1]]
        self._logger.debug(f"location {location} for coordinates {coordinates}")
        return location

    def _perpendicular_vector_dimensions(
        self, perpendicular_vector_count: int, direction_vector_count: int, dimension: int
    ) -> List[int]:
        """Calculates the vector dimensions for the perpendicular vector.

        E.g. the heights for the rows.

        :param perpendicular_vector_count: Count for the perpendicular vector.
        :param direction_vector_count: Count for the directional vector.
        :param dimension: The dimension to calculate with, 0 for width (x-dimension), 1 for height (y-dimension).
        :return: A list of dimensions for a vector.
        """

        return [
            max(
                image.size[dimension]
                for image in self._images[
                    vector * direction_vector_count : (vector * direction_vector_count) + direction_vector_count
                ]
            )
            for vector in range(perpendicular_vector_count)
        ]


def main():
    """Entry point."""

    # arguments

    parser = ArgumentParser()

    parser.add_argument("-b", "--background-color", default="white", help="Background color for gaps between images.")
    parser.add_argument(
        "-c",
        "--max-columns",
        default=0,
        help="Maximum number of columns of images. If set less than 1, no maximum.",
        type=int,
    )
    parser.add_argument(
        "-d",
        "--direction",
        choices=[e.value for e in Direction],
        default=Direction.HORIZONTAL,
        help="The direction to place the tiles in.",
        type=Direction,
    )  # TODO: linting thinks e.value is an unresolved reference, figure out why
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite output file if it exists.")
    parser.add_argument("-o", "--output", help="Output file name.", required=True)
    parser.add_argument(
        "-r", "--max-rows", default=0, help="Maximum number of rows of images. If less than 1, no maximum.", type=int
    )
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Verbosity.")
    parser.add_argument("input_files", help="Files to tile.", nargs="+", type=FileType("rb"))

    args = parser.parse_args()

    # set logging

    logging_level = {0: WARNING, 1: INFO}.get(args.verbose, DEBUG)

    log = getLogger()
    log.setLevel(logging_level)
    debug(f"debug logging on")  # TODO: HACK: if not present DEBUG & INFO do not log. Figure out why.

    # check for output file if not forcing it

    if not args.force and exists(args.output):
        log.error(f"Output file {args.output} already exists")
        exit(1)

    try:
        # build tile tableau

        tableau = Tableau(
            [Image.open(file) for file in args.input_files], args.direction, args.max_columns, args.max_rows, log
        )

        # instantiate output image

        output_image = Image.new("RGB", tableau.output_size, args.background_color)

        # paste tiles onto output image

        for tile in tableau.tiles:
            log.debug(f"location {tile.location}")
            output_image.paste(tile.image, tile.location)

        # save output image

        output_image.save(args.output)

    except Exception as ex:  # TODO: use more specific exceptions
        log.critical("Failed to build output image")
        log.exception(ex)
        exit(1)


if __name__ == "__main__":
    main()