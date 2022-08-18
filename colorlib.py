# StickerColorLibrary
# Copyright (C) 2022  GlitchFur

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
# StickerColorLibrary

A library to help developers generate color palettes from stickers.

Full `README.md` can be found at https://github.com/glitchfur/StickerColorLibrary

## Quick start

First, import the `Colors` class then load up some stickers from your storage device.

```python
from colorlib import Colors
colors = Colors(["01.png", "02.png", "03.png", "04.png"])
```

The major colors of the whole sticker set are immediately available as the
`colors.rgb_colors` property. You can also get associated alpha channel values
by using `colors.rgba_colors` instead. By default, colors are sorted in order
of most to least relevance until you start applying filters to them.

It is recommended that you filter out transparent pixels from stickers, as most
stickers tend to have unique shapes requiring transparent backgrounds. Also, if
you are importing more than one sticker, it is highly recommended to run K-means
clustering to group together similar colors from all stickers. Both of these can
be done in one go like so:

```python
colors = colors.filter_transparency().run_kmeans()
```

This will replace the old `colors` object with a new one, with both transparent 
pixels removed and K-means clustering applied using default values. The methods
in this class work by returning a new copy of the object with filters you choose
applied. This allows you to iteratively apply multiple filters at once in
whichever order you want using method-chaining as we have done above.

At this point, you can technically already use the colors provided to you by
accessing `colors.rgb_colors` again, or you can fine-tune your results even more
using other filters, such as `.filter_saturation()` or `.filter_value()`. An
example making use of all the methods in this class is shown below:

```python
colors = colors.filter_transparency()
    .run_kmeans()
    .filter_saturation()
    .filter_value()
    .rgb_colors
```

The end result would be `colors` being a `list` of `tuple` representing RGB 
values, in order of most relevance to least relevance, except for colors with
low saturation and low value which are moved to the back of the list.

You can view an actual image of the colors in your current palette at any time
by calling `.show()`, which will pop out a window showing your color collection.

