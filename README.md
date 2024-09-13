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

#Next Steps (Current Shortcomings)
A number of shortcomings in the current method are noted.  Specifically:

* Geometric assumptions that the object is circular and in a 2D plane.
* The algorithm is sensitive to noise and outliers.
* Fitting struggles with partial occlusion of the flyer as well as * potential for deformed flyers and any perspective distortion of the experimental setup.
* The method is not robust if there is uneven lighting or poor image contrast. 
* The method has limited flexibility and really only works well for clearly defined, near-circular objects

Next steps are to advance the algorithm to deal with some of this.  Specific plan is:

* try RANSAC (Random Sample Consensus) for circle fitting with scikit-learn's RANSAC regressor (or a custom implementation for circle fitting, if needed). RANSAC fits geometric shapes by iteratively selecting random subsets of points and fitting the model to them. It’s especially useful when the data contains outliers or noise, or when only part of the circle is available. RANSAC is robust to outliers and noisy or incomplete data and can be tuned to find a circle even from a small arc.  RANSAC can be challenging because it requires selecting a proper threshold for outlier rejection and it may be slower because of its iterative approach.  
* The new circle fitting method of H. Abdul-Rahman and N. Chernov found in [https://arxiv.org/pdf/1505.03795](https://arxiv.org/pdf/1505.03795). fast and numerically stable fitting, even in challenging conditions like small arcs or when large circles are involved. The algorithm is particularly adept at handling round-off errors and uses a gradient-based minimization with a Newton step to ensure rapid convergence and high precision. The approach is good for cases with partial circles or limited data. Not sure if there is a Python wrapped version of it yet, but some of their codes are here: [https://people.cas.uab.edu/~mosya/cl/CPPcircle.html](https://people.cas.uab.edu/~mosya/cl/CPPcircle.html). 