import pandas as pd
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

def _generate_data(skillinflow: pd.DataFrame, skilloutflow: pd.DataFrame, time_range: list, skills: list, class_num: int, min_length: int):
    '''generate training sequence data and demand/supply normalized company-position pairwise matrix data
    '''
    inflow_matrices = _get_matrices(skillinflow, time_range)
    outflow_matrices = _get_matrices(skilloutflow, time_range)
    # print(torch.isnan(inflow_matrices).any())
    # print(inflow_matrices[:,0])
    # print(inflow_matrices)
    # sampling
    data = []
    assert inflow_matrices.size() == outflow_matrices.size()
    max_length = inflow_matrices.size(0)
    min_length = min_length
    # for l in range(min_length, 18, 2):  # l: x's length
    #     for i in range(0, max_length - l, 3):
    #         temp_i_x = []
    #         temp_i_y = []
    #         temp_o_x = []
    #         temp_o_y = []
    #         temp_s = []
    #         Length = l
    #         sta = i
    #         end = i+l-1
    #         for si in range(len(skills)):
    #             temp_i_x.append(inflow_matrices[i: i + l, si])
    #             temp_o_x.append(outflow_matrices[i: i + l, si])
    #             temp_i_y.append(inflow_matrices[i + l, si])
    #             temp_o_y.append(outflow_matrices[i + l, si])
    #             temp_s.append(si)
    #         temp_i_x = torch.stack(temp_i_x,dim=0)
    #         temp_o_x = torch.stack(temp_o_x,dim=0)
    #         temp_i_y = torch.stack(temp_i_y,dim=0)
    #         temp_o_y = torch.stack(temp_o_y,dim=0)
    #         temp_s = torch.tensor(np.array(temp_s))
    #         sample = {'X': (temp_i_x, temp_o_x), 'Y': (temp_i_y, temp_o_y), 'L': Length, 'S': temp_s, 'Sta': sta, 'End': end}
    #         data.append(sample)
    # # labeling
    # ys = []
    # for sample in data:
    #     d_y, s_y = sample['Y']
    #     ys.append(d_y)
    #     ys.append(s_y)
    # val_range_list = _get_labels(torch.stack(ys), class_num)
    # # print(val_range_list)
    # for sample in data:
    #     d_y, s_y = sample['Y']
    #     d_y_label = _to_label(d_y, val_range_list, class_num)
    #     s_y_label = _to_label(s_y, val_range_list, class_num)
    #     sample['Y_Label'] = (d_y_label, s_y_label)
    # return data, inflow_matrices, outflow_matrices
    # d_ys = []
    # s_ys = []
    # for sample in data:
    #     d_y, s_y = sample['Y']
    #     d_ys.append(d_y)
    #     s_ys.append(s_y)
    # d_val_range_list = _get_labels(torch.stack(d_ys), class_num)
    # s_val_range_list = _get_labels(torch.stack(s_ys), class_num)
    
    # print(val_range_list)
    # std_inflow_dict = {}
    # std_outflow_dict = {}
    # for si in range(len(skills)):
    #     std_inflow_si = np.std(inflow_matrices[:, si])
    #     std_outflow_si = np.std(outflow_matrices[:, si])
    #     std_inflow_dict[si] = std_inflow_si
    #     std_outflow_dict[si] = std_outflow_si
    for l in range(min_length, inflow_matrices.size(0), 2):  # l: x's length
        for i in range(0, max_length - l, 3):
            for si in range(len(skills)):
                x = (inflow_matrices[i: i + l, si], outflow_matrices[i: i + l, si])
                # if x[0].sum() < 0.2 or x[1].sum() < 0.2:
                #     continue
                y = (inflow_matrices[i + l, si], outflow_matrices[i + l, si])
                sample = {'X': x, 'Y': y, 'L': l, 'S': si, 'Sta': i, 'End': i + l - 1}
                data.append(sample)
    
    # labeling
    ys = []
    for sample in data:
        d_y, s_y = sample['Y']
        ys.append(d_y)
        ys.append(s_y)
    val_range_list = _get_labels(torch.stack(ys), class_num)

    # print(val_range_list)
    for sample in data:
        d_y, s_y = sample['Y']
        d_y_label = _to_label(d_y, val_range_list, class_num)
        s_y_label = _to_label(s_y, val_range_list, class_num)
        sample['Y_Label'] = (d_y_label, s_y_label)
    return data, inflow_matrices, outflow_matrices
    


def _get_matrices(count, time_range):
    '''get normalized company-position pairwise matrix data
    '''
    matrices = {}
    # build matrix
    for time in time_range:
        matrix = count[time].astype('float32')
        matrix[matrix.isna()] = 0.0
        matrix += 1.0  # avoid divided by 0
        matrices[time] = torch.from_numpy(matrix.values)
    # stack data
    matrices = torch.stack(list(matrices.values()),dim=0).float()
    # print(torch.std(matrices,dim=0,unbiased=True).shape)
    # print((torch.std(matrices,dim=0,unbiased=True)==0).any())
    # normalize data
    matrices = F.normalize(matrices, dim=0)
    print(matrices[0,:])
    # matrices_submean = torch.sub(matrices, torch.mean(matrices, dim=0))
    # matrices = torch.div(matrices_submean, torch.maximum(torch.std(matrices,dim=0,unbiased=True), torch.tensor(1)))
    return matrices

def _get_labels(vec: torch.Tensor, class_num: int):
    '''split all range for data and get value range for each labels
    '''
    vec_tmp: torch.Tensor = vec.reshape(-1)
    vec_tmp, _ = vec_tmp.sort()
    n = len(vec_tmp)
    val_range_list: list = []
    for i in range(class_num):
        val_range_list.append(vec_tmp[(n // class_num) * i])
    val_range_list.append(vec_tmp[-1])
    return val_range_list

# def _get_label_SAX(vec: torch.Tensor, class_num: int):
    
def _to_label(vec: torch.Tensor, val_range_list: list, class_num: int):
    '''map continuous values to `class_num` discrete labels for `vec` using `val_range_list`
    '''

    def _to_label_(v: float, val_range_list: list, class_num: int):
        if v < val_range_list[0]:
            return 0
        for i in range(class_num):
            if val_range_list[i] <= v <= val_range_list[i + 1]:
                return i
        return class_num - 1

    return vec.clone().apply_(lambda x: _to_label_(x, val_range_list, class_num)).long()