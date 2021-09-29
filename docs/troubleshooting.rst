.. _troubleshooting:

Troubleshooting
=========================

- **Camera is not detected by the software**

  - Camera is disconnected, turned off, its drivers are missing, or it is used by a different program: Andor Solis, Hokawo, NI MAX, PFRemote, PCO Camware, ThorCam, etc. Check if it can be opened in its native software.
  - Software can not find the libraries. Make sure that the :ref:`native camera software <overview_software_requirements>` is installed in the default path, or :ref:`manually specify the DLL paths <settings_file_system>`.
  - Frame grabber cameras and IMAQdx cameras currently have only limited support. Please, :ref:`contact the developer <overview_feedback>` to see if it is possible to add your specific camera to the software.

- **Camera camera controls are disabled and camera status says "Disconnected"**

  - Camera is disconnected, turned off, its drivers are missing, or it is used by a different program. Check if it can be opened in its native software.

- **The image is not updated when the camera acquisition is running**

  - Make sure that you are looking at the correct image tab, and that the ``Update`` button is pressed.
  - The camera is in the external trigger mode and no triggering signal is incoming. Switch the camera to the internal trigger mode.
  - In some cases certain camera setting combinations result in unstable behavior. Check if these exact camera settings work in the native software.

- **The operation or frames update is slow or laggy**
  
  - Frame plotting takes up too much resources. Reduce the frame update period or, if necessary, turn off the display update.
  - Additional plotting features take up too much resources. Turn off frame cuts plotting, color histogram, and switch to the plain grayscale color scheme.
  - On-line processing takes up too much resources. Turn off pre-binning, background subtraction, filters (disable or unload), and mean frame plots.
  - Slowdown is turned on, camera frame rate is low, or time frame binning is enabled with a large factor. All of these can lead to actually low generated frame rate.
  - Selected display update period (selected under the plot parameters) is too large. 
  - By default, the camera is polled for new frames every 50ms, so the frame rate is limited by 20 FPS. To increase it, you can specify the ``loop/min_poll_period`` parameter the :ref:`settings file <settings_file_camera>`.

- **Missing frames are reported after saving**

  - Acquisition can not deal with high data or frame rate. Check if the :ref:`frame buffer <interface_camera_status>` is full or constantly increasing. If so, reduce the frame rate or frame size.
  - Frame info acquisition takes too much time. On some cameras (e.g., uc480 and Silicon Software frame grabbers) acquiring frame information can take a significant fraction of the frame readout, especially for small frames and high readout rates. If this is the case, you need to turn the frame info off.
  - Frames pre-binning can not deal with high data rate. Check if the frame buffer is full or constantly increasing. If so, reduce the frame rate or frame size, or turn the pre-binning off.
  - Software as a whole can not deal with high data or frame rate. Minimize the load from unnecessary programs running on this PC. Avoid using remote control software (e.g., TeamViewer or Windows Remote Desktop) during the saving sessions.
  - Acquisition has been restarted during saving (e.g., due to parameters change).
  - PhotonFocus cameras can generate frames faster than some frame grabbers (e.g., SiliconSoftware microEnable 4) can manage. This shows up as lower frame rate than expected from the frame period. If this is the case, reduce the frame rate.
  - The data rate is higher than the drive writing rate, and the :ref:`save buffer <pipeline_saving_buffer>` is overflown. Reduce the size of a single saving session, switch to a faster drive (SSD), or increase the save buffer size.
  - (especially if missing frames occur right at the beginning) Obtaining camera settings for saving takes too much time. Increase the buffer size using ``misc/buffer/min_size/time`` parameter in the :ref:`settings file <settings_file_camera>`, or turn off the settings file (not recommended).

- **Saving in Tiff format ends abruptly or produces corrupted files**

  - Tiff format does not support files larger than 2 Gb. Either split data in smaller files (e.g., using the :ref:`file split <interface_save_control>` settings), or use other format such as BigTiff.

- **Control window is too large and does not fit into the screen**
  
  - You can enable the compact mode in the :ref:`setting file <settings_file_general>`.

- **Camera performance is lower than can be achieved in the native software**

  - Make sure that all available settings (including advanced settings such as readout speed, pixel clock, etc.) are the same in both cases.
  - Some specific cameras might not be fully supported. Please, :ref:`contact the developer <overview_feedback>` to add necessary settings of your specific camera to the software.