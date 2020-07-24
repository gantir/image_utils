import os
import dload
import csv
import shutil
import time
from PIL import Image,ImageOps
from math import ceil
import numpy as np
import cv2
import random
import copy
import logging
import zipfile
import glob

logging.basicConfig(filename='logs/debug.log',
  filemode='a',
  format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
  datefmt='%H:%M:%S',
  level=logging.DEBUG
)

logger = logging.getLogger(__name__)

def download_images(img_url_file: str, img_dest: str):
  src_filepath = os.path.join(os.getcwd(), img_url_file)
  dest_filepath = os.path.join(os.getcwd(), "img_src_local_map.csv")
  with open(src_filepath) as s, open(dest_filepath,'w') as d:
    dest_file = csv.writer(d,lineterminator=os.linesep, quoting=csv.QUOTE_ALL)
    urls = sorted(set(s.readlines()))
    for i, img_url in enumerate(urls):
      img_url = img_url.strip()
      dest_image_name = "img{:04d}.jpg".format(i+1)
      dest_image_path = os.path.join(os.getcwd(), img_dest, dest_image_name)
      try:
        print("Downloading as {} image {}".format(dest_image_name, img_url))
        dest_file.writerow([dest_image_name,img_url])
        dload.save(img_url, dest_image_path)
        if "pixabay" in img_url:
          # This delay is needed as otherwise the pixabay was throwing 403 error
          time.sleep(5)
      except Exception as e:
        print("Error: Error downloading as {} image {}".format(dest_image_name, img_url))
        pass

def alter_bg_image(src_img_dir: str, src_img_filename: str, dest_img_folder: str, image_size=(224,224), convert_gray_scale=False ):
  image_path = os.path.join(src_img_dir,src_img_filename)
  org_img = Image.open(image_path)
  if convert_gray_scale:
    org_img = ImageOps.grayscale(org_img)
  altered_image = ImageOps.fit(org_img,image_size, method=Image.ANTIALIAS)
  # altered_image.show()
  altered_image.save(os.path.join(dest_img_folder,src_img_filename))

def alter_fg_image(src_img_dir, src_img_filename, dest_img_folder, dest_img_folder_gray, max_size=200):
  image_path = os.path.join(src_img_dir,src_img_filename)
  try:
    # https://pillow.readthedocs.io/en/latest/handbook/concepts.html#modes
    org_img = Image.open(image_path)
    org_img_gray = org_img.convert('LA')

    width,height = org_img.size
    ratio = width/height
    new_width = max_size
    new_height = ceil(max_size/ratio)
    if width < height:
      new_width = ceil(max_size*ratio)
      new_height = max_size
    # print(ratio,src_img_filename,[width,height],[new_width,new_height])
    altered_image = ImageOps.fit(org_img,(new_width,new_height), method=Image.ANTIALIAS)
    altered_image.save(os.path.join(dest_img_folder,src_img_filename))

    altered_image_gray = ImageOps.fit(org_img_gray,(new_width,new_height), method=Image.ANTIALIAS)
    altered_image_gray.save(os.path.join(dest_img_folder_gray,src_img_filename))
  except Exception as e:
    print(e)
    pass

def rename_files(src_img_dir, dest_img_dir):
  img_files = sorted(list(glob.glob(src_img_dir+"/**", recursive=True)))
  with open("data/original_rename_map.csv","w") as f, open("data/img_class.csv", "w") as ic:
    mapping_file = csv.writer(f,lineterminator=os.linesep, quoting=csv.QUOTE_ALL)
    img_class_file = csv.writer(ic,lineterminator=os.linesep, quoting=csv.QUOTE_ALL)
    mapping_file.writerow(["id","source","destination","dest_file_name","img_class"])

    img_index = 0
    for i, img in enumerate(img_files):
      if os.path.isfile(img) and -1 == img.find(".DS_Store"):
        src_img_name, src_img_extension = os.path.splitext(img)
        if src_img_extension == ".jpeg":
          src_img_extension = ".jpg"

        dest_image_name = "img{:05d}{}".format(img_index+1,src_img_extension)
        img_class = src_img_name.replace(src_img_dir,"").split("/")[1]
        os.makedirs(os.path.join(dest_img_dir,img_class), exist_ok=True)

        src_img_path = os.path.join(src_img_dir, img)
        dest_image_path = os.path.join(dest_img_dir,img_class,dest_image_name)

        shutil.copyfile(src_img_path, dest_image_path)
        mapping_file.writerow([img_index,src_img_path,dest_image_path,dest_image_name,img_class])
        img_class_file.writerow([dest_image_name,img_class])

        img_index+=1

