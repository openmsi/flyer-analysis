# flyer-detection
Repo containing the flyerdetection framework along with a Python notebook to run it

# Installation
Create and activate a new conda environment:
```
conda create -n flyer-detection python==3.9
conda activate flyer-detection
```
Install `libsodium` and `librdkafka` for OpenMSIStream using the instructions in the [OpenMSIStream documentation](https://openmsistream.readthedocs.io/en/latest/introduction/installing_openmsistream.html).

clone and pip install this repository:
```
git clone https://github.com/aki-au/flyer-detection.git
cd flyer-detection
pip install --editable .
```
