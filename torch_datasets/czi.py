from aicspylibczi import CziFile
import os
import torch
import numpy as np
from skimage.measure import label
from skimage.measure import regionprops_table
from skimage.filters import threshold_otsu
import pandas as pd


# Authored by Johannes Losert
# CZI type Dataset object for loading in czi files as tensors.
# supports any dimensionality (2d, 3d, video, image)
# transform can be used for preproeessing step (i.e. cropping, filters)
# 
# Important Note: if you are having trouble using this dataset, run "bash setup_paths.sh"
# from the home directory of the CVProject folder 

class CZIDataset(torch.utils.data.Dataset):
    
    def __init__(self, folder, transform=None):
        self.files = [folder + '/' + filename for filename in os.listdir(folder)]
        self.transform = transform

    def __len__(self):
        return len(self.files)

    # returns the data in numpy format for easier preprocessing
    def __getitem__(self, idx):
        # Load CZI file
        img_path = self.files[idx]
        img = CziFile(img_path)
        dims = img.dims
        shape = img.size
        frames_data, shape = img.read_image()
        # Convert image data to a torch tensor and remove dims with single element
        data = np.squeeze(frames_data).astype(np.uint32)

        # Apply transform if any
        if self.transform:
            data = self.transform(data)

        return data, dims, shape

#TODO_1: return a numpy ndarray instead of a list by adding padding
#TODO_2: perform cell matching across frames using bounding box similarity
#TODO_3: optimize memory usage by minimizing internmediate objects / being more pythonic
#       / using kernel fusion


class Transforms2D:

    # you may not want to do the whole video if too big
    def bounding_boxes(video,first_frame = 0,last_frame= -1,min_area=200):
        video = video[first_frame:last_frame]
        
        # find threshhold in first frame
        thresh = threshold_otsu(video[0])

        # labeling connected components of each frame
        binary_video = video >= thresh
        
        #applying the label for mask
        labeled_video = np.array([label(binary_frame,background=0,connectivity=2) for binary_frame in binary_video]) 
        
        # deducing centroids, max side length, 
        all_bboxes = list()
        max_num_cells=0
        for labeled_frame in labeled_video:
            props = regionprops_table(label_image=labeled_frame,
                                      properties=['bbox','area']
            )
            df = pd.DataFrame(props)
            df = df[df['area'] >= min_area]
            df= df.drop(columns = ['area'])
            print(df)
            max_num_cells = max(max_num_cells, df.shape[0])
            all_bboxes.append(list(df.itertuples(index=False, name=None)))

        # bboxes_video = np.zeros((frames, max_num_cells, max_bbox_size, max_bbox_size))
        bboxes_video = list()
        for frame_idx, frame in enumerate(video):
            frame_list = list()
            for bbox in all_bboxes[frame_idx]:
                print(bbox)
                min_row, min_col, max_row, max_col = bbox
                print(max_row, min_row)
                frame_list.append(frame[min_row:max_row,min_col:max_col])
            bboxes_video.append(frame_list)

        return bboxes_video
        
  
        
    