.. _expanding:

Expanding and modifying
=======================


.. _expanding_modifying_distrib:

Accessing and modifying the distribution
----------------------------------------

Cam-control runs in an isolated Python interpreter (located in ``python`` subfolder within the main folder), which has only basic dependencies installed. Sometimes you might want to modify the installed packages, for example, to add the ones required by your custom code (such as a :ref:`custom filter <expanding_filter>`), or to replace or update some of them. To do that, you can run ``local-python.bat`` located in the ``python`` folder, which launches a command line interface referenced to the local Python interpreter. From there you can simply use ``python -m pip`` to modify the distribution, e.g., run ``python -m pip install -U <pkg>`` to install or update any desired package, or ``python -m pip uninstall <pkg>`` to uninstall a currently present package.

.. warning::
  Due to some specifics of path handling in Python scripts on Windows, simply running ``pip`` will not work. You should always use ``python -m pip`` instead.

As an alternative for your own code (such as filters), you can request additional packages to be installed during the execution. This can be achieved by adding the following lines to your code file::

      from pylablib.core.utils import module as module_utils
      module_utils.install_if_older("some-package")

where ``"some-package"`` is the name of the package to install (e.g., ``"scikit-image"``). This code checks if the package is already installed, and runs ``pip install`` if it is missing. Note that this code should be included before the required package is first imported.


Running from source
~~~~~~~~~~~~~~~~~~~~~~

It is also possible to run cam-control in your own Python environment. All of the required code is contained in ``cam-control`` folder and can be obtained either on `GitHub <https://github.com/AlexShkarin/pylablib-cam-control/>`__ or directly from the folder. To run it, you also need to install the necessary dependencies: `NumPy <https://docs.scipy.org/doc/numpy/>`_, `SciPy <https://docs.scipy.org/doc/scipy/reference/>`_, `pandas <https://pandas.pydata.org/>`_, `Numba <https://numba.pydata.org/>`_, `RPyC <https://rpyc.readthedocs.io/en/latest/>`_, `PyQt5 <https://www.riverbankcomputing.com/software/pyqt/>`_ (or `PySide2 <https://www.pyside.org/>`_ with `shiboken2 <https://wiki.qt.io/Qt_for_Python/Shiboken>`_), `pyqtgraph <http://www.pyqtgraph.org/>`_, and `imageio <https://imageio.readthedocs.io/en/stable/>`_. All of the dependencies are included in ``requirements.txt`` file inside the ``cam-control`` folder (it can also be extracted by running ``python -m pip freeze`` in the local python command line). In addition, the GitHub-hosted version requires `pylablib <https://pylablib.readthedocs.io/en/stable/>`_ v1.3.1 (not included in ``requirements.txt``).


.. _expanding_filter:

Custom filters
-------------------------

Filters give a way to add custom on-line image processing. They can be used to quickly assess the data in real time or to :ref:`automate data acquisition <advanced_save_trigger>`.

The filter is defined as a subclass of ``IFrameFilter`` class with methods to specify its parameters (displayed in cam-control), receive frames from the camera and generate output.


Single-frame filter
~~~~~~~~~~~~~~~~~~~~~~~~~

In the simplest scenario, filters simply take a single frame and output the transformed image. In this case, the filter can inherit from a more specific ``ISingleFrameFilter`` class and only define a couple of new methods. For example, this is the built-in Gaussian blur filter::

    ### The class inherits not from the most generic frame class,
    ### but from ISingleFrameFilter, meaning that it transforms a single frame
    class GaussianBlurFilter(ISingleFrameFilter):
        """
        Filter that applies Gaussian blur to a frame.
        """
        _class_name = "blur"  # unique filter identifier; should obey usual variable naming rules
        _class_caption = "Gaussian blur"  # caption which shows up in the filter selection menu
        _class_description = "Standard convolution Gaussian blur filter"  # detailed description

        ### This method sets up the filter upon loading
        ### Usually it defines GUI parameters and internal variables
        def setup(self):
            super().setup()  # call setup from the parent class
            # set up the width parameter
            self.add_parameter("width", label = "Width", limit = (0,None), default = 2)

        ### This methods processes a frame (2D numpy array) and returns the result
        def process_frame(self, frame):
            # self.p is used to access previously defined parameters;
            # frame is converted into float, since it can also be an integer array
            return scipy.ndimage.gaussian_filter(frame.astype("float"), self.p["width"])