def convert2jgp(src_img_path):
  return None


def rename_fg_files(src_dir, dest_img_dir):
  # classes = ['bird','boat','car','cat','cow','dog','person']
  classes = ['person']
  img_files = []
  for cl in classes:
    for img in os.listdir(os.path.join(src_dir,cl)):
      if 'png' in img:
        img_files.append((cl,os.path.join(src_dir,cl,img)))

  class_img = []
  for i, details in enumerate(img_files):
    dest_image_name = "img{:04d}.png".format(i+1)
    dest_image_path = os.path.join(dest_img_dir, dest_image_name)
    shutil.copy2(details[1],dest_image_path)
    class_img.append((details[0],dest_image_name))

  with open('/Users/projects/Downloads/s14-15/fg_img_class_map.csv','w') as f:
    fg_map_file = csv.writer(f,lineterminator=os.linesep, quoting=csv.QUOTE_ALL)
    fg_map_file.writerows(class_img)

def generate_mask(src_img_dir, dest_img_dir):
  img_files = sorted(os.listdir(src_img_dir))
  for img in img_files:
    # https://stackoverflow.com/questions/28430904/set-numpy-array-elements-to-zero-if-they-are-above-a-specific-threshold
    # https://codereview.stackexchange.com/questions/184044/processing-an-image-to-extract-green-screen-mask
    image = cv2.imread(os.path.join(src_img_dir,img))
    white_indicies = image >= 1
    image[white_indicies] = 255
    dest_image_path = os.path.join(dest_img_dir, img)
    cv2.imwrite(dest_image_path, (image).astype(np.uint8))

