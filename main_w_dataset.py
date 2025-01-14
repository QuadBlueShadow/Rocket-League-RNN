from genericpath import isdir
from keras.models import Sequential
from keras.layers import Dense, LSTM
from keras.optimizers import adam_v2
from keras.models import load_model
import numpy as np
import tensorflow as tf
# import gzip
import rlgym.make
from rlgym.utils.obs_builders.advanced_obs import AdvancedObs
from agents.Vector_load_hack.parsers.discrete_act import DiscreteAction
from terminal_conditions.custom_timeouts import KickoffTimeoutCondition
from rlgym.utils.terminal_conditions.common_conditions import TimeoutCondition
from agents.Vector_load_hack.agent import Agent
import tqdm
import tkinter
from tkinter import messagebox
import os
from extra_functions import *

run_rocket_league_instance = False

if run_rocket_league_instance == True:
    env = rlgym.make(tick_skip=1, use_injector=True, action_parser=DiscreteAction(), obs_builder=AdvancedObs(),
                    terminal_conditions=[TimeoutCondition(60*30), KickoffTimeoutCondition(60*5)], self_play=True)

# UI "stop training" window stuff
keep_training = True
top = tkinter.Tk()
top.geometry('150x100')


def stop_program():
    if messagebox.askyesno("Confirm", "Confirm Stop?"):
        T.delete("1.0", "end")
        T.insert("1.0", "Stopping...")
        global keep_training
        keep_training = False


B = tkinter.Button(top, text="Stop Training", command=stop_program)

T = tkinter.Text(top, padx=10, pady=10)
T.insert("1.0", "Training...")

B.pack(pady=10, padx=10)
T.pack()

# initialize Vector agent
actor = Agent()

# amount of steps to collect for the dataset
ep_len = 100_000
# the amount of steps taken in order to check for a chance to save an array
save_every = 2000
# batch size for learner
batch_size = 10_000

# directory to store data
directory = "data_collection"
# name of data
data_name = "arr_test"
# name of compiled final array
final_file = "Vector_data_full_arr"

# whether to load a model or not
load_model_file = False
# NOTE: loading uses the same variables as saving
# model save directory
save_directory = "model"
# model save name
model_name = "model_1"
# save optimizer option
save_optimizer = True

if os.path.isdir(directory) == False:
    create_directory(directory)
else:
    print(" ")
    print("Data directory found")

if os.path.isdir(save_directory) == False:
    create_directory(save_directory)
else:
    print(" ")
    print("Save directory found")


if not load_model_file:
    model = Sequential()
    model.add(LSTM(500, activation="relu", return_sequences=True))
    model.add(LSTM(200, activation="relu", return_sequences=True))
    model.add(LSTM(200, activation="relu", return_sequences=True))
    model.add(LSTM(200, activation="relu", return_sequences=True))
    model.add(LSTM(200, activation="relu", return_sequences=True))
    model.add(LSTM(200, activation="relu", return_sequences=True))
    model.add(LSTM(200, activation="relu", return_sequences=True))
    model.add(LSTM(200, activation="relu", return_sequences=True))
    model.add(Dense(500, activation='relu'))
    model.add(Dense(500, activation='relu'))
    model.add(Dense(500, activation='tanh'))

    opt = adam_v2.Adam(learning_rate=1e-3, decay=1e-4)

    model.compile(loss='mean_squared_error', optimizer=opt,
                  metrics=['mean_squared_error', 'accuracy'])
else:
    model = load_model(f"{save_directory}/{model_name}.tf")  # compiles by default


while keep_training:
    # console progress bar
    prog_bar = tqdm.tqdm(desc="Collecting steps", total=ep_len, leave=True, smoothing=0.01, colour='green')

    # delete all files in data directory and reset
    # for f_str in os.listdir(directory):
    #     os.remove(f_str)

    # #################################################################### #
    # start of data collection loop

    if run_rocket_league_instance == False:
        print(" ")
        print("Skiping data gather")
        prog_bar.update(100)

    while run_rocket_league_instance == True:
        obs = env.reset()
        actions = actor.act(obs)

        done = False
        ep_len_exceeded = False
        time_to_save = False

        x = 0
        while not ep_len_exceeded:
            x += 1
            prog_bar.update(1)
            top.update()
            obs, reward, done, gameinfo = env.step(actions)

            # check if we need to save
            if x % save_every == 0:
                time_to_save = True

            if done:
                obs = env.reset()
                # check when done if we need to save
                if time_to_save:
                    # see DiscreteAction.save_arr for understanding purposes, specialty function for data collection
                    env._match._action_parser.save_arr(f"{directory}/{data_name}{x}")
                    time_to_save = False

            actions = actor.act(obs)

            if x == ep_len:
                ep_len_exceeded = True
        break

    #env._match._action_parser.save_arr(f"{directory}/{data_name}_final")

    # end of data gathering
    # #################################################################### #
    # start of array packing

    arr = load_directory_info(directory, final_file)

    # this is the data input arr
    arr_input = arr[:-1]
    # this is the target input arr
    arr_targ = arr[1:]

    dataset = tf.keras.utils.timeseries_dataset_from_array(arr_input, arr_targ, sequence_length=1,
                                                           batch_size=batch_size)

    # end of packing arrays into arr
    # #################################################################### #
    # start learning

    for batch in dataset:
        input_data, target = batch
        model.fit(
            input_data,
            target,
            verbose=1,
            epochs=3,
            validation_data=dataset,
            workers=4,
            validation_split=0.2,
            use_multiprocessing=True)

    model.save(f"{save_directory}/{model_name}.tf", include_optimizer=save_optimizer)

# we're done, close it up
if run_rocket_league_instance == True:
    env.close()
