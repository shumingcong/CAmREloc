import tensorflow as tf


def weight_variable(shape, name='', w=0.1):
    initial = tf.truncated_normal(shape, stddev=w)

    if name != '':
        return tf.Variable(initial, name=name)

    return tf.Variable(initial)


def weight_xavier(shape, name=''):
    initializer = tf.contrib.layers.xavier_initializer()
    if name != '':
        return tf.Variable(initializer(shape), name=name)

    return tf.Variable(initializer(shape))


def bias_variable(shape, name='', w=0.001):
    initial = tf.truncated_normal(shape, stddev=w)

    if name != '':
        return tf.Variable(initial, name=name)

    return tf.Variable(initial)


def bias_constant(shape, name=''):
    initializer = tf.constant_initializer(0.0)

    if name != '':
        return tf.Variable(initializer(shape), name=name)

    return tf.Variable(initializer(shape))


def conv_block(inp_ten, k_size, c_in, c_out, strides=[1, 1, 1, 1], padding='SAME', enable_activation=True):
    w = weight_xavier(shape=[k_size, k_size, c_in, c_out])
    b = bias_constant(shape=[c_out])
    conv = tf.nn.conv2d(input=inp_ten, filter=w, strides=strides, padding=padding)
    conv = tf.nn.bias_add(conv, b)
    
    if enable_activation:
        return tf.nn.relu(conv)
    else:
        return conv


def inception_block(inp_ten, f11, f11_reduce3, f11_reduce5, f33, f55, fpp):
    """

    :param inp_ten:     block input
    :param f11:         num 1x1 filters
    :param f11_reduce3: num 1x1 reduce filters
    :param f11_reduce5: num 1x1 reduce filters
    :param f33:         num 3x3 filters
    :param f55:         num 5x5 filters
    :param fpp:         num 1x1 filters after max_pool
    :return:
    """
    c_in = inp_ten.get_shape().as_list()[-1]

    conv_1_3 = conv_block(inp_ten, k_size=1, c_in=c_in, c_out=f11_reduce3)
    conv_3_3 = conv_block(conv_1_3, k_size=3, c_in=f11_reduce3, c_out=f33)

    conv_1_5 = conv_block(inp_ten, k_size=1, c_in=c_in, c_out=f11_reduce5)
    conv_5_5 = conv_block(conv_1_5, k_size=5, c_in=f11_reduce5, c_out=f55)

    max_pool_1_1 = tf.nn.max_pool(value=inp_ten, ksize=[1, 3, 3, 1], strides=[1, 1, 1, 1], padding='SAME')
    conv_pool_1 = conv_block(max_pool_1_1, k_size=1, c_in=c_in, c_out=fpp)

    conv_1_1 = conv_block(inp_ten, k_size=1, c_in=c_in, c_out=f11)

    concat = tf.concat([conv_1_1, conv_3_3, conv_5_5, conv_pool_1], axis=3)

    return concat


def in_block(inp_ten):
    c_in = inp_ten.get_shape().as_list()[-1]

    conv_1 = conv_block(inp_ten, k_size=7, c_in=c_in, c_out=64, strides=[1, 2, 2, 1])
    max_pool_1 = tf.nn.max_pool(value=conv_1, ksize=[1, 3, 3, 1], strides=[1, 2, 2, 1], padding='SAME')

    lrn_1 = tf.nn.local_response_normalization(max_pool_1)

    conv_2 = conv_block(lrn_1, k_size=1, c_in=64, c_out=64)
    conv_3 = conv_block(conv_2, k_size=3, c_in=64, c_out=192)

    lrn_2 = tf.nn.local_response_normalization(conv_3)

    max_pool_2 = tf.nn.max_pool(value=lrn_2, ksize=[1, 3, 3, 1], strides=[1, 2, 2, 1], padding='SAME')

    return max_pool_2


def auxiliary_classifier_block(inp_ten):
    av_pool = tf.nn.avg_pool(value=inp_ten, ksize=[1, 5, 5, 1], strides=[1, 3, 3, 1], padding='SAME')

    c_in = av_pool.get_shape().as_list()[-1]
    conv_1 = conv_block(av_pool, k_size=1, c_in=c_in, c_out=128)

    flatten = tf.layers.flatten(conv_1)
    fc_1 = tf.layers.dense(inputs=flatten, units=2048)
    # fc_1 = tf.nn.dropout(fc_1, 0.3)
    # fc_2 = tf.layers.dense(inputs=fc_1, units=7)
    fc_pos = tf.layers.dense(fc_1, units=3)
    fc_qua = tf.layers.dense(fc_1, units=4)

    fc_2 = tf.concat([fc_pos, fc_qua], 1)

    return fc_2


def residual_block(inp_ten, filter_size, c_out, strides=[1, 1, 1, 1], padding='SAME', enable_proj_shortcut=False, is_train=True):

    shortcut = inp_ten
    c_in = inp_ten.get_shape().as_list()[-1]

    if enable_proj_shortcut:
        shortcut = conv_block(inp_ten, k_size=filter_size, c_in=c_in, c_out=c_out, strides=[1, 2, 2, 1], padding=padding)

    conv_1 = conv_block(inp_ten, k_size=filter_size, c_in=c_in, c_out=c_out, strides=strides, padding=padding)
  
    conv_1 = tf.layers.batch_normalization(conv_1, training=is_train)

    conv_2 = conv_block(conv_1, k_size=filter_size, c_in=c_out, c_out=c_out, enable_activation=False)

    conv_2 = tf.layers.batch_normalization(conv_2, training=is_train)

    return tf.nn.relu(conv_2 + shortcut)


def decoder_block(inp_ten, filter_size, c_out, out_size, is_train=True):

    in_size = inp_ten.get_shape().as_list()[2]
    pad_size_l = (out_size - in_size) // 2
    pad_size_r = out_size - in_size - pad_size_l 

    pad_ten = tf.pad(inp_ten, paddings=[[0, 0], [pad_size_l, pad_size_r], [pad_size_l, pad_size_r], [0, 0]])
    c_in = pad_ten.get_shape().as_list()[-1]
    conv_1 = conv_block(pad_ten, k_size=filter_size, c_in=c_in, c_out=c_out)

    return tf.layers.batch_normalization(conv_1, training=is_train)


def hourglass_regressor(inp_ten):
    flatten = tf.layers.flatten(inp_ten)

    fc_1 = tf.layers.dense(inputs=flatten, units=2048)

    fc_pos = tf.layers.dense(fc_1, units=3)
    fc_qua = tf.layers.dense(fc_1, units=4)

    fc_2 = tf.concat([fc_pos, fc_qua], 1)

    return fc_2
