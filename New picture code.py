import tkinter
from tkinter import filedialog
import os
import exifread
import datetime
import shutil
from pathlib import Path


class PictureInformation:
    def __init__(self, f):

        self.path = f
        self.has_date = True
        t_format = '%Y:%m:%d %H:%M:%S'

        # open file
        photo = open(self.path, 'rb')
        photo_tags = exifread.process_file(photo)
        photo.close()

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

        self.selection_var = tkinter.BooleanVar()
        # radio buttons to decide between stricter or looser image identical checks
        self.strict_radio = tkinter.Checkbutton(master, text="Strict identical check", variable=self.selection_var)
        self.strict_radio.grid(row=4, column=1)

        self.output_box = tkinter.Label(master, text="Press start to begin process")
        self.output_box.grid(row=5, columnspan=2)

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
            self.start_photo_sort()

    def start_photo_sort(self):
        # TODO:catch error related with opening files
        source_directory = self.source_input.get()
        destination_directory = self.destination_input.get()

        if destination_directory.startswith(source_directory):
            # TODO: make a popup
            print("Destination directory can not be within the source directory")
            self.action()
            return

        # list of photo extensions worked with
        photoextensions = (".jpg", ".png", ".jpeg", ".bmp", ".cr2")

        files_copied = 0
        files_renamed = 0
        identical_photos = 0
        undated_images = 0

        global is_process_running
        self.output_box["text"] = "Copying in progress"

        # recursively go through source directory and obtain each file
        for rootdir, dirs, filenames in os.walk(source_directory):
            for f in filenames:
                # only copy if file is a photo
                if f.lower().endswith(photoextensions):

                    full_path = os.path.join(rootdir, f)
                    photo_info = PictureInformation(full_path)

                    # TODO: if date folder does not exist, create it
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
                    result = self.check_identical_and_copy_file(photo_info, final_path)

                    # log results
                    if result == IDENTICAL:
                        identical_photos += 1
                    elif result == IDENTICAL_NAME:
                        files_renamed += 1
                        files_copied += 1
                    elif result == DIFFERENT:
                        files_copied += 1
            # if user has pressed stop button stop the process
            if not self.is_process_running:
                break

        results_stats = "Copying done!\nPhotos copied: " + str(files_copied) \
                        + "\nPhotos renamed: " + str(files_renamed) \
                        + "\nIdentical photos found: " + str(identical_photos) \
                        + "\nUndated photos: " + str(undated_images)

        # set process running to false
        self.output_box["text"] = results_stats
        #change button back to default
        self.action()

    # copies file f to given directory dir *********************************

    def compare_photo_in_directory(self, photo1, date_directory):

        final_path = os.path.join(date_directory, photo1.name)

        if Path(final_path).is_file():
            # name is identical
            if photo1.size == os.path.getsize(final_path):
                # size is identical

                if self.selection_var:
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
        if is_identical == IDENTICAL:
            # if two files are identical do not copy
            return is_identical
        elif is_identical == IDENTICAL_NAME:
            # if two files have the same name but are different then rename
            # copy file over
            name_index = 1
            name_base, name_extension = os.path.splitext(photo1.name)
            new_name = os.path.join(date_directory, name_base + "(" + str(name_index) + ")" + name_extension)
            while Path(new_name).is_file():
                name_index += 1
                new_name = os.path.join(date_directory, name_base + "(" + str(name_index) + ")" + name_extension)

            shutil.copy(photo1.path, new_name)

        elif is_identical == DIFFERENT:
            # files are not identical in any way so just copy over
            shutil.copy(photo1.path, os.path.join(date_directory, photo1.name))

        return is_identical


root = tkinter.Tk()
my_gui = MainWindow(root)
root.mainloop()
