import enum
from argparse import ArgumentParser, FileType
from enum import Enum
from logging import DEBUG, debug, getLogger, INFO, Logger, WARNING
from math import ceil, floor, sqrt
from os.path import exists
from PIL import Image
from typing import Iterator, List, Tuple


@enum.unique
class Direction(str, Enum):
    """Enumeration of tiling directions."""

    HORIZONTAL = "h"
    VERTICAL = "v"


@enum.unique
class HorizontalAlignment(str, Enum):
    """Enumeration of horizontal tile alignments."""

    CENTER = "c"
    LEFT = "l"
    RIGHT = "r"


@enum.unique
class SizingMode(str, Enum):
    """Image tile dimension sizing mode."""

    AVERAGE = "a"
    LARGEST = "l"
    SMALLEST = "s"


@enum.unique
class StretchMode(str, Enum):
    """Image tile stretching mode."""

    FILL = "f"
    ORIGINAL = "o"
    RATIO = "r"


@enum.unique
class VerticalAlignment(str, Enum):
    """Enumeration of vertical tile alignments."""

    BOTTOM = "b"
    MIDDLE = "m"
    TOP = "t"


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
    """

    def __init__(
        self,
        images: List[Image.Image],
        direction: Direction,
        max_columns: int = 0,
        max_rows: int = 0,
        horizontal_alignment: HorizontalAlignment = HorizontalAlignment.LEFT,
        vertical_alignment: VerticalAlignment = VerticalAlignment.TOP,
        sizing_mode: SizingMode = SizingMode.LARGEST,
        stretch_mode: StretchMode = StretchMode.ORIGINAL,
        logger: Logger = getLogger(),
    ):
        """Creates an image tile tableau.

        Calculates the positions and sizing based on the inputted images and defined parameters (direction, max sizes,
        etc).

        :param images: The inputted images.
        :param direction: The direction to tile in.
        :param max_columns: Maximum number of columns.
        :param max_rows: Maximum number of rows.
        :param horizontal_alignment: The horizontal alignment of the tiles.
        :param sizing_mode: The image resizing mode.
        :param stretch_mode: The image stretching mode.
        :param vertical_alignment: The vertical alignment of the tiles.
        :param logger: A logger, if you feel like it.
        """

        self._direction = direction
        self._horizontal_alignment = horizontal_alignment
        self._logger = logger
        self._sizing_mode = sizing_mode
        self._stretch_mode = stretch_mode
        self._vertical_alignment = vertical_alignment

        self._logger.debug(f"direction {self._direction}")
        self._logger.debug(f"horizontal_alignment {self._horizontal_alignment}")
        self._logger.debug(f"resize_mode {self._sizing_mode}")
        self._logger.debug(f"stretch_mode {self._stretch_mode}")
        self._logger.debug(f"vertical_alignment {self._vertical_alignment}")

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
            self._column_count, self._row_count = self._calculate_counts(max_columns, max_rows)
        else:
            self._row_count, self._column_count = self._calculate_counts(max_rows, max_columns)

        self._logger.debug(f"column_count {self._column_count}")
        self._logger.debug(f"row_count {self._row_count}")

        # restrict the image's we're working with

        self._images = images[: self._count]

        # calculate each column's width and row's height

        self._column_widths = (
            self._direction_vector_dimensions(self._column_count, 0)
            if direction == Direction.HORIZONTAL
            else self._perpendicular_vector_dimensions(self._column_count, self._row_count, 0)
        )
        self._logger.debug(f"column_widths {self._column_widths}")
        self._row_heights = (
            self._perpendicular_vector_dimensions(self._row_count, self._column_count, 1)
            if direction == Direction.HORIZONTAL
            else self._direction_vector_dimensions(self._row_count, 1)
        )
        self._logger.debug(f"row_heights {self._row_heights}")

        # calculate the output image's size

        self.output_size = sum(self._column_widths), sum(self._row_heights)
        self._logger.debug(f"output_size {self.output_size}")

        # calculate the starting locations by row & column

        self._column_starts = [sum(self._column_widths[0:i]) for i in range(self._column_count)]
        self._logger.debug(f"column_starts {self._column_starts}")
        self._row_starts = [sum(self._row_heights[0:i]) for i in range(self._row_count)]
        self._logger.debug(f"row_starts {self._row_starts}")

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

    def _location_builder(self, coordinates: Tuple[int, int], image_size: Tuple[int, int]) -> Tuple[int, int]:
        """Calculates a tile's pixel location based on its column, row coordinates.

        :param coordinates: The column, row coordinates to calculate the location for.
        :param image_size: The size of the image the location is being calculated for.
        :return: The x,y pixel location for the given coordinates.
        """

        alignment_shift = 0
        if self._horizontal_alignment == HorizontalAlignment.CENTER:
            alignment_shift = floor((self._column_widths[coordinates[0]] - image_size[0]) / 2)
        elif self._horizontal_alignment == HorizontalAlignment.RIGHT:
            alignment_shift = self._column_widths[coordinates[0]] - image_size[0]

        self._logger.debug(f"horizontal alignment_shift {alignment_shift}")

        x = self._column_starts[coordinates[0]] + alignment_shift

        alignment_shift = 0
        if self._vertical_alignment == VerticalAlignment.MIDDLE:
            alignment_shift = floor((self._row_heights[coordinates[1]] - image_size[1]) / 2)
        elif self._vertical_alignment == VerticalAlignment.BOTTOM:
            alignment_shift = self._row_heights[coordinates[1]] - image_size[1]

        self._logger.debug(f"vertical alignment_shift {alignment_shift}")

        y = self._row_starts[coordinates[1]] + alignment_shift

        self._logger.debug(f"location {x}, {y} for {coordinates}")

        return x, y

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

    def _resize(self, image: Image.Image, coordinate: Tuple[int, int]) -> Image.Image:
        """Resizes and stretches an image based on the resize and stretch modes.

        Note: This is not guaranteed to generate a new image. If the image did not need to be resized, no new image will
        be generated.

        :param image: The image to resize & stretch.
        :param coordinate: The image's coordinates.
        :return: The resized & stretched image. Note: this is potentially the original image.
        """

        # this mode combination requires no resizing
        if self._stretch_mode == StretchMode.ORIGINAL and self._sizing_mode == SizingMode.LARGEST:
            return image

        return image

    def tiles(self) -> Iterator[Tile]:
        """Generates the tiles, with their location and sizes calculated.

        :return: Yields an iterator of the image tiles.
        """

        coordinate_builder = CoordinateBuilder(self._direction, self._column_count, self._row_count)

        for image in self._images:
            coordinate = coordinate_builder.next()
            resized_imaged = self._resize(image, coordinate)
            yield Tile(resized_imaged, self._location_builder(coordinate, image.size))


def main():
    """Entry point."""

    # arguments

    parser = ArgumentParser()

    # background color
    parser.add_argument("-b", "--background-color", default="white", help="Background color for gaps between images.")

    # maximum columns
    parser.add_argument(
        "-c",
        "--max-columns",
        default=0,
        help="Maximum number of columns of images. If set less than 1, no maximum.",
        type=int,
    )

    # tiling direction
    # TODO: linting thinks e.value is an unresolved reference, figure out why
    parser.add_argument(
        "-d",
        "--direction",
        choices=[e.value for e in Direction],
        default=Direction.HORIZONTAL,
        help="The direction to place the tiles in.",
        type=Direction,
    )

    # force output image writing
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite output file if it exists.")

    # stretching mode
    # TODO: linting thinks e.value is an unresolved reference, figure out why
    parser.add_argument(
        "-m",
        "--stretch",
        choices=[e.value for e in StretchMode],
        default=StretchMode.ORIGINAL,
        help="Image stretching mode.",
        type=StretchMode,
    )

    # output file path
    parser.add_argument("-o", "--output", help="Output file name.", required=True)

    # maximum rows
    parser.add_argument(
        "-r", "--max-rows", default=0, help="Maximum number of rows of images. If less than 1, no maximum.", type=int
    )

    # sizing mode
    # TODO: linting thinks e.value is an unresolved reference, figure out why
    parser.add_argument(
        "-s",
        "--sizing",
        choices=[e.value for e in SizingMode],
        default=SizingMode.LARGEST,
        help="Tile sizing mode.",
        type=SizingMode,
    )

    # logging verbosity
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Verbosity.")

    # horizontal alignment
    # TODO: linting thinks e.value is an unresolved reference, figure out why
    parser.add_argument(
        "-x",
        "--horizontal-align",
        choices=[e.value for e in HorizontalAlignment],
        default=HorizontalAlignment.LEFT,
        help="Horizontal alignment of image.",
        type=HorizontalAlignment,
    )

    # vertical alignment
    # TODO: linting thinks e.value is an unresolved reference, figure out why
    parser.add_argument(
        "-y",
        "--vertical-align",
        choices=[e.value for e in VerticalAlignment],
        default=VerticalAlignment.TOP,
        help="Vertical alignment of image.",
        type=VerticalAlignment,
    )

    # input file paths
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
            [Image.open(file) for file in args.input_files],
            args.direction,
            args.max_columns,
            args.max_rows,
            args.horizontal_align,
            args.vertical_align,
            args.sizing,
            args.stretch,
            log,
        )

        # instantiate output image

        output_image = Image.new("RGB", tableau.output_size, args.background_color)

        # paste tiles onto output image

        for tile in tableau.tiles():
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
