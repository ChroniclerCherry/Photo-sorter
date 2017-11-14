import tkinter
from tkinter import filedialog
import os
import exifread
import datetime
import shutil
from pathlib import Path
import threading


class PictureInformation:
    def __init__(self, f):

        self.path = f
        self.has_date = True
        t_format = '%Y:%m:%d %H:%M:%S'

        # open file
        with open(self.path, 'rb') as photo:
            photo_tags = exifread.process_file(photo)

        self.name = os.path.basename(self.path)
        self.size = os.path.getsize(self.path)

        # check if it has date time
        if "EXIF DateTimeOriginal" not in photo_tags:
            self.datetime_taken = datetime.datetime(1, 1, 1, 1, 0, 0)
            self.has_date = False
        else:
            self.datetime_taken = datetime.datetime.strptime(str(photo_tags['EXIF DateTimeOriginal']), t_format)


IDENTICAL = 0
IDENTICAL_NAME = 1
DIFFERENT = 2


class MainWindow:
    is_process_running = False

    def __init__(self, master):

        # set title of window
        self.master = master
        master.title("Photo sorter")

        # simple text describing application
        self.label = tkinter.Label(master, text="Takes photos from one directory and copies & sorts them by date")
        self.label.grid(row=1, columnspan=2)

        # entry box for source folder path
        self.source_input = tkinter.Entry(master, textvariable="", width=50)
        self.source_input.grid(row=2, column=0)
        # browse button for source
        self.source_button = tkinter.Button(master, text="Browse source", command=self.set_source)
        self.source_button.grid(row=2, column=1)

        # entry box for destination folder path
        self.destination_input = tkinter.Entry(master, textvariable="", width=50)
        self.destination_input.grid(row=3, column=0)
        # browse button for destination
        self.destination_button = tkinter.Button(master, text="Browse destination", command=self.set_destination)
        self.destination_button.grid(row=3, column=1)

        # button to start or stop the process
        self.start_button = tkinter.Button(master, text="Start", command=self.action)
        self.start_button.grid(row=4, column=0)

        self.strict_identical_selection = tkinter.BooleanVar()
        # radio buttons to decide between stricter or looser image identical checks
        self.strict_radio = tkinter.Checkbutton(master, text="Strict identical check",
                                                variable=self.strict_identical_selection)
        self.strict_radio.grid(row=4, column=1)

        self.move_selection = tkinter.BooleanVar()
        # radio buttons to decide between stricter or looser image identical checks
        self.move_radio = tkinter.Checkbutton(master, text="Move files instead of copy", variable=self.move_selection)
        self.move_radio.grid(row=5, column=1)

        self.output_box = tkinter.Label(master, text="Press start to begin process")
        self.output_box.grid(row=6, columnspan=2)

    # put source folder path in correct text box
    def set_source(self):
        self.source_input.delete(0, tkinter.END)
        self.source_input.insert(0, tkinter.filedialog.askdirectory())

    # put destination folder path in correct text box
    def set_destination(self):
        self.destination_input.delete(0, tkinter.END)
        self.destination_input.insert(0, tkinter.filedialog.askdirectory())

    # executes or stops process when action button is clicked
    def action(self):
        if self.is_process_running:
            self.start_button["text"] = "Start"
            self.is_process_running = False
        else:
            self.start_button["text"] = "Stop"
            self.is_process_running = True

            sorting_thread = threading.Thread(target=self.start_photo_sort)
            sorting_thread.start()

    def start_photo_sort(self):

        source_directory = self.source_input.get()
        destination_directory = self.destination_input.get()

        if destination_directory.startswith(source_directory):
            self.output_box["text"] = "Error: Destination directory can not be within the source directory"
            self.action()
            return

        # list of photo extensions worked with
        photo_extensions = (".jpg", ".png", ".jpeg", ".bmp", ".cr2")
        video_extensions = ('avi', 'mts', 'mwv', 'mwa', 'mpg', 'mp4')

        files_copied = 0
        files_renamed = 0
        identical_photos = 0
        undated_images = 0
        video_files = 0
        files_failed = 0

        log_path = os.path.join(os.getcwd(), "Photo Sorter log")

        log_start_time = "Process began at: " + str(datetime.datetime.now())
        log_text = ""

        global is_process_running
        self.output_box["text"] = "Copying in progress"

        # recursively go through source directory and obtain each file
        for rootdir, dirs, filenames in os.walk(source_directory):
            for f in filenames:
                # only copy if file is a photo
                if f.lower().endswith(photo_extensions):

                    try:
                        full_path = os.path.join(rootdir, f)
                        self.output_box["text"] = "# files processed: %d \nCurrently processing: %s" % (
                        files_copied, full_path)
                        photo_info = PictureInformation(full_path)

                        if photo_info.has_date:
                            final_path = os.path.join(destination_directory,
                                                      str(photo_info.datetime_taken.year),
                                                      str(photo_info.datetime_taken.strftime("%B")),
                                                      str(photo_info.datetime_taken.strftime("%B") + "_" + str(
                                                          photo_info.datetime_taken.day)))
                        else:
                            undated_images += 1
                            final_path = os.path.join(destination_directory, "Undated")

                        # create directory for the file
                        os.makedirs(final_path, exist_ok=True)

                        # copy file
                        try:
                            result, photo_name = self.check_identical_and_copy_file(photo_info, final_path)
                            log_text += "Source: " + full_path + "\nDestination:" + photo_name
                        except OSError:
                            with open(log_path, 'w') as log_file:
                                log_file.write(log_start_time + "\n")
                                log_file.write("Process ended: " + str(datetime.datetime.now()) + "\n")
                                log_file.write("An error has occured: the destination may be out of storage\n")
                                log_file.write("******************************\n")
                                log_file.write(log_text)
                            self.action()
                            self.output_box["text"] = "An error has occurred: destination is out of space"

                            return

                        # log results
                        if result == IDENTICAL:
                            log_text += " IDENTICAL, DID NOT COPY\n\n"
                            identical_photos += 1
                        elif result == IDENTICAL_NAME:
                            log_text += "\nRENAMED\n\n"
                            files_renamed += 1
                            files_copied += 1
                        elif result == DIFFERENT:
                            log_text += "\n\n"
                            files_copied += 1
                    except OSError:
                        log_text += "An error as occurred with ths file: " + os.path.join(rootdir, f) + "\n\n"
                        files_failed += 1
                elif f.lower().endswith(video_extensions):
                    try:
                        os.makedirs(os.path.join(destination_directory, "Videos"), exist_ok=True)
                        full_path = os.path.join(rootdir, f)
                        final_path = os.path.join(destination_directory, "Videos", f)
                        name_base, name_extension = os.path.splitext(f)

                        if Path(final_path).is_file():

                            if os.path.getsize(full_path) != os.path.getsize(final_path):
                                name_index = 1
                                while Path(final_path).is_file():
                                    final_path = os.path.join(destination_directory, "Videos",
                                                              name_base + "(" + str(name_index) + ")" + name_extension)
                                    name_index += 1
                                video_files += 1
                                log_text += "Source: " + full_path + "\nDestination:" + final_path + "\nVIDEO FILE\n\n"

                                if self.move_selection:
                                    shutil.move(full_path, final_path)
                                else:
                                    shutil.copy(full_path, final_path)
                            else:
                                identical_photos += 1
                        else:
                            video_files += 1
                            log_text += "Source: " + full_path + "\nDestination:" + final_path + "\nVIDEO FILE\n\n"
                            if self.move_selection:
                                shutil.move(full_path, final_path)
                            else:
                                shutil.copy(full_path, final_path)

                    except OSError:
                        log_text += "An error as occurred with this file: " + os.path.join(rootdir, f) + "\n\n"
                        files_failed += 1

                # if user has pressed stop button stop the process
                if not self.is_process_running:
                    results_stats = "Copying stopped!\nPhotos copied: " + str(files_copied) \
                                    + "\nPhotos renamed: " + str(files_renamed) \
                                    + "\nIdentical photos found: " + str(identical_photos) \
                                    + "\nUndated photos: " + str(undated_images) \
                                    + "\nVideo files: " + str(video_files) \
                                    + "\nFiles failed: " + str(files_failed)

                    with open(log_path, 'w') as log_file:
                        log_file.write(log_start_time + "\n")
                        log_file.write("Process ended: " + str(datetime.datetime.now()) + "\n")
                        log_file.write(results_stats + "\n")
                        log_file.write("************************************\n")
                        log_file.write(log_text)

                    self.output_box["text"] = results_stats + "\nResults log can be found at " + log_path

                    self.start_button["text"] = "Start"
                    self.is_process_running = False

                    return

        results_stats = "Copying done!\nPhotos copied: " + str(files_copied) \
                        + "\nPhotos renamed: " + str(files_renamed) \
                        + "\nIdentical photos found: " + str(identical_photos) \
                        + "\nUndated photos: " + str(undated_images) \
                        + "\nVideo files: " + str(video_files) \
                        + "\nFiles failed: " + str(files_failed)
        with open(log_path, 'w') as log_file:
            log_file.write(log_start_time + "\n")
            log_file.write("Process ended: " + str(datetime.datetime.now()) + "\n")
            log_file.write(results_stats + "\n")
            log_file.write("************************************\n")
            log_file.write(log_text)

        # set process running to false
        self.output_box["text"] = results_stats + "\nResults log can be found at " + log_path
        #change button back to default
        self.action()

    # copies file photo1 to given directory from each date

    def compare_photo_in_directory(self, photo1, date_directory):

        final_path = os.path.join(date_directory, photo1.name)

        if Path(final_path).is_file():
            # name is identical
            if photo1.size == os.path.getsize(final_path):
                # size is identical

                if self.strict_identical_selection:
                    photo2 = PictureInformation(final_path)

                    if photo1.datetime_taken != photo2.datetime_taken:
                        # same name different file
                        return IDENTICAL_NAME
                    else:
                        return IDENTICAL
                else:
                    return IDENTICAL
            else:
                return IDENTICAL_NAME
        else:
            return DIFFERENT

    def check_identical_and_copy_file(self, photo1, date_directory):
        # check if file exists already
        is_identical = self.compare_photo_in_directory(photo1, date_directory)
        final_name = ""
        if is_identical == IDENTICAL:
            # if two files are identical do not copy
            return is_identical, ""
        elif is_identical == IDENTICAL_NAME:
            # if two files have the same name but are different then rename
            # copy file over
            name_index = 1
            name_base, name_extension = os.path.splitext(photo1.name)
            final_name = os.path.join(date_directory, name_base + "(" + str(name_index) + ")" + name_extension)
            while Path(final_name).is_file():
                name_index += 1
                final_name = os.path.join(date_directory, name_base + "(" + str(name_index) + ")" + name_extension)

            if self.move_selection:
                shutil.move(photo1.path, final_name)
            else:
                shutil.copy(photo1.path, final_name)

        elif is_identical == DIFFERENT:
            # files are not identical in any way so just copy over
            final_name = os.path.join(date_directory, photo1.name)

            if self.move_selection:
                shutil.move(photo1.path, final_name)
            else:
                shutil.copy(photo1.path, final_name)

        return is_identical, final_name

root = tkinter.Tk()
my_gui = MainWindow(root)
root.mainloop()