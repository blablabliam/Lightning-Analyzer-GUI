__author__ = "Liam Plybon (blablabliam.github.io)"
__copyright__ = "Copyright 2022, Liam Plybon"
__credits__ = ["Saulius Lukse", "Drake Anthony (Styropyro)"]
__license__ = "MIT"
__version__ = "2"
__maintainer__ = "Liam Plybon"
__email__ = "lplybon1@gmail.com"
__status__ = "Prototype"
__date__ = "5-19-2022"

import sys
import time
import os
#tkinter required for pyinstaller
import tkinter
from PIL import Image, ImageTk
import cv2
import imageio

# imports for gui interface
from PySide2.QtCore import Qt, QObject, QThread, Signal, Slot
from PySide2.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QLineEdit,
    QProgressBar,
    QMessageBox
)
from PySide2.QtGui import (
    QPalette,
    QColor,
    QIntValidator,
    QIcon
)

#global variables
SCALE = 0.5
NOISE_CUTOFF = 5
BLUR_SIZE = 3
# input, output, and threshold are manipulated by the directory select buttons
# this allows them to pass into the worker thread without slots and signals.
# as such they are used as global variables
# for clarity, all globals are redefined as global wherever used.
global input_folder
input_folder = 'No Folder Chosen'
global output_folder
output_folder = 'No Folder Chosen'
global threshold
threshold = '5000000'
#buttonstate determines output file name type.
global buttonState
buttonState = True


def count_diff(img1, img2):
    # Finds a difference between a frame and the frame before it.
    small1 = cv2.resize(img1, (0, 0), fx=SCALE, fy=SCALE)
    small2 = cv2.resize(img2, (0, 0), fx=SCALE, fy=SCALE)
    diff = cv2.absdiff(small1, small2)
    diff = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
    frame_delta1 = cv2.threshold(diff, NOISE_CUTOFF, 255, 3)[1]
    frame_delta1_color = cv2.cvtColor(frame_delta1, cv2.COLOR_GRAY2RGB)
    delta_count1 = cv2.countNonZero(frame_delta1)

    return delta_count1


def error_popup(message):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText("Error")
    msg.setInformativeText(str(message))
    msg.setWindowTitle("Lightning Analysis Error")
    #prevents crash after closing message box
    msg.setAttribute(Qt.WA_DeleteOnClose)
    msg.exec_()


def info_popup(message):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText("Analysis Complete!")
    msg.setInformativeText(str(message))
    msg.setWindowTitle("Lightning Analysis Complete")
    #prevents crash after closing message box
    msg.setAttribute(Qt.WA_DeleteOnClose)
    msg.exec_()