The main method for a single-frame filter is ``process_frame``, which takes a single frame as a 2D array (integer or float) and returns either a processed frame as a 2D array, or ``None``, meaning that a new frame is not available. The other important method is ``setup``, which is used to initialize variables and define the filter parameters. Finally, each filter class should define ``_class_name``, ``_class_caption`` and, if appropriate, ``_class_description`` strings.

Multi-frame filter
~~~~~~~~~~~~~~~~~~~~~~~~~

In a more complicated case, a filter takes several most recent frames and combines them together to get a result. This can be handled by inheriting from ``IMultiFrameFilter`` class. For example, here is the built-in moving average filter, which simply calculates the averages of the last ``n`` frames::

    ### This class still inherits from a helper IMultiFrameFilter class,
    ### which keeps a buffer of the last several frames
    class MovingAverageFilter(IMultiFrameFilter):
        """
        Filter that generates moving average (averages last ``self.p["length"]`` received frames).
        """
        _class_name = "moving_avg"
        _class_caption = "Moving average"
        _class_description = ("Averages a given number of consecutive frames into a single frame. "
            "Frames are averaged within a sliding window.")

        def setup(self):
            # set up the buffer filter; process_incomplete = True means
            #   that it will work even with a partially filled buffer
            super().setup(process_incomplete = True)
            # add the parameters
            self.add_parameter("length", label = "Number of frames", kind = "int",
                limit = (1,None), default = 1)
            self.add_parameter("period", label = "Frame step", kind = "int",
                limit = (1,None), default = 1)

        ### This methods is called whenever a parameter is changed in GUI
        ### Normally it simply updates self.p dictionary,
        ### but in this case it also changes the buffer parameters if necessary
        def set_parameter(self, name, value):
            super().set_parameter(name, value)
            # update the buffer parameters
            buffer_size = value if name == "length" else None
            buffer_step = value if name == "period" else None
            self.reshape_buffer(buffer_size, buffer_step)

        ### This method is called when a new frame is requested
        ### The argument is the buffer, which is a list of 2D numpy arrays
        def process_buffer(self, buffer):
            # if buffer is empty, return None (no new frame to show)
            if not buffer:
                return None
            return np.mean(buffer, axis = 0)

The first difference from the previous example is the different calculation method, which is now called ``process_buffer``, and which takes a list of 2D arrays instead of a singe array. The second is the redefined ``set_parameter`` method. This method is called every time a user changes a parameter value in the GUI. By default, it simply updates ``self.p`` attribute, which can be used when calculating the frame, like in the Gaussian filter example. However, here it also updates the buffer parameters.

Filter storage
~~~~~~~~~~~~~~~~~~~~~~~~~

To appear in the cam-control, the file defining one or more custom filter classes should simply be added to the ``plugins/filter`` folder inside the main ``cam-control`` directory. For further examples, you can examine files already in that folder: ``builtin.py`` for :ref:`built-in filters <advanced_filter>`, ``examples.py`` for several example classes, and ``template.py`` for a template file containing a single filter class.

Debugging
~~~~~~~~~~~~~~~~~~~~~~~~~

Debugging a filter class by running it from the camera control might be cumbersome. Instead, it might be more convenient to test it on generated or pre-loaded frames. Here is a short snippet for doing that::

    ### Simple filter testing script
    # Assume that it is a separate .py file located in the main 
    #   cam-control folder (the one with control.py) 
    
    # import the filters module
    from plugins.filters import examples

    import numpy as np

    # create and setup the filter 
    flt = examples.MovingAverageFilter()
    flt.setup()

    # specify filter parameters
    flt.set_parameter("length", 100)
    flt.set_parameter("step", 10)

    # generate input frames (here 300 random 256x256 frames);
    #   must be a 3D array where the first axis is frame index
    frames = np.random.randint(0, 256, size = (300,256,256), dtype = "uint16")
    # feed the frames to the filter
    flt.receive_frames(frames)
    # calculate the result
    result = flt.generate_frame()


.. _expanding_server:

Control server
-------------------------

