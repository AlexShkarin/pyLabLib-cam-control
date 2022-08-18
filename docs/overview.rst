.. _overview:

Overview
=========================

.. _overview_install:

Installation
------------------------- 

Download the zip file with the `latest release <https://github.com/AlexShkarin/pylablib-cam-control/releases/latest/download/cam-control.zip>`__ and unpack it to the desired location. The software comes with its own isolated Python interpreter with all the basic packages installed, so no additional installations are necessary. Download links to older version are available on the :ref:`release history <changelog>` page.

To run the software, simply execute ``control.exe``. On the first run it will suggest to either load settings file (``settings.cfg``) from the previous version, or to detect all connected supported cameras and store their connection parameters. Make sure that at this point all cameras are connected, turned on, and not used in any other software (e.g., Andor Solis, Hokawo, or NI MAX). If new cameras are added to the PC, they can be re-discovered by running ``detect.exe``.

If only one camera is found, running ``control.exe`` will automatically connect to it. Otherwise, a dropdown menu will show up allowing selection of specific cameras.


.. _overview_software_requirements:

Software requirements
-------------------------

Cam-control is built using `pylablib <https://github.com/AlexShkarin/pyLabLib/>`__ and includes all of the cameras supported there. All of these cameras need some kind of drivers and API installed:

- Andor cameras: `Andor Solis <https://andor.oxinst.com/products/solis-software/>`__ or `Andor SKD <https://andor.oxinst.com/products/software-development-kit/>`__.
- Hamamatsu/DCAM cameras: Hamamatsu-supplied software such as Hokawo, or the freely available `DCAM API <https://dcam-api.com/downloads/>`__. Keep in mind, that you also need to install the drivers for the corresponding camera type (USB, Ethernet, IEEE 1394). These drivers are in the same installer, but need to be installed separately.
- Thorlabs uc480 and Thorlabs scientific imaging cameras: freely available `ThorCam <https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam>`__ software (no older than v3.5.0 for the scientific imaging cameras).
- IDS uEye cameras: freely available (upon registration) `IDS Software Suite <https://en.ids-imaging.com/ids-software-suite.html>`__.
- PCO cameras: freely available `pco.camware <https://www.pco.de/software/camera-control-software/pcocamware/>`__ software.
- IMAQdx cameras: all the necessary code is contained in the freely available `Vision Acquisition Software <https://www.ni.com/en-us/support/downloads/drivers/download.vision-acquisition-software.html>`__. However, the IMAQdx part of the software is proprietary, and needs to be purchased to use.
- IMAQ frame grabbers: freely available `Vision Acquisition Software <https://www.ni.com/en-us/support/downloads/drivers/download.vision-acquisition-software.html>`__. In addition, you would also need to specify the correct camera file, which describes the camera communication protocol details.
- Silicon Software frame grabbers: freely available (upon registration) `Silicon Software Runtime Environment <https://www.baslerweb.com/en/sales-support/downloads/software-downloads/#type=framegrabbersoftware;language=all;version=all;os=windows64bit>`__ (the newest version for 64-bit Windows is `5.7.0 <https://www.baslerweb.com/en/sales-support/downloads/software-downloads/complete-installation-for-windows-64bit-ver-5-7-0/>`__).
- PhotonFocus: on top of IMAQ or Silicon Software requirements, it needs freely available (upon registration) `PFInstaller <https://www.photonfocus.com/support/software/>`__ software.
- PICam (Princeton Instruments) cameras: freely available `PICam <https://www.princetoninstruments.com/products/software-family/pi-cam>`__ software.
- PVCAM (Photometrics) cameras: freely available (upon registration) `PVCAM software <https://www.photometrics.com/support/download/pvcam>`__.
- Basler cameras: freely available (upon registration) `Basler pylon Camera Software Suite <https://www.baslerweb.com/en/downloads/software-downloads/>`__ (the current latest version is `7.1.0 <https://www.baslerweb.com/en/downloads/software-downloads/software-pylon-7-1-0-windows/>`__).
- BitFlow Axion frame grabbers require several steps:

  - First, you need to install freely available `BitFlow SDK 6.5 <https://www.bitflow.com/downloads/bfsdk65.zip>`__, preferrably into its default folder or, at least, using the default folder name ``BitFlow SDK 6.5``.
  - Second, you have to download manufacturer-provided `BitFlow Python 3.8 package <https://www.bitflow.com/downloads/BFPython38_Release.zip>`__, extract ``BFModule-1.0.1-cp38-cp38-win_amd64.whl`` file from there to the ``python`` folder within ``cam-control`` (it should contain files like ``python.exe``), and run ``install-dependencies.bat`` script contained in the same folder.
  - Next, you need to specify the correct camera file for your camera using ``SysReg`` utility located in the ``Bin64`` folder of your BitFlow installation (by default, ``C:\BitFlow SDK 6.5\Bin64``).
  - Afterwards, you should copy this camera file into the main ``cam-control`` folder (it should contain files like ``settings.cfg``). The camera file is located in ``Config\Axn`` folder within the BitFlow installation (by default, ``C:\BitFlow SDK 6.5\Config\Axn``) and has ``.bfml`` extension, e.g., ``PhotonFocus-MV1-D1024E-160-CL.bfml``.
  - You can now search for the cameras by running either ``control.exe`` for the first time, or ``detect.exe`` at any point.

