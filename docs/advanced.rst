.. _advanced:

Advanced features
=========================


.. _advanced_slowdown:

Playback slowdown
-------------------------

Fast cameras are typically used to analyze fast events. However, cam-control still has to display data in real time, which means that this fast acquisition potential is lost during on-line analysis. Of course, it still saves all the frames for further examination, but it usually takes some time to load and go through them.

For a quick check, there is an option to temporarily slow data display to the desired frame rate, slowing down the playback. For example, if the camera operates at 10 kFPS and the playback is set to work at 100 FPS, the process is seen 100 times slower.

The way it works is by storing all incoming camera frames into a temporary buffer, and then taking these frames from the buffer at a lower rate. Since the size of this buffer is limited, the slowdown naturally can only proceed for a finite time. It is easy to calculate that, e.g., for the same 10 kFPS camera speed and 100 FPS playback speed the buffer of 1000 frames will take 0.1s of real time and stretch it into 10s of display time.

Note that the slowdowns happens after the pre-binning, but before filters and background subtraction. Hence, it affects all of the displayed frames, but not the saving, which still happens at the regular rate.

This feature controls are on the :ref:`Processing tab <interface_processing>`.


.. _advanced_time_plot:

Time plot
-------------------------

Sometimes it is useful to look at how the image values evolve in time. Cam-control has basic capabilities for plotting the mean value of the frame or a rectangular ROI within it as a function of time or frame number. It can be set in two slightly different ways: either plot averages of displayed frames vs. time, or averages of all camera frames vs. frame index.

This feature is only intended for a quick on-line data assessment, so there is currently no provided way to save these plots. As an alternative, you can either save the whole move, or use :ref:`time map filter <advanced_filter>` and save the resulting frame.

This feature controls are on the :ref:`Processing tab <interface_time_plot>`.


.. _advanced_save_trigger:

Saving trigger
-------------------------

Often we would like to automate data acquisition. There are two basic built-in ways to do that in cam-control.

The first is simple timer automation, where a new data set is acquired with a given period. It is useful when monitoring relatively slow processes, when recording data continuously is excessive.

The second is based on the acquired images themselves. Specifically, it is triggered when any pixel in a displayed image goes above a certain threshold value. Since multiple consecutive frames can trigger saving, this method also includes a dead time: a time after triggering during which all triggers are ignored. This way, settings the dead time larger than the saving time (plus a small 1-2 second buffer period) ensures that each trigger results in a complete save.

The image-based method strongly benefits from two other software features: :ref:`pre-trigger buffer <pipeline_saving_pretrigger>` and :ref:`filters <advanced_filter>`. The first one allows to effectively start saving some time before the triggering image, to make sure that the data preceding the event is also recorded. The second one adds a lot of flexibility to the exact triggering conditions. Generally, it is pretty rare that one is really interested in the brightest pixel value. Using filters, you can transform image to make the brightest pixel value more relevant (e.g., use transform to better highlight particles, or use temporal variations to catch the moment when the image starts changing a lot), or even create a "fake" filter output a single-pixel 0 or 1 image, whose sole job is to trigger the acquisition.

Both timed and image trigger also support a couple common features. They both can trigger either standard save for more thorough data acquisition, or snapshot to get a quick assessment. And both can take a limit on the total number of saving events.

This feature controls are on the :ref:`Plugins tab <interface_saving_trigger>`.


.. _advanced_filter:

Filters
-------------------------

Filters provide a flexible way to perform on-line image processing. They can be used to quickly assess the data in real time or even to :ref:`automate data acquisition <advanced_save_trigger>`.

They are primarily designed for :ref:`expanding by users <expanding_filter>`. Nevertheless, there are several pre-made filters covering some basic spatial and temporal image transforms:

- **Gaussian blur**: standard image blur, i.e., spatial low-pass filter. The only parameter is the blur size.
- **FFT filter**: Fourier domain filter, which is a generalization of Gaussian filter. It involves both low-pass ("minimal size") and high-pass ("maximal size") filtering, and can be implemented either using a hard cutoff in the Fourier space, or as a Gaussian, which is essentially equivalent to the Gaussian filter above.
- **Moving average**: average several consecutive frames within a sliding window together. It is conceptually similar to :ref:`time pre-binning <pipeline_prebinning>`, but only affects the displayed frames and works within a sliding window. It is also possible to take only every n'th frame (given by ``Period`` parameter) to cover larger time span without increasing the computational load.
- **Moving accumulator**: a more generic version of moving average. Works very similarly, but can apply several different combination methods in addition to averaging: taking per-pixel median, min, max, or standard deviation (i.e., plot how much each pixel's value fluctuates in time).
- **Moving average subtraction**: combination of the moving average and the time derivative. Averages frames in two consecutive sliding windows and displays their difference. Can be thought of as a combination of a moving average and a sliding :ref:`background subtraction <pipeline_background_subtraction>`. This approach was used to enhance sensitivity of single protein detection in interferometric scattering microscopy (iSCAT) [Young2018]_, and it is described in detail in [Dastjerdi2021]_.
- **Time map**: a 2D map which plots a time evolution of a line cut. The cut can be taken along either direction and possibly averaged over several rows or columns. For convenience, the ``Frame`` display mode shows the frames with only the averaged part visible. This filter is useful to examine some time trends in the data in more details than the simple local average plot.
- **Difference matrix**: a map for pairwise frames differences. Shows a map ``M[i,j]``, where each element is the RMS difference between ``i``'th and ``j``'th frames. This is useful for examining the overall image evolution and spot, e.g., periodic disturbances or switching behavior.

This feature controls are on the :ref:`Filter tab <interface_filter>`.

.. [Young2018] Gavin Young et al., `"Quantitative mass imaging of single biological macromolecules," <https://doi.org/10.1126/science.aar5839>`__ *Science* **360**, 423-427 (2018)

.. [Dastjerdi2021] Houman Mirzaalian Dastjerdi, Mahyar Dahmardeh, André Gemeinhardt, Reza Gholami Mahmoodabadi, Harald Köstler, and Vahid Sandoghdar, `"Optimized analysis for sensitive detection and analysis of single proteins via interferometric scattering microscopy," <https://doi.org/10.1101/2021.08.16.456463>`__ *bioRxiv doi*: `10.1101/2021.08.16.456463 <https://www.biorxiv.org/content/10.1101/2021.08.16.456463>`__