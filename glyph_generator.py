import argparse
import os
import re
import sys

from PIL import Image, ImageOps

DEFAULT_GRID = 16
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")


class Log:

    @staticmethod
    def info(text):
        print(f"Info   - {text}")

    @staticmethod
    def notice(text):
        print(f"Notice - {text}")

    @staticmethod
    def error(text):
        print(f"Error  - {text}")


def sanitize_name(name):
    name = re.sub(r"[^A-Za-z0-9_-]", "", name or "").strip("_-")
    return name or "glyph"


def fit_image(img, limit):
    if limit and (img.width > limit or img.height > limit):
        scale = limit / max(img.width, img.height)
        new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
        return img.resize(new_size, Image.LANCZOS)
    return img


def collect_images(folder):
    if not os.path.isdir(folder):
        Log.error(f"Folder not found: {folder}")
        return None
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(IMAGE_EXTS))
    if not files:
        exts = ", ".join(IMAGE_EXTS)
        Log.error(f"No supported images found in '{folder}' (accepted: {exts})")
        return []
    return files


def make_glyph(folder, glyph_name, grid_cells=DEFAULT_GRID, padding=0,
               max_size=0, output_dir="."):
    files = collect_images(folder)
    if files is None or not files:
        return False

    grid_cells = max(1, grid_cells)
    padding = max(0, padding)
    max_size = max(0, max_size)

    max_slots = grid_cells * grid_cells
    if len(files) > max_slots:
        Log.error(f"{len(files)} images found but the {grid_cells}x{grid_cells} "
                  f"grid only fits {max_slots}; extra images will be skipped.")
        files = files[:max_slots]

    loads = []
    largest = 0
    for filename in files:
        img = ImageOps.exif_transpose(Image.open(os.path.join(folder, filename)))
        largest = max(largest, img.width, img.height)
        loads.append((filename, img))
    loads.sort(key=lambda item: item[0])

    Log.info(f"Found {len(files)} image(s), largest dimension is {largest}px")

    cell_size = largest
    if max_size and cell_size > max_size:
        Log.notice(f"Capping cell size to {max_size}px (largest image was {cell_size}px)")
        cell_size = max_size

    usable = cell_size - 2 * padding
    if usable < 1:
        Log.error("Padding is too large for the cell size")
        return False

    output_size = cell_size * grid_cells
    canvas = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))

    for i, (filename, img) in enumerate(loads):
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img = fit_image(img, usable)

        row, col = divmod(i, grid_cells)
        offset_x = col * cell_size + padding + (usable - img.width) // 2
        offset_y = row * cell_size + padding + (usable - img.height) // 2
        canvas.paste(img, (offset_x, offset_y), img)

    os.makedirs(output_dir, exist_ok=True)
    safe_name = sanitize_name(glyph_name)
    output_path = os.path.join(output_dir, f"glyph_{safe_name}.png")
    canvas.save(output_path, "PNG", optimize=True)

    Log.info(f"Saved: {output_path}")
    Log.notice(f"Done! {grid_cells}x{grid_cells} grid, {cell_size}px cells, "
               f"{len(loads)} image(s)")
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a glyph atlas from a folder of images.")
    parser.add_argument("--folder", "-f", help="Folder containing the images")
    parser.add_argument("--name", "-n", help="Glyph name (e.g., E3)")
    parser.add_argument("--grid", "-g", type=int, default=DEFAULT_GRID,
                        help=f"Grid size, rows = columns (default: {DEFAULT_GRID})")
    parser.add_argument("--padding", "-p", type=int, default=0,
                        help="Padding in px between glyphs (default: 0)")
    parser.add_argument("--max-size", type=int, default=0,
                        help="Cap each cell to this many px, scaling images to fit")
    parser.add_argument("--output", "-o", default=".",
                        help="Output folder (default: current directory)")
    return parser.parse_args()


def run_interactive(args):
    while True:
        try:
            folder = input("Images Folder -> ").strip()
            if args.name:
                name = args.name
            else:
                name = input("Glyph Name (e.g., E3) -> ").strip()
            if not make_glyph(folder, name, args.grid, args.padding,
                              args.max_size, args.output):
                print("Nothing was generated.")
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        cont = input("\nGenerate another? [Enter=yes | q=quit] -> ").strip().lower()
        if cont in ("q", "quit", "exit"):
            print("Goodbye!")
            break


def main():
    args = parse_args()
    if args.folder and args.name:
        ok = make_glyph(args.folder, args.name, args.grid, args.padding,
                        args.max_size, args.output)
        sys.exit(0 if ok else 1)
    run_interactive(args)


if __name__ == "__main__":
    main()