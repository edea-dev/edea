import argparse
from math import ceil, fsum

import pyvips
from PIL import Image, ImageOps, ImageChops

"""
Compare two images and render a composite showing the changes;
green for additions, and red for removed parts, while showing the original image in greyscale.
"""
DEBUG = False


def get_dominant_color_from_corner(image):
    """
    detection logic for background color (light/dark theme)
    if the image is dark, we invert it initially, use the same logic, then invert it back at the end
    for sampling we only use the top-left corner, 16x16 pixels
    """
    corner = image.crop(box=(0, 0, 16, 16))
    colors = corner.getcolors()

    if len(colors) == 1 and not DEBUG:
        return colors[0][1]

    color_count = 0
    dominant_color = None
    half_pixel_count = ceil(corner.size[0] * corner.size[1] * 0.5)

    for count, color in colors:
        if count > color_count:
            color_count = count
            dominant_color = color
            if count > half_pixel_count:
                break
    if DEBUG:
        print(f"{dominant_color=}")
    return dominant_color[:3]


def read_svg_hack(svg_filename, dpi=300):
    """
    Read an svg file and return a Pillow image
    """

    image = pyvips.Image.new_from_file(
        svg_filename, dpi=dpi
    )

    return Image.fromarray(image.numpy())


def imgdiff(image_file_a, image_file_b, output_file):
    """
    Ugly hack for visual diffing. Renders to output_file.
    Returns a percentage (0...100%) of different pixels between A and B.
    """
    global DEBUG

    base_image = read_svg_hack(image_file_a) if image_file_a.endswith('.svg') else Image.open(image_file_a)
    new_image = read_svg_hack(image_file_b) if image_file_b.endswith('.svg') else Image.open(image_file_b)

    # Cairo renders full transparency as transparent black even when it was supposed to be transparent white...
    # this hack should deal with that
    if image_file_a.endswith('.svg'):
        base_image = ImageChops.add(
            base_image,
            ImageChops.invert(base_image.getchannel('A')).convert('RGBA'))
    if image_file_a.endswith('.svg'):
        new_image = ImageChops.add(
            new_image,
            ImageChops.invert(new_image.getchannel('A')).convert('RGBA'))

    if image_file_a.endswith('.svg') and False:
        dark_theme = False
    else:
        dark_theme = fsum(get_dominant_color_from_corner(base_image)) < 127 * 3  # this is a fuck

    base_image_bw = ImageChops.invert(ImageOps.grayscale(base_image)) if dark_theme else ImageOps.grayscale(base_image)
    new_image_bw = ImageChops.invert(ImageOps.grayscale(new_image)) if dark_theme else ImageOps.grayscale(new_image)

    # alpha = 0 means fully transparent, alpha=255 means fully opaque
    alpha_blend = None
    if 'A' in base_image.mode or 'A' in new_image.mode:
        if base_image.mode != 'RGBA':
            base_image = base_image.convert('RGBA')

        if new_image.mode != 'RGBA':
            new_image = new_image.convert('RGBA')
        alpha_blend = ImageChops.lighter(base_image.getchannel('A'), new_image.getchannel('A'))

    img_difference_gray = ImageChops.subtract_modulo(base_image_bw, new_image_bw)
    if DEBUG:
        img_difference_gray.save(output_file[:-4] + '.img_difference_gray.png')

    background = ImageChops.lighter(base_image_bw, new_image_bw)
    common = ImageChops.darker(base_image_bw, new_image_bw)

    if dark_theme:
        background, common = common, background  # I love Python

    if DEBUG:
        background.save(output_file[:-4] + '.background.png')
        common.save(output_file[:-4] + '.common.png')

    base_mask = ImageChops.multiply(
        ImageChops.invert(base_image_bw).convert('RGB'),
        Image.new('RGB', background.size, color=(200, 0, 200) if dark_theme else (0, 200, 200)))  # )
    if DEBUG:
        base_mask.save(output_file[:-4] + '.base_mask.png')  # DEBUG

    new_mask = ImageChops.multiply(
        ImageChops.invert(new_image_bw).convert('RGB'),
        Image.new('RGB', background.size, color=(0, 200, 200) if dark_theme else (200, 0, 200)))  # )
    if DEBUG:
        new_mask.save(output_file[:-4] + '.new_mask.png')  # DEBUG

    output_image = ImageChops.subtract(
        ImageChops.subtract(
            Image.new('RGB', background.size, color=(255, 255, 255)),
            base_mask),
        new_mask)

    if dark_theme:
        output_image = ImageChops.invert(output_image)

    if alpha_blend is not None:
        output_image.putalpha(alpha_blend)

    changes_bounding_box = img_difference_gray.getbbox()
    change_pct = None
    if changes_bounding_box is None:
        change_pct = 0
        # no changes detected between images A and B - return the input but greyscale
        output_image = new_image_bw
    else:
        output_image.crop(changes_bounding_box).save(output_file[:-4] + '.crop.png')
        hist = img_difference_gray.crop(changes_bounding_box).histogram()
        change_pct = 100 * fsum(hist[1:]) / (base_image.size[0] * base_image.size[1])

    output_image.save(output_file)
    return change_pct


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('base_image', type=str, nargs=1, help="Base image for comparison")
    parser.add_argument('new_image', type=str, nargs=1,
                        help="Updated image for comparison (additions will be shown in green)")
    parser.add_argument('-o', type=str, nargs=1, help="Output file (stdout if not specified)")

    args = parser.parse_args()
    imgdiff(args.base_image[0], args.new_image[0], args.o[0])
