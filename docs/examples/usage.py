"""
Run pyLossless using an example dataset
=======================================
"""
# %%
# First import we import our packages for this tutorial. 
# ------------------------------------------------------
# We 'll import pylossless as ll for expediency.
import tempfile

import pandas as pd

from mne.datasets import sample
import mne_bids

import openneuro

import pylossless as ll

# %%
# Loading the pipeline configuration
# ----------------------------------
# Running the pipeline always requires 1) a dataset and 2) a configuration
# file describing the parameters for the preprocessing. A default version of
# this configuration file can be fetched as a starting point that can be
# adjusted to the specific needs of a given project
config = ll.config.Config()
config.load_default()
config.print()
config.save("my_project_ll_config.yaml")

# %%
# Downloading an example BIDS compliant dataset
# ---------------------------------------------
# The PyLossless pipeline expects the EEG recordings to be stored as BIDS data.
# We can demonstrate the usage of the pipeline on a BIDS dataset loaded from
# OpenNeuro. First, we need to download the dataset

# Shamelessly copied from https://mne.tools/mne-bids/stable/auto_examples/read_bids_datasets.html
# pip install openneuro-py
dataset = 'ds002778'
subject = 'pd6'

# Download one subject's data from each dataset
bids_root = sample.data_path() / dataset
bids_root.mkdir(exist_ok=True)

openneuro.download(dataset=dataset, target_dir=bids_root,
                   include=[f'sub-{subject}'])
# %%
# Running the pipelin on the BIDS compliant dataset
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# Now that we have a BIDS dataset saved locally, we can use mne_bids to load
# this dataset as as mne.io.Raw instance
datatype = 'eeg'
session = 'off'
task = 'rest'
suffix = 'eeg'
bids_path = mne_bids.BIDSPath(subject=subject, session=session, task=task,
                              suffix=suffix, datatype=datatype, root=bids_root)
raw = mne_bids.read_raw_bids(bids_path)

# %%
# Great! We have our two ingredients (a dataset and a configuration file),
# and we can now run the pipeline on that dataset (actually, just one recording
# in that case)
pipeline = ll.LosslessPipeline('my_project_ll_config.yaml')
pipeline.run(raw)

# %%
# Note that running the pipeline for a full dataset is not much more
# complicated. We only need a list of BIDSPath for all the recordings of that
# dataset. For example, if bids_paths contains such a list, the whole dataset
# can be processed as follows:
pipeline.run_dataset(bids_paths)

# %%
# This function essentially loads one raw instance after another from the BIDS
# recordings specified in bids_paths and calls pipeline.run(raw) with these
# raw objects.

# %%
# Making your own data BIDS compliant
# -----------------------------------
# PyLossless provides some functions to help the user import non-BIDS
# recordings. Since the code to import datasets recorded in different formats
# and with different properties can vary much from one project to the next, the
# user must provide a function that can load and return a raw object along with
# the standard MNE events array and event_id dictionary. For example, in the
# case of our dataset

# %%
# Example import function
# ^^^^^^^^^^^^^^^^^^^^^^^
def egi_import_fct(path_in, stim_channel):

    # read in a file
    raw = mne.io.read_raw_egi(path_in, preload=True)

    # events and event IDs for events sidecar
    events = mne.find_events(raw, stim_channel=['STI 014'])
    event_id = raw.event_id

    # MNE-BIDS doesn't currently support RawMFF objects.
    with tempfile.TemporaryDirectory() as temp_dir:
        raw.save(Path(temp_dir) / "tmp_raw.fif")

        # preload=True is important since this file is volatile
        raw = mne.io.read_raw_fif(Path(temp_dir) / 'tmp_raw.fif', preload=True)

    # we only want EEG channels in the channels sidecar
    raw.pick_types(eeg=True, stim=False)
    raw.rename_channels({'E129': 'Cz'})  # to make compatible with montage

    return raw, events, event_id

# %%
# Then, the dataset can be converted to BIDS as follows
import_args = [{"stim_channel": 'STI 014', "path_in": './sub-s004-ses_07_task-MMN_20220218_022348.mff'},
               {"stim_channel": 'STI 014', "path_in": './sub-s004-ses_07_task-MMN_20220218_022348.mff'}]

bids_path_args = [{'subject': '001', 'run': '01', 'session': '01', "task": "mmn"},
                  {'subject': '002', 'run': '01', 'session': '01', "task": "mmn"}]

bids_paths = ll.bids.convert_dataset_to_bids(egi_import_fct, import_args, bids_path_args, overwrite=True)

# %%
# Note that, in this case, we used twice the same input file just to
# demonstrate how this function can be used for multiple recordings. In
# practice, a user may want to have this information stored in CSV files that
# can be readily used. For example, if we create such files for the demonstration:
pd.DataFrame(import_args).to_csv("import_args.csv", index=False)
pd.DataFrame(bids_path_args).to_csv("bids_path_args.csv", index=False)

# %%
# Now, regardless of how such files have been produced (e.g., from Excel),
# these can be used directly to process the whole dataset:
import_args = list(pd.read_csv("import_args.csv").T.to_dict().values())
bids_path_args = list(pd.read_csv("bids_path_args.csv").T.to_dict().values())
bids_paths = ll.bids.convert_dataset_to_bids(egi_import_fct, import_args, bids_path_args, overwrite=True)
pipeline.run_dataset(bids_paths)