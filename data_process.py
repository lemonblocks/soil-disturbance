import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt
import random
from data_split import activitySplit
import pywt

def cut_value(data, value):
    """整个数组减去某个值
    """
    if isinstance(data, list):
        return [(data_ - value) for data_ in data]
    elif isinstance(data, np.ndarray):
        return data - value
    else:
        raise TypeError("Input data must be list or numpy.array, not {}".format(type(data)))

def cut_mean(data):
    """减均值操作
    """
    return cut_value(data, np.mean(data))

def min_max_normalize(data):
    """最大 - 最小值归一化
    """
    if isinstance(data, list):
        return [(data_ - np.min(data)) / (np.max(data) - np.min(data)) for data_ in data]
    elif isinstance(data, np.ndarray):
        return (data - np.min(data)) / (np.max(data) - np.min(data))
    else:
        raise TypeError("Input data must be list or numpy.array, not {}".format(type(data)))

def fill_data_with_value(data, value, length=96):
    """用 value 将 data 填充到 length，超过则截断
    """
    if len(data) < length:
        data = data + [value] * (length-len(data))
    return data[:length]

def extract_data_from_center(data, center, value, length=96):
    """以 center 为中心向两边扩张，从 data 中截取一段长为 length 的信号
    """
    step = length // 2
    return fill_data_with_value(data[center-step: center+step], value)

def get_activity_label(file_name):
    """根据文件名，给出分类的标签
    """
    if 'dig' in file_name:
        return 0
    elif 'jump' in file_name:
        return 1
    elif 'walk' in file_name:
        return 2 
    else:
        raise ValueError("Unrecognized activity: {}".format(file_name))

def get_area_label(floder):
    """根据文件根级目录，给出土质(场地)标签
    """
    if 'syf' in floder:
        return 0
    elif 'yqcc' in floder:
        return 1
    elif 'zwy' in floder:
        return 2
    elif 'j11' in floder:
        return 3
    elif 'zyq' in floder:
        return 4
    else:
        raise ValueError("Unrecognized area: {}".format(floder))

def plot_time(signal, sample_rate=1, title=None):
    """matplot画图
    """
    time = np.arange(0, len(signal)) * (1.0 / sample_rate)
    plt.figure(figsize=(20, 5))
    plt.plot(time, signal)
    plt.xlabel('Time(s)')
    plt.ylabel('Amplitude')
    if title:
        plt.title(title)
    plt.grid()

def cal_angles(base_value):
    """计算三轴加速度与g方向的夹角
    """
    return {'x': np.arctan(np.sqrt(base_value[1]**2 + base_value[2]**2) / base_value[0]),
            'y': np.arctan(np.sqrt(base_value[0]**2 + base_value[2]**2) / base_value[1]),
            'z': np.arctan(np.sqrt(base_value[0]**2 + base_value[1]**2) / base_value[2])}

def generate_data(root_path, by_txt=True, shuffle=True, factor=0.2):
    """
    根据打好标签的 txt 文件导入数据，并按文件来划分训练集以及测试集
    其中训练集，测试集默认按 0.8 0.2 比例划分
    数据集目录结构：area/data/, area/txt/
    """
    data_root, txt_root = root_path + '/data', root_path + '/txt'
    train_data, test_data = [], []
    file_data_dict = {}

    file_name_list = os.listdir(data_root)

    for file_name in file_name_list:
        
        file_path = data_root + '/' + file_name
        
        dataXYZ = pd.read_csv(file_path, header= 0)
        data_x, data_y, data_z = list(dataXYZ.iloc[:,0]), list(dataXYZ.iloc[:, 1]), list(dataXYZ.iloc[:, 2])
        base_value = cal_base_value(dataXYZ, 32, 16, 500)
        
        if by_txt:
            txt_path = txt_root + '/' + file_name[:-3] + 'txt'
            with open(txt_path, 'r') as f:
                activity_list = f.readlines()
            activity_list = [int(activity[:-1]) for activity in activity_list]
        else:
            activity_list = [int(np.mean(idx)) for idx in activitySplit(dataXYZ, 32, 16, 500)]

        activity_list = [{'data_x': np.array(extract_data_from_center(data_x, center, base_value[0])),
                        'data_y': np.array(extract_data_from_center(data_y, center, base_value[1])),
                        'data_z': np.array(extract_data_from_center(data_z, center, base_value[2])),
                        'label': get_activity_label(file_name), 'file_name': file_name, 'base_value':base_value,
                        'angle': cal_angles(base_value), 'area': get_area_label(root_path) }
                        for center in activity_list]
        
        if shuffle:
            random.shuffle(activity_list)
        
        test_data = test_data + activity_list[: int(factor * len(activity_list))]
        train_data = train_data + activity_list[int(factor * len(activity_list)): ]
        file_data_dict[file_name] = activity_list
    
    return train_data, test_data, file_name_list, file_data_dict