To allow platform-independent external control of the software, there is an option to run a TCP/IP server. This server can receive commands from and send data to any other software running either locally on the same PC, or within the local network. The communication is mostly done via a text JSON protocol, which is straightforward to parse in most common languages.


Setting up and connection
~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the server is not enabled. To activate it, you need to add the following line into the :ref:`settings file <settings_file>`:

.. code-block:: none

    plugins/serv/class	server

The default port on which the server runs is ``18923``. If this port is occupied (e.g., by another instance of cam-control running), it tries to connect to the next 10 ports in ascending order. If that is still unsuccessful, it does not run at all. The port can also be manually set in the settings file with the following line:

.. code-block:: none

    plugins/serv/parameters/port	23456

If you use more than one camera, it might make sense to assign them different well-defined ports using the :ref:`camera-specific settings <settings_file_camera>`:

.. code-block:: none

    css/ppimaq_0/plugins/serv/parameters/port	23456
    css/uc480_0/plugins/serv/parameters/port	23467

Finally, if the PC has several network interfaces, you can specify the IP address in the same way as the port:

.. code-block:: none

    plugins/serv/parameters/ip	127.0.0.1

After the server is set up and software is started, the server starts automatically. If it is running, you can see its status on the bottom of the ``Plugins`` tab. It shows the server IP address and port, as well as the number of currently connected clients. Several clients can be operating simultaneously.


General message format
~~~~~~~~~~~~~~~~~~~~~~~~~

The protocol is based on JSON messages. Almost all of the messages sent to and from the server are simple JSON data. The only exception are the messages containing large data (e.g., frames), in which case the message consists of a JSON header and appended binary data, whose format is described within the header.

The first message kind is the one establishing the protocol. It has a simple format ``{"protocol": "1.0"}``, where instead of ``1.0`` it can have any protocol version. The reply has the same format, which specifies the actual protocol used by the server. Currently only a single protocol (version ``1.0``) is supported, so this message is not necessary. However, it is still recommended to start with it to make sure that the server runs the specified version and future-proof the applications.

Apart from this message, other messages follow the same general structure:

.. code-block:: none

    {
        "id": 0,
        "purpose": "request",
        "parameters": {
            "name": "cam/param/get",
            "args": {
                "name": "exposure"
            }
        }
    }

The first field is ``"id"``, which can contain a message ID. If it is defined, then the reply to this message will have the same value of the ``"id"`` field. If it is omitted, then ``"id"`` is omitted in the reply as well.

The second field is ``"purpose"``, which specifies the purpose of the message. The messages sent to the server have purpose ``"request"``, which is assumed by default if this field is omitted. The other possibilities used in the server-sent messages are ``"reply"`` for a reply to the request or ``"error"`` if an error arose.

The next field is ``"parameters"``, which describe the parameters of the request, reply, or error. Request parameters have two sub-fields ``"name"`` and ``"args"`` specifying, correspondingly, request name and its arguments. Depending on the request, the arguments might also be omitted.

The last possible field (not shown above) is ``"payload"``, which signifies that the JSON message is followed by a binary payload and describes its parameters. It is encountered only in some special replies and is described in detail later.

