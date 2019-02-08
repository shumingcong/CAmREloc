import os
import numpy as np


from utils.image_processing import preprocess


class Batcher:

    def __init__(self, path_to_data, path_to_csv, batch_size, net_type='pose_net'):
        self.data_path = path_to_data
        self.csv_path = path_to_csv
        self.batch_size = batch_size
        self.net_type = net_type

        self.data = []
        self.num_ex = 0
        self.load_set()

        self.global_idx = 0
        self.generator = self.__iter__()

    @property
    def all_num_ex(self):
        return self.num_ex

    @property
    def b_size(self):
        return self.batch_size

    def load_set(self):

        with open(self.csv_path, 'r') as csv_file:
            lines = csv_file.readlines()
            self.num_ex = len(lines)

            for line in lines:
                info = line.split(',')
                img_path = info[-3]
                px, py, pz = info[3:6]
                qw, qx, qy, qz = info[6:10]
                sample_dict = {
                    'pos': np.array([px, py, pz], dtype=np.float32),
                    'qua': np.array([qw, qx, qy, qz], dtype=np.float32),
                    'img': preprocess(os.path.join(self.data_path, img_path), (480, 640, 3), 'center_crop')
                }

                self.data.append(sample_dict)

        print('Data loaded!')

    def next_batch(self):

        return next(self.generator)

    def __iter__(self):
        while True:
            if self.global_idx + self.batch_size < self.num_ex:
                self.global_idx = 0
                np.random.shuffle(self.data)

            idx = self.global_idx
            self.global_idx += self.batch_size

            if self.net_type == 'pose_net':
                x = []
                y = []
                for i in range(idx, idx+self.batch_size):
                    x.append(self.data[idx]['img'])
                    y.append(np.hstack((self.data[idx]['pos'], self.data[idx]['qua'])))

                yield np.stack(x), np.stack(y)
            else:
                yield self.data[idx:idx + self.batch_size]
