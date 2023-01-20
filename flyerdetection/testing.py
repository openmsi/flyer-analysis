#imports
import pathlib
import pandas as pd
from PIL import Image
from flyer_detection import *

root = pathlib.Path('/Users/margareteminizer/Desktop/dmref_materials_project/laser_shock_lab/')
test_file_dir = root/'flyer_image_examples'/'Camera_11_30_10'
output_dir = root/'TESTING'
output_file = output_dir/'results.csv'

temp=Flyer_Detection()
for i in range(120,160) :
    test_file_path = test_file_dir/f'Camera_11_30_10_{i}.bmp'
    img = np.asarray(Image.open(test_file_path))
    filtered_image=temp.filter_image(img) 
    data = vars(temp.radius_from_lslm(filtered_image,test_file_path,output_dir))
    data_frame = pd.DataFrame([data])
    if output_file.is_file() :
        data_frame.to_csv(output_file,mode='a',index=False,header=False)
    else :
        data_frame.to_csv(output_file,mode='w',index=False,header=True)
