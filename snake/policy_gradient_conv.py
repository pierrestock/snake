# -------- Setup ------- #
#load useful libraries
import numpy as np
import tensorflow as tf
import pickle as pkl

from time import time
from numpy import random
from tools import sample_from_policy
import matplotlib.pyplot as plt

# load THE SNAKE
from snake import Snake
snake = Snake()

# define parameters
n_input = 2 * snake.grid_size * snake.grid_size
n_hidden = 200
n_classes = 4

# --- Policy Network --- #

# define placeholders for inputs and outputs
input_frames = tf.placeholder(tf.float32, [None, n_input])
y_played = tf.placeholder(tf.float32, [None, n_classes])
advantages = tf.placeholder(tf.float32, [1, None])

# initialize weights
w1 = tf.Variable(tf.truncated_normal([n_input, n_hidden]))
b1 = tf.Variable(tf.zeros([1, n_hidden]))
w2 = tf.Variable(tf.truncated_normal([n_hidden, n_classes]))
b2 = tf.Variable(tf.zeros([1, n_classes]))

# define network structure
hidden_layer = tf.add(tf.matmul(input_frames, w1), b1)
hidden_layer = tf.nn.relu(hidden_layer)
out_layer = tf.add(tf.matmul(hidden_layer, w2), b2)
out_probs = tf.nn.softmax(out_layer)

# define loss and optimizer
epsilon = 1e-15
log_probs = tf.log(tf.add(out_probs, epsilon))
loss = tf.reduce_sum(tf.matmul(advantages,(tf.mul(y_played, log_probs))))
optimizer = tf.train.AdamOptimizer(learning_rate=0.001).minimize(loss)

# ------ Train ------ #
def train(batch_size, n_iterations):

    # initialize the variables
    init = tf.global_variables_initializer()

    # initialize counts
    games_count = 0
    iterations_count = 0
    running_time = time()

    with tf.Session() as sess:

        # initialize variables
        sess.run(init)

        # used later to save variables for the batch
        frames_stacked = []
        targets_stacked = []
        rewards_stacked = []
        lifetime = []
        avg_lifetime = []
        fruits_count = 0

        while iterations_count < n_iterations:

            # initialize snake environment and some variables
            snake = Snake()
            frame_curr = snake.grid
            rewards_running = []
            reset = False

            # loop for one game
            while not reset:

                # get current frame
                frame_prev = np.copy(frame_curr)
                frame_curr = snake.grid

                # forward previous and current frames
                last_two_frames = np.reshape(np.hstack((frame_prev, frame_curr)), (1, n_input))
                frames_stacked.append(last_two_frames)
                policy = np.ravel(sess.run(out_probs, feed_dict = {input_frames : last_two_frames}))

                # sample action from returned policy
                action = sample_from_policy(policy)

                # build labels according to the sampled action
                target = np.zeros(4)
                target[action] = 1

                # play THE SNAKE and get the reward associated to the action
                reward, reset = snake.play(action)
                if reward == 100:
                    fruits_count += 1
                rewards_running += [reward]

                # save targets
                targets_stacked.append(target)

            # stack rewards
            games_count += 1
            lifetime.append(len(rewards_running)*1.)
            rewards_stacked.append([np.sum(rewards_running)] * len(rewards_running)) # TODO: add gamma factor

            if games_count % batch_size == 0:
                iterations_count += 1

                # display every 10 batches
                if iterations_count % 10 == 0:
                    print("Batch #%d, average lifetime %.2f, fruits eaten %d, games played: %d, time %d sec" %
                            (iterations_count, np.mean(lifetime), fruits_count, games_count, time() - running_time))
                    running_time = time()

                # stack frames, targets and rewards
                frames_stacked = np.vstack(frames_stacked)
                targets_stacked = np.vstack(targets_stacked)
                rewards_stacked = np.hstack(rewards_stacked)
                rewards_stacked = np.reshape(rewards_stacked, (1, len(rewards_stacked)))*1.
                avg_lifetime.append(np.mean(lifetime))

                # normalize rewards
                rewards_stacked -= np.mean(rewards_stacked)
                std = np.std(rewards_stacked)
                if std != 0:
                    rewards_stacked /= std

                # backpropagate
                sess.run([optimizer, loss], feed_dict={input_frames: frames_stacked, y_played: targets_stacked, advantages: rewards_stacked})

                # reset variables
                frames_stacked = []
                targets_stacked = []
                rewards_stacked = []
                lifetime = []
                fruits_count = 0

        # Plot useful statistics
        plt.plot(avg_lifetime)
        plt.title('Average lifetime')
        plt.show()
        plt.savefig('average_lifetime.png')

        # save model
        print('Saving model to weights.p')
        pkl.dump((w1.eval(), b1.eval(), w2.eval(), b2.eval()), open('weights.p','w'))

# ---- Test ---- #
def test(weights_path):

    # asssign weights
    print('Loading model')
    weights = pkl.load(open('weights.p', 'rb'))
    assign_w1 = tf.assign(w1, weights[0])
    assign_b1 = tf.assign(b1, weights[1])
    assign_w2 = tf.assign(w2, weights[2])
    assign_b2 = tf.assign(b2, weights[3])

    # initialize the variables
    init = tf.global_variables_initializer()

    with tf.Session() as sess:

        # initialize variables
        sess.run(init)
        sess.run(assign_w1)
        sess.run(assign_b1)
        sess.run(assign_w2)
        sess.run(assign_b2)


        # loop for n games
        n = 10
        for i in range(n):
            # initialize snake environment and some variables
            snake = Snake()
            frame_curr = snake.grid
            rewards_running = []
            reset = False
            while not reset:
                snake.display()
                # get current frame
                frame_prev = np.copy(frame_curr)
                frame_curr = snake.grid

                # forward previous and current frames
                last_two_frames = np.reshape(np.hstack((frame_prev, frame_curr)), (1, n_input))
                policy = np.ravel(sess.run(out_probs, feed_dict = {input_frames : last_two_frames}))

                # sample action from returned policy
                action = np.argmax(policy)
                print(action)
                # play THE SNAKE and get the reward associated to the action
                reward, reset = snake.play(action)
                rewards_running += [reward]