# imgquilt

Stitches images together into a bigger image.

## Requirements

- I've not tested it below Python 3.8.
- [Pillow](https://python-pillow.org) has [external library](https://pillow.readthedocs.io/en/stable/installation.html#external-libraries) requirements, but I've not looked deeply into them yet.

## Use

```
> python main.py -h

usage: main.py [-h] [-b BACKGROUND_COLOR] [-c MAX_COLUMNS] [-d {h,v}] [-f] [-m {f,o,r}] -o OUTPUT [-r MAX_ROWS] [-s {a,l,s}] [-v] [-x {c,l,r}]
           [-y {b,m,t}]
           input_files [input_files ...]

positional arguments:
  input_files           Files to tile.

optional arguments:
  -h, --help            show this help message and exit
  -b BACKGROUND_COLOR, --background-color BACKGROUND_COLOR
                        Background color for gaps between images.
  -c MAX_COLUMNS, --max-columns MAX_COLUMNS
                        Maximum number of columns of images. If set less than 1, no maximum.
  -d {h,v}, --direction {h,v}
                        The direction to place the tiles in.
  -f, --force           Overwrite output file if it exists.
  -m {f,o,r}, --stretch {f,o,r}
                        Image stretching mode.
  -o OUTPUT, --output OUTPUT
                        Output file name.
  -r MAX_ROWS, --max-rows MAX_ROWS
                        Maximum number of rows of images. If less than 1, no maximum.
  -s {a,l,s}, --sizing {a,l,s}
                        Tile sizing mode.
  -v, --verbose         Verbosity.
  -x {c,l,r}, --horizontal-align {c,l,r}
                        Horizontal alignment of image.
  -y {b,m,t}, --vertical-align {b,m,t}
                        Vertical alignment of image.
```

## Development

Standard Git & Python things:

1. Clone the repo
2. Create and activate virtualenv
3. `pip install -r requirements.txt`
4. `pre-commit install`

## Background

I needed a tool to tile irregularly sized images. Then I kept fiddling with the tool, and here we are.

## Planned features

- Image resizing, scaling, stretching.
- Installable as a command line tool.
- Improve command line arguments & help.

## What's with the name?

Yes, I know I normally name projects things like **pretentious-raptor** or **underwater-basket**. But, since I'm going to be actually typing this on the command line, I gave it a short, sensible name. Sorry.
