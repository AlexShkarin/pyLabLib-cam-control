.. _configuring:

Configuring
=========================


.. _command_line:

Command line arguments
-------------------------

``control.bat`` takes several command line arguments to customize the software launch sequence:

    - ``--camera <camera name>``, ``-c <camera name>``: select a specific camera to control; ``<camera name>`` is the name of the camera used within the settings file, such as ``ppimaq_0``. Normally, if several cameras are available, the software first shows the dropdown menu to choose the camera to control. However, if this argument is specified, this camera will be selected automatically. Can be used to, e.g., create separate shortcuts for controlling different cameras.
    - ``--config-file <file>``, ``-cf <file>``: specify a configuration file if it is different from the default ``settings.cfg``. The path is always specified relative to ``control.py`` location.



.. _settings_file:

Settings file
-------------------------

Software settings are defined in ``settings.cfg`` file inside the main folder. These include the camera connection parameters, as well as some additional interface and camera settings. The settings are described in a plain text format with one parameter per row. The most important settings are either defined by default, do not need explicit definition, or filled in by the camera detection. However, you can also edit them manually. Below is the list of available parameters.

.. _settings_file_general:

General parameters
-------------------------

``interface/compact``
    | Switch to compact three-panel layout with a smaller controls area.
    | *Values*: ``True``, ``False``
    | *Default*: ``False``

``interface/color_theme``
    | Color theme (based of `qdarkstyle <https://github.com/ColinDuquesnoy/QDarkStyleSheet>`__).
    | *Values*: ``dark``, ``light``, ``standard`` (standard Windows style)
    | *Default*: ``dark``

``interface/plotter/binning/max_size``
    | Maximal size of the image shown in the plotter window (any image larger than this size gets binned). Only affect plotting, and only useful to speed up image display.
    | *Values*: any positive integer
    | *Default*: not defined (no maximal size)

``interface/plotter/binning/mode``
    | Binning mode for plotting display, if the frame needs to be binned. Works in conjunction with ``interface/plotter/binning/max_size``.
    | *Values*: ``mean``, ``min``, ``max``, ``skip``
    | *Default*: ``mean``

``interface/popup_on_missing_frames``
    | Show a pop-up message in the end of saving if the saved data contains missing frames.
    | *Values*: ``True``, ``False``
    | *Default*: ``True``

``interface/datetime_path/file``
    | Template to generate file names when ``Add date/time`` is selected but ``Create separate folder`` is not.
    | *Values*: ``pfx`` (add date as a prefix, e.g., ``20210315_120530_video.bin``), ``sfx`` (add date as a suffix, e.g., ``video_20210315_120530.bin``), or ``folder`` (create folder with the datetime as name, e.g.,  ``20210315_120530/video.bin``)
    | *Default*: ``sfx``

``interface/datetime_path/folder``
    | Template to generate folder names when both ``Add date/time`` and ``Create separate folder`` are selected.
    | *Values*: ``pfx`` (add date as a prefix, e.g., ``20210315_120530_video/``), ``sfx`` (add date as a suffix, e.g., ``video_20210315_120530/``), or ``folder`` (create folder with the datetime as name, e.g.,  ``20210315_120530/video/``)
    | *Default*: ``sfx``

``interface/cam_control/roi_kind``
    | ROI entry method in camera control.
    | *Values*: ``minmax`` (ROI is defined by minimal and maximal coordinates), or ``minsize`` (ROI is defined by minimal coordinates and size)
    | *Default*: ``minsize`` for PhotonFocus cameras, ``minmax`` for all other cameras

``frame_processing/status_line_policy``
    | Method to deal with a status line (on PhotonFocus or PCO edge cameras) for the raw image display. Only affects the displayed image.
    | *Values*: ``keep`` (keep as is), ``cut`` (cut off rows with the status line), ``zero`` (set status line pixels to zero), ``median`` (set status line pixels to the image median),or ``duplicate`` (replace status line with pixels from a nearby row)
    | *Default*: ``duplicate``

``saving/max_queue_ram``
    | Maximal size of the saving buffer in bytes. Makes sense to increase if large movies are saved to slow drive, or if large pre-trigger buffer is used (the size of the saving queue must be larger than the pre-trigger buffer). Makes sense to decrease if the PC has small amount of RAM.
    | *Values*: any positive integer
    | *Default*: ``4294967296`` (i.e., 4 GB)


.. _settings_file_camera:

Camera-related parameters
-------------------------

In this section ``<camera name>`` stands for any camera name, e.g., ``ppimaq_0``. For example, ``cameras/<camera name>/params`` can become ``cameras/ppimaq_0/params``.

``css/<camera name>/<key>``
    | Camera-specific parameter. Allows for any generic parameter (such as GUI parameters described above) to take different values for different cameras. For example, if there are two cameras named ``ppimaq_0`` and ``uc480_0`` defined in the file, then one can use ``css/ppimaq_0/saving/max_queue_ram`` to specify the saving buffer size for the first camera, and ``css/uc480_0/saving/max_queue_ram`` for the second one. Either of those can also be omitted, in which case the generic value (either specified or default) will be used instead.