def cal_base_value(dataXYZ, windowSize, stepSize, length):
    """计算采集得到信号的基线值
    """
    
    data_x, data_y, data_z = list(dataXYZ.iloc[:,0]), list(dataXYZ.iloc[:, 1]), list(dataXYZ.iloc[:, 2])
    length = min(len(data_x) // stepSize, length)

    base_x = []
    base_y = []
    base_z = []
    for i in range(0, len(data_x), stepSize):
        base_x.append(np.mean(data_x[i: i+windowSize]))
        base_y.append(np.mean(data_y[i: i+windowSize]))
        base_z.append(np.mean(data_z[i: i+windowSize]))
    
    base_x = base_x[: length]
    base_y = base_y[: length]
    base_z = base_z[: length]

    base_x.sort()
    base_y.sort()
    base_z.sort()

    base_x_ = (base_x[int(0.25*length)] + base_x[int(0.75*length)]) / 2
    base_y_ = (base_y[int(0.25*length)] + base_y[int(0.75*length)]) / 2
    base_z_ = (base_z[int(0.25*length)] + base_z[int(0.75*length)]) / 2

    return base_x_, base_y_, base_z_

def get_wt_features(signal, level=4):
    """指定某一轴的信号，进行小波分解，获取特征
    """
    features = []
    wp = pywt.WaveletPacket(data=signal, wavelet='db3', mode='symmetric', maxlevel=level)
    for node in wp.get_level(level, 'freq'):
        data = wp[node.path].data
        features.append(data)
    
    return np.array(features, dtype=np.float64)

def handle_data_3dims(item, mode='origin'):
    """
    将单个切割出来的数据处理按mode处理成三轴数
    mode: 'origin'-只减基线，'combine'-转换为x2+y2+z2, x2+y2, z三轴数据
    """
    base, angle = item['base_value'], item['angle'] # xyz的基线，以及其与g的夹角
    data_x, data_y, data_z = item['data_x'], item['data_y'], item['data_z']

    if mode == 'combine':
        data_xyz = np.sqrt((data_x-base[0])**2 + (data_y-base[1])**2 + (data_z-base[2])**2) # x2+y2+z2不论如何都减基线
        data_z_rectify = data_x * np.cos(angle['x']) + data_y * np.cos(angle['y']) + data_z * np.cos(angle['z']) # 修正过的z轴数据
        base_z = base[0] * np.cos(angle['x']) + base[0] * np.cos(angle['y']) + base[0] * np.cos(angle['z']) # 修正过的z轴baseline
        data_xy = np.sqrt((data_x-base[0])**2 + (data_y-base[1])**2)
        data_z_rectify = data_z_rectify - base_z # 修正过的z轴数据，并减去基线

        # data = np.array([data_z_rectify, data_xy, data_xyz], dtype=np.float64)
        data = np.array([cut_mean(data_xyz), cut_mean(data_xy), cut_mean(data_z_rectify)], dtype=np.float64)

    elif mode == 'origin':
        data = np.array([data_x-base[0], data_y-base[1], data_z-base[2]], dtype=np.float64)

    elif mode == 'wavelet':
        wt_x, wt_y, wt_z = get_wt_features(data_x-base[0]), get_wt_features(data_y-base[1]), \
            get_wt_features(data_z-base[2])
        data = np.array([wt_x, wt_y, wt_z])

    else:
        raise ValueError("Unrecognized mode: {}".format(mode))
    
    return data

def handle_dataset_3dims(dataset, file_name_list, mode='origin'):
    """
    对原始的数据进行处理，生成 data 与对应的 label
    file_name_list: 需要用于生成数据集的文件名，在测试时可以选择几个文件单独生成数据集
    mode: 'origin'-只减基线，'combine'-转换为x2+y2+z2, x2+y2, z三轴数据
    """
    
    data = []
    label = []

    for item in dataset:
        if item['file_name'] in file_name_list:
            data.append(handle_data_3dims(item, mode))
            label.append(item['label'])
    
    data = np.array(data, dtype=np.float64)
    label = np.array(label)
    return data, label

def get_specific_data(root_path, by_txt=True, activity='dig', dis='1.0', num=None):
    """具体取出某距离上发生的某事件信号
    """
    data_root, txt_root = root_path + '/data', root_path + '/txt'
    total_activity = []
    file_name_list = [name for name in os.listdir(data_root) if activity in name and dis in name]

    for file_name in file_name_list:
        file_path = data_root + '/' + file_name
        dataXYZ = pd.read_csv(file_path, header= 0)
        data_x, data_y, data_z = list(dataXYZ.iloc[:,0]), list(dataXYZ.iloc[:, 1]), list(dataXYZ.iloc[:, 2])
        base_value = cal_base_value(dataXYZ, 32, 16, 500)
        
        if by_txt: # 获取 activity_list
            txt_path = txt_root + '/' + file_name[:-3] + 'txt'
            with open(txt_path, 'r') as f:
                activity_list = f.readlines()
            activity_list = [int(activity[:-1]) for activity in activity_list]
        else:
            activity_list = [int(np.mean(idx)) for idx in activitySplit(dataXYZ, 32, 16, 500)]

        activity_list = [{'data_x': np.array(extract_data_from_center(data_x, center, base_value[0])),
                        'data_y': np.array(extract_data_from_center(data_y, center, base_value[1])),
                        'data_z': np.array(extract_data_from_center(data_z, center, base_value[2])),
                        'label': get_activity_label(file_name), 'file_name': file_name, 'base_value':base_value,
                        'angle': cal_angles(base_value), 'area': get_area_label(data_root)} 
                        for center in activity_list]
        
        total_activity += activity_list

    if num is not None:
        return random.choices(total_activity, k=num)
    else:
        return total_activity

def cal_snr(s, n):
    """估计信号的信噪比，Ps/Pn（没有将x与n分开，并非精确SNR）
    inputs:
        s: 原始时间序列 np.array
        n: 噪声序列 np.array
    returns:
        snr: 估计的信噪比
    """
    return np.sum(s**2) / np.sum(n**2)


if __name__ == '__main__':
    root = 'E:/研一/嗑盐/土壤扰动/dataset/zwy_d1'
    print(get_specific_data(root))
