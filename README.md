# flyer-analysis
Repo containing the flyeranalysis framework along with a Python notebook to run it and an installed application to run it as a stream processor using [OpenMSIStream](https://github.com/openmsi/openmsistream)

# Installation
Create and activate a new conda environment:
```
conda create -n flyer-analysis python==3.9
conda activate flyer-analysis
```
Install `libsodium` and `librdkafka` for OpenMSIStream using the instructions in the [OpenMSIStream documentation](https://openmsistream.readthedocs.io/en/latest/introduction/installing_openmsistream.html).

clone and pip install this repository:
```
git clone https://github.com/openmsi/flyer-analysis.git
cd flyer-analysis
pip install --editable .
```

# Stream processing

To see how to run the flyeranalysis analysis as a stream processor, type:
```
FlyerAnalysisStreamProcessor -h
```
