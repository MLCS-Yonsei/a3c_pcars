import tensorflow as tf
import numpy as np
import cv2
from time import time, sleep
import os
from glob import glob
import uuid


DATA_FOLDER = './data/data_road/testing/image_2_pcars'

def model_init(device='/gpu:0'):
    INPUT_TENSOR_NAME = 'image_input'
    FINAL_TENSOR_NAME = 'lambda_4/resize_images/ResizeBilinear'
    FREEZED_PATH = './model/frozen.pb'
    IMAGE_SHAPE = (160, 576)

    tf.reset_default_graph()
    with tf.device(device):
        rs_sess = tf.Session(
                config=tf.ConfigProto(
                allow_soft_placement=True,
                log_device_placement=False))
        with tf.gfile.FastGFile(FREEZED_PATH, 'rb') as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())
            tf.import_graph_def(graph_def, name='')

        # op = sess.graph.get_operations()
        # [print(m.values()) for m in op][1]

        input_tensor = rs_sess.graph.get_tensor_by_name(
            INPUT_TENSOR_NAME + ':0')
        output_tensor = rs_sess.graph.get_tensor_by_name(
            FINAL_TENSOR_NAME + ':0')

        img = cv2.imread('./seg/test.png')
        img = cv2.resize(img, (IMAGE_SHAPE[1], IMAGE_SHAPE[0]))
        pimg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pimg = np.float32(pimg) / 127.5 - 1.0
        pimg = np.expand_dims(pimg, axis=0)
        # warm up
        out = rs_sess.run(
            output_tensor, feed_dict={input_tensor: pimg}).squeeze()

        return rs_sess, input_tensor, output_tensor

def load_img(img_path):
    IMAGE_SHAPE = (160, 576)

    img = cv2.imread(img_path)
    img = cv2.resize(img, (IMAGE_SHAPE[1], IMAGE_SHAPE[0]))
    # pimg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # pimg = np.float32(pimg) / 127.5 - 1.0
    pimg = np.expand_dims(pimg, axis=0)

    return img, pimg

def pred_img(sess, input_tensor, output_tensor, pimg): 

    out = sess.run(output_tensor,
                    feed_dict={input_tensor: pimg}).squeeze()
    
    pred = np.uint8(out.argmax(axis=-1))
    # pred_rgb = np.dstack((0 * pred, 255 * pred, 0 * pred))
    # res_img = cv2.addWeighted(img, 0.6, pred_rgb, 0.4, 0.0)
    # img_fn = os.path.join('results',(str(uuid.uuid4())+'.png'))
    # cv2.imwrite(img_fn, res_img)

    return pred

if __name__ == "__main__":

    sess, input_tensor, output_tensor = model_init(FREEZED_PATH)

    print("Start prediction")
    for image_file in glob(os.path.join(DATA_FOLDER, '*.png')):
        
        img, pimg = load_img(image_file)
        tic = time()
        pred_img(sess, input_tensor, output_tensor, img, pimg)
        toc = time()
        duration = (toc - tic)
        print("One forward pass took: %.4f ms"
                % (duration * 1000))
# pred_img(sess, input_tensor, output_tensor)
