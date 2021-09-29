PyLabLib cam-control: Software for universal camera control and frames acquisition
==================================================================================

PyLabLib cam-control aims to provide a convenient interface for controlling cameras and acquiring their data in a unified way.

.. image:: docs/overview.png


Features
~~~~~~~~~~~~~~~~~~

- Communication with a variety of cameras: Andor, Hamamatsu, Thorlabs, PCO, PhotonFocus with IMAQ and Silicon Software frame grabbers.
- Operating at high frame (>50 kFPS) and data (>300 Mb/s) rates.
- On-line data processing and analysis: `binning <https://pylablib-cam-control.readthedocs.io/en/latest/pipeline.html#pipeline-prebinning>`__, `background subtraction <https://pylablib-cam-control.readthedocs.io/en/latest/pipeline.html#pipeline-background-subtraction>`__, simple built-in `image filters <https://pylablib-cam-control.readthedocs.io/en/latest/advanced.html#advanced-filter>`__ (Gaussian blur, Fourier filtering), `playback slowdown <https://pylablib-cam-control.readthedocs.io/en/latest/advanced.html#advanced-slowdown>`__ for fast process analysis.
- Customization using `user-defined filters <https://pylablib-cam-control.readthedocs.io/en/latest/expanding.html#expanding-filter>`__ (simple Python code operating on numpy arrays) or control from other software via a `TCP/IP interface <https://pylablib-cam-control.readthedocs.io/en/latest/expanding.html#expanding-server>`__.
- Flexible data acquisition: `pre-trigger buffering <https://pylablib-cam-control.readthedocs.io/en/latest/pipeline.html#pipeline-saving-pretrigger>`__, initiating acquisition on `timer, specific image property <https://pylablib-cam-control.readthedocs.io/en/latest/advanced.html#advanced-save-trigger>`__, or `external software signals <https://pylablib-cam-control.readthedocs.io/en/latest/expanding.html#expanding-server>`__.


Installation
~~~~~~~~~~~~~~~~~~

To install cam-control, download the latest version from `GitHub <https://github.com/AlexShkarin/pylablib-cam-control/releases/latest/download/cam-control.zip>`__ as a self-contained Zip file and then follow further `instructions <https://pylablib-cam-control.readthedocs.io/en/latest/overview.html#overview-install>`__ for how to run it.


Documentation
~~~~~~~~~~~~~~~~~~

Detailed documentation is available at https://pylablib-cam-control.readthedocs.io/en/latest/


Related projects
~~~~~~~~~~~~~~~~~~

Cam-control is built using `pylablib <https://github.com/AlexShkarin/pyLabLib>`__, a more generic library for experiment automation and data acquisition, which included lots of additional `devices <https://pylablib-cam-control.readthedocs.io/en/latest/devices/devices_root.html>`__ besides cameras.