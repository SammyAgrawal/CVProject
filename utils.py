from aicspylibczi import CziFile
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.pyplot import imshow
import os


def get_file(vid_type, num):
    root_dir = "/mnt/datadisk/"
    vid_type = vid_type.lower()
    if(vid_type == "processed"):
        folder = 'FactinProcessed'
        fname = f'dicty_factin_pip3-0{num}_processed.czi'
    elif(vid_type == 'mip'):
        folder = 'FactinMIP'
        fname = f'dicty_factin_pip3-0{num}_MIP.czi'
    elif(vid_type == 'new'):
        folder = 'FactinMIP'
        fname = f'New-0{num}_MIP.czi'
    else:
        print(f"invalid type, try again from {['processed', 'mip', 'new']}")
        return(-1)
    fpath = os.path.join(root_dir, folder, fname)
    video = CziFile(fpath)
    print(f"Loading {fname} with dims {video.get_dims_shape()}")
    return(video)


def scale_img(img):
    lower_bound = np.percentile(img, 1)
    upper_bound = np.percentile(img, 99.9)
    I = (img - lower_bound) / (upper_bound - lower_bound)
    I = np.clip(I, 0, 1)
    return(I)


def binarize_video(frames, thresh_calc='all'):
    binary_frames = []
    if (thresh_calc=='all'):
        for frame_idx, frame in enumerate(frames):
            thresh=threshold_otsu(frame)
            B = frame >= thresh
            B = label(B, background=0, connectivity=2)
            binary_frames.append(B)
            
    elif (thresh_calc == 'first'):
        # use threshhold in first frame across entire video
        thresh = threshold_otsu(frames[0])
        for frame_idx, frame in enumerate(frames):
            B = frames[frame_idx] >= thresh
            B = label(B, background=0, connectivity=2)
            binary_frames.append(B)
    
    ## func for labelling connected components
    # https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.label

    return(np.array(binary_frames))


def bounding_boxes(mask, min_area=300):    
    # deducing centroids, max side length, 
    all_bboxes_coords = list()
    max_num_cells=0
    num_cells_frames = list()
    # region props can calculate a LOT of useful properties
    # might want to look into better cell filtering
    props = regionprops_table(label_image=mask,
                              properties=['bbox','area']
    )
    # each row corresponds to cell id, columns corresponds to properties
    # box returned as min_row, min_col, max_row, max_col
    df = pd.DataFrame(props)
    df = df[df['area'] >= min_area]
    cell_areas = df['area'].values
    df= df.drop(columns = ['area'])
    bboxes, num_cells = list(df.itertuples(index=False, name=None)), df.shape[0]
    return bboxes, num_cells, cell_areas


def draw_boxes(frame, boxes, thickness=2, val=1):
    img = frame.copy()
    for bbox in boxes:
        min_row, min_col, max_row, max_col = bbox
        img = cv2.rectangle(img, (min_col, min_row), (max_col, max_row), val, thickness)
    return(img)



def box_tracking_video(frames, masks=-1, thickness=2):
    if(masks == -1):
        # if not provided, calculated
        masks = binarize_video(frames)
        print("Computed binary masks")
    video = []
    num_cells_per_frame = []
    cell_areas = []
    for frame_idx in range(len(frames)):
        boxes, num_cells, areas = bounding_boxes(masks[frame_idx])
        num_cells_per_frame.append(num_cells)
        cell_areas.append(areas)

        img_with_boxes = draw_boxes(frames[frame_idx], boxes, thickness, val=1)
        video.append(img_with_boxes)
        
    return(video, num_cells_per_frame, cell_areas)



def track_cell(cell_id, frames=frames, masks=-1, padding=0):
    N = frames.shape[0]
    data = {"patches" : [], 'boxes' : [], "masks" : []}    
    if(masks == -1):
        # if not provided, calculated
        masks = binarize_video(frames)
        print("Computed binary masks")

    def get_corresponding_cell_box(boxes, num, areas, cell_prev_position=0, cell_prev_area=0):
        ## TO DO : Ensure that index of boxes stays consistent even as boxes appear and dissapear
        return(cell_id)
    
    h_max, w_max = 0, 0
    skip_frames = []
    for i in range(N):
        boxes, num_cells, areas = bounding_boxes(masks[frame_idx]) # all on frame
        index_of_cell = get_corresponding_cell_box(boxes, num_cells, areas) # right now assume same index throughout entire video
        
        bbox = boxes[index_of_cell] # cell id is meant to track a SPECIFIC cell, ensure maintain integrity of cell over time
        
        min_row, min_col, max_row, max_col = bbox

        # adjust boxes based on padding, 
        #TODO might expand boxes to homogenize sizes; 
        min_row -= padding
        min_col -= padding
        max_row += padding
        max_col += padding

        data['boxes'].append((min_row, min_col, max_row, max_col))
        
        patch = frames[i, min_row:max_row, min_col:max_col]
        mask_patch = masks[i, min_row:max_row, min_col:max_col]
        data['patches'].append(patch)
        data['masks'].append(mask_patch)

    return(data)