The requests and replies normally have the same format, with the reply typically having the same name but different set of arguments. The error messages have ``"name"`` parameter describing the kind of error (e.g., ``"wrong_request`` or ``"wrong_argument"``), ``"description"`` field with the text description and ``"args"`` field with further arguments depending on the error kind.

Finally, note again that in request only ``"parameters"`` field is necessary. Hence, the command above can be shortened to ``{"parameters":{"name":"cam/param/get","args":{"name":"exposure"}}}`` and, e.g., to start camera acquisition you can simply send ``{"parameters":{"name":"cam/acq/start"}}``.


Requests description
~~~~~~~~~~~~~~~~~~~~~~~~~

GUI requests
*************************

These requests directly address the GUI. They are almost directly analogous to entering values and pressing buttons in the GUI or reading values of controls or indicators:

- ``"gui/get/value"``: get value of a GUI parameter
  
  - *Request args*:
  
    - ``"name"``: parameter name; by default, return all parameters
  
  - *Reply args*:
  
    - ``"name"``: parameter name, same as in request
    - ``"value"``: parameter value; can be a dictionary
  
  - *Examples*:
  
    - ``{"name": "gui/get/value", "args": {"name": "cam/save/path"}}`` requests the saving path
    - ``{"name": "gui/get/value"}`` requests all GUI values

- ``"gui/get/indicator"``: get value of a GUI indicator; not that many indicators (e.g., anything in the status tables) are still technically values, and their values should be requested using ``"gui/get/value"``
  
  - *Request args*:
  
    - ``"name"``: indicator name; by default, return all indicators
  
  - *Reply args*:
  
    - ``"name"``: indicator name, same as in request
    - ``"value"``: indicator value; can be a dictionary
  
  - *Examples*:
  
    - ``{"name": "gui/get/indicator", "args": {"name": "cam/cam/frame_period"}}`` requests the camera frame period indicator
    - ``{"name": "gui/get/indicator"}`` requests all GUI indicators

- ``"gui/set/value"``: set value of a GUI parameter
  
  - *Request args*:
  
    - ``"name"``: parameter name
    - ``"value"``: parameter value
  
  - *Reply args*:
  
    - ``"name"``: parameter name, same as in request
    - ``"value"``: set parameter value; normally the same as in request, but can differ if, e.g., the range was coerced
  
  - *Examples*:
  
    - ``{"name": "gui/set/value", "args": {"name": "cam/save/batch_size", "value": 100}}`` sets the saving frames limit to 100
    - ``{"name": "gui/set/value", "args": {"name": "plugins/trigger_save.ts/params/period", "value": 2}}`` sets the period of the saving trigger to 2 seconds

To initiate a button press, you need to set its value to ``True``.


Save requests
*************************

These requests initiate or stop data streaming to the drive:

- ``"save/start"``: start the standard saving with the specified parameters; the parameters which are not specified are taken from the GUI
  
  - *Request args*:
  
    - ``"path"``: save path
    - ``"batch_size"``: number of frames per saved video (``None`` for no limit)
    - ``"append"``: determines whether the data is appended to the existing file
    - ``"format"``: file format; can be ``"raw"``, ``"tiff"``, or ``"bigtiff"``
    - ``"filesplit"``: number of frames to save per file (``None`` if no splitting is active)
    - ``"save_settings"``: determines whether the settings are saved
  
  - *Reply args*:
  
    - ``"result"``: should be ``"success"`` if the saving was successful
  
  - *Examples*:
  
    - ``{"name": "save/start"}`` starts saving with all parameters as specified in the GUI
    - ``{"name": "save/start", "args": {"batch_size": 10}}`` starts saving of 10 frames with all other parameters as specified in the GUI

- ``"save/stop"``: stop the standard saving if it is running; no parameters are specified
  
  - *Reply args*:
  
    - ``"result"``: should be ``"success"`` if the saving was successful

- ``"save/snap"``: perform a snapshot saving with the specified parameters; the parameters which are not specified are taken from the GUI
  
  - *Request args*:
  
    - ``"source"``: snapshot frame source; normally either ``"standard"`` (frame from the ``Standard`` image tab) or ``"filter.filt"`` (frame from the ``Filter`` image tab)
    - ``"path"``: save path
    - ``"format"``: file format; can be ``"raw"``, ``"tiff"``, or ``"bigtiff"``
    - ``"save_settings"``: determines whether the settings are saved
  
  - *Reply args*:
  
    - ``"result"``: should be ``"success"`` if the saving was successful
  
  - *Examples*:
  
    - ``{"name": "save/snap"}`` snaps the image with all parameters as specified in the GUI
    - ``{"name": "save/start", "args": {"source": "filter.filt"}}`` snaps an image from the filter tab with all other parameters as specified in the GUI

Note that if the path is explicitly specified in the request, then this exact path is used. That is, of ``On duplicate name`` is set to ``Rename`` in the interface, it will not take an effect.


Camera requests
*************************

These requests directly control the camera:

- ``"acq/stop"``: start the camera acquisition; no parameters are specified
  
  - *Reply args*:
  
    - ``"result"``: should be ``"success"`` if the saving was successful

- ``"acq/stop"``: stop the camera acquisition if it is running; no parameters are specified
  
  - *Reply args*:
  
    - ``"result"``: should be ``"success"`` if the saving was successful

- ``"acq/param/get"``: set the camera parameter
  
  - *Request args*:
  
    - ``"name"``: parameter name; by default, return all parameters
  
  - *Reply args*:
  
    - ``"name"``: parameter name, same as in request
    - ``"value"``: parameter value; can be a dictionary
  
  - *Examples*:
  
    - ``{"name": "cam/param/get", "args": {"name": "exposure"}}}`` requests the camera exposure
    - ``{"name": "cam/param/get"}`` requests all camera parameters

