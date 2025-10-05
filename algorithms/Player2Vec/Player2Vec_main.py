"""
This code is attributed to Yutong Deng (@yutongD), Yingtong Dou (@YingtongDou),
Zhongzheng Lu(@lzz-hub-dev) and UIC BDSC Lab
DGFraud (A Deep Graph-based Toolbox for Fraud Detection)
https://github.com/safe-graph/DGFraud
"""

import argparse
import numpy as np
from tqdm import tqdm

import tensorflow as tf
from tensorflow.keras import optimizers

from algorithms.Player2Vec.Player2Vec import Player2Vec
from utils.data_loader import load_data_dblp
from utils.utils import preprocess_adj, preprocess_feature, sample_mask


# init the common args, expect the model specific args
parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=123, help='Random seed.')
parser.add_argument('--dataset_str', type=str, default='dblp',
                    help="['dblp','example']")
parser.add_argument('--train_size', type=float, default=0.2,
                    help='training set percentage')
parser.add_argument('--epochs', type=int, default=30,
                    help='Number of epochs to train.')
parser.add_argument('--weight_decay', type=float, default=0.001,
                    help='weight decay')
parser.add_argument('--batch_size', type=int, default=1000)
parser.add_argument('--dropout', type=float, default=0.5, help='dropout rate')
parser.add_argument('--momentum', type=int, default=0.9)
parser.add_argument('--learning_rate', default=0.001,
                    help='the ratio of training set in whole dataset.')
parser.add_argument('--nhid', type=int, default=128,
                    help='number of hidden units in GCN')
parser.add_argument('--lr', default=0.001, help='learning rate')

args = parser.parse_args()

# set seed
np.random.seed(args.seed)
tf.random.set_seed(args.seed)


def Player2Vec_main(support: list,
                    features: tf.SparseTensor,
                    label: tf.Tensor,
                    masks: list,
                    args: argparse.ArgumentParser().parse_args()) -> None:
    """
    Main function to train, val and test the model

    :param support: a list of the sparse adjacency matrices
    :param features: node feature tuple for all nodes {coords, values, shape}
    :param label: the label tensor for all nodes
    :param masks: a list of mask tensors to obtain the train, val, test data
    :param args: additional parameters
    """
    model = Player2Vec(args.input_dim, args.nhid, args.output_dim, args)
    # optimizer = optimizers.Adam(lr=args.lr)
    optimizer = optimizers.legacy.Adam(learning_rate=args.lr)

    # train
    for epoch in tqdm(range(args.epochs)):
        with tf.GradientTape() as tape:
            train_loss, train_acc = model([support, features, label, masks[0]])

        grads = tape.gradient(train_loss, model.trainable_variables)
        optimizer.apply_gradients(zip(grads, model.trainable_variables))

        # validation
        val_loss, val_acc = model([support, features, label, masks[1]])
        print(
            f"Epoch: {epoch:d}, train_loss: {train_loss:.4f}, "
            f"train_acc: {train_acc:.4f},"
            f"val_loss: {val_loss:.4f}, val_acc: {val_acc:.4f}")

    # test
    test_loss, test_acc = model([support, features, label, masks[2]])
    print(f"test_loss: {test_loss:.4f}, test_acc: {test_acc:.4f}")


if __name__ == "__main__":
    # load the data
    adj_list, features, [idx_train, _, idx_val, _, idx_test, _], y = \
        load_data_dblp(meta=True, train_size=args.train_size)
    args.nodes = features.shape[0]

    # convert to dense tensors
    train_mask = tf.convert_to_tensor(sample_mask(idx_train, y.shape[0]))
    val_mask = tf.convert_to_tensor(sample_mask(idx_val, y.shape[0]))
    test_mask = tf.convert_to_tensor(sample_mask(idx_test, y.shape[0]))
    label = tf.convert_to_tensor(y, dtype=tf.float32)

    # get sparse tuples
    features = preprocess_feature(features)
    supports = [preprocess_adj(adj) for adj in adj_list]

    # initialize the model parameters
    args.num_meta = len(supports)
    args.input_dim = features[2][1]
    args.output_dim = y.shape[1]
    args.train_size = len(idx_train)
    args.class_size = y.shape[1]
    args.num_features_nonzero = features[1].shape

    # get sparse tensors
    features = tf.cast(tf.SparseTensor(*features), dtype=tf.float32)
    supports = [tf.cast(tf.SparseTensor(*support), dtype=tf.float32) for
                support in supports]

    Player2Vec_main(supports, features, label,
                    [train_mask, val_mask, test_mask], args)