.. note::

    Cam-control is only available in 64-bit version, which in most cases means that you must install 64-bit versions of the software described above.

.. note::

    It is strongly recommended that you install the manufacturer software (especially Andor Solis and ThorCam) into their default locations. Otherwise, cam-control might not be able to find the required DLLs and communicate with the cameras. In this case, you would need to specify the location of the necessary DLLs in the :ref:`settings file <settings_file_system>`.

In most cases, you already have the necessary software installed to communicate with the cameras to begin with. As a rule of thumb, if you can open the camera in the manufacturer-supplied software, you can open it in the cam-control as well.

In rare cases you might also need to install Microsoft Visual C++ Redistributable Package. You can obtain it on the `Microsoft website <https://aka.ms/vs/16/release/vc_redist.x64.exe>`__.

Specifying camera files
~~~~~~~~~~~~~~~~~~~~~~~~~

Cameras using NI-IMAQ frame grabbers also need the correct ``.icd`` camera file for the connected camera, which describes the communication protocol details, sensor size, possible bit depths, etc. Some of the common camera files are already provided when you install Vision Acquisition Software, others need to be obtained from the manufacturer. To specify them, follow the following steps:

1) If you are using a manufacturer-provided file, copy it into the NI-IMAQ camera file storage. By default it is located at ``C:\Users\Public\Documents\National Instruments\NI-IMAQ\Data`` (the folder should already exist and have many ``.icd`` files).
2) Run NI MAX, and there find the camera entry in ``Devices and Interfaces`` -> ``NI-IMAQ Devices`` -> ``img<n>: <Frame grabber name>`` (e.g., ``img0: NI PCIe-1433``) -> ``Channel <n>`` (0 for single-channel frame grabbers).
3) Right-click on the camera entry and there select ``Camera`` -> ``<Manufacturer>`` -> ``<Camera model corresponding to the file>``.

PhotonFocus provides camera files with PFRemote, and they can be found in ``<Photon Focus folder>\PFRemote\fg_files``. There are several files with names like ``pfFg_ni_2tap_8bit.icd``, which should be selected based on the desired bit depth (usually 12 bit is preferable, if it is available for your camera) and the number of CameraLink taps (specified in the technical specification found in the camera manual; e.g., MV1-D1024E-160-CL has 2 taps). After specifying the file, you need to also specify the camera pixel depth using PFRemote. The correct setting is located at ``Data Output`` -> ``Output Mode`` -> ``Resolution``.


.. _overview_layout:

General layout
-------------------------

.. image:: overview.png

The window is split into two parts. The left half shows the images, possibly with several tabs to show several different kinds of images (e.g., if filters are used). The right half controls data saving, shows camera status (in the middle column), and has additional controls for camera, on-line processing, or additional plugins (rightmost column).

The acquisition is started by pressing ``Start acquisition`` button. Note that you might need to adjust camera parameters (e.g., specify exposure, ROI, binning, pixel readout rate) to get reasonable image quality and performance.

All of the entered values are automatically saved on exit and restored on the next restart. It is also possible to :ref:`save the settings to a file <interface_footer>` and load them later, which is helpful for working in several different regimes.

You can find more information either on the :ref:`interface page <interface>`, or in the built-in :ref:`tutorial <interface_tutorial>`.

.. image:: overview_compact.png

In case the interface takes too much space and does not fit in the screen, you can enable the compact mode in the :ref:`preferences <interface_preferences>`.

The software uses a dark color theme by default. You can change it in the :ref:`preferences <interface_preferences>`.

.. _overview_feedback:

Support and feedback
-------------------------

If you have any issues, suggestions, or feedback, you can either raise an issue on GitHub at https://github.com/SandoghdarLab/pyLabLib-cam-control/issues, or send an e-mail to pylablib@gmail.com.