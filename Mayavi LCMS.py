import os
import numpy as np
from mayavi import mlab
import pandas as pd
from scipy import signal
import wx


def scale_function(lcms_data):
    """
    Finds a number for each axis that will rescale the axis to a specific range.

    :param lcms_data:   Full data file
    :return:            A rescaling number for each axis
    """

    # Retention time
    a = lcms_data[:, 0]
    # m/z ratio
    b = lcms_data[:, 1]
    # Intensity
    c = lcms_data[:, 2]

    max_x = max(a)
    max_y = max(b)
    max_z = max(c)

    max_num_x = 30
    max_num_y = 35
    max_num_z = 20

    x_scaling = max_num_x / max_x

    y_scaling = max_y / max_num_y

    z_scaling = max_z / max_num_z

    return x_scaling, y_scaling, z_scaling


def rate_downsampling(lcms_data):
    """
    Finds a number to scale downsampling rate based on the size of the data file.
    Default rate is 1.5 and increases by 0.1 with every 10 MB greater than 100,
    and decreases 0.1 with every 10 MB less than 80.

    :param lcms-data:   Full data file
    :return:            A number to scale downsampling rate
    """

    # Finds the size of given file.
    # Converts it from bytes to megabytes.
    file_size = os.stat(lcms_data).st_size * 0.000001

    if 80 <= file_size <= 100:
        # Default rate
        return 1.5
    if file_size > 100:
        # For every 10 MB greater than 100, increase rate by 0.1
        diff = file_size - 100
        return 1.5 + ((1 / 10) * (diff / 10))
    else:
        # For every 10 MB less than 80, decrease rate by 0.1
        diff = 80 - file_size
        return 1.5 - ((1 / 10) * (diff / 10))


def artifact_remover(downsamp_data):
    """
    Find and remove all artifacts from the plot.
    Artifacts are those sections of the plot that creates triangles instead of a straight line peak.

    :param downsamp-data:   Downsampled data of the full data set
    :return:                Three lists with all major artifacts removed
    """

    a = downsamp_data[:, 0]
    b = downsamp_data[:, 1]
    c = downsamp_data[:, 2]

    # TODO: Continue here


