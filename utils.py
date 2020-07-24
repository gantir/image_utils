import csv
import glob
import logging
import os
from math import ceil

from PIL import Image
from PIL import ImageOps

logging.basicConfig(
    filename="logs/debug.log",
    filemode="a",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.DEBUG,
)

logger = logging.getLogger(__name__)


def _calculate_image_size(old_size, new_max_size):
    width, height = old_size
    if width < new_max_size or height < new_max_size:
        return old_size

    ratio = width / height
    new_width = new_max_size
    new_height = ceil(new_max_size / ratio)

    if width < height:
        new_width = ceil(new_max_size * ratio)
        new_height = new_max_size

    return (new_width, new_height)


def _get_all_images_recursive(image_dir: str) -> list:
    return sorted(
        [
            f
            for f in list(glob.glob(image_dir + "/**", recursive=True))
            if os.path.isfile(f) and -1 == f.find(".DS_Store")
        ]
    )


def alter_image(
    src_img_file_path,
    dest_img_file_path,
    max_size=448,
    convert_gray_scale=False,
):
    try:
        # https://pillow.readthedocs.io/en/latest/handbook/concepts.html#modes
        org_img = Image.open(src_img_file_path).convert("RGB")
        if convert_gray_scale:
            org_img = ImageOps.grayscale(org_img)

        new_size = _calculate_image_size(org_img.size, max_size)

        altered_image = ImageOps.fit(org_img, new_size, method=Image.ANTIALIAS)
        os.makedirs(os.path.dirname(dest_img_file_path), exist_ok=True)

        dest_img_file_path = dest_img_file_path.replace("png", "jpg").replace(
            "webp", "jpg"
        )
        altered_image.save(dest_img_file_path)

    except Exception as e:
        logger.exception(e)


def rename_files(src_img_dir, dest_img_dir):
    img_files = _get_all_images_recursive(src_img_dir)

    with open("data/original_rename_map.csv", "w") as f:
        mapping_file = csv.writer(
            f, lineterminator=os.linesep, quoting=csv.QUOTE_ALL
        )
        mapping_file.writerow(
            ["id", "source", "destination", "dest_file_name", "img_class"]
        )

        img_index = 0
        for img in img_files:
            src_img_name, src_img_extension = os.path.splitext(img)
            if src_img_extension == ".jpeg":
                src_img_extension = ".jpg"

            dest_image_name = "img{:05d}{}".format(
                img_index + 1, src_img_extension
            )
            img_class = src_img_name.replace(src_img_dir, "").split("/")[1]
            os.makedirs(os.path.join(dest_img_dir, img_class), exist_ok=True)

            src_img_path = os.path.join(src_img_dir, img)
            dest_image_path = os.path.join(
                dest_img_dir, img_class, dest_image_name
            )

            # shutil.copyfile(src_img_path, dest_image_path) # noqa
            os.rename(src_img_path, dest_image_path)
            mapping_file.writerow(
                [
                    img_index,
                    src_img_path,
                    dest_image_path,
                    dest_image_name,
                    img_class,
                ]
            )

            img_index += 1


if __name__ == "__main__":
    print(_calculate_image_size((280, 320), 448))
    exit()
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    original_images = os.path.join(cur_dir_path, "data/original")
    renamed_images = os.path.join(cur_dir_path, "data/renamed")
    resized_images = os.path.join(cur_dir_path, "data/resized")
    rename_files(original_images, renamed_images)

    # uncomment the below only to resize files

    # all_images = _get_all_images_recursive(renamed_images) # noqa: E800
    # for i, src_img in enumerate(all_images):                  # noqa: E800
    #   alter_image(src_img, src_img.replace("renamed","resized")) # noqa: E800

    with open("data/original_rename_map.csv", "r") as f, open(
        "data/img_class.csv", "w"
    ) as ic:
        rename_map = csv.reader(f)
        img_class_map = csv.writer(
            ic, lineterminator=os.linesep, quoting=csv.QUOTE_ALL
        )
        for i, row in enumerate(rename_map):
            if 0 != i:
                img_class_map.writerow(
                    [
                        row[3].replace("png", "jpg").replace("webp", "jpg"),
                        row[4],
                    ]
                )
