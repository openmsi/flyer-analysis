# flyer-analysis

Code and examples for the flyer image analysis tasks and for ingesting the Laser Shock Lab FileMaker DB to a SQL (or other relational) DB (also linked to flyer image analysis results)

# Installation
Create and activate a new conda environment:
```
conda create -n flyer-analysis python=3.9
conda activate flyer-analysis
```
Install `libsodium` and `librdkafka` for OpenMSIStream using the instructions in the [OpenMSIStream documentation](https://openmsistream.readthedocs.io/en/latest/introduction/installing_openmsistream.html).

clone and pip install this repository:
```
git clone https://github.com/openmsi/flyer-analysis.git
cd flyer-analysis
pip install --editable .
```

# Contents

This repository includes some Python programs for ingesting the Laser Shock Lab FileMaker DB entries directly to a different relational DB, and for performing analyses of the high speed camera video frames to determine the location, tilt, and curvature of the flyer within them and add the raw video frames and analysis results to the same DB. It also has some notebooks demonstrating how to use the resulting DB. 

To ingest the FileMaker DB entries to a relational DB:

    python -m flyeranalysis.filemaker_to_sql [connection_string] [filemaker_instance_IP]

where `[connection_string]` is the SQLAlchemy-formatted connection string to use for connecting to the relational DB into which you'd like to ingest FileMaker entries, and `[filemaker_instance_IP]` is the IP address at which the FileMaker instance can be reached for reading entries.

If high speed video frames have been produced to a Kafka topic, you can run a StreamProcessor to analyze them and add them as well as their analysis results to the DB with:

    FlyerAnalysisStreamProcessor --config [config_file_path] --topic_name [topic_name] --db_connection_str [connection_string]

If the connection string isn't given the relational DB won't be used and output will go in CSV files on the local system instead.

For both of these programs, you can add "`-h`" on the command line to see the full set of command line options and arguments available.

The [notebooks](./notebooks/) folder contains several Jupyter notebooks that were used in developing and testing the programs above, and a few illustrating their results and giving examples of how to query the output database as well.
