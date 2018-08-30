import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion

import csv
import time


model_path='./model/rs_model.ckpt'

# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.' \
                                                            '  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    # Define the name of the tensors
    vgg_tag = 'vgg16'
    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'

    # Get the needed layers' outputs for building FCN-VGG16
    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)
    image_input = tf.get_default_graph().get_tensor_by_name(vgg_input_tensor_name)
    keep_prob = tf.get_default_graph().get_tensor_by_name(vgg_keep_prob_tensor_name)
    vgg_layer3_out = tf.get_default_graph().get_tensor_by_name(vgg_layer3_out_tensor_name)
    vgg_layer4_out = tf.get_default_graph().get_tensor_by_name(vgg_layer4_out_tensor_name)
    vgg_layer7_out = tf.get_default_graph().get_tensor_by_name(vgg_layer7_out_tensor_name)

    return image_input, keep_prob, vgg_layer3_out, vgg_layer4_out, vgg_layer7_out



def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer7_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer3_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # making sure the resulting shape are the same
    vgg_layer7_logits = tf.layers.conv2d(
        vgg_layer7_out, num_classes, kernel_size=1,
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),
        kernel_regularizer= tf.contrib.layers.l2_regularizer(1e-4), name='vgg_layer7_logits')
    vgg_layer4_logits = tf.layers.conv2d(
        vgg_layer4_out, num_classes, kernel_size=1,
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),
        kernel_regularizer= tf.contrib.layers.l2_regularizer(1e-4), name='vgg_layer4_logits')
    vgg_layer3_logits = tf.layers.conv2d(
        vgg_layer3_out, num_classes, kernel_size=1,
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),
        kernel_regularizer= tf.contrib.layers.l2_regularizer(1e-4), name='vgg_layer3_logits')

    # # Apply the transposed convolutions to get upsampled version, and then merge the upsampled layers
    fcn_decoder_layer1 = tf.layers.conv2d_transpose(
        vgg_layer7_logits, num_classes, kernel_size=4, strides=(2, 2),
        padding='same',
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),
        kernel_regularizer= tf.contrib.layers.l2_regularizer(1e-4), name='fcn_decoder_layer1')

    # add the first skip connection from the vgg_layer4_out
    fcn_decoder_layer2 = tf.add(
        fcn_decoder_layer1, vgg_layer4_logits, name='fcn_decoder_layer2')

    # then follow this with another transposed convolution layer and make shape the same as layer3
    fcn_decoder_layer3 = tf.layers.conv2d_transpose(
        fcn_decoder_layer2, num_classes, kernel_size=4, strides=(2, 2),
        padding='same',
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),
        kernel_regularizer= tf.contrib.layers.l2_regularizer(1e-4), name='fcn_decoder_layer3')

    # apply the same steps for the third layer output.
    fcn_decoder_layer4 = tf.add(
        fcn_decoder_layer3, vgg_layer3_logits, name='fcn_decoder_layer4')
    fcn_decoder_output = tf.layers.conv2d_transpose(
        fcn_decoder_layer4, num_classes, kernel_size=16, strides=(8, 8),
        padding='same',
        kernel_initializer= tf.random_normal_initializer(stddev=0.01),
        kernel_regularizer= tf.contrib.layers.l2_regularizer(1e-4), name='fcn_decoder_layer4')

    return fcn_decoder_output


def predict_images(test_data_path, print_speed=False):
    num_classes = 2
    image_shape = (160, 576)
    runs_dir = './runs'

    # Path to vgg model
    vgg_path = os.path.join('./data', 'vgg')

    with tf.Session() as sess:
        # Predict the logits
        input_image, keep_prob, vgg_layer3_out, vgg_layer4_out, vgg_layer7_out = load_vgg(sess, vgg_path)
        nn_last_layer = layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes)
        logits = tf.reshape(nn_last_layer, (-1, num_classes))

        # Restore the saved model
        saver = tf.train.Saver()
        saver.restore(sess, model_path)
        print("Restored the saved Model in file: %s" % model_path)

        # Predict the samples
        helper.pred_samples(runs_dir, test_data_path, sess, image_shape, logits, keep_prob, input_image, print_speed)

if __name__ == '__main__':

    training_flag = False   # True: train the NN; False: predict with trained NN

    if training_flag:
        # run unittest before training
        tests.test_load_vgg(load_vgg, tf)
        tests.test_layers(layers)
        tests.test_optimize(optimize)
        tests.test_train_nn(train_nn)

        # train the NN and save the model
        run()
    else:
        # use the pre-trained model to predict more images
        test_data_path = './data/data_road/testing/image_2'
        predict_images(test_data_path, print_speed=True)