- ``"acq/param/set"``: set the camera parameter
  
  - *Request args* contain camera parameters and their values (parameter names are the same as given by ``acq/param/get`` command)
  
  - *Reply args*:
  
    - ``"result"``: should be ``"success"`` if the saving was successful
  
  - *Examples*:
  
    - ``{"name": "cam/param/set", "args": {"exposure": 0.1, "roi": [0, 256, 0, 256]}}`` set the camera exposure to 0.1 s and ROI to span from 0 to 256 on both axes


Streaming requests
*************************

These requests control transfer of the camera data.

Some of the replies can contain binary frame data, so their format differs from other replies. First, in addition to ``"purpose"`` and ``"parameters"`` field they also contain ``"payload"`` field with the information regarding the binary data. For example, the full JSON header can look like

.. code-block:: none

    {
        "purpose": "reply",
        "parameters": {
            "args": {
                "first_index": 41849,
                "last_index": 41948
            },
            "name": "stream/buffer/read"
        },
        "payload": {
            "nbytes": 13107200,
            "dtype": "<u2",
            "shape": [100, 256, 256]
        }
    }

Payload description has 3 fields. First, ``"nbytes"`` specifies the total payload size in bytes. In the example above it states that this message is followed by ``13107200`` bytes of binary data. Next ,``"dtype"`` specifies the binary data format in the standard `numpy format <https://numpy.org/doc/stable/reference/arrays.dtypes.html>`__. Here ``"<u2"`` means that the data is 2-byte unsigned integer withe the little-endian byte order (the system default). Finally, ``"shape"`` specifies the shape of the result, i.e., dimensions along each axis when it is represented as a multidimensional array. In the example the shape is ``[100, 256, 256]``, which means a 3D 100x256x256 array. In this particular reply the first axis is the frame index and the other 2 are the frame axes, i.e., the data contains 100 of 256x256 frames.

The streaming is done through requests, which means that it requires an intermediate buffer to store the frames between these requests (similar to, e.g., camera frame buffer). Hence, one first need to setup this buffer using ``"stream/buffer/setup"`` command, and then request the frames with ``"stream/buffer/read"`` command:

- ``"stream/buffer/setup"``: setup the streaming buffer or clear it if it is already set up
  
  - *Request args*:
  
    - ``"size"``: number of frames in the buffer; if not specified, set to ``1`` if the buffer is not set up or keep the current value if it is (in which case it just clears the buffer)
  
  - *Reply args*: same as ``"stream/buffer/status"`` (see below)
  
  - *Examples*:
  
    - ``{"name": "stream/buffer/setup", "args": {"size": 100}}}`` sets up the buffer with 100 frames

- ``"stream/buffer/clear"``: clear the streaming buffer
  
  - *Request args*: no arguments required
  
  - *Reply args*: same as ``"stream/buffer/status"`` (see below)

- ``"stream/buffer/status"``: get the buffer status
  
  - *Request args*: no arguments required
  
  - *Reply args*:
  
    - ``"filled"``: number of unread frames in the buffer
    - ``"size"``: total size of the buffer (as specified with ``"stream/buffer/setup"``)
    - ``"first_index"``: index of the oldest frame in the buffer
    - ``"last_index"``: index of the newest frame in the buffer

- ``"stream/buffer/read"``: read some frames from the buffer
  
  - *Request args*: 
  
    - ``"n"``: number of frames to read; if not specified, read all frames; otherwise, read ``n`` oldest frames
    - ``"peek"``: if ``True``, return the frames but keep them in the buffer; otherwise (default), the frames are removed from the buffer after transfer
  
  - *Reply args*:
  
    - ``"first_index"``: index of the first transferred frame
    - ``"last_index"``: index of the last transferred frame
    - the frames data is contained in the payload as described above
  
  - *Examples*:
  
    - ``{"name": "stream/buffer/read", "args": {"n": 10}}}`` requests 10 oldest frames from the buffer