``select_camera``
    | Default selected camera. If this parameter is set, then this camera is automatically selected even if several cameras are present (i.e., the camera select menu doesn't show up). In this case, the only way to start other cameras is by using ``--camera`` :ref:`command line argument <command_line>`.
    | *Values*: any camera name (e.g., ``ppimaq_0``)


``cameras/<camera name>/params``
    | Parameters for camera initialization (interface name, index, etc.) Created automatically by the ``detect`` script, and usually does not need to be changed
    | *Values*: depends on the camera

``cameras/<camera name>/display_name``
    | Camera name to be shown in the camera select window (if multiple cameras are available) and in the window header
    | *Values*: any text
    | *Default*: automatically filled by the ``detect`` script based on the camera kind, model, serial number, etc.


``cameras/<camera name>/params/misc``
    | Additional minor camera parameters
    | *Values*: depends on the camera (see generic parameters below)

``cameras/<camera name>/params/misc/buffer/min_size/time``
    | Minimal camera frame buffer size defined in terms of acquisition time (in seconds). For example, for ``time = 0.5`` the frame buffer size would be 50 frame for 100 FPS frame rate and 500 frames for 1 kFPS frame rate.
    | *Values*: any positive floating point number
    | *Default*: 1 second for most cameras

``cameras/<camera name>/params/misc/buffer/min_size/frames``
    | Minimal camera frame buffer size defined in terms of number of frames.
    | *Values*: any positive integer
    | *Default*: camera-dependent; usually, between 100 and 1000

For any given FPS the maximal of the two declared buffer sizes is used. For example, if ``time = 1`` and ``frames = 100``, then at 50 FPS the frame buffer size is 100 (defined through ``frames``), and at 1000 FPS the frame buffer size is 1000 (defined through ``time``).

``cameras/<camera name>/params/misc/loop/min_poll_period``
    | The period to polled the camera for new frames. The new frames are read out from this camera with this period, which means that the *display* period is limited by the poll. However, since multiple frames are read out at once, the overall readout frame rate does not depend on the poll period. Lower number results in higher image update rates but also, usually, in somewhat lower performance.
    | *Values*: any positive number
    | *Default*: 0.05 (corresponding to the maximum of 20 FPS update rate)

``cameras/<camera name>/params/misc/trigger/in/src``
    | Source of the input trigger for cameras supporting several trigger sources
    | *Values*: camera-dependent. For IMAQ cameras (e.g., using NI frame grabber) a tuple ``(kind, index)``, where ``kind`` can be ``"ext"`` (external SMB connector), ``"rtsi"`` (RTSI connection), or ``"iso_in"`` (ISO connection), and ``line`` is an integer line number. For example, ``("ext",0)`` is the default external SMB connector, and ``("rtsi",4)`` is the RTSI line 4.
    | *Default*: ``("ext",0)``

``cameras/<camera name>/params/misc/trigger/out/src``
    | Destination of the output trigger for cameras supporting several trigger destinations
    | *Values*: camera-dependent. For IMAQ cameras (e.g., using NI frame grabber) a tuple ``(kind, index)``, where ``kind`` can be ``"ext"`` (external SMB connector), ``"rtsi"`` (RTSI connection), or ``"iso_out"`` (ISO connection), and ``line`` is an integer line number. For example, ``("ext",0)`` is the default external SMB connector, and ``("rtsi",4)`` is the RTSI line 4.
    | *Default*: ``("ext",0)``


.. _settings_file_system:

Specific system parameters
--------------------------

    ``dlls/<camera interface>``
        | Paths to camera-specific DLL locations, if different from the device location. ``<camera interface>`` can stand for one of the following:
    
        - ``andor_sdk2``: path to ``atmcd64d.dll`` for Andor SDK2. By default, search in the default location of Andor Solis.
        - ``andor_sdk3``: path to ``atcore.dll`` and related DLLs for Andor SDK3. By default, search in the default location of Andor Solis.
        - ``dcamapi``: path to ``dcamapi.dll`` and related DLLs for Hamamatsu/DCAM cameras. By default, search in ``System32`` folder, where it is placed after installing DCAM API or Hokawo software.
        - ``niimaq``: path to ``imaq.dll`` for NI IMAQ frame grabber interface. By default, search in ``System32`` folder, where it is placed after installing NI Vision Acquisition Software.
        - ``niimaqdx``: path to ``niimaqdx.dll`` for NI IMAQdx frame grabber interface. By default, search in ``System32`` folder, where it is placed after installing NI Vision Acquisition Software.
        - ``pco_sc2``: path to ``SC2_Cam.dll`` for PCO cameras. By default, search in the default location of pco.camware or pco.sdk.
        - ``pfcam``: path to ``pfcam.dll`` for PhotonFocus cameras. By default, search in PFRemote folder specified in the ``PATH`` environment variable.
        - ``sisofgrab``: path to ``fglib5.dll`` for Silicon Software frame grabber interface. By default, search in Silicon Software Runtime Environment folder specified in the ``PATH`` environment variable.
        - ``thorlabs_tlcam``: path to ``thorlabs_tsi_camera_sdk.dll`` and related DLLs for Thorlabs Scientific Cameras. By default, search in the default location of ThorCam.
        - ``uc480``: path to ``uc480_64.dll`` and related DLLs for uc480 camera interface. By default, search in the default location of ThorCam.