def main_function(file):
    # Process the data to arrays
    # file = "HP_1a1.csv"
    data = pd.read_csv(file)
    data = np.array(data)

    # x: Retention time
    # y: m/z ratio
    # z: Intensity
    x = data[:, 0]
    y = data[:, 1]
    z = data[:, 2]

    # Retrieve scaling scalars from scale function
    x_scale, y_scale, z_scale = scale_function(data)

    # Retrieve rate to downsample data
    rate = rate_downsampling(file)

    # Begin full downsampling of data

    # These lists store the final data of each axis
    xnew = []
    ynew = []
    znew = []

    # These lists are temporary placeholders for each section/bucket of each axis
    data_BucketX = []
    data_BucketY = []
    data_BucketZ = []

    index = 0
    for item in x:
        # Ignore the first line
        if index == 0:
            index += 1
            continue
        # Retention values are the same, grouped into same bucket
        if item == x[index - 1]:
            data_BucketX.append(item)
            data_BucketY.append(y[index])
            data_BucketZ.append(z[index])
        # Different bucket
        else:
            # Ignore buckets with fewer than 100 data points
            if len(data_BucketX) < 100:
                index += 1
                continue
            xn = []
            yn = []
            zn = []

            # Downsample length of each bucket

            # TODO: Fix the rate error
            # An error like the one below may occur with regards to rate:
            #   ERROR: In C:\VPP\standalone-build\VTK-source\Filters\Core\vtkDelaunay2D.cxx, line 819
            #   vtkDelaunay2D (0000027AE2A2ACF0): ERROR: Edge [118461 118462] is non-manifold!!!
            sample = int(len(data_BucketX) / rate)
            xn.extend(signal.resample(data_BucketX, sample))
            yn.extend(signal.resample(data_BucketY, sample))
            zn.extend(signal.resample(data_BucketZ, sample))

            i = 0
            for foo in zn:
                # Rescaled each axis
                xnew.append(xn[i] * x_scale)
                ynew.append(yn[i] / y_scale)
                znew.append(zn[i] / z_scale)
                i += 1

            data_BucketX.clear()
            data_BucketY.clear()
            data_BucketZ.clear()
        index += 1

    # From here, continue to remove data, specifically intensity values, that are too small and irrelevant

    # Temporary list to store indices
    foo = []

    # Set a max z-axis threshold
    z_threshold = max(znew) * 0.01

    # Loop through intensity list
    for i in range(len(znew)):
        # Append to the temporary list the indices of intensity values that are less than the threshold
        if znew[i] < z_threshold:
            foo.append(i)

    # Removes all corresponding elements from each array
    # Must remove from all three lists to preserve uniformity
    xnew = np.delete(xnew, foo)
    ynew = np.delete(ynew, foo)
    znew = np.delete(znew, foo)

    # From here, we are ready to get our plots set up

    # Dummy object to get accurate and original intensity values for colorbar label
    original = mlab.points3d(x, y, z, z, mode='point')
    original.remove()

    # Visualize the points
    pts = mlab.points3d(xnew, ynew, znew, znew, mode='point')

    # Create and visualize the mesh
    mesh = mlab.pipeline.delaunay2d(pts)
    surf = mlab.pipeline.surface(mesh)
    pts.remove()

    # Simple plot axis info rendering
    mlab.xlabel("Retention")
    mlab.ylabel("m/z")
    mlab.zlabel("Intensity")

    # Add text to plot indicating how each axis was rescaled
    mlab.text(0.5, 0.80, 'Retention scaled up by %.2f' % x_scale, width=0.8)
    mlab.text(0.5, 0.85, 'm/z scaled down by %.2f' % y_scale, width=0.8)
    mlab.text(0.5, 0.90, 'Intensity scaled down by %.2f' % z_scale, width=1.0)

    # Colorbar with original intensity values
    colorbar = mlab.colorbar(object=original, title='Intensity', orientation='vertical')
    colorbar.scalar_bar_representation.position = [0.85, 0.18]

    # Show the final plot scene
    mlab.show()


# This is an UI that allows the user to select a particular data file to visualize
# First we build the MyFrame class and define
class MyFrame(wx.Frame):
    def __init__(self, parent: wx.Frame, title: str, size: int):
        super(MyFrame, self).__init__(parent, title=title, size=size)
        self.panel = MyPanel(self)


# Here we build the panel and fill it with a button
class MyPanel(wx.Panel):
    def __init__(self, parent: wx.Frame):
        super(MyPanel, self).__init__(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizerv = wx.BoxSizer(wx.VERTICAL)
        self.label = wx.StaticText(self, label="Select an LCMS file to visualize.\n"
                                               "Please allow a few seconds for the plot to render.",
                                                pos=(0, 30))
        self.font = wx.Font(18, wx.DECORATIVE, wx.NORMAL, wx.NORMAL)
        self.label.SetFont(self.font)
        sizerv.Add(self.label)
        self.btn = wx.Button(self, label="File")
        sizer.Add(self.btn, 10)
        self.btn.Bind(wx.EVT_BUTTON, self.OnclickMe)
        self.SetSizer(sizer)

    # Here is our event method fired OnClick
    def OnclickMe(self, event: wx.EVT_BUTTON):
        with wx.FileDialog(self, "Open CSV file", wildcard="CSV files (*.csv)|*.csv",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            # The user changed their mind
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # Proceed loading the file chosen by the user
            pathname = fileDialog.GetPath()
            filename = os.path.basename(pathname)

            text = "You have selected the file: " + filename
            self.label.SetLabelText(text)

        # Call the function that renders everything and does the visualization
        main_function(filename)


# then we build our my app class initialize our frame and show content
class MyApp(wx.App):
    def OnInit(self):
        self.frame = MyFrame(parent=None, title="Liquid Chomatography - Mass Spectrometry", size=(600, 500))
        self.frame.Show()
        return True


# here is the loop that keeps our frame open and displayed to the user on launch
app = MyApp()
app.MainLoop()