class Worker(QObject):
    # worker thread for the analysis.
    finished = Signal()
    threadProgress = Signal(int)

    def run(self):
        """Long-running task."""
        # Launches analysis of the videos in the in directory.
        # In future, this needs to have error handling.
        # For now, it is fine without it.
        global input_folder
        global output_folder
        global threshold
        global buttonState
        in_folder = input_folder
        out_folder = output_folder
        threshold_integer = int(threshold)
        start = time.time()
        # set framecount, strike counter to zero before looping all frames
        frame_count = 0
        strikes = 0
        self.threadProgress.emit(10)
        try:
            # error if the folder is invalid. Check folder for verification.
            path, dirs, files = next(os.walk(in_folder))
            filecount = len(files)
        except:
            error_popup('Input folder not valid. Select a valid folder.')
            self.threadProgress.emit(0)
            self.finished.emit()
            return
        try:
            # determine if the output folder is valid
            path, dirs, files = next(os.walk(out_folder))
            outfilecount = len(files)
        except:
            error_popup('Output folder not valid. Select a valid folder.')
            self.threadProgress.emit(0)
            self.finished.emit()
            return
        for index, filename in enumerate(os.listdir(in_folder)):
            # itterates over files in directory
            # f_in and f_out control input and destination targets
            try:
                completion = 10+(90*((index+1)/filecount))
            except:
                self.threadProgress.emit(0)
                self.finished.emit()
                return
            self.threadProgress.emit(completion)
            f_in = os.path.join(in_folder, filename)
            f_out = os.path.join(out_folder, filename)
            video = cv2.VideoCapture(f_in)
            # gets statistics on current video
            nframes = (int)(video.get(cv2.CAP_PROP_FRAME_COUNT))
            width = (int)(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = (int)(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = (int)(video.get(cv2.CAP_PROP_FPS))
            #print('FPS is '+ str(fps))
            # video diagnostics printout for user ease.
            # Might incorporate into visible log at later date
            frame_size = "Frame size: " + str(width) + str(height) + '\n'
            total_frames = "Total frames: " + str(nframes) + '\n'
            video_fps = "Fps: " + str(fps) + '\n'
            #print(frame_size)
            #print(total_frames)
            #print(video_fps)
            #checks if input is an actual video before opening csv.
            # opens csv for statistics- might want to disable for production.
            if fps==0 or nframes==1:
                print('zerofps or image!')
                continue
            fff = open(f_out+".csv", 'w')
            # reads the video out to give a frame and flag
            flag, frame0 = video.read()
            # savestate for using the deadzone.
            deadzone = 0
            # creates list for gif frames
            gif_frames = []
            gif_name = ''
            for i in range(nframes-1):
                # loops through all of the frames, looking for strikes.
                # itterate progress bar
                file_completion = 10*(i/nframes)*((index+1)/filecount)+completion
                self.threadProgress.emit(file_completion)
                # process the video
                flag, frame1 = video.read()
                diff1 = count_diff(frame0, frame1)
                #checks for file output name system
                name = f_out+"_%06d.jpg" % i
                if not buttonState and type(fps)==int:
                    timestamp = str(round(int(i)/int(fps), 2)).replace('.','-')
                    name = f_out+ '-'+ str(timestamp) + '.png'

                if diff1 > threshold_integer:
                    # pass condition to save a frame and start a save state
                    strikes = strikes + 1
                    #write previous gif list to a gif
                    if deadzone == 0 and strikes > 1:
                        gif_start_frame = gif_frames[0]
                        gif_frames.pop(0)
                        #gif_name = str(name)[:-4] + '.gif'
                        with imageio.get_writer(gif_name, mode="I") as writer:
                            for idx, frame in enumerate(gif_frames):
                                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                writer.append_data(rgb_frame)
                        gif_frames=[]
                    # deadzone must be an int > 0 to save an image.
                    deadzone = 3
                    gif_name = str(name)[:-4] + '.gif'

                if diff1 < threshold_integer/100:
                    # itterates deadzone to zero, leaving deadzone condition.
                    # if the diff is less than 1% of the threshold, the
                    # deadzone is reduced by 1. Deadzone of 0 will result
                    # in not saving the frame.
                    if deadzone > 0:
                        deadzone = deadzone - 1

                if deadzone > 0:
                    #save frame for passing the deadzone condition.
                    cv2.imwrite(name, frame1)
                    #save frame to list for writing to gif
                    gif_frames.append(frame1)


                text = str(f_out)+', '+str(diff1)
                # print text to csv
                fff.write(text + '\n')
                fff.flush()
                # pass frame forward
                frame0 = frame1
                if i == nframes-1 and not gif_frames[0]:
                    #saves a gif at the end of a file
                    gif_start_frame = gif_frames[0]
                    gif_frames.pop(0)
                    #gif_name = str(name)[:-4] + '.gif'
                    print(gif_name)
                    with imageio.get_writer(gif_name, mode="I") as writer:
                        for idx, frame in enumerate(gif_frames):
                            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            writer.append_data(rgb_frame)
                    # gif_start_frame.save(gif_name,
                    #                      save_all=True,
                    #                      append_images=gif_frames,
                    #                      duration=100,
                    #                      loop=0)
                    gif_frames=[]
        fff.close()
        # statistics
        video_strikes = 'Strikes: '+ str(strikes) + '\n'
        elapsed_time = 'Process Time: ' + str(int(time.time() - start)) + ' s\n'
        #print(video_strikes)
        #print(elapsed_time)
        info = video_strikes+elapsed_time
        info_popup(info)
        #sends finished signal. Essentially terminates the thread.
        self.threadProgress.emit(100)
        self.finished.emit()


class Window(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        #self.clicksCount = 0
        self.setupUi()
        # self.setIcon()

    def setupUi(self):
        # sets up the gui layout itself
        self.setWindowTitle("ZapCapture")
        self.resize(300, 150)
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        # Create and connect widgets
        #directory widgets
        self.inputFileDirectoryButton = QPushButton("Select Input Directory", self)
        self.inputFileDirectoryButton.clicked.connect(self.pick_new_input)
        self.inputFileDirectoryLabel = QLabel(input_folder)
        self.inputFileDirectoryLabel.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.outputFileDirectoryButton = QPushButton("Select Output Directory", self)
        self.outputFileDirectoryButton.clicked.connect(self.pick_new_output)
        self.outputFileDirectoryLabel = QLabel(output_folder)
        self.outputFileDirectoryLabel.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        #file name widgets
        self.outputFilenameLabel = QLabel('Output File Name (❓)')
        self.outputFilenameLabel.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.outputFilenameLabel.setToolTip('Output File Name determines the standard used to give a file name. Frame number will output files as an integer, while timestamp will output files as a timestamp.')
        self.outputFrameNumButton = QRadioButton("Frame Number")
        self.outputFrameNumButton.setChecked(True)
        self.outputFrameNumButton.toggled.connect(lambda:self.btnstate(self.outputFrameNumButton))
        self.outputTimestampButton = QRadioButton("Timestamp")
        self.outputTimestampButton.setChecked(False)
        self.outputTimestampButton.toggled.connect(lambda:self.btnstate(self.outputTimestampButton))
        #threshold widget
        self.thresholdLabel = QLabel("Threshold (❓)", self)
        self.thresholdLabel.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.thresholdLabel.setToolTip('Threshold determines the sensitivity of the computer vision algorithm. High thresholds will execute quickly with few output images, while low thresholds will potentially detect every frame of the video as a lightning event. Each video in your folder may need an individually tuned threshold; in this case, make subfolders for videos from the same camera and event. For example, separate your dash-cam footage and stationary camera footage. Nighttime footage can require thresholds aroung 10 million, while daytime footage can be as low as 10 thousand.')
        self.thresholdEntry = QLineEdit(threshold)
        # restricts the threshold to be numbers only
        self.onlyInt = QIntValidator()
        self.thresholdEntry.setValidator(self.onlyInt)
        self.analysisButton = QPushButton('Perform Analysis', self)
        # self.analysisButton.clicked.connect(self.analysis)
        self.analysisButton.clicked.connect(self.runLongTask)
        self.progressBar = QProgressBar(self)
        self.progressBar.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        #self.progressBar.setGeometry(200, 80, 250, 20)
        self.progressBar.setValue(0)

        # Set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.inputFileDirectoryButton)
        layout.addWidget(self.inputFileDirectoryLabel)
        layout.addWidget(self.outputFileDirectoryButton)
        layout.addWidget(self.outputFileDirectoryLabel)
        layout.addWidget(self.outputFilenameLabel)
        layout.addWidget(self.outputFrameNumButton)
        layout.addWidget(self.outputTimestampButton)
        layout.addWidget(self.thresholdLabel)
        layout.addWidget(self.thresholdEntry)
        layout.addWidget(self.analysisButton)
        layout.addWidget(self.progressBar)
        self.centralWidget.setLayout(layout)

    def pick_new_input(self):
        dialog = QFileDialog()
        folder_path = dialog.getExistingDirectory(None, "Select Input Folder")
        global input_folder
        input_folder = str(folder_path)
        self.inputFileDirectoryLabel.setText(str(folder_path))
        #reset the progress bar to 0
        self.progressBar.setValue(0)
        self.analysisButton.setEnabled(True)

    def pick_new_output(self):
        dialog = QFileDialog()
        folder_path = dialog.getExistingDirectory(None, "Select Output Folder")
        global output_folder
        output_folder = str(folder_path)
        self.outputFileDirectoryLabel.setText(str(folder_path))
        #reset the progress bar to 0
        self.progressBar.setValue(0)
        self.analysisButton.setEnabled(True)

    def btnstate(self, b):
        global buttonState
        if b.text() == "Frame Number":
            if b.isChecked() == True:
                buttonState = True
                print(b.text()+" is selected")
            else:
                buttonState = False
                print(b.text()+" is deselected")


    def runLongTask(self):
        # set the threshold
        global threshold
        threshold = self.thresholdEntry.text()
        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = Worker()
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # setup progress bar signal
        self.worker.threadProgress.connect(self.onCountChanged)
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)
        # Step 6: Start the thread
        self.thread.start()

        # Final resets
        self.analysisButton.setEnabled(False)
        self.thread.finished.connect(self.enableAnalysisButton)
        # self.thread.finished.connect(
        #     lambda: self.analysisButton.setEnabled(True)
        # )

    def onCountChanged(self, value):
        self.progressBar.setValue(value)

    def enableAnalysisButton(self):
        self.analysisButton.setEnabled(True)




app = QApplication(sys.argv)

# Dark Mode code
# Force the style to be the same on all OSs:
app.setStyle("Fusion")

# Now use a palette to switch to dark colors:
palette = QPalette()
palette.setColor(QPalette.Window, QColor(53, 53, 53))
palette.setColor(QPalette.WindowText, Qt.white)
palette.setColor(QPalette.Base, QColor(25, 25, 25))
palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
palette.setColor(QPalette.ToolTipBase, Qt.black)
palette.setColor(QPalette.ToolTipText, Qt.white)
palette.setColor(QPalette.Text, Qt.white)
palette.setColor(QPalette.Button, QColor(53, 53, 53))
palette.setColor(QPalette.ButtonText, Qt.white)
palette.setColor(QPalette.BrightText, Qt.red)
palette.setColor(QPalette.Link, QColor(42, 130, 218))
palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
palette.setColor(QPalette.HighlightedText, Qt.black)
app.setPalette(palette)

# finish building window
win = Window()
win.show()
sys.exit(app.exec_())
