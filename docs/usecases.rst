.. _usecases:

Use cases
=========================

Here we describe some basic use cases and applications of the cam-control software.

- **Standard acquisition**

    This is the standard mode which requires minimal initial configuration. Simply setup the :ref:`camera parameters <interface_camera_settings>`, configure the :ref:`saving <interface_save_control>`, start the acquisition, and press ``Saving``.

- **Recording of rare events**

    Manual recording of rare and fast events is often challenging. Usually you have to either record everything and sift through the data later, or hope to press ``Saving`` quickly enough to catch most of it. Neither option is ideal: the first method takes a lot of extra storage space, while the second requires fast reaction. :ref:`Pretrigger buffer <pipeline_saving_pretrigger>` takes the best of both worlds: it still allows to only record interesting parts, put lets you start saving a couple seconds before the button is pressed, so it is not necessary to press it as quickly as possible. The buffer is set up in the :ref:`saving parameters <interface_save_control>`.

- **Periodic acquisition**

    To record very slow processes, you might want to just occasionally take a snapshot or a short movie. You can use :ref:`saving trigger <advanced_save_trigger>` for that.

- **Image-based acquisition start**

    Another :ref:`saving trigger <advanced_save_trigger>` application is to automate data acquisition. It gives an option to start acquisition based on the frame values. Combined with :ref:`custom filters <expanding_filter>`, it provides a powerful way to completely automate acquisition of interesting events.

- **Background subtraction**

    Oftentimes the camera images contain undesired static or slowly changing background. It is possible to get rid of it using the built-in basic :ref:`background subtraction <pipeline_background_subtraction>`. Keep in mind that it only affects the displayed data (and, as such, is not applied to frames supplied to filters).

- **On-line image processing**

    More complicated on-line processing is available through filters. Cam-control already comes with several basic :ref:`built-in filters <advanced_filter>`, but the real power in custom application comes from the ability to easily write :ref:`custom filters <expanding_filter>`.

- **On-line analysis of fast processes**

    To do a quick on-line analysis of fast processes, you can use the :ref:`frame slowdown <advanced_slowdown>` capability.

- **Interfacing with external software**

    Cam-control provides a :ref:`TCP/IP server control <expanding_server>` which allows one to control GUI, start or stop acquisition and saving, and directly acquire frames from the camera. Since this is implemented as a server, it is platform- and software-independent, so it can interface with any custom software written in, e.g., C++, Java, LabView, or Matlab. It can be used to synchronize data acquisition with other devices, implement more sophisticated automation, or provide frames for custom image-processing software.

- **Controlling several cameras**

    Cam-control allows for control of several connected cameras. If more than one camera is specified in the settings file (typically these are found by running the ``detect`` script), then every time the software is started, it allows to select which camera to control. Several instances can run simultaneously for different cameras without interference. The default GUI parameters are stored independently for all cameras.

    The selection window can be avoided by specifying the camera either directly in the :ref:`settings file <settings_file_camera>`, or by supplying its name in the command line using ``--camera`` :ref:`argument <command_line>` (e.g., run ``control.bat --camera ppimaq_0``).