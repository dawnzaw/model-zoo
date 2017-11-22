import numpy as np

import sklearn.preprocessing as prep
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data

from autoencoder_models.DenoisingAutoencoder import MaskingNoiseAutoencoder

import missinglink as ml

FLAGS = tf.flags.FLAGS

mnist = input_data.read_data_sets('MNIST_data', one_hot = True)

def standard_scale(X_train, X_test):
    preprocessor = prep.StandardScaler().fit(X_train)
    X_train = preprocessor.transform(X_train)
    X_test = preprocessor.transform(X_test)
    return X_train, X_test

def get_random_block_from_data(data, batch_size):
    start_index = np.random.randint(0, len(data) - batch_size)
    return data[start_index:(start_index + batch_size)]

X_train, X_test = standard_scale(mnist.train.images, mnist.test.images)


n_samples = int(mnist.train.num_examples)
training_epochs = 100
batch_size = 128
display_step = 1

autoencoder = MaskingNoiseAutoencoder(n_input = 784,
                                      n_hidden = 200,
                                      transfer_function = tf.nn.softplus,
                                      optimizer = tf.train.AdamOptimizer(learning_rate = 0.001),
                                      dropout_probability = 0.95)

project = ml.TensorFlowProject(owner_id="your-owner-id", project_token="your-project-token")

avg_cost = 0.
with project.create_experiment(
    "Autoencoder",
    custom_metrics={'avg cost': lambda: avg_cost},
    monitored_metrics={'cost': autoencoder.cost}
) as experiment:
    for epoch in experiment.epoch_loop(training_epochs):
        avg_cost = 0.
        total_batch = int(n_samples / batch_size)
        # Loop over all batches
        for i in experiment.batch_loop(total_batch):
            batch_xs = get_random_block_from_data(X_train, batch_size)

            # Fit training using batch data
            with experiment.train():
                cost = autoencoder.partial_fit(batch_xs)
                # Compute average loss
                avg_cost += cost / n_samples * batch_size

        # Display logs per epoch step
        if epoch % display_step == 0:
            print("Epoch:", '%04d' % (epoch + 1), "cost=", "{:.9f}".format(avg_cost))

print("Total cost: " + str(autoencoder.calc_total_cost(X_test)))