def generate_images(source, dest, max_rand=360, image_size=(448,448), save_image_files=False):
  logger.debug("Starting to generate Images")
  bg_images = sorted(os.listdir(source['bg']))[0:1]
  fg_images = sorted(os.listdir(source['fg']))[0:1]
  black_image = Image.open(source['black'])
  black_image = ImageOps.fit(black_image, image_size, method=Image.ANTIALIAS)

  bg_fg_zip = zipfile.ZipFile(os.path.join(dest,'bg_fg.zip'), mode='a', compression=zipfile.ZIP_STORED)
  bg_fg_mask_zip = zipfile.ZipFile(os.path.join(dest,'bg_fg_mask.zip'), mode='a', compression=zipfile.ZIP_STORED)

  for bg_image_name in bg_images:
    logger.debug("Background Image : {}".format(bg_image_name))
    bg_image = Image.open(os.path.join(source['bg'], bg_image_name))
    for fg_image_name in fg_images:
      logger.debug("Foreground Image : {}".format(fg_image_name))
      # https://stackoverflow.com/questions/7911451/pil-convert-png-or-gif-with-transparency-to-jpg-without
      fg_image = Image.open(os.path.join(source['fg'], fg_image_name)).convert('RGBA')
      fg_mask_image = Image.open(os.path.join(source['fg-mask'], fg_image_name)).convert('RGBA')

      fg_image_flip = ImageOps.mirror(fg_image)
      fg_mask_image_flip = ImageOps.mirror(fg_mask_image)

      partial_dest_dir = os.path.join(
          "bg-{}".format(bg_image_name.split('.')[0]),
          "fg-{}".format(fg_image_name.split('.')[0])
      )

      dest_image_path = os.path.join(dest,"temp")
      dest_mask_path = os.path.join(dest,"temp-mask")
      if save_image_files:
        dest_image_path = os.path.join(dest,"bg-fg", partial_dest_dir)
        dest_mask_path = os.path.join(dest,"bg-fg-mask", partial_dest_dir)

      os.makedirs(dest_image_path, exist_ok=True)
      os.makedirs(dest_mask_path, exist_ok=True)

      for placement in range(1,21):
        x1,y1 = random.randint(1,max_rand), random.randint(1,max_rand)
        bg_fg = copy.deepcopy(bg_image)
        mask = copy.deepcopy(black_image)
        bg_fg.paste(fg_image, (x1,y1), fg_image)
        mask.paste(fg_mask_image, (x1,y1), fg_mask_image)

        x2,y2 = random.randint(1,max_rand), random.randint(1,max_rand)
        bg_fg_flip = copy.deepcopy(bg_image)
        mask_flip = copy.deepcopy(black_image)
        bg_fg_flip.paste(fg_image_flip, (x2,y2), fg_image_flip)
        mask_flip.paste(fg_mask_image_flip, (x2,y2), fg_mask_image_flip)

        bg_fg_file_name = "{}.jpg".format(placement)
        bg_fg_flip_file_name = "{}-flip.jpg".format(placement)

        bg_fg.save(os.path.join(dest_image_path, bg_fg_file_name ))
        mask.save(os.path.join(dest_mask_path, bg_fg_file_name))

        bg_fg_flip.save(os.path.join(dest_image_path, bg_fg_flip_file_name))
        mask_flip.save(os.path.join(dest_mask_path, bg_fg_flip_file_name))

        bg_fg_zip.write(
          os.path.join(dest_image_path, bg_fg_file_name),
          arcname= os.path.join("bg-fg",partial_dest_dir,bg_fg_file_name)
        )
        bg_fg_zip.write(
          os.path.join(dest_image_path, bg_fg_flip_file_name),
          arcname= os.path.join("bg-fg",partial_dest_dir, bg_fg_flip_file_name)
        )

        bg_fg_mask_zip.write(
          os.path.join(dest_mask_path, bg_fg_file_name),
          arcname= os.path.join("bg-fg-mask",partial_dest_dir, bg_fg_file_name)
        )
        bg_fg_mask_zip.write(
          os.path.join(dest_mask_path, bg_fg_flip_file_name),
          arcname= os.path.join("bg-fg-mask",partial_dest_dir, bg_fg_flip_file_name)
        )

  bg_fg_zip.close()
  bg_fg_mask_zip.close()

if __name__ == "__main__":
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))

    rename_files(os.path.join(cur_dir_path,'data/original'),os.path.join(cur_dir_path,'data/renamed'))
    # alter_image()
    # bg_img_files = sorted(os.listdir('/Users/projects/Downloads/s14-15/images/bg/original/'))
    # for img in bg_img_files:
    #   alter_bg_image('/Users/projects/Downloads/s14-15/images/bg/original/', img,'/Users/projects/Downloads/s14-15/images/bg/altered/', (224,224))

    # rename_fg_files('/Users/projects/Downloads/s14-15/images/fg/actual/','/Users/projects/Downloads/s14-15/images/fg/original/')

    # fg_img_files = sorted(os.listdir('/Users/projects/Downloads/s14-15/images/fg/original/'))
    # for i, img in enumerate(fg_img_files):
    #   alter_fg_image('/Users/projects/Downloads/s14-15/images/fg/original/', img,'/Users/projects/Downloads/s14-15/images/fg/altered/','/Users/projects/Downloads/s14-15/images/fg/altered-gray/', max_size=100)

    # generate_mask('/Users/projects/Downloads/s14-15/images/fg/altered-gray/','/Users/projects/Downloads/s14-15/images/fg/mask')

    # cur_dir = os.curdir
    # generate_images({
    #   'bg': os.path.join(os.curdir,'images/bg/altered/'),
    #   'fg': os.path.join(os.curdir,'images/fg/altered/'),
    #   'fg-mask':os.path.join(os.curdir,'images/fg/mask/'),
    #   'black': os.path.join(os.curdir,'images/black.jpg')
    #   }
    #   , dest= os.path.abspath(os.path.join(os.curdir,'images/generated'))
    #   , max_rand=160, image_size=(224,224), save_image_files=True
    # )

    # image = Image.open('images/generated/bg-fg-mask/bg-img0001/fg-img0001/1.jpg')
    # k = image.getdata()
    # print(len(k))