Full API documentation is available below.
"""

from __future__ import annotations

from typing import BinaryIO, Optional
from colorsys import rgb_to_hsv as colorsys_rgb_to_hsv

from PIL import Image, ImageDraw
from sklearn.cluster import KMeans


class Colors:
    """
    Class representing a pool of colors and their weights derived from a
    collection of stickers passed into the class upon instantiation.
    """

    def __init__(
        self,
        stickers: Optional[list[str | BinaryIO | Image.Image]] = None,
        quantize: int = 16,
    ):
        """
        Create a new instance of `Colors` which aggregates color information
        from any number of stickers and sorts them by weight, meaning how
        much each color occurs in the entire collection overall. This order may
        change depending on what methods of this class you call.

        All stickers are converted to RGBA regardless of their mode before
        gathering color information.

        ---

        ### Parameters:

        #### stickers

        A list of any of the following:
        - strings of file paths to sticker images
        - file-like objects with a `.read()` method
        - pre-made PIL `Image` objects

        Can also be left `None`, which means the color list is created empty.

        #### quantize
        *Default:* `16`

        The number of colors *at most* to reduce each sticker down to.
        """

        if stickers == None:
            self._colors = []
            return

        aggregate_colors = {}

        for sticker in stickers:
            if isinstance(sticker, Image.Image):
                sticker_img = sticker.convert("RGBA")
            else:
                sticker_img = Image.open(sticker).convert("RGBA")
            sticker_quantized = sticker_img.quantize(quantize).convert("RGBA")
            sticker_colors = sticker_quantized.getcolors()
            for color in sticker_colors:
                if not color[1] in aggregate_colors:
                    aggregate_colors[color[1]] = 0
                aggregate_colors[color[1]] += color[0]

        self._colors = sorted(
            [(v, k) for k, v in aggregate_colors.items()], reverse=True
        )

    def copy(self) -> Colors:
        """Create an identical copy of this object."""

        colors_cp = Colors()
        colors_cp._colors = self._colors.copy()
        return colors_cp

    @property
    def weights(self) -> list[int]:
        """
        Return the list of "weights" of each color, or how relevant that color
        is in the entire collection.

        Depending on context, "weight" has two definitions:

        - By default, weight is a count of the number of pixels that matched
        that color. This does not mean the number of pixels in the original
        image, but the number of pixels after quantization, which occurs when
        this class is instantiated.
        - After calling `run_kmeans()`, the number then represents how many
        specific colors from each sticker became a part of that color's cluster.
        """

        return [color[0] for color in self._colors]

    @property
    def rgb_colors(self) -> list[tuple[int, int, int]]:
        """
        The list of `RGB` colors in the image.
        """

        return [color[1][:3] for color in self._colors]

    @property
    def rgba_colors(self) -> list[tuple[int, int, int, int]]:
        """
        The list of `RGBA` colors in the image.

        For images whose initial mode was `RGB`, the `A` value will be `255` for all colors.
        """

        return [color[1] for color in self._colors]

    def run_kmeans(
        self, k_clusters: int = 8, runs: int = 64, max_iter: int = 256
    ) -> Colors:
        """
        Run [K-means clustering](https://en.wikipedia.org/wiki/K-means_clustering)
        on all the colors in the pool, which is useful if you instantiated the
        class with many stickers. This will ultimately group together similar
        colors, allowing you to choose from a much narrower selection while
        still maintaining color relevance.

        ---

        ### Parameters:

        #### k_clusters
        *Default:* `8`

        The number of clusters to attempt to find.

        #### runs
        *Default:* `64`

        How many times to run the K-means clustering algorithm. The run with the
        lowest error score will be chosen.

        #### max_iter
        *Default:* `256`

        The maximum number of iterations allowed for each run.
        """

        kmeans = KMeans(
            init="random", n_clusters=k_clusters, n_init=runs, max_iter=max_iter
        )

        kmeans.fit(self.rgba_colors)

        counts = [0] * k_clusters

        for i in kmeans.labels_:
            counts[i] += 1

        colors = []

        for count, color in zip(counts, kmeans.cluster_centers_):
            r, g, b, a = (
                round(color[0]),
                round(color[1]),
                round(color[2]),
                round(color[3]),
            )
            colors.append((count, (r, g, b, a)))

        colors.sort(reverse=True)

        color_obj = Colors()
        color_obj._colors = colors

        return color_obj

    def filter_transparency(
        self, threshold: int = 230, remove: bool = True, invert: bool = False
    ) -> Colors:
        """
        Filter out colors whose transparency is too low.

        ---

        ### Parameters:

        #### threshold
        *Default:* `230`

        Value ranging from `0` to `255`. If a color's alpha channel value is
        *under* this value, it will be removed from the list.

        #### remove
        *Default:* `True`

        If `remove` is `True` (default), colors will be completely removed from
        the list. Otherwise, colors are added back on to the end of the list.

        #### invert
        *Default:* `False`

        If `invert` is `True`, the filter is inverted: Colors that would have
        been removed are kept on the list, and vice-versa.
        """

        approved_colors = []
        reject_colors = []

        for color in self._colors:
            if color[1][3] >= threshold:  # [1] == RGBA value, [3] == Alpha
                approved_colors.append(color)
            else:
                reject_colors.append(color)

        colors = []

        if not invert:
            colors.extend(approved_colors)
            if not remove:
                colors.extend(reject_colors)
        else:
            colors.extend(reject_colors)
            if not remove:
                colors.extend(approved_colors)

        color_obj = Colors()
        color_obj._colors = colors

        return color_obj

    def filter_saturation(
        self, threshold: int = 35, remove: bool = False, invert: bool = False
    ) -> Colors:
        """
        Filter out colors whose saturation is too low.

        ---

        ### Parameters:

        #### threshold
        *Default:* `35`

        Value ranging from `0` to `100`. If a color's saturation level is
        *under* this value, it will be removed from the list.

        #### remove
        *Default:* `False`

        If `remove` is `False` (default), colors are added back on to the end of
        the list. Otherwise, they are removed entirely.

        #### invert
        *Default:* `False`

        If `invert` is `True`, the filter is inverted: Colors that would have
        been removed are kept on the list, and vice-versa.
        """

        approved_colors = []
        reject_colors = []

        for color in self._colors:
            sat = rgb_to_hsv(*color[1][:3])[1]  # *[1][:3] == Unpacked RGB value
            if sat >= threshold:
                approved_colors.append(color)
            else:
                reject_colors.append(color)

        colors = []

        if not invert:
            colors.extend(approved_colors)
            if not remove:
                colors.extend(reject_colors)
        else:
            colors.extend(reject_colors)
            if not remove:
                colors.extend(approved_colors)

        color_obj = Colors()
        color_obj._colors = colors

        return color_obj

    def filter_value(
        self, threshold: int = 20, remove: bool = False, invert: bool = False
    ) -> Colors:
        """
        Filter out colors whose value (lightness) is too low.

        ---

        ### Parameters:

        #### threshold
        *Default:* `20`

        Value ranging from `0` to `100`. If a color's value level is *under*
        this value, it will be removed from the list.

        #### remove
        *Default:* `False`

        If `remove` is `False` (default), colors are added back on to the end of
        the list. Otherwise, they are removed entirely.

        #### invert
        *Default:* `False`

        If `invert` is `True`, the filter is inverted: Colors that would have
        been removed are kept on the list, and vice-versa.
        """

        approved_colors = []
        reject_colors = []

        for color in self._colors:
            val = rgb_to_hsv(*color[1][:3])[2]  # *[1][:3] == Unpacked RGB value
            if val >= threshold:
                approved_colors.append(color)
            else:
                reject_colors.append(color)

        colors = []

        if not invert:
            colors.extend(approved_colors)
            if not remove:
                colors.extend(reject_colors)
        else:
            colors.extend(reject_colors)
            if not remove:
                colors.extend(approved_colors)

        color_obj = Colors()
        color_obj._colors = colors

        return color_obj

    def show(self, width: int = 1024, height: int = 128):
        """
        Display an image showing the current collection of colors.

        ---

        ### Parameters:

        #### width
        *Default:* `1024`

        The width of the image displaying the colors.

        #### height
        *Default:* `128`

        The height of the image displaying the colors.
        """

        img = Image.new("RGB", (width, height), (255, 255, 255))
        img_draw = ImageDraw.Draw(img)

        color_width = width // len(self.rgb_colors)

        for i in range(len(self.rgb_colors)):
            img_draw.rectangle(
                (i * color_width, 0, (i * color_width) + color_width, height),
                fill=self.rgb_colors[i],
            )

        img.show()


def rgb_to_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    """
    Convert RGB values to HSV values (hue, saturation, and value).

    This is similar to `colorsys`'s `rgb_to_hsv` function except that RGB values
    are expected to be between 0 and 255 and HSV values are translated to be
    between 0-360, 0-100, and 0-100 respectively. This is similar to how some
    image manipulation applications (ex. GIMP) represent RGB and HSV values.
    """
    h, s, v = colorsys_rgb_to_hsv(r / 255, g / 255, b / 255)
    return (h * 360, s * 100, v * 100)
