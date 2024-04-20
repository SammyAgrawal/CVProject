from aicspylibczi import CziFile
import os
import torch
import numpy as np
from skimage.measure import label # version at least 0.22
from skimage.measure import regionprops_table # version at least 0.22
from skimage.filters import threshold_otsu # version at least 0.22
import pandas as pd

#import torch_datasets.czi as czi
#


# Authored by Johannes Losert
# CZI type Dataset object for loading in czi files as tensors.
# supports any dimensionality (2d, 3d, video, image)
# transform can be used for preproeessing step (i.e. cropping, filters)
# 
# Important Note: if you are having trouble using this dataset, run "bash setup_paths.sh"
# from the home directory of the CVProject folder 

class CZIDataset(torch.utils.data.Dataset):
    
    def __init__(self, folder, transform=None, twod_vid_channel=None):
        self.files = [folder + '/' + filename for filename in os.listdir(folder)]
        self.transform = transform
        self.twod_vid_channel = twod_vid_channel

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
        if (type(self.twod_vid_channel) == int and self.twod_vid_channel >= 0 \
            and len(data.shape)==4):
            data = np.squeeze(data[:,self.twod_vid_channel,:,:]) 

        return data, dims, shape

#TODO_1: return a numpy ndarray instead of a list by adding padding
#TODO_2: perform cell matching across frames using bounding box similarity
#TODO_3: optimize memory usage by minimizing internmediate objects / being more pythonic
#       / using kernel fusion


class Transforms2D:

    # returns the coords of the bounding boxes for frame in the range (first frame, last_frame-1)
    # (frame, bounding boxes, box_tuple)
    # format of box_tuple is 'min_row, min_col, max_row, max_col = bbox'
    # min area parameter determines the smallest bounding boxes you want to output based on area 
    def bounding_boxes_coords(video,channel=0,first_frame = 0,last_frame= -1,min_area=200, thresh_calc="first-frame"):
        if len(video.shape) == 4:
            video = np.squeeze(video[:,channel,:,:])
        
        video = video[first_frame:last_frame]
        
        binary_video = None
        if (thresh_calc=='all-frames'):
            binary_video = np.zeros(video.shape)
            for frame_idx, frame in enumerate(video):
                thresh=threshold_otsu(frame)
                binary_video[frame_idx] = video[frame_idx] >= thresh
        
        elif (True or thresh_calc == 'first-frame'):
            # find threshhold in first frame
            thresh = threshold_otsu(video[0])
            # labeling connected components of each frame
            binary_video = video >= thresh


        #applying the label for mask
        labeled_video = np.array([label(binary_frame,background=0,connectivity=2) for binary_frame in binary_video]) 
        
        # deducing centroids, max side length, 
        all_bboxes_coords = list()
        max_num_cells=0
        num_cells_frames = list()
        for labeled_frame in labeled_video:
            props = regionprops_table(label_image=labeled_frame,
                                      properties=['bbox','area']
            )
            df = pd.DataFrame(props)
            df = df[df['area'] >= min_area]
            df= df.drop(columns = ['area'])
            max_num_cells = max(max_num_cells, df.shape[0])
            num_cells_frames.append(df.shape[0])
            all_bboxes_coords.append(list(df.itertuples(index=False, name=None)))
        
        return all_bboxes_coords, max_num_cells, num_cells_frames

    
    #returns an JAGGED array of shape (num frames, num bboxes, height of image slice corresponding to bbox in frame
    #                                  width of image slice corresponding to bbox in frame)
    def coords_to_bbox_vid(video, bbox_coords):
        # bboxes_video = np.zeros((frames, max_num_cells, max_bbox_size, max_bbox_size))
        bboxes_video = list()
        for frame_idx, frame in enumerate(video):
            frame_list = list()
            for bbox in bbox_coords[frame_idx]:
                min_row, min_col, max_row, max_col = bbox
                frame_list.append(frame[min_row:max_row,min_col:max_col])
            bboxes_video.append(frame_list)

        return bboxes_video

    # borrowed from sammy. can be passed as a "transform argument"
    def scale_img(img):
        lower_bound = np.percentile(img, 1)
        upper_bound = np.percentile(img, 99.9)
        I = (img - lower_bound) / (upper_bound - lower_bound)
        I = np.clip(I, 0, 1)
        return(I)
    
  